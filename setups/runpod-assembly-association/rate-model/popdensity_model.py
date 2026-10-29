"""
popdensity_model.py

Model A of round 4 (rate-model-task.md, "Round 4: two group models"): a finite-size stochastic population-density
model of the assembly-association network.

Intent. Keep what the smooth rate curves lost: the finite number of neurons per group (about 58, 12 of them
injected), their fluctuations, refractoriness and synchronous recruitment.

Form (age-structured refractory density with a hazard derived from the engine's Izhikevich map). Each location
group has three populations: bulk excitatory neurons, the k_inject injected excitatory neurons (identical to the bulk
except for the injected current), and inhibitory neurons. Each population is split into K parameter classes (the
engine draws r uniform per neuron; class k stands for the midpoint quantile of r) and, within a class, into bins of
age a (steps since the neuron's last spike, a = 0 .. A; the last bin collects all older neurons). A bin holds an
integer number of neurons m and ONE representative membrane state (v, u) that follows the engine's update exactly
(snn_simulation.cu:79-86, two half steps) under the population's input. Neurons of a bin differ by their synaptic
input (each neuron receives a Poisson number of synapses per presynaptic spike; variance derived from the sampled
synapse counts), so the bin's neurons are spread around the representative state with standard deviation equal to
that input fluctuation. The hazard of the bin is the probability that a neuron's state lies beyond the separatrix
v_sep(u) of the engine's map (the voltage above which the engine's neuron fires without further input; found by
bisection on the engine's own update); the number of neurons that commit in a step is drawn binomially. A committed
neuron fires after the latency the engine's map needs to reach v > 30 (iterated on the engine's update), is reset
(v = c, u += d) and enters age bin 0. Spike counts per group and type are integers; they drive the couplings, fields
and plasticity of rate_model.py (derived couplings, sampled connectivity, delays, fields, plasticity, protocol).

Free parameters: sigma_scale (multiplier on the derived input fluctuation), see Spec fields. Everything else is
derived (rate_model.DERIVED) or an option.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Tuple

import numpy as np

from rate_model import (
    DERIVED, RateNetwork, Spec, ChemicalFieldLattice, group_distances, lattice_coords, group_sizes,
    sample_counts, gate, path_groups, pick_pairs, run_round, run_test, run_pair_protocol,
)

# --------------------------------------------------------------------------------------------------
# Engine map (snn_simulation.cu:79-86, with the spike/reset handled by the population)
# --------------------------------------------------------------------------------------------------
V_PEAK = 30.0        # a neuron with v > 30 at the start of a step fires in that step (snn_simulation.cu:79)
V_CLIP = (-400.0, 200.0)


def izh_advance(v, u, a, b, i):
    """One engine step without the spike test: two half steps of v, then u (float64, vectorised)."""
    v = v + 0.5 * (0.04 * v * v + 5.0 * v + 140.0 - u + i)
    v = v + 0.5 * (0.04 * v * v + 5.0 * v + 140.0 - u + i)
    u = u + a * (b * v - u)
    return np.clip(v, *V_CLIP), u


def class_params(kind: str, n_classes: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(a, b, c, d) of the K classes at the midpoint quantiles of r ~ U[0, 1] (izhikevich_presets.py:85-95)."""
    r = (np.arange(n_classes) + 0.5) / n_classes
    if kind == "E":
        return (np.full(n_classes, 0.02), np.full(n_classes, 0.2), -65.0 + 15.0 * r ** 2, 8.0 - 6.0 * r ** 2)
    if kind == "I":
        return (0.02 + 0.08 * r, 0.2 + 0.05 * (1.0 - r), np.full(n_classes, -65.0), np.full(n_classes, 2.0))
    raise ValueError(kind)


_TABLES: Dict[tuple, dict] = {}
U_GRID = np.arange(-30.0, 50.0 + 1e-9, 0.25)


def tables(n_classes: int) -> dict:
    """
    Per (type, class): rest state (fixed point of the engine's map reached from the post-warm-up state) and the
    separatrix v_sep(u) on U_GRID by bisection on the engine's update with zero input. type 0 = excitatory (all
    classes share a, b), 1 = inhibitory.
    """
    key = (n_classes,)
    if key in _TABLES:
        return _TABLES[key]
    out = {}
    for ti, kind in enumerate(("E", "I")):
        a, b, c, d = class_params(kind, n_classes)
        # rest: iterate from the engine's initial state (v0 = -65, u0 = b v0)
        v = np.full(n_classes, -65.0)
        u = b * v
        for _ in range(6000):
            v, u = izh_advance(v, u, a, b, 0.0)
        out[("rest_v", ti)], out[("rest_u", ti)] = v.copy(), u.copy()
        # separatrix: smallest v (after a step) from which the neuron fires with zero further input
        nu = len(U_GRID)
        A = np.repeat(a[:, None], nu, axis=1)
        B = np.repeat(b[:, None], nu, axis=1)
        U0 = np.repeat(U_GRID[None, :], n_classes, axis=0)

        def fires(v0):
            vv, uu = v0.copy(), U0.copy()
            hit = vv > V_PEAK
            for _ in range(400):
                vv, uu = izh_advance(vv, uu, A, B, 0.0)
                hit |= vv > V_PEAK
                if hit.all():
                    break
            return hit
        lo = np.full((n_classes, nu), -90.0)
        hi = np.full((n_classes, nu), 0.0)
        always = fires(lo)                       # no stable rest state at this u: fires from anywhere
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            f = fires(mid)
            hi = np.where(f, mid, hi)
            lo = np.where(f, lo, mid)
        out[("vsep", ti)] = np.where(always, -90.0, 0.5 * (lo + hi))
    _TABLES[key] = out
    return out


def _erf(x):
    """erf by Abramowitz and Stegun 7.1.26 (absolute error below 1.5e-7)."""
    s = np.sign(x)
    x = np.abs(x)
    t = 1.0 / (1.0 + 0.3275911 * x)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * np.exp(-x * x)
    return s * y


def _phi_cdf(z):
    return 0.5 * (1.0 + _erf(z / math.sqrt(2.0)))


def _phi_pdf(z):
    return np.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)


def clipped_gauss_moments(mu, sig, lo, hi):
    """Mean and standard deviation of clip(X, lo, hi) for X ~ N(mu, sig^2) (closed form). sig = 0 gives clip(mu)."""
    mu = np.asarray(mu, dtype=float)
    sig = np.asarray(sig, dtype=float)
    lo = -np.inf if lo is None else lo
    hi = np.inf if hi is None else hi
    safe = np.where(sig > 0, sig, 1.0)
    a, b = (lo - mu) / safe, (hi - mu) / safe
    Fa = np.where(np.isfinite(a), _phi_cdf(np.where(np.isfinite(a), a, 0.0)), 0.0)
    Fb = np.where(np.isfinite(b), _phi_cdf(np.where(np.isfinite(b), b, 0.0)), 1.0)
    fa = np.where(np.isfinite(a), _phi_pdf(np.where(np.isfinite(a), a, 0.0)), 0.0)
    fb = np.where(np.isfinite(b), _phi_pdf(np.where(np.isfinite(b), b, 0.0)), 0.0)
    lo_f = np.where(np.isfinite(lo), lo, 0.0)
    hi_f = np.where(np.isfinite(hi), hi, 0.0)
    mid = Fb - Fa
    m1 = lo_f * Fa + hi_f * (1.0 - Fb) + mu * mid + safe * (fa - fb)
    aa = np.where(np.isfinite(a), a, 0.0)
    bb = np.where(np.isfinite(b), b, 0.0)
    m2 = (lo_f ** 2 * Fa + hi_f ** 2 * (1.0 - Fb) + mu ** 2 * mid + 2.0 * mu * safe * (fa - fb)
          + safe ** 2 * (mid - (bb * fb - aa * fa)))
    sd = np.sqrt(np.maximum(m2 - m1 ** 2, 0.0))
    det = np.clip(mu, lo, hi)
    return np.where(sig > 0, m1, det), np.where(sig > 0, sd, 0.0)


@dataclass
class PopSpec(Spec):
    """Spec of rate_model plus the options of the population-density model."""
    n_classes: int = 12                   # parameter classes per type (midpoint quantiles of r)
    age_bins: int = 80                    # age bins 0 .. age_bins; the last one collects older neurons
    latency_max: int = 12                 # cap on the steps from crossing the separatrix to the spike
    sigma_scale: float = 1.0              # FREE PARAMETER 1: multiplier on the derived input fluctuation (1 = derived)
    sigma_floor: float = 0.0              # option: additional voltage spread (mV), 0 = none
    act_mean_thr: float = 5e-2            # a group with input below this (mean current) and variance below the next is not simulated
    act_var_thr: float = 1e-1
    rest_tol: float = 2e-2                # (v, u) distance from rest below which a quiet group is not simulated
    commit_rule: str = "separatrix"       # round 5: "separatrix" (round 4: a neuron beyond the separatrix is committed to fire after its latency, irrevocably) or "peak" (a neuron fires when v > 30, as the engine; the upswing is integrated and can be stopped by inhibition)
    ei_inter_scale: float = 1.0           # round 5: factor on the weight of E -> I synapses between groups (1 = derived; 0.3 from the engine's single-group response)
    transfer: str = "sigmoid0"            # unused here (inherited); keeps RateNetwork.__init__ from building the round-3 curves


# --------------------------------------------------------------------------------------------------
# The network
# --------------------------------------------------------------------------------------------------

class PopNetwork(RateNetwork):
    """
    One realization. Reuses RateNetwork for the sampled sizes and synapse counts, the derived coupling matrices,
    delays, fields, plasticity and weights; replaces the group dynamics by the population-density model.
    """

    KINDS = ("E", "I", "J")               # bulk excitatory, inhibitory, injected excitatory
    TYPE_OF_KIND = (0, 1, 0)

    def __init__(self, spec: PopSpec, seed: int = 0, counts=None, sizes=None):
        super().__init__(spec, seed=seed, counts=counts, sizes=sizes)
        s, G = spec, self.G
        self.nu = 1.0                     # rE below is already the per-neuron spike probability of the step
        K, A1 = s.n_classes, s.age_bins + 1
        self.K, self.A1 = K, A1
        self.rng = np.random.default_rng([self.seed, 4])
        # class parameters (3 kinds, K classes)
        aE, bE, cE, dE = class_params("E", K)
        aI, bI, cI, dI = class_params("I", K)
        self.PA = np.stack([aE, aI, aE])
        self.PB = np.stack([bE, bI, bE])
        self.PC = np.stack([cE, cI, cE])
        self.PD = np.stack([dE, dI, dE])
        tb = tables(K)
        self.tabs = tb
        self.rest_v = np.stack([tb[("rest_v", t)] for t in self.TYPE_OF_KIND])      # (3, K)
        self.rest_u = np.stack([tb[("rest_u", t)] for t in self.TYPE_OF_KIND])
        self.vsep_tab = np.stack([tb[("vsep", t)] for t in self.TYPE_OF_KIND])       # (3, K, len(U_GRID))
        # neurons per class: classes are multinomial (r uniform per neuron); the injected neurons are a random
        # subset of the group's excitatory neurons (hypergeometric over classes)
        cnt = np.zeros((3, G, K), dtype=np.int64)
        for g in range(G):
            ne, ni = int(round(self.nE[g])), int(round(self.nI[g]))
            ce = self.rng.multinomial(ne, np.full(K, 1.0 / K))
            kj = min(int(s.k_inject), ne)
            cj = self.rng.multivariate_hypergeometric(ce, kj) if kj > 0 else np.zeros(K, dtype=np.int64)
            cnt[0, g], cnt[2, g] = ce - cj, cj
            cnt[1, g] = self.rng.multinomial(ni, np.full(K, 1.0 / K))
        self.class_counts = cnt
        # variance matrices: per presynaptic spike, the number of synapses onto a given postsynaptic neuron is
        # Poisson with mean lam = counts / (n_pre n_post); each carries the same weight
        c = self.counts
        M_EE = c["EE"].copy()
        self.m_intra = np.maximum(M_EE.diagonal() / (self.nE ** 2), 1e-12)
        np.fill_diagonal(M_EE, 0.0)
        self.B_EE = (s.gain * s.gain_ee_inter) ** 2 * M_EE / (self.nE[:, None] * self.nE[None, :])
        self.B_EI = (s.gain * s.gain_ei) ** 2 * c["EI"] / (self.nE[:, None] * self.nI[None, :])
        if s.ei_inter_scale != 1.0:        # round 5: scale the inter-group E -> I weight (mean and variance)
            off = ~np.eye(G, dtype=bool)
            self.A_EI[off] *= s.ei_inter_scale
            self.B_EI[off] *= s.ei_inter_scale ** 2
        self.B_IE = (s.gain * s.gain_ie * abs(s.w_ie)) ** 2 * c["IE"] / (self.nI[:, None] * self.nE[None, :])
        # simulation bookkeeping
        self.Q = s.latency_max + 2
        self.reset_dynamics()
        self.n_steps_simulated = 0        # group-steps simulated (cost measure)
        self.n_bin_steps = 0

    # -- state -----------------------------------------------------------------------------------
    # The bins are kept as a flat list (only groups that are not at rest are in it): arrays bg (group), bkind (0 bulk
    # excitatory, 1 inhibitory, 2 injected), bcls (class), bage (steps since the last spike; age_bins = old bin of
    # all older neurons), bm (neurons), bv, bu (representative state). A group at rest has all its neurons in the old
    # bins at the rest state and is not in the list.
    def reset_dynamics(self):
        if not hasattr(self, "class_counts"):          # called by RateNetwork.__init__ before this class is set up
            return super().reset_dynamics()
        G = self.G
        self.A = self.spec.age_bins
        self.bg = np.zeros(0, dtype=np.int64)
        self.bkind = np.zeros(0, dtype=np.int64)
        self.bcls = np.zeros(0, dtype=np.int64)
        self.bage = np.zeros(0, dtype=np.int64)
        self.bm = np.zeros(0, dtype=np.int64)
        self.bv = np.zeros(0)
        self.bu = np.zeros(0)
        self.inlist = np.zeros(G, dtype=bool)
        self.qn = np.zeros((self.Q, 3, G, self.K), dtype=np.int64)
        self.qu = np.zeros((self.Q, 3, G, self.K))
        self.nonrest = np.zeros(G, dtype=bool)
        self.Ag = np.zeros(G)
        self.rE = np.zeros(G)
        self.rI = np.zeros(G)
        self.H = getattr(self, "H", 2)
        self.hE = np.zeros((self.H, G))
        self.hI = np.zeros((self.H, G))
        self.t = 0
        self.spk_E_total = np.zeros(G)
        self.spk_I_total = np.zeros(G)

    def _filter(self, keep):
        self.bg, self.bkind, self.bcls, self.bage = self.bg[keep], self.bkind[keep], self.bcls[keep], self.bage[keep]
        self.bm, self.bv, self.bu = self.bm[keep], self.bv[keep], self.bu[keep]

    def _append(self, g, kind, cls, age, m, v, u):
        self.bg = np.concatenate([self.bg, g])
        self.bkind = np.concatenate([self.bkind, kind])
        self.bcls = np.concatenate([self.bcls, cls])
        self.bage = np.concatenate([self.bage, np.full(len(g), age, dtype=np.int64)])
        self.bm = np.concatenate([self.bm, m.astype(np.int64)])
        self.bv = np.concatenate([self.bv, v])
        self.bu = np.concatenate([self.bu, u])

    # -- inputs ------------------------------------------------------------------------------------
    def _inputs(self, w_ee, w_ei):
        """Mean input current and its variance for the excitatory and inhibitory neurons of every group."""
        s = self.spec
        act = np.nonzero(self.hE.max(axis=0) > 0.0)[0]
        actI = np.nonzero(self.hI.max(axis=0) > 0.0)[0]
        n_prev = self.rE * self.nE
        xE = self.intra * self.rE
        s2E = (self.intra / self.nE) ** 2 * n_prev / self.m_intra
        xI = np.zeros(self.G)
        s2I = np.zeros(self.G)
        if len(act):
            if w_ee is None:
                we = np.clip(self.wp_ee[act] + self.wf_ee[act], s.w_lo, s.w_hi)
                wi = np.clip(self.wp_ei[act] + self.wf_ei[act], s.w_lo, s.w_hi)
            else:
                we, wi = w_ee[act], w_ei[act]
            rdE = self._delayed(self.hE, act)                       # (na, G) spike fractions of the presynaptic groups
            nd = rdE * self.nE[act][:, None]                        # spike counts
            xE += (self.A_EE[act] * we * rdE).sum(axis=0)
            xI += (self.A_EI[act] * wi * rdE).sum(axis=0)
            s2E += (self.B_EE[act] * we ** 2 * nd).sum(axis=0)
            s2I += (self.B_EI[act] * wi ** 2 * nd).sum(axis=0)
        if len(actI):
            rdI = self._delayed(self.hI, actI)
            xE -= (self.A_IE[actI] * rdI).sum(axis=0)
            s2E += (self.B_IE[actI] * (rdI * self.nI[actI][:, None])).sum(axis=0)
        return xE, xI, s2E, s2I

    def _vsep(self, kind, k, u):
        """Separatrix voltage for bins (kind, class k, state u) by linear interpolation in U_GRID."""
        x = np.clip((u - U_GRID[0]) / (U_GRID[1] - U_GRID[0]), 0.0, len(U_GRID) - 1.000001)
        i0 = x.astype(np.int64)
        f = x - i0
        tab = self.vsep_tab
        return tab[kind, k, i0] * (1.0 - f) + tab[kind, k, i0 + 1] * f

    def _latency(self, v, u, a, b, x):
        """Steps from commitment to the spike registered by the engine: 1 if v > 30 already, else 1 + the number of
        further engine steps (input x kept) until v > 30; capped at latency_max. Returns (latency, u at the spike)."""
        L = np.ones(len(v), dtype=np.int64)
        alive = v <= V_PEAK
        vv, uu = v.copy(), u.copy()
        for _ in range(self.spec.latency_max - 1):
            if not alive.any():
                break
            nv, nu_ = izh_advance(vv, uu, a, b, x)
            vv = np.where(alive, nv, vv)
            uu = np.where(alive, nu_, uu)
            L = L + alive
            alive = alive & (vv <= V_PEAK)
        return L, uu

    # -- one step -----------------------------------------------------------------------------------
    def step(self, inj: Optional[np.ndarray] = None, w_ee=None, w_ei=None, learn: bool = False,
             consolidate: bool = False, release1: bool = False, release2: bool = False, chem: bool = True):
        s = self.spec
        G, K, A = self.G, self.K, self.A
        xE, xI, s2E, s2I = self._inputs(w_ee, w_ei)
        sdE, sdI = np.sqrt(np.maximum(s2E, 0.0)) * s.sigma_scale, np.sqrt(np.maximum(s2I, 0.0)) * s.sigma_scale
        if s.sigma_floor > 0.0:
            sdE, sdI = np.sqrt(sdE ** 2 + s.sigma_floor ** 2), np.sqrt(sdI ** 2 + s.sigma_floor ** 2)
        if s.i_min is not None or s.i_max is not None:
            # each neuron's summed input is clamped (assoc_protocol.py:359): moments of the clamped Gaussian input
            xE, sdE = clipped_gauss_moments(xE, sdE, s.i_min, s.i_max)
            xI, sdI = clipped_gauss_moments(xI, sdI, s.i_min, s.i_max)
        jm = (inj > 0) if inj is not None else np.zeros(G, dtype=bool)
        slot = self.t % self.Q
        pend = self.qn.sum(axis=(0, 1, 3)) > 0
        want = (self.nonrest | pend | jm | (np.abs(xE) > s.act_mean_thr) | (np.abs(xI) > s.act_mean_thr)
                | (sdE ** 2 > s.act_var_thr) | (sdI ** 2 > s.act_var_thr))
        # groups returning to rest leave the list, groups that are wanted enter it with their old bins at rest
        leave = self.inlist & ~want
        if leave.any():
            self._filter(~leave[self.bg])
            self.inlist[leave] = False
        enter = want & ~self.inlist
        if enter.any():
            gs = np.nonzero(enter)[0]
            ki, gi, ci = np.nonzero(self.class_counts[:, gs, :] > 0)
            self._append(gs[gi], ki, ci, A, self.class_counts[ki, gs[gi], ci], self.rest_v[ki, ci], self.rest_u[ki, ci])
            self.inlist[gs] = True
        spE = np.zeros(G)
        spI = np.zeros(G)
        if len(self.bg):
            self.n_steps_simulated += int(self.inlist.sum())
            self.n_bin_steps += len(self.bg)
            # ages advance; young bins reaching the old age merge with the old bin of their class
            reached = self.bage == A - 1
            self.bage = np.minimum(self.bage + 1, A)
            if reached.any():
                ia = np.nonzero(self.bage == A)[0]
                key = (self.bg[ia] * 3 + self.bkind[ia]) * K + self.bcls[ia]
                uq, first, inv = np.unique(key, return_index=True, return_inverse=True)
                if len(uq) < len(ia):
                    msum = np.bincount(inv, weights=self.bm[ia])
                    vsum = np.bincount(inv, weights=self.bm[ia] * self.bv[ia])
                    usum = np.bincount(inv, weights=self.bm[ia] * self.bu[ia])
                    tgt = ia[first]
                    self.bm[tgt] = np.rint(msum).astype(np.int64)
                    self.bv[tgt] = vsum / msum
                    self.bu[tgt] = usum / msum
                    keep = np.ones(len(self.bg), dtype=bool)
                    keep[ia] = False
                    keep[tgt] = True
                    self._filter(keep)
        # arrivals of this step (spikes registered now) enter age 0 after reset
        arr = self.qn[slot]
        if arr.any():
            ki, gi, ci = np.nonzero(arr)
            n = arr[ki, gi, ci]
            uu0 = self.qu[slot][ki, gi, ci] / n + self.PD[ki, ci]
            self._append(gi, ki, ci, 0, n, self.PC[ki, ci].copy(), uu0)
            spE = np.bincount(gi, weights=n * (ki != 1), minlength=G)
            spI = np.bincount(gi, weights=n * (ki == 1), minlength=G)
            self.qn[slot] = 0
            self.qu[slot] = 0.0
        self.Ag = np.zeros(G)
        if len(self.bg):
            # inputs per kind (injection is added after the clamp, as in assoc_protocol.run)
            XA = np.stack([xE, xI, xE + np.where(jm, s.inject_current, 0.0)])
            SA = np.stack([sdE, sdI, sdE])
            x = XA[self.bkind, self.bg]
            sig = SA[self.bkind, self.bg]
            a_, b_ = self.PA[self.bkind, self.bcls], self.PB[self.bkind, self.bcls]
            vv, uu = izh_advance(self.bv, self.bu, a_, b_, x)
            dd = vv - (V_PEAK if s.commit_rule == "peak" else self._vsep(self.bkind, self.bcls, uu))
            safe = np.where(sig > 0, sig, 1.0)
            z = dd / safe
            p = np.clip(np.where(sig > 0, _phi_cdf(z), (dd > 0).astype(float)), 0.0, 1.0)
            nc = self.rng.binomial(self.bm, p)
            pdf = np.where(sig > 0, _phi_pdf(z), 0.0)
            # conditional mean shifts of the voltage spread (committed: above, remaining: below)
            shift_c = np.where(sig > 0, sig * pdf / np.maximum(p, 1e-12), 0.0)
            shift_r = np.where(sig > 0, -sig * pdf / np.maximum(1.0 - p, 1e-12), 0.0)
            self.bv = np.clip(np.where(p < 1.0, vv + shift_r, vv), *V_CLIP)
            self.bu = uu
            sel = nc > 0
            if sel.any():
                ci_ = np.nonzero(sel)[0]
                lat, uf = self._latency(vv[ci_] + shift_c[ci_], uu[ci_], a_[ci_], b_[ci_], x[ci_])
                if getattr(self, "diag_group", None) is not None:      # round 5 diagnostic: commitments of the monitored group
                    for j in range(len(ci_)):
                        if self.bg[ci_[j]] == self.diag_group and self.bkind[ci_[j]] != 1:
                            self.diag_commits.append((self.t, int(lat[j]), int(nc[ci_[j]])))
                slots = (self.t + lat) % self.Q
                np.add.at(self.qn, (slots, self.bkind[ci_], self.bg[ci_], self.bcls[ci_]), nc[ci_])
                np.add.at(self.qu, (slots, self.bkind[ci_], self.bg[ci_], self.bcls[ci_]), nc[ci_] * uf)
                self.bm = self.bm - nc
                self._filter(self.bm > 0)
            # bookkeeping: activity A_g and the quiet test
            self.nonrest = np.zeros(G, dtype=bool)
            if len(self.bg):
                msk = (self.bage < s.window) & (self.bkind != 1)
                self.Ag = np.bincount(self.bg[msk], weights=self.bm[msk], minlength=G) / self.nE
                young = self.bage < A
                self.nonrest[self.bg[young]] = True
                off = (~young) & ((np.abs(self.bv - self.rest_v[self.bkind, self.bcls]) > s.rest_tol)
                                  | (np.abs(self.bu - self.rest_u[self.bkind, self.bcls]) > s.rest_tol))
                self.nonrest[self.bg[off]] = True
        if getattr(self, "diag_group", None) is not None:
            self.diag_I.append(float(spI[self.diag_group]))
            self.diag_E.append(float(spE[self.diag_group]))
        self.rE = spE / self.nE
        self.rI = spI / self.nI
        self.spk_E_total += spE
        self.spk_I_total += spI
        self.t += 1
        self.hE[self.t % self.H] = self.rE
        self.hI[self.t % self.H] = self.rI
        if chem:
            spk = spE + spI
            if release1:
                self.c1.release(spk, s.c1["gain"], s.c1.get("saturation"))
            if release2:
                self.c2.release(spk, s.c2["gain"], s.c2.get("saturation"))
            self.c1.diffuse()
            self.c2.diffuse()
            if release2 and s.c2_uniform is not None:
                self.c2.c[:] = float(s.c2_uniform)
        if learn or consolidate:
            self._plasticity(learn, consolidate)

    # -- protocol interface -------------------------------------------------------------------------
    def activity(self, r=None) -> np.ndarray:
        """A_g: fraction of the group's excitatory neurons that fired within the last `window` steps (exact count)."""
        return self.Ag.copy()

    def injection(self, groups: List[int]) -> np.ndarray:
        """Flag vector: the injected neurons of these groups receive inject_current (value = inject_current)."""
        inj = np.zeros(self.G)
        for g in groups:
            inj[g] = self.spec.inject_current
        return inj
