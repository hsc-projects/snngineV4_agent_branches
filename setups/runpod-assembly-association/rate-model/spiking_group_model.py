"""
spiking_group_model.py

Model B of round 4 (rate-model-task.md): a REDUCED SPIKING NETWORK of the assembly-association network.
It keeps what the smooth rate models lost, the individual spikes and their synchrony, at a cost far
below the GPU runs: the engine's Izhikevich neurons (snn_simulation.cu, update_N_state_), the engine's
input clamp, delays, gains and weights (assoc_engine.py), connectivity drawn with the rule of
rewire_by_distance, the gated plasticity of assoc_plasticity.py (rule "both"), the activity measure and
fields of assoc_fields.py, and the protocol of assoc_protocol.py, but with fewer synapses per neuron
(`syn_scale`) and optionally fewer neurons per location group (`neuron_scale`), run with numpy.

REDUCTION (derivations; test_spiking_group_model.py checks each against the engine's code)
  * synapses per neuron S' = round(syn_scale * S). Each presynaptic spike delivers S' instead of S
    synapses, each with its weight multiplied by S_type / S'_type (E->E 1600 / S'_ee, E->I 400 / S'_ei,
    I->E 2000 / S'), so that the expected summed input of a postsynaptic neuron per presynaptic spike
    volley is unchanged: n_pre * S_type * P(group) * w / n_post = (n_pre * S'_type * P(group)) * (w S_type /
    S'_type) / n_post, whatever the neuron counts. The plasticity bounds act on the normalized weight and
    are not scaled; the learned change per spike summed over a neuron's outgoing synapses is unchanged,
    because the weight factor 1 / syn_scale multiplies the engine weight, not the normalized one.
  * intra-group excitatory synapses keep the engine's normalization (weight = w_intra_ee_total / in-degree
    of the postsynaptic neuron, assoc_engine.typed_weights), so a whole group's volley delivers 40 * gain
    to each of its members however many synapses there are; they are not scaled again.
  * neurons per group n' = neuron_scale * n (multinomial draw as in the full network); injected neurons
    k' = round(k * neuron_scale), so the injected fraction of the group and the injected group drive per
    neuron (k' * 20 / n'_E) are unchanged. The release of C2 per spike is divided by neuron_scale, since
    the group has that many times fewer spikes.
  * not reduced: delays (D from the full network's N), grid, lambda, gains, window, protocol, fields.
Free parameters (at most three, named; the defaults are 1, i.e. the derived values): `w_inter_scale`
(common factor on the engine weight of the plastic synapses E->E between groups), `learn_scale` (common
factor on a_pre, a_plus and a_minus), `w_inh_scale` (factor on I->E). See the report for which were used.

Requires numpy (see the .venv in this folder). The spiking code (torch, CUDA) is not imported.
"""

from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Tuple

import numpy as np

from rate_model import (DERIVED, Spec, ChemicalFieldLattice, gate, path_groups, pick_pairs, group_distances,
                        lattice_coords, delay_count)

# KIND_EE: E -> E outside assemblies (between groups, or within a non-assembly group: assoc_engine.inter_ee_mask);
# KIND_EE_INTRA: within an assembly; KIND_IE: I -> E within a group, KIND_IE_INTER between groups (gain_ie_inter)
KIND_EE, KIND_EE_INTRA, KIND_EI, KIND_IE, KIND_EI_INTER, KIND_II, KIND_IE_INTER = 0, 1, 2, 3, 4, 5, 6
PLASTIC_LUT = np.array([True, False, True, False, True, False, False])   # KIND_II: only in exported engine networks (round 6)
W_LO, W_HI = 0.05, 1.0


@dataclass
class SpikeSpec(Spec):
    """Spec of the rate model (derived values of the passing protocol) plus the reduction and its options."""
    neuron_scale: float = 1.0       # neurons per group relative to the full network (58.3)
    syn_scale: float = 0.125        # synapses per neuron relative to S = 2000
    w_inter_scale: float = 1.0      # free parameter 1
    learn_scale: float = 1.0        # free parameter 2
    w_inh_scale: float = 1.0        # free parameter 3
    ei_inter_scale: float = 1.0     # factor on the engine weight of E->I synapses between groups (calibration option)
    runaway_frac: float = 0.5       # assoc_protocol runaway stop (session69a-stage2.json runaway_frac)
    delay_offset: int = 0           # round 5 diagnostic: extra steps between a spike's delivery bucket and its arrival (0: as modelled)
    exc_r: Optional[float] = None   # round 5 diagnostic: fixed r of the excitatory neurons
    inh_r: Optional[float] = None   # round 5 diagnostic: fixed r of the inhibitory neurons (None: uniform per neuron, default_init)
    export_dir: Optional[str] = None  # round 6: load the engine's network exported by round6_export_engine.py (seed unused)
    # round 6: inhibitory neurons with inhibitory targets (I -> I, normalized weight w_ie, gain only), a fraction
    # frac_I_to_I of their synapses, as measured in networks built by the engine before its fix of 2026-10-30
    # (transposed synapse table, round6-report.md). 0 is the configured composition (rounds 4 and 5, the fixed engine).
    frac_I_to_I: float = 0.0
    # sparse task S6 (assoc_engine.set_gains): E -> I and I -> E synapses between groups additionally times these;
    # exported networks only (round 6 step 4)
    gain_ei_inter: float = 1.0
    gain_ie_inter: float = 1.0

    @property
    def S_red(self) -> int:
        return max(2, int(round(self.syn_scale * self.S)))

    @property
    def S_ee(self) -> int:
        return int(round(self.S_red * (1.0 - self.frac_E_to_I)))

    @property
    def S_ei(self) -> int:
        return self.S_red - self.S_ee

    @property
    def S_ii(self) -> int:
        return int(round(self.S_red * self.frac_I_to_I))

    @property
    def N_red(self) -> int:
        return int(round(self.N * self.neuron_scale))

    @property
    def k_red(self) -> int:
        return max(1, int(round(self.k_inject * self.neuron_scale)))


# ------------------------------------------------------------------------------------------------------
# Izhikevich neurons (snn_simulation.cu, update_N_state_, lines 79-86 of the model branch "model == 0")
# ------------------------------------------------------------------------------------------------------
F32 = np.float32


def neuron_parameters(rng: np.random.Generator, is_exc: np.ndarray, inh_r: Optional[float] = None,
                      exc_r: Optional[float] = None):
    """a, b, c, d per neuron: izhikevich_presets.py default_init (r uniform per neuron, masks by type)."""
    r = rng.random(len(is_exc)).astype(F32)
    if inh_r is not None:
        r[~is_exc] = F32(inh_r)
    if exc_r is not None:
        r[is_exc] = F32(exc_r)
    inh = (~is_exc).astype(F32)
    exc = is_exc.astype(F32)
    a = F32(0.02) + F32(0.08) * r * inh
    b = F32(0.2) + F32(0.05) * (F32(1.0) - r) * inh
    c = F32(-65.0) + F32(15.0) * (r ** 2) * exc
    d = F32(2.0) * inh + (F32(8.0) - F32(6.0) * (r ** 2)) * exc
    return a.astype(F32), b.astype(F32), c.astype(F32), d.astype(F32)


class Izhikevich:
    """Vectorized engine update in float32: if v > 30 at the start of a step the neuron fires and resets
    (v = c, u += d); then two half-steps of v and one step of u; `i` is the step's input current."""

    def __init__(self, a, b, c, d):
        self.a, self.b, self.c, self.d = a, b, c, d
        n = len(a)
        self.v = np.full(n, -65.0, dtype=F32)
        self.u = (self.b * self.v).astype(F32)
        self._t = np.empty(n, dtype=F32)
        self._t2 = np.empty(n, dtype=F32)

    def step(self, i: np.ndarray) -> np.ndarray:
        """Advance one step with input `i` (float32); returns the indices of the neurons that fired."""
        v, u, t, t2 = self.v, self.u, self._t, self._t2
        fired = np.flatnonzero(v > F32(30.0))
        if len(fired):
            v[fired] = self.c[fired]
            u[fired] += self.d[fired]
        for _ in range(2):
            np.multiply(v, F32(0.04), out=t)
            t *= v
            np.multiply(v, F32(5.0), out=t2)
            t += t2
            t += F32(140.0)
            t -= u
            t += i
            t *= F32(0.5)
            v += t
        np.multiply(self.b, v, out=t)
        t -= u
        t *= self.a
        u += t
        return fired

    def state(self):
        return self.v.copy(), self.u.copy()

    def set_state(self, v, u):
        self.v[:] = v
        self.u[:] = u


# ------------------------------------------------------------------------------------------------------
# Network: sampled neurons and synapses
# ------------------------------------------------------------------------------------------------------

def _cdf_flat(kern: np.ndarray, n_target: np.ndarray) -> np.ndarray:
    """assoc_engine.rewire_by_distance: prob = kern * counts, row-normalized, cumulative; the row index is added
    so that one searchsorted over the flattened array draws a group for every synapse."""
    prob = kern * n_target[None, :].astype(np.float64)
    prob = prob / np.maximum(prob.sum(axis=1, keepdims=True), 1e-300)
    cdf = np.cumsum(prob, axis=1)
    cdf[:, -1] = 1.0
    G = kern.shape[0]
    return (cdf + np.arange(G, dtype=np.float64)[:, None]).reshape(-1)


def draw_targets(rng: np.random.Generator, pre_group: np.ndarray, flat: np.ndarray, G: int,
                 starts: np.ndarray, counts: np.ndarray) -> np.ndarray:
    """Target neuron per synapse: group drawn from the row of its presynaptic group, neuron uniform within the
    group (members of the target type), as rewire_by_distance."""
    u = rng.random(pre_group.shape) * (1.0 - 1e-12)
    k = np.searchsorted(flat, pre_group.astype(np.float64) + u, side="right")
    g_new = np.clip(k - pre_group * G, 0, G - 1)
    u2 = rng.random(pre_group.shape)
    cnt = np.maximum(counts[g_new], 1)
    j = starts[g_new] + np.minimum((u2 * cnt).astype(np.int64), cnt - 1)
    return j


class SpikingNetwork:
    """One realization (seed): neuron counts per group, neuron parameters, synapses, weights; state and plasticity."""

    def __init__(self, spec: SpikeSpec, seed: int = 0):
        self.spec = s = spec
        self.seed = int(seed)
        rng = np.random.default_rng(self.seed)
        self.G = G = s.G
        self.dist = group_distances(s.grid_dim)
        self.coords = lattice_coords(s.grid_dim)
        self.D = s.D
        self.rng_inj = np.random.default_rng(self.seed + 7919)
        self._inj_cache: Dict[int, np.ndarray] = {}
        self.capture_raw = False                 # round 6: keep the unclamped summed input of the last step
        self.spike_acc = None                    # optional (N,) spike counter, incremented by run() (AssocRun.spike_acc)
        self.input_acc = None                    # optional (N,) summed unclamped synaptic input per step (AssocRun.input_acc)
        self.lo2 = self.hi2 = None               # per-synapse plasticity bounds (N, S), only for heavy-tailed weights
        if s.export_dir:
            self._load_export(s.export_dir)
            N = self.N
        else:
            if s.gain_ei_inter != 1.0 or s.gain_ie_inter != 1.0:
                raise ValueError("gain_ei_inter / gain_ie_inter are supported on exported networks only")
            N = self._build_own(rng)
        self.lo_f = None if self.lo2 is None else self.lo2.reshape(-1)
        self.hi_f = None if self.hi2 is None else self.hi2.reshape(-1)
        # --- fields (cell lattice, as in round 3)
        self.c1 = ChemicalFieldLattice(s.grid_dim, s.c1["k"], s.c1["decay"], vox_per_cell=s.vox_per_cell)
        self.c2 = ChemicalFieldLattice(s.grid_dim, s.c2["k"], s.c2["decay"], vox_per_cell=s.vox_per_cell)
        self.release_scale = 1.0 / (N / float(s.N))
        self.fast_decay = math.exp(-1.0 / s.tau_fast) if s.tau_fast > 0 else 0.0
        self._rev = None
        self.reset_plasticity()
        self.reset_dynamics()

    def _build_own(self, rng: np.random.Generator) -> int:
        """Neurons and synapses drawn by the model (rounds 4 and 5)."""
        s, G = self.spec, self.G
        # --- neurons: excitatory first (sorted by group), then inhibitory; counts per group multinomial
        N = s.N_red
        nE_tot = int(round(s.exc_frac * N))
        nI_tot = N - nE_tot
        self.nE = rng.multinomial(nE_tot, np.full(G, 1.0 / G)).astype(np.int64)
        self.nI = rng.multinomial(nI_tot, np.full(G, 1.0 / G)).astype(np.int64)
        self.N, self.nE_tot, self.nI_tot = N, nE_tot, nI_tot
        self.grp = np.concatenate([np.repeat(np.arange(G), self.nE), np.repeat(np.arange(G), self.nI)]).astype(np.int64)
        self.isE = np.arange(N) < nE_tot
        self.e_start = np.cumsum(self.nE) - self.nE
        self.i_start = nE_tot + np.cumsum(self.nI) - self.nI
        a, b, c, d = neuron_parameters(rng, self.isE, s.inh_r, s.exc_r)
        self.neurons = Izhikevich(a, b, c, d)
        # engine warm-up: 5 steps without input; the post-warm-up state is the state every reset returns to
        zero = np.zeros(N, dtype=F32)
        for _ in range(5):
            self.neurons.step(zero)
        self.init_state = self.neurons.state()
        # --- synapses
        self._build_synapses(rng)
        return N

    def _load_export(self, path: str):
        """
        Round 6: the engine's own network, exported by round6_export_engine.py (same neuron order as the engine).
        Neurons: the engine's a, b, c, d and post-warm-up v, u. Synapses: the engine's targets, delay buckets and
        normalized weights; the engine weight is the normalized one times the gain of the synapse's kind (as
        _build_synapses with syn_scale 1), checked against the exported engine weights.
        """
        s, G = self.spec, self.G
        if abs(s.syn_scale - 1.0) > 1e-9 or abs(s.neuron_scale - 1.0) > 1e-9:
            raise ValueError("an exported network is used at full size (syn_scale = neuron_scale = 1)")
        meta = json.loads(open(os.path.join(path, "meta.json")).read())
        ld = lambda k: np.load(os.path.join(path, f"{k}.npy"))
        if int(meta["G"]) != G or int(meta["D"]) != self.D:
            raise ValueError(f"export has G {meta['G']}, D {meta['D']}; spec has G {G}, D {self.D}")
        # the engine numbers its location groups in another order: relabel every engine group to the model's
        # lattice index x * dim^2 + y * dim + z of its grid cell (engine_to_model; pairs are mapped with it)
        gc = ld("group_cell").astype(np.int64)
        dim = s.grid_dim
        self.engine_to_model = gc[:, 0] * dim * dim + gc[:, 1] * dim + gc[:, 2]
        if np.unique(self.engine_to_model).size != G:
            raise ValueError("engine group cells do not cover the lattice once each")
        types = ld("types")
        grp = self.engine_to_model[ld("groups").astype(np.int64)]
        if (ld("model_flag") != 0).any():
            raise ValueError("neurons with model flag != 0 (non-Izhikevich branch of update_N_state_)")
        N = len(types)
        self.N = N
        self.isE = types == int(meta.get("type_exc", 2))
        self.grp = grp
        self.nE = np.bincount(grp[self.isE], minlength=G).astype(np.int64)
        self.nI = np.bincount(grp[~self.isE], minlength=G).astype(np.int64)
        self.nE_tot, self.nI_tot = int(self.nE.sum()), int(self.nI.sum())
        abcd, vu = ld("abcd"), ld("init_vu")
        self.neurons = Izhikevich(*(abcd[:, j].astype(F32).copy() for j in range(4)))
        self.init_state = (vu[:, 0].astype(F32).copy(), vu[:, 1].astype(F32).copy())
        self.neurons.set_state(*self.init_state)
        post = ld("post")
        if (post < 0).any():
            raise ValueError("deleted synapses (-1) are not supported by the model")
        self.S = S = post.shape[1]
        self.post = np.ascontiguousarray(post.astype(np.int32))
        bnd = ld("bnd").astype(np.int32)
        self.bnd = np.ascontiguousarray(bnd)
        delay = np.zeros(post.shape, dtype=np.int8)
        cols = np.arange(S, dtype=np.int32)[None, :]
        for r in range(1, self.D + 1):
            delay += (cols >= bnd[:, r:r + 1]).astype(np.int8)
        self.delay = delay
        # sparse assemblies (round 6 step 4): which groups are assemblies, in the model's numbering (all without a layout)
        self.is_asm = np.ones(G, dtype=bool)
        if meta.get("is_asm") is not None:
            self.is_asm[self.engine_to_model] = np.asarray(meta["is_asm"], dtype=bool)
        same = grp[self.post] == grp[:, None]
        postE = self.isE[self.post]
        preE = self.isE[:, None]
        intra_asm = same & self.is_asm[grp][:, None]
        kind = np.full(post.shape, KIND_IE_INTER, dtype=np.int8)
        kind[~preE & postE & same] = KIND_IE
        kind[preE & postE & intra_asm] = KIND_EE_INTRA
        kind[preE & postE & ~intra_asm] = KIND_EE
        kind[preE & ~postE & same] = KIND_EI
        kind[preE & ~postE & ~same] = KIND_EI_INTER
        kind[~preE & ~postE] = KIND_II          # the engine builds inhibitory -> inhibitory synapses too
        self.kind = kind
        self.wp0 = np.ascontiguousarray(ld("w_norm").astype(F32))
        self.wp = self.wp0.copy()
        self.F = np.zeros((N, S), dtype=F32)
        self.touched = np.zeros((N, S), dtype=bool)
        # heavy-tailed initial weights (S2, S3: weights.inter_ee): the bounds apply to plastic changes only, so each
        # such synapse's bounds widen to include its initial weight (assoc_protocol.AssocRun.new_plasticity)
        if (meta.get("params", {}).get("weights") or {}).get("inter_ee") is not None:
            m = kind == KIND_EE
            self.lo2 = np.where(m, np.minimum(F32(W_LO), self.wp0), F32(W_LO)).astype(F32)
            self.hi2 = np.where(m, np.maximum(F32(W_HI), self.wp0), F32(W_HI)).astype(F32)
        self.gm = np.array([
            s.gain * s.gain_ee_inter * s.w_inter_scale,
            s.gain,
            s.gain * s.gain_ei,
            s.gain * s.gain_ie * s.w_inh_scale,
            s.gain * s.gain_ei * s.gain_ei_inter * s.ei_inter_scale,
            s.gain,                              # I -> I: set_gains applies neither gain_ei nor gain_ie
            s.gain * s.gain_ie * s.gain_ie_inter * s.w_inh_scale], dtype=F32)
        # the engine weights must equal normalized weight x kind gain at the derived gains (all factors 1)
        if s.w_inter_scale == 1.0 and s.w_inh_scale == 1.0 and s.ei_inter_scale == 1.0:
            dev = float(np.abs(ld("w_engine") - self.wp0 * self.gm[kind]).max())
            if dev > 1e-5:
                raise ValueError(f"engine weights differ from normalized x kind gain by up to {dev}")
        self.kind_f, self.post_f = self.kind.reshape(-1), self.post.reshape(-1)
        self.delay_f = self.delay.reshape(-1)
        self.wp_f, self.F_f = self.wp.reshape(-1), self.F.reshape(-1)
        self.touched_f = self.touched.reshape(-1)
        self.export_meta = meta

    def set_injection(self, g: int, idx: np.ndarray):
        """Use these neurons as group g's injected neurons (round 6: the engine's choice, from the export)."""
        self._inj_cache[int(g)] = np.sort(np.asarray(idx, dtype=np.int64))

    # -- construction ---------------------------------------------------------------------------------
    def _build_synapses(self, rng: np.random.Generator):
        s, G, N = self.spec, self.G, self.N
        S, S_ee, S_ei = s.S_red, s.S_ee, s.S_ei
        self.S = S
        kern = np.exp(-self.dist / float(s.lam))
        flat_E = _cdf_flat(kern, self.nE)
        flat_I = _cdf_flat(kern, self.nI)
        eN, iN = self.nE_tot, self.nI_tot
        post = np.empty((N, S), dtype=np.int32)
        kind = np.empty((N, S), dtype=np.int8)
        pg_E = self.grp[:eN]
        pg_I = self.grp[eN:]
        if S_ee > 0:
            pe = np.broadcast_to(pg_E[:, None], (eN, S_ee))
            t = draw_targets(rng, pe, flat_E, G, self.e_start, self.nE)
            self._fix_autapses(rng, t, np.arange(eN)[:, None], pe, flat_E, self.e_start, self.nE)
            post[:eN, :S_ee] = t
            kind[:eN, :S_ee] = np.where(self.grp[t] == pg_E[:, None], KIND_EE_INTRA, KIND_EE)
        if S_ei > 0:
            pe = np.broadcast_to(pg_E[:, None], (eN, S_ei))
            t = draw_targets(rng, pe, flat_I, G, self.i_start, self.nI)
            post[:eN, S_ee:] = t
            kind[:eN, S_ee:] = np.where(self.grp[t] == pg_E[:, None], KIND_EI, KIND_EI_INTER)
        S_ii = s.S_ii
        S_ie = S - S_ii
        pi = np.broadcast_to(pg_I[:, None], (iN, S_ie))
        t = draw_targets(rng, pi, flat_E, G, self.e_start, self.nE)
        post[eN:, :S_ie] = t
        kind[eN:, :S_ie] = KIND_IE
        if S_ii > 0:
            pi = np.broadcast_to(pg_I[:, None], (iN, S_ii))
            t = draw_targets(rng, pi, flat_I, G, self.i_start, self.nI)
            self._fix_autapses(rng, t, (eN + np.arange(iN))[:, None], pi, flat_I, self.i_start, self.nI)
            post[eN:, S_ie:] = t
            kind[eN:, S_ie:] = KIND_II
        # delays: round((D - 1) * d / d_max) (assoc_engine.rewire_by_distance); synapses sorted by delay per neuron
        dmax = max(float(self.dist.max()), 1e-9)
        delay = np.rint((self.D - 1) * self.dist[self.grp[:, None], self.grp[post]] / dmax).astype(np.int8)
        order = np.argsort(delay, axis=1, kind="stable")
        self.post = np.take_along_axis(post, order, axis=1)
        self.kind = np.take_along_axis(kind, order, axis=1)
        delay = np.take_along_axis(delay, order, axis=1)
        self.delay = delay
        self.bnd = np.stack([(delay < r).sum(axis=1) for r in range(self.D + 1)], axis=1).astype(np.int32)
        # weights (normalized): w_ee inter, w_intra_ee_total / in-degree intra, built E->I 0.45, built I->E -0.44
        wp = np.empty((N, S), dtype=F32)
        wp[self.kind == KIND_EE] = s.w_ee
        wp[(self.kind == KIND_EI) | (self.kind == KIND_EI_INTER)] = s.w_ei
        wp[(self.kind == KIND_IE) | (self.kind == KIND_II)] = s.w_ie
        intra = self.kind == KIND_EE_INTRA
        indeg = np.bincount(self.post[intra].ravel(), minlength=N).astype(np.float64)
        self.intra_indeg = indeg
        wp[intra] = (s.w_intra_ee_total / indeg[self.post[intra]]).astype(F32)
        self.wp0 = wp
        self.wp = wp.copy()
        self.F = np.zeros((N, S), dtype=F32)                # fast part, true value = F * m
        self.touched = np.zeros((N, S), dtype=bool)
        # engine weight = normalized weight * gain map * (S_type / S'_type): engine gain rules (assoc_engine.set_gains)
        self.gm = np.array([
            s.gain * s.gain_ee_inter * (s.S * (1.0 - s.frac_E_to_I) / max(S_ee, 1)) * s.w_inter_scale,
            s.gain,
            s.gain * s.gain_ei * (s.S * s.frac_E_to_I / max(S_ei, 1)),
            s.gain * s.gain_ie * (s.S * s.frac_I_to_E * (1.0 - s.frac_I_to_I) / max(S_ie, 1)) * s.w_inh_scale,
            s.gain * s.gain_ei * (s.S * s.frac_E_to_I / max(S_ei, 1)) * s.ei_inter_scale,
            s.gain * (s.S * s.frac_I_to_I / max(S_ii, 1)),
            s.gain * s.gain_ie * (s.S * s.frac_I_to_E * (1.0 - s.frac_I_to_I) / max(S_ie, 1)) * s.w_inh_scale],
            dtype=F32)                           # the own construction labels every I -> E synapse KIND_IE
        self.kind_f, self.post_f = self.kind.reshape(-1), self.post.reshape(-1)
        self.delay_f = self.delay.reshape(-1)
        self.wp_f, self.F_f = self.wp.reshape(-1), self.F.reshape(-1)
        self.touched_f = self.touched.reshape(-1)

    def _fix_autapses(self, rng, t, pre_idx, pre_group, flat, starts, counts, tries: int = 20):
        """No autapses (rewire_by_distance redraws them)."""
        for _ in range(tries):
            bad = t == pre_idx
            if not bad.any():
                return
            t[bad] = draw_targets(rng, pre_group[bad], flat, self.G, starts, counts)
        bad = t == pre_idx
        if bad.any():
            raise RuntimeError(f"{int(bad.sum())} autapses left")

    def reverse_index(self):
        """Incoming synapses per neuron (for the STDP potentiation): flat ids sorted by postsynaptic neuron."""
        if self._rev is None:
            order = np.argsort(self.post_f, kind="stable").astype(np.int64)
            ptr = np.zeros(self.N + 1, dtype=np.int64)
            np.cumsum(np.bincount(self.post_f, minlength=self.N), out=ptr[1:])
            self._rev = (order, ptr)
        return self._rev

    # -- state ---------------------------------------------------------------------------------------------
    def reset_plasticity(self):
        np.copyto(self.wp, self.wp0)
        self.F.fill(0.0)
        self.m = 1.0
        self.touched.fill(False)
        self._touch_ver = 0
        self._tid_cache, self._tid_key = None, -1
        self.c1.reset()
        self.c2.reset()

    def reset_dynamics(self):
        self.neurons.set_state(*self.init_state)
        self.I = np.zeros(self.N, dtype=F32)
        self.recent = [np.empty(0, dtype=np.int64) for _ in range(self.D + self.spec.delay_offset)]
        self.k = 0
        self.last = np.full(self.N, -10 ** 6, dtype=np.int64)         # plasticity: last spike step
        self.lastA = np.full(self.N, -10 ** 9, dtype=np.int64)        # activity window
        self.Acount = np.zeros(self.G, dtype=np.int64)
        self.fired_E_hist: List[np.ndarray] = []
        self.isF = np.zeros(self.N, dtype=bool)

    def reset_all(self):
        self.reset_plasticity()
        self.reset_dynamics()

    def inject_idx(self, g: int) -> np.ndarray:
        """k' excitatory neurons of group g (assoc_protocol.AssocRun.inject_idx, cached per group)."""
        if g not in self._inj_cache:
            members = np.arange(self.e_start[g], self.e_start[g] + self.nE[g])
            k = min(self.spec.k_red, len(members))
            self._inj_cache[g] = np.sort(self.rng_inj.choice(members, size=k, replace=False))
        return self._inj_cache[g]

    # -- weights -------------------------------------------------------------------------------------------
    def engine_weights(self, ids: np.ndarray, fmult: float) -> np.ndarray:
        """Engine weight of synapses `ids`: gain map * effective normalized weight; effective = clip(w_perm +
        w_fast, 0.05, 1) for plastic synapses, w_perm otherwise (GatedPlasticity.effective); fmult 0: w_perm only."""
        kd = self.kind_f[ids]
        w = self.wp_f[ids]
        if fmult != 0.0:
            w = w + self.F_f[ids] * F32(fmult * self.m)
        w = np.where(PLASTIC_LUT[kd], self._clip(w, ids), w)
        return w * self.gm[kd]

    def _clip(self, w: np.ndarray, ids: np.ndarray) -> np.ndarray:
        """Clip normalized weights of synapses `ids` to their plasticity bounds."""
        if self.hi_f is None:
            return np.clip(w, W_LO, W_HI)
        return np.clip(w, self.lo_f[ids], self.hi_f[ids])

    def _bound(self, ids: np.ndarray):
        """Upper bound of the soft-bounded changes (GatedPlasticity.bound) of synapses `ids`."""
        return F32(W_HI) if self.hi_f is None else self.hi_f[ids]

    def effective_normalized(self, ids: np.ndarray, fmult: float = 1.0) -> np.ndarray:
        w = self.wp_f[ids]
        if fmult != 0.0:
            w = w + self.F_f[ids] * F32(fmult * self.m)
        return self._clip(w, ids)

    # -- one step ---------------------------------------------------------------------------------------------
    def _deliver(self, fired: np.ndarray, fmult: float):
        """update_current_: synapses of neurons that fired `lag` steps ago whose delay is `lag` add their weight to
        the target's input for the next step. Returns (clamped float32 input, delivered ids, their lags)."""
        self.recent.insert(0, fired)
        self.recent.pop()
        pres, lags = [], []
        off = self.spec.delay_offset
        for lag, arr in enumerate(self.recent):
            if len(arr) and lag >= off:
                pres.append(arr)
                lags.append(np.full(len(arr), lag - off, dtype=np.int64))
        if not pres:
            return None, None, None
        pre = np.concatenate(pres) if len(pres) > 1 else pres[0]
        lag = np.concatenate(lags) if len(lags) > 1 else lags[0]
        lo = self.bnd[pre, lag]
        cnt = self.bnd[pre, lag + 1] - lo
        tot = int(cnt.sum())
        if tot == 0:
            return None, None, None
        base = pre.astype(np.int64) * self.S + lo
        csum = np.cumsum(cnt)
        ids = np.repeat(base - (csum - cnt), cnt) + np.arange(tot)
        w = self.engine_weights(ids, fmult)
        arr = np.bincount(self.post_f[ids], weights=w, minlength=self.N)
        if self.capture_raw:
            self.last_input_raw = arr.astype(F32)
        sp = self.spec
        if sp.i_min is not None or sp.i_max is not None:
            np.clip(arr, sp.i_min, sp.i_max, out=arr)
        return arr.astype(F32), ids, np.repeat(lag, cnt)

    def _activity_update(self, fired: np.ndarray, window: int):
        """GroupActivity.update: A_g = fraction of the group's excitatory neurons that fired in the last `window` steps."""
        k = self.k
        fe = fired[self.isE[fired]] if len(fired) else fired
        self.fired_E_hist.append(fe)
        if len(self.fired_E_hist) > window:
            old = self.fired_E_hist.pop(0)
            if len(old):
                alive = old[self.lastA[old] == k - window]
                if len(alive):
                    self.Acount -= np.bincount(self.grp[alive], minlength=self.G)
        if len(fe):
            new = fe[self.lastA[fe] <= k - window]
            if len(new):
                self.Acount += np.bincount(self.grp[new], minlength=self.G)
            self.lastA[fe] = k
        return self.Acount / np.maximum(self.nE, 1)

    def step(self, window: int, learn: bool, consolidate: bool, fmult: float, release1: bool, release2: bool,
             chem: bool, inj: Optional[np.ndarray], c2_uniform: Optional[float] = None):
        sp = self.spec
        fired = self.neurons.step(self.I)
        # time index of this step's spikes
        self.k += 1
        nxt, ids, lags = self._deliver(fired, fmult)
        if nxt is None and self.capture_raw:
            self.last_input_raw = np.zeros(self.N, dtype=F32)
        if self.spike_acc is not None and len(fired):
            self.spike_acc[fired] += 1.0
        if self.input_acc is not None and nxt is not None:
            self.input_acc += self.last_input_raw             # synaptic input only: before clamp and injection
        A = self._activity_update(fired, window)
        n_fired = len(fired)
        if chem and (release1 or release2 or self.c1.c.any() or self.c2.c.any()):
            spk = np.bincount(self.grp[fired], minlength=self.G).astype(np.float64) * self.release_scale if n_fired else np.zeros(self.G)
            if release1:
                self.c1.release(spk, sp.c1["gain"], sp.c1.get("saturation"))
            if release2:
                self.c2.release(spk, sp.c2["gain"], sp.c2.get("saturation"))
            self.c1.diffuse()
            self.c2.diffuse()
            if release2 and c2_uniform is not None:
                self.c2.c[:] = float(c2_uniform)
        if learn or consolidate:
            self._plasticity(fired, ids, lags, learn, consolidate)
        if n_fired:
            self.last[fired] = self.k
        self.I = nxt if nxt is not None else np.zeros(self.N, dtype=F32)
        if inj is not None:
            self.I[inj] += F32(sp.inject_current)
        return A, n_fired

    # -- plasticity (assoc_plasticity.GatedPlasticity.step) ---------------------------------------------------------
    def _gate_groups(self):
        s = self.spec
        g1 = gate(self.c1.flat(), s.theta1, s.soft1)
        return g1

    def _plasticity(self, fired, ids, lags, learn: bool, consolidate: bool):
        s = self.spec
        ls = s.learn_scale
        a_plus, a_minus, a_pre = s.a_plus * ls, s.a_minus * ls, s.a_pre * ls
        k, D, S = self.k, self.D, self.S
        g1grp = self._gate_groups()
        g1_trivial = bool((g1grp >= 1.0).all())
        if learn:
            m = self.m
            if s.plasticity_rule in ("stdp", "both"):
                u_ids, u_dw = [], []
                if len(fired):
                    order, ptr = self.reverse_index()
                    lo, hi = ptr[fired], ptr[fired + 1]
                    cnt = hi - lo
                    tot = int(cnt.sum())
                    if tot:
                        csum = np.cumsum(cnt)
                        sel = order[np.repeat(lo - (csum - cnt), cnt) + np.arange(tot)]
                        pre = sel // S
                        self.isF[fired] = True
                        lp = np.where(self.isF[pre], k, self.last[pre])
                        self.isF[fired] = False
                        dt = k - lp
                        ok = PLASTIC_LUT[self.kind_f[sel]] & (dt >= 0) & (dt <= 2 * D)
                        sel = sel[ok]
                        if len(sel):
                            w = self.effective_normalized(sel)
                            dw = a_plus * w * (self._bound(sel) - w)
                            if not g1_trivial:
                                dw = dw * g1grp[self.grp[self.post_f[sel]]]
                            u_ids.append(sel)
                            u_dw.append(dw)
                if ids is not None:
                    dly = lags
                    ok = (dly > 0) & PLASTIC_LUT[self.kind_f[ids]]
                    if ok.any():
                        sel, lg = ids[ok], dly[ok]
                        lastp = self.last[self.post_f[sel]]          # the post's last spike strictly before this step
                        t_fire = k - lg
                        ok2 = (lastp < t_fire) & (lastp >= t_fire - lg)
                        sel = sel[ok2]
                        if len(sel):
                            w = self.effective_normalized(sel)
                            dw = -a_minus * w * (self._bound(sel) - w)
                            if not g1_trivial:
                                dw = dw * g1grp[self.grp[self.post_f[sel]]]
                            u_ids.append(sel)
                            u_dw.append(dw)
                if u_ids:
                    all_ids = np.concatenate(u_ids)
                    all_dw = (np.concatenate(u_dw) / m).astype(F32)
                    np.add.at(self.F_f, all_ids, all_dw)
                    self.touched_f[all_ids] = True
                    self._touch_ver += 1
            if s.plasticity_rule in ("pre_c1", "both") and len(fired):
                fe = fired[self.isE[fired]]
                if len(fe):
                    kd = self.kind[fe]
                    pl = PLASTIC_LUT[kd]
                    if self.hi2 is None:
                        w = np.clip(self.wp[fe] + self.F[fe] * F32(m), W_LO, W_HI)
                        g = a_pre * w * (W_HI - w)
                    else:
                        w = np.clip(self.wp[fe] + self.F[fe] * F32(m), self.lo2[fe], self.hi2[fe])
                        g = a_pre * w * (self.hi2[fe] - w)
                    if not g1_trivial:
                        g = g * g1grp[self.grp[fe]][:, None] * g1grp[self.grp[self.post[fe]]]
                    self.F[fe] += np.where(pl, g / m, 0.0).astype(F32)
                    self.touched[fe] |= pl
                    self._touch_ver += 1
        if learn or consolidate:
            if consolidate:
                g12 = g1grp * gate(self.c2.flat(), s.theta2, s.soft2)
                if g12.any():
                    tid = self._touched_ids()
                    gp = g12[self.grp[self.post_f[tid]]]
                    on = gp > 0.0
                    if on.any():
                        tid, gp = tid[on], gp[on]
                        fast = self.F_f[tid] * F32(self.m)
                        moved = (s.kappa * gp).astype(F32) * fast
                        self.wp_f[tid] = self._clip(self.wp_f[tid] + moved, tid)
                        self.F_f[tid] = (fast - moved) / F32(self.m)
            self.m *= self.fast_decay

    def _touched_ids(self) -> np.ndarray:
        """Plastic synapses with a nonzero fast part (cached while no new learning)."""
        if self._tid_cache is None or self._tid_key != self._touch_ver:
            ids = np.flatnonzero(self.touched_f)
            self._tid_cache, self._tid_key = ids[PLASTIC_LUT[self.kind_f[ids]]], self._touch_ver
        return self._tid_cache

    # -- a phase of the protocol (AssocRun.run) ----------------------------------------------------------------------
    def run(self, steps: int, inject: List[np.ndarray] = (), inject_steps: Optional[int] = None, learn=False,
            consolidate=False, release1=False, release2=False, chem=True, fmult: float = 1.0,
            c2_uniform: Optional[float] = None) -> dict:
        """Step `steps` times; the neurons in `inject` get inject_current for the first `inject_steps` steps
        (added after each step, for the next one). Returns the per-group maximum of A_g over the phase, the
        spike count and the runaway record (more than runaway_frac * N spikes in one step stops the phase)."""
        s = self.spec
        inj_n = s.inject_steps if inject_steps is None else inject_steps
        inj_all = np.concatenate(inject) if len(inject) else None
        gmax = np.zeros(self.G)
        n_spikes = 0
        stopped = None
        limit = s.runaway_frac * self.N if s.runaway_frac else None
        steps_done = 0
        for i in range(steps):
            A, nf = self.step(s.window, learn, consolidate, fmult, release1, release2, chem,
                              inj_all if (inj_all is not None and i < inj_n) else None, c2_uniform)
            steps_done += 1
            np.maximum(gmax, A, out=gmax)
            n_spikes += nf
            if limit is not None and nf > limit:
                stopped = {"step": i, "spikes": nf, "fraction": nf / self.N}
                break
        self.steps_run = getattr(self, "steps_run", 0) + steps_done
        return {"gmax": gmax, "spikes": n_spikes, "stopped": stopped}


# ------------------------------------------------------------------------------------------------------
# Protocol (assoc_protocol.py: AssocRun.test, protocol_body), as in rate_model.run_pair_protocol
# ------------------------------------------------------------------------------------------------------

def run_test(net: SpikingNetwork, src: int, dst: int, mode: str, exclude: List[int]) -> dict:
    """Inject into src alone, everything frozen; B must reach A_g >= active within the window (AssocRun.test)."""
    s = net.spec
    net.reset_dynamics()
    res = net.run(s.test_window, inject=[net.inject_idx(src)], inject_steps=s.inject_steps, chem=False,
                  fmult=0.0 if mode == "perm" else 1.0)
    gmax = res["gmax"]
    outside = np.ones(net.G, dtype=bool)
    outside[[src, dst] + [g for g in exclude if g not in (src, dst)]] = False
    n_out = int((outside & (gmax >= s.active)).sum())
    return {"src_max": float(gmax[src]), "dst_max": float(gmax[dst]), "success": bool(gmax[dst] >= s.active),
            "n_active_outside": n_out, "n_above_inactive_outside": int((outside & (gmax > s.inactive)).sum()),
            "bounded": bool(res["stopped"] is None and n_out <= s.stray_limit),
            "spikes": res["spikes"], "runaway": res["stopped"]}


def run_round(net: SpikingNetwork, groups: List[int], learn: bool, consolidate: bool, release1: bool,
              release2: bool, c2_uniform: Optional[float] = None) -> dict:
    s = net.spec
    net.reset_dynamics()
    return net.run(s.inject_steps + s.gap_steps, inject=[net.inject_idx(g) for g in groups],
                   inject_steps=s.inject_steps, learn=learn, consolidate=consolidate, release1=release1,
                   release2=release2, c2_uniform=c2_uniform)


def run_pair_protocol(net: SpikingNetwork, a: int, b: int, c2_stage: bool = True, control0: bool = True,
                      trace: Optional[list] = None, c: Optional[int] = None) -> dict:
    """
    The passing protocol on one pair: joint rounds (A and B injected together, learning rule "both") and a
    test of A alone on w_perm + w_fast after each round, until the first transfer (B active) or
    max_c1_rounds; then, if c2_stage, the short-circuit stage (consolidation of w_fast under C2, no new learning)
    and the final strict tests. Class by the first transfer: 'contained' (at most the stray limit of groups
    active outside A, B and the route), 'ignition' (more, or a runaway), or 'none'.
    """
    s = net.spec
    net.reset_all()
    path = path_groups(net.coords, a, b)
    out = {"A": a, "B": b, "path": path}
    t0 = time.perf_counter()
    if control0:
        out["control0"] = {"A_to_B": run_test(net, a, b, "perm", path), "B_to_A": run_test(net, b, a, "perm", path)}
    rounds, first, runaway_round = 0, None, None
    while rounds < s.max_c1_rounds:
        res = run_round(net, [a, b], learn=True, consolidate=False, release1=True, release2=False)
        rounds += 1
        if res["stopped"] is not None:      # the training round itself ran away: stop before consolidation
            runaway_round = rounds
            if trace is not None:
                trace.append({"round": rounds, "runaway_in_training": True, "spikes": res["spikes"]})
            break
        t = run_test(net, a, b, "effective", path)
        if trace is not None:
            oth = np.ones(net.G, dtype=bool)
            oth[[a, b] + ([c] if c is not None else []) + list(path)] = False
            gm = res["gmax"]
            trace.append({"round": rounds, "spikes": res["spikes"], "others_max": float(gm[oth].max()),
                          "n_others_ge_0.5": int((gm[oth] >= s.active).sum()), "path_max": float(gm[path].max()) if path else 0.0,
                          "test_src_max": t["src_max"], "test_dst_max": t["dst_max"], "test_out": t["n_active_outside"],
                          "test_above_inactive": t["n_above_inactive_outside"], "test_spikes": t["spikes"],
                          "w_fast_abs_mean": float(np.abs(net.F).mean() * abs(net.m))})
        if t["success"]:
            first = t
            break
    out["c1_rounds"] = rounds
    out["runaway_round"] = runaway_round
    if first is None:
        out["class"] = "none"
        out["strays"] = None
        out["seconds"] = time.perf_counter() - t0
        out["steps"] = net.steps_run
        return out
    out["class"] = "contained" if first["bounded"] else "ignition"
    out["strays"] = first["n_active_outside"]
    out["first_transfer"] = first
    if c2_stage:
        n_c2, final = 0, None
        limit = s.c2_rounds + s.max_extra_c2_rounds
        while n_c2 < limit:
            res = run_round(net, [a, b], learn=False, consolidate=True, release1=True, release2=True,
                            c2_uniform=s.c2_uniform)
            n_c2 += 1
            if res["stopped"] is not None:
                out["c2_runaway_round"] = n_c2
                break
            if n_c2 >= s.c2_rounds:
                final = {"A_to_B": run_test(net, a, b, "perm", path), "B_to_A": run_test(net, b, a, "perm", path)}
                if final["A_to_B"]["success"] or final["B_to_A"]["success"]:
                    break
        if final is None:
            final = {"A_to_B": run_test(net, a, b, "perm", path), "B_to_A": run_test(net, b, a, "perm", path)}
        out["c2_rounds"] = n_c2
        out["final"] = final
        out["association"] = bool(any(final[d]["success"] and final[d]["bounded"] for d in ("A_to_B", "B_to_A")))
    out["seconds"] = time.perf_counter() - t0
    out["steps"] = net.steps_run
    return out
