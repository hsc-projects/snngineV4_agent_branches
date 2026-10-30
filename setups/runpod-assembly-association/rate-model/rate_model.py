"""
rate_model.py

Host-local rate model of the assembly-association network (round 2): one excitatory and one inhibitory
rate unit per location group on a 3D lattice, coupling derived from the spiking network's code and
parameters, synapse counts between groups sampled per realization from the spiking network's rewiring
rule, fields C1 / C2 (ChemicalField update), gated plasticity (rule "both" as rate products), and the
protocol with its tests (assoc_protocol.py).

Everything is either DERIVED (see DERIVED below: value, source file and line) or one of the three fitted
parameters (sigmoid threshold `theta`, gain `beta`, time constant `tau`). Forms and parameters are
options (Spec fields, `transfer`, `plasticity_rule`, `sample_sizes`, ...) so the model can be extended.

Requires numpy (see the .venv in this folder). The spiking code itself (torch, CUDA) is not imported.

Units. r_E[g], r_I[g] in [0, 1] = fraction of the group's excitatory / inhibitory neurons active in the
window (A_g of assoc_fields.GroupActivity). An active neuron emits `nu_act` spikes per step, so a group
with n neurons emits n * nu_act * r spikes per step. Synaptic input to a neuron is the summed current per
step (engine units), spikes times weight times gain.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Tuple

import numpy as np

# --------------------------------------------------------------------------------------------------
# Derived constants. value, where it comes from (path relative to the parent folder
# setups/runpod-assembly-association unless it starts with snngine_v4/; line numbers as of 2026-10-29).
# test_rate_model.py re-reads each source and compares.
# --------------------------------------------------------------------------------------------------
DERIVED: Dict[str, Tuple[object, str]] = {
    "n_neurons": (20000, "archive-pre-engine-fix/params/session69a-stage2.json engine.n_neurons (line 4)"),
    "S": (2000, "archive-pre-engine-fix/params/session69a-stage2.json engine.n_synapses (line 5)"),
    "lam": (0.4, "archive-pre-engine-fix/params/session69a-stage2.json engine.rewire.lam (line 8); assoc_engine.py rewire_by_distance (line 109; kern line 128, target probabilities line 141)"),
    "exc_ratio": ((1, 4), "snngine_v4/nn/config_models/reservoir/n_type_groups.py:145-146 gen_factors [1, 4] "
                          "(inhibitory : excitatory); neuron counts n_type_groups.py:150-160"),
    "frac_E_to_I": (0.2, "n_type_groups.py:278-307 generate_uniform_connections (excitatory synapses split by gen_factors 1 : 4: 400 onto "
                         "inhibitory, 1600 onto excitatory of S = 2000)"),
    "frac_I_to_E": (1.0, "n_type_groups.py:278-307 (inhibitory neurons: one connection type, I -> E only)"),
    "w_ei": (0.45, "assoc_build.py:84 NTypeGroupConnInit(src=1, snk=0, w0=0.45): excitatory -> inhibitory built weight"),
    "w_ie": (-0.44, "assoc_build.py:83 NTypeGroupConnInit(src=0, snk=1, w0=-0.44): inhibitory -> excitatory built weight"),
    "w_ee": (0.05, "archive-pre-engine-fix/params/session69a-stage2.json weights.w_ee (line 29): excitatory -> excitatory weight set by "
                   "assoc_engine.py typed_weights (line 330)"),
    "w_intra_ee_total": (40.0, "archive-pre-engine-fix/params/session69a-stage2.json weights.w_intra_ee_total (line 30); "
                               "assoc_engine.py:334-337 (per-synapse weight = total / in-degree)"),
    "gain": (4.0, "archive-pre-engine-fix/params/session69a-stage2.json gain (line 24); assoc_engine.py:272 (m = gain)"),
    "gain_ei": (1.0, "archive-pre-engine-fix/params/session69a-stage2.json gain_ei; assoc_engine.py:273"),
    "gain_ie": (2.0, "archive-pre-engine-fix/params/session69a-stage2.json gain_ie (line 25); assoc_engine.py:274"),
    "gain_ee_inter": (0.6, "archive-pre-engine-fix/params/session69a-stage2.json gain_ee_inter (line 74); assoc_engine.py:276-278 (not on "
                           "intra-assembly synapses)"),
    "i_min": (-100.0, "archive-pre-engine-fix/params/session69a-stage2.json i_min (line 27); assoc_protocol.py:359 clamp; assoc_engine.py clamp_current"),
    "i_max": (100.0, "archive-pre-engine-fix/params/session69a-stage2.json i_max; assoc_protocol.py:359 clamp"),
    "k_inject": (12, "archive-pre-engine-fix/params/session69a-stage2.json k_inject (line 22); assoc_protocol.py:299"),
    "inject_current": (20.0, "archive-pre-engine-fix/params/session69a-stage2.json inject_current; assoc_protocol.py:21 (injection in run())"),
    "inject_steps": (50, "assoc_protocol.py:21 DEFAULTS inject_steps"),
    "gap_steps": (50, "assoc_protocol.py:21 DEFAULTS gap_steps"),
    "test_window": (100, "assoc_protocol.py:21 DEFAULTS test_window"),
    "window": (20, "assoc_protocol.py:20 DEFAULTS window (A_g window)"),
    "active": (0.5, "assoc_protocol.py:20 DEFAULTS active"),
    "inactive": (0.1, "assoc_protocol.py:20 DEFAULTS inactive"),
    "a_pre": (0.5, "archive-pre-engine-fix/params/session69a-stage2.json plasticity.a_pre"),
    "a_plus": (0.5, "archive-pre-engine-fix/params/session69a-stage2.json plasticity.a_plus"),
    "a_minus": (0.5, "archive-pre-engine-fix/params/session69a-stage2.json plasticity.a_minus"),
    "tau_fast": (2000.0, "archive-pre-engine-fix/params/session69a-stage2.json plasticity.tau_fast; assoc_plasticity.py:88 exp(-1/tau)"),
    "kappa": (0.05, "archive-pre-engine-fix/params/session69a-stage2.json plasticity.kappa"),
    "theta1": (-1.0, "archive-pre-engine-fix/params/session69a-stage2.json plasticity.theta1 (C1 gate open everywhere)"),
    "soft1": (0.0, "archive-pre-engine-fix/params/session69a-stage2.json plasticity.soft1"),
    "theta2": (0.6, "archive-pre-engine-fix/params/session69a-stage2.json plasticity.theta2"),
    "soft2": (0.6, "archive-pre-engine-fix/params/session69a-stage2.json plasticity.soft2"),
    "w_lo": (0.05, "assoc_plasticity.py:63 w_exc=(0.05, 1.0)"),
    "w_hi": (1.0, "assoc_plasticity.py:63 w_exc=(0.05, 1.0)"),
    "c1": ({"gain": 0.0, "k": 0.16, "decay": 0.003, "saturation": 8.0},
           "archive-pre-engine-fix/params/session69a-stage2.json c1"),
    "c2": ({"gain": 1.0, "k": 0.02, "decay": 0.01, "saturation": None},
           "archive-pre-engine-fix/params/session69a-stage2.json c2"),
    "vox_per_cell": (4, "assoc_protocol.py:26 DEFAULTS vox_per_cell"),
    "max_c1_rounds": (30, "archive-pre-engine-fix/params/session69a-stage2.json protocol.max_c1_rounds"),
    "c2_rounds": (5, "archive-pre-engine-fix/params/session69a-stage2.json protocol.c2_rounds"),
    "max_extra_c2_rounds": (5, "archive-pre-engine-fix/params/session69a-stage2.json protocol.max_extra_c2_rounds"),
    "max_active_frac": (0.1, "archive-pre-engine-fix/params/session69a-stage2.json protocol.max_active_frac; "
                             "assoc_protocol.py:477 (limit = int(frac * G) = 34)"),
    "pair_distance": (4.0, "archive-pre-engine-fix/params/session69a-stage2.json protocol.pair_distance"),
    "neurons_per_group": (20000 / 343, "N / G = 20000 / 343 = 58.3 (archive-pre-engine-fix/tuning-log.md iteration 61 "
                                       "'group size mean 58.3'; the 9^3 and 11^3 builds keep 58.3)"),
    "delay_rule": ("round((D - 1) * d / d_max)", "assoc_engine.py:165"),
    "D_rule": ("int(min(20, max(log10(N) * (1 + sqrt(log10(N))), 2)))",
               "snngine_v4/nn/config_models/reservoir/nn_reservoir_config.py:144-146 (_calc_delay_count)"),
    "grid_rule": ("int(D / sqrt(3)) cells per axis", "snngine_v4/.../nn_reservoir_config.py:178-; "
                                                    "assoc_build.py docstring"),
    # Measured from the spiking runs, not from code: spikes per step of an active neuron.
    "nu_act": (0.074, "median of 39 isolated single-group tests (control0_before, s71 E0, 48 tests, src_max >= 0.9, "
                      "no other group above 0.1): spikes / (100 steps * 58.3 neurons); range 0.026 to 0.125 "
                      "(output/s71-d4-s*-p*/s4-*-E0.json; output/ is gitignored)"),
}


def delay_count(n_neurons: float) -> int:
    """Delay count D from the spiking network's rule (nn_reservoir_config._calc_delay_count)."""
    n = math.log10(n_neurons)
    return int(min(max(int(max(n * (1 + math.sqrt(n)), 2)), 2), 20))


# --------------------------------------------------------------------------------------------------
# Transfer functions derived from the engine's neuron model (round 3)
# --------------------------------------------------------------------------------------------------
# Engine neuron (snn_simulation.cu, update_N_state_, Izhikevich model, lines 79-86): at the start of a step, if
# v > 30: v = c, u += d, spike; then two half-steps v += 0.5 (0.04 v^2 + 5 v + 140 - u + i), then
# u += a (b v - u). i = summed input of the step, clamped to [i_min, i_max] by the harness (assoc_protocol.py:359).
# Per-neuron a, b, c, d (snngine_v4/nn/config_models/neurons/presets/izhikevich_presets.py:85-95, default_init;
# r uniform in [0, 1] per neuron): excitatory a = .02, b = .2, c = -65 + 15 r^2, d = 8 - 6 r^2;
# inhibitory a = .02 + .08 r, b = .2 + .05 (1 - r), c = -65, d = 2; v0 = -65, u0 = b v0.
IZH_V0 = -65.0


def izh_params(kind: str, n_r: int = 32) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(a, b, c, d) of n_r neurons at the midpoint quantiles of r ~ U[0, 1] (the engine draws r per neuron)."""
    r = (np.arange(n_r) + 0.5) / n_r
    if kind == "E":
        return (np.full(n_r, 0.02), np.full(n_r, 0.2), -65.0 + 15.0 * r ** 2, 8.0 - 6.0 * r ** 2)
    if kind == "I":
        return (0.02 + 0.08 * r, 0.2 + 0.05 * (1.0 - r), np.full(n_r, -65.0), np.full(n_r, 2.0))
    raise ValueError(kind)


def izh_rates(a, b, c, d, currents: np.ndarray, steps: int = 3000, warm: int = 1000,
              dtype=np.float32) -> np.ndarray:
    """
    Firing rate (spikes per 1 ms step) of Izhikevich neurons (parameter arrays a..d) under constant input current,
    one value per (current, neuron): shape (len(currents), len(a)). The engine's update, in `dtype` (float32 as on the
    GPU); rate counted over `steps - warm` steps after `warm` steps.
    """
    cur = np.asarray(currents, dtype=dtype)[:, None]
    a, b, c, d = (np.asarray(x, dtype=dtype)[None, :] for x in (a, b, c, d))
    v = np.full((cur.shape[0], a.shape[1]), IZH_V0, dtype=dtype)
    u = b * v
    count = np.zeros(v.shape)
    half = dtype(0.5)
    for t in range(steps):
        fired = v > 30.0
        v = np.where(fired, c, v)
        u = np.where(fired, u + d, u)
        v = v + half * (dtype(0.04) * v * v + dtype(5) * v + dtype(140) - u + cur)
        v = v + half * (dtype(0.04) * v * v + dtype(5) * v + dtype(140) - u + cur)
        u = u + a * (b * v - u)
        if t >= warm:
            count += fired
    return count / float(steps - warm)


_CURVE_CACHE: Dict[tuple, np.ndarray] = {}
_PERNEURON_CACHE: Dict[tuple, np.ndarray] = {}
CURVE_GRID = np.arange(-100.0, 100.0 + 1e-9, 1.0)


def per_neuron_rates(kind: str, n_r: int = 32) -> np.ndarray:
    """(len(CURVE_GRID), n_r) steady-state rate of each representative neuron at each constant input."""
    key = (kind, n_r)
    if key not in _PERNEURON_CACHE:
        a, b, c, d = izh_params(kind, n_r)
        _PERNEURON_CACHE[key] = izh_rates(a, b, c, d, CURVE_GRID)
    return _PERNEURON_CACHE[key]


def raw_rate_curve(kind: str, i_min: float = -100.0, i_max: float = 100.0, n_r: int = 32) -> Tuple[np.ndarray, np.ndarray]:
    """Population-mean steady-state rate (spikes/step) of the E or I population vs constant input, on CURVE_GRID."""
    return CURVE_GRID, per_neuron_rates(kind, n_r).mean(axis=1)


def activity_from_rate_table(kind: str, window: int, sigma: float, n_r: int = 32) -> Tuple[np.ndarray, np.ndarray]:
    """
    Mapping from the population's mean rate nu (spikes/step) to A, the fraction of its neurons that fired at least once
    in the last `window` steps (assoc_fields.GroupActivity): per neuron 1 - (1 - nu_i)^window at the same constant input,
    averaged over neurons (and input noise sigma); both axes indexed by the input current, returned sorted by nu.
    """
    rates = per_neuron_rates(kind, n_r)
    act = 1.0 - (1.0 - np.minimum(rates, 1.0)) ** window
    nu, A = rates.mean(axis=1), act.mean(axis=1)
    if sigma > 0.0:
        z = np.linspace(-4.0, 4.0, 81)
        w = np.exp(-0.5 * z ** 2)
        w /= w.sum()
        noisy = np.clip(CURVE_GRID[:, None] + sigma * z[None, :], CURVE_GRID[0], CURVE_GRID[-1])
        nu = (np.interp(noisy, CURVE_GRID, nu) * w[None, :]).sum(axis=1)
        A = (np.interp(noisy, CURVE_GRID, A) * w[None, :]).sum(axis=1)
    nu = np.maximum.accumulate(nu) + 1e-12 * np.arange(len(nu))
    return nu, np.maximum.accumulate(A)


def smoothed_rate_curve(kind: str, sigma: float, i_min: float = -100.0, i_max: float = 100.0,
                        n_r: int = 32) -> Tuple[np.ndarray, np.ndarray]:
    """The raw curve averaged over Gaussian input noise of width sigma (noisy input clamped to [i_min, i_max])."""
    grid, raw = raw_rate_curve(kind, n_r=n_r)
    if sigma <= 0.0:
        return grid, raw
    z = np.linspace(-4.0, 4.0, 81)
    w = np.exp(-0.5 * z ** 2)
    w /= w.sum()
    noisy = np.clip(grid[:, None] + sigma * z[None, :], max(i_min, grid[0]), min(i_max, grid[-1]))
    return grid, (np.interp(noisy, grid, raw) * w[None, :]).sum(axis=1)


@dataclass
class Spec:
    """Network and protocol parameters. Defaults are the derived values of the passing protocol (DERIVED)."""
    grid_dim: int = 7
    neurons_per_group: float = DERIVED["neurons_per_group"][0]
    S: int = 2000
    lam: float = 0.4
    exc_frac: float = 0.8                 # gen_factors [1, 4]
    frac_E_to_I: float = 0.2
    frac_I_to_E: float = 1.0
    w_ee: float = 0.05
    w_ei: float = 0.45
    w_ie: float = -0.44
    w_intra_ee_total: float = 40.0
    gain: float = 4.0
    gain_ei: float = 1.0
    gain_ie: float = 2.0
    gain_ee_inter: float = 0.6
    i_min: Optional[float] = -100.0
    i_max: Optional[float] = 100.0
    k_inject: int = 12
    inject_current: float = 20.0
    inject_steps: int = 50
    gap_steps: int = 50
    test_window: int = 100
    window: int = 20
    active: float = 0.5
    inactive: float = 0.1
    nu_act: float = 0.074
    # plasticity
    plasticity_rule: str = "both"         # "stdp", "pre_c1", "both"
    plastic_ei: bool = True               # excitatory -> inhibitory synapses are plastic too (plastic_exc_only)
    a_pre: float = 0.5
    a_plus: float = 0.5
    a_minus: float = 0.5
    tau_fast: float = 2000.0
    kappa: float = 0.05
    theta1: float = -1.0
    soft1: float = 0.0
    theta2: float = 0.6
    soft2: float = 0.6
    w_lo: float = 0.05
    w_hi: float = 1.0
    # chemistry
    c1: dict = field(default_factory=lambda: {"gain": 0.0, "k": 0.16, "decay": 0.003, "saturation": 8.0})
    c2: dict = field(default_factory=lambda: {"gain": 1.0, "k": 0.02, "decay": 0.01, "saturation": None})
    vox_per_cell: int = 4
    c2_uniform: Optional[float] = None    # iteration 64 control: C2 held at this value while released
    # protocol
    max_c1_rounds: int = 30
    c2_rounds: int = 5
    max_extra_c2_rounds: int = 5
    max_active_frac: float = 0.1
    pair_distance: float = 4.0
    accept_uncontained: bool = True
    # options of the model (not parameters of the spiking network)
    n_delays: Optional[int] = None        # None: derived from N by the spiking network's rule
    sample_sizes: bool = True             # draw the neurons per group (multinomial) instead of the mean
    use_delays: bool = True
    active_eps: float = 0.01              # groups with r_E below this (over the history) neither send nor learn
    transfer: str = "izhikevich"          # "izhikevich" (round 3): curves derived from the engine neuron model; "sigmoid0" / "sigmoid" (round 2)
    noise_sigma: float = 5.0              # fitted (round 3): Gaussian input-noise width smoothing the derived curves
    injection_mode: str = "subpop"          # "mean": injected current averaged over the group's E neurons; "subpop": the k injected neurons as a subpopulation (round 3 option)
    input_scale: float = 1.0              # option: common factor on the input current; 1 = derived scale (not fitted unless it demonstrably misses)
    # fitted parameters
    theta: float = 5.0
    beta: float = 0.5
    tau: float = 10.0
    tau_i_ratio: float = 1.0              # option: tau of the inhibitory units = ratio * tau (not fitted; 1 = same)
    tau_i: Optional[float] = None         # option: absolute tau of the inhibitory units (overrides the ratio), e.g. the A_g window 20

    @property
    def G(self) -> int:
        return self.grid_dim ** 3

    @property
    def N(self) -> int:
        return int(round(self.neurons_per_group * self.G))

    @property
    def D(self) -> int:
        """Delay count: explicit n_delays; else the engine's rule for N when it gives this grid; else (larger grids
        are built with assoc_build.build_network(n_delays=...), archive-pre-engine-fix/params/session73-*.json: 16 for 9^3, 20 for 11^3)
        the smallest D whose grid int(D / sqrt(3)) equals grid_dim."""
        if self.n_delays is not None:
            return int(self.n_delays)
        d = delay_count(self.N)
        if int(d / math.sqrt(3)) == self.grid_dim:
            return d
        return min(x for x in range(2, 21) if int(x / math.sqrt(3)) == self.grid_dim)

    @property
    def stray_limit(self) -> int:
        return int(self.max_active_frac * self.G)

    @classmethod
    def from_session(cls, path: str, job: int = 0, **over) -> "Spec":
        """Derive the spec from a spiking session file (e.g. archive-pre-engine-fix/params/session69a-stage2.json)."""
        with open(path) as f:
            d = json.load(f)
        j = d["jobs"][job]
        p = j["params"]
        eng = j.get("engine", d.get("engine", {}))
        pr, pl = p["protocol"], p["plasticity"]
        kw = dict(
            S=eng["n_synapses"], lam=eng["rewire"]["lam"], neurons_per_group=eng["n_neurons"] / 343.0,
            w_ee=p["weights"]["w_ee"], w_intra_ee_total=p["weights"]["w_intra_ee_total"], gain=p["gain"],
            gain_ei=p["gain_ei"], gain_ie=p["gain_ie"], gain_ee_inter=p["gain_ee_inter"],
            i_min=p.get("i_min"), i_max=p.get("i_max"), k_inject=p["k_inject"], inject_current=p["inject_current"],
            plasticity_rule=pl["rule"], a_pre=pl["a_pre"], a_plus=pl["a_plus"], a_minus=pl["a_minus"],
            tau_fast=pl["tau_fast"], kappa=pl["kappa"], theta1=pl["theta1"], soft1=pl["soft1"],
            theta2=pl["theta2"], soft2=pl["soft2"], c1=dict(p["c1"]), c2=dict(p["c2"]),
            max_c1_rounds=pr["max_c1_rounds"], c2_rounds=pr["c2_rounds"],
            max_extra_c2_rounds=pr["max_extra_c2_rounds"], max_active_frac=pr["max_active_frac"],
            pair_distance=pr["pair_distance"], accept_uncontained=pr["accept_uncontained"])
        kw.update(over)
        return cls(**kw)


# --------------------------------------------------------------------------------------------------
# Lattice and connectivity
# --------------------------------------------------------------------------------------------------

def lattice_coords(dim: int) -> np.ndarray:
    """(G, 3) cell coordinates; group index = x * dim^2 + y * dim + z (as in the spiking network)."""
    idx = np.arange(dim ** 3)
    return np.stack([idx // (dim * dim), (idx // dim) % dim, idx % dim], axis=1).astype(float)


def group_distances(dim: int) -> np.ndarray:
    c = lattice_coords(dim)
    return np.linalg.norm(c[:, None, :] - c[None, :, :], axis=2)


def synapse_kernel(dist: np.ndarray, lam: float) -> np.ndarray:
    """exp(-d / lam), own group included (assoc_engine.rewire_by_distance: kern)."""
    return np.exp(-dist / float(lam))


def group_sizes(spec: Spec, rng: Optional[np.random.Generator]) -> Tuple[np.ndarray, np.ndarray]:
    """Excitatory and inhibitory neurons per group. Positions are uniform, so a type's neurons per group are
    multinomial (rng given and spec.sample_sizes) or equal to the mean."""
    G, N = spec.G, spec.N
    n_exc = int(round(spec.exc_frac * N))
    n_inh = N - n_exc
    if rng is not None and spec.sample_sizes:
        return (rng.multinomial(n_exc, np.full(G, 1.0 / G)).astype(float),
                rng.multinomial(n_inh, np.full(G, 1.0 / G)).astype(float))
    return np.full(G, n_exc / G), np.full(G, n_inh / G)


def _target_probs(kern: np.ndarray, n_target: np.ndarray) -> np.ndarray:
    """P(target group g | presynaptic group j) proportional to n_target[g] * kern[j, g]."""
    p = kern * n_target[None, :]
    return p / p.sum(axis=1, keepdims=True)


def expected_counts(spec: Spec, n_exc: np.ndarray, n_inh: np.ndarray, dist: np.ndarray) -> Dict[str, np.ndarray]:
    """Expected synapses j -> g for given group sizes (the means of sample_counts)."""
    kern = synapse_kernel(dist, spec.lam)
    S = spec.S
    return {
        "EE": (n_exc * S * (1.0 - spec.frac_E_to_I))[:, None] * _target_probs(kern, n_exc),
        "EI": (n_exc * S * spec.frac_E_to_I)[:, None] * _target_probs(kern, n_inh),
        "IE": (n_inh * S * spec.frac_I_to_E)[:, None] * _target_probs(kern, n_exc),
    }


def sample_counts(spec: Spec, n_exc: np.ndarray, n_inh: np.ndarray, dist: np.ndarray,
                  rng: np.random.Generator) -> Dict[str, np.ndarray]:
    """
    Synapse counts between groups, one realization. Every synapse of a presynaptic neuron lands in a group
    with probability proportional to (neurons of the target type there) * exp(-d / lam) (assoc_engine.py
    rewire_by_distance); synapses of one presynaptic group are independent, so its counts are multinomial.
    Per-neuron synapse numbers by type: S * (1 - frac_E_to_I) E -> E and S * frac_E_to_I E -> I per
    excitatory neuron, S I -> E per inhibitory neuron (n_type_groups.py). Autapses (rewired away in the spiking
    network) are not removed; they affect only the own group's count by about 1 / n.
    """
    G = spec.G
    kern = synapse_kernel(dist, spec.lam)
    out = {}
    for key, n_pre, n_per, n_tgt in (
            ("EE", n_exc, spec.S * (1.0 - spec.frac_E_to_I), n_exc),
            ("EI", n_exc, spec.S * spec.frac_E_to_I, n_inh),
            ("IE", n_inh, spec.S * spec.frac_I_to_E, n_exc)):
        P = _target_probs(kern, n_tgt)
        tot = np.rint(n_pre * n_per).astype(np.int64)
        M = np.zeros((G, G))
        for j in range(G):
            M[j] = rng.multinomial(int(tot[j]), P[j])
        out[key] = M
    return out


# --------------------------------------------------------------------------------------------------
# Chemical field (assoc_fields.ChemicalField) on the group lattice
# --------------------------------------------------------------------------------------------------

class ChemicalFieldLattice:
    """
    ChemicalField on the cell lattice. The spiking fields live on a voxel grid with `vox_per_cell` voxels per
    cell and axis; the diffusion constant k (per step, in voxel units) becomes k / v^2 in cell units, and the
    release of a spike (gain at the neuron's voxel) becomes gain / v^3 on the cell mean. Per step:
        c <- clamp((c + k * lap(c)) * (1 - decay) - depreciation, 0, c_max), then sources clamped,
    zero-flux boundaries (laplacian_zero_flux).
    """
    MAX_STABLE_K = 1.0 / 6.0

    def __init__(self, dim: int, k: float, decay: float = 0.0, depreciation: float = 0.0, c_max: float = 2000.0,
                 vox_per_cell: int = 4, voxel_k: bool = True):
        self.dim = int(dim)
        self.v = int(vox_per_cell)
        self.k = float(k) / (self.v ** 2) if voxel_k else float(k)
        if not 0.0 <= self.k <= self.MAX_STABLE_K + 1e-12:
            raise ValueError(f"k={self.k} outside the stable range")
        self.decay, self.depreciation, self.c_max = float(decay), float(depreciation), float(c_max)
        self.c = np.zeros((dim, dim, dim))
        self.source = np.zeros_like(self.c)
        ax = np.arange(dim)
        lo, hi = np.maximum(ax - 1, 0), np.minimum(ax + 1, dim - 1)
        idx = np.arange(dim ** 3).reshape(dim, dim, dim)
        self._nb = np.stack([idx[lo][:, :, :], idx[hi][:, :, :], idx[:, lo, :], idx[:, hi, :],
                             idx[:, :, lo], idx[:, :, hi]]).reshape(6, -1)     # zero-flux: edge neighbour = self

    def reset(self):
        self.c[:] = 0.0
        self.source[:] = 0.0

    def release(self, spikes_per_group: np.ndarray, gain: float, saturation: Optional[float] = None):
        """spikes_per_group (G,): spikes in the step; the release is spread over the cell's v^3 voxels."""
        if gain == 0.0:
            return
        counts = spikes_per_group.reshape(self.dim, self.dim, self.dim) / (self.v ** 3)
        if saturation:
            s = float(saturation)
            inc = counts * gain * np.clip(1.0 - self.c / s, 0.0, None)
            self.c = np.where(self.c < s, np.minimum(self.c + inc, s), self.c)
        else:
            self.c = self.c + counts * gain
        np.clip(self.c, None, self.c_max, out=self.c)

    def laplacian(self) -> np.ndarray:
        f = self.c.reshape(-1)
        return (f[self._nb].sum(axis=0) - 6.0 * f).reshape(self.c.shape)

    def diffuse(self, substeps: int = 1):
        mask = self.source > 0.0
        if not mask.any() and not self.c.any() and self.depreciation == 0.0:
            return                                   # all zero stays zero
        for _ in range(substeps):
            c = self.c + self.k * self.laplacian()
            if self.decay != 0.0:
                c = c * (1.0 - self.decay)
            if self.depreciation != 0.0:
                c = c - self.depreciation
            c = np.clip(c, 0.0, self.c_max)
            if mask.any():
                c = np.where(mask, self.source, c)
            self.c = c

    def flat(self) -> np.ndarray:
        return self.c.reshape(-1)


def gate(c: np.ndarray, threshold: float, softness: float) -> np.ndarray:
    """assoc_plasticity.gate: 0 below threshold, 1 above threshold + softness, linear between."""
    if softness <= 0.0:
        return (c >= threshold).astype(float)
    return np.clip((c - threshold) / softness, 0.0, 1.0)


# --------------------------------------------------------------------------------------------------
# The rate network
# --------------------------------------------------------------------------------------------------

class RateNetwork:
    """One realization of the network: sampled group sizes and synapse counts, coupling, state, plasticity."""

    def __init__(self, spec: Spec, seed: int = 0, counts: Optional[Dict[str, np.ndarray]] = None,
                 sizes: Optional[Tuple[np.ndarray, np.ndarray]] = None):
        self.spec = spec
        self.seed = int(seed)
        rng = np.random.default_rng(self.seed)
        self.G = G = spec.G
        self.dist = group_distances(spec.grid_dim)
        self.coords = lattice_coords(spec.grid_dim)
        self.nE, self.nI = sizes if sizes is not None else group_sizes(spec, rng)
        self.nE = np.maximum(self.nE, 1.0)
        self.nI = np.maximum(self.nI, 1.0)
        self.counts = counts if counts is not None else sample_counts(spec, self.nE, self.nI, self.dist, rng)
        s = spec
        # --- derived coupling: current per step into a postsynaptic neuron per unit of presynaptic spikes/step
        # gain_map (assoc_engine.set_gains): E -> E inter-group gain * gain_ee_inter; E -> I gain * gain_ei;
        # I -> E gain * gain_ie. Per postsynaptic neuron: synapses j -> g divided by the group's neurons.
        M_EE = self.counts["EE"].copy()
        np.fill_diagonal(M_EE, 0.0)           # own group: intra-group rule below
        self.A_EE = s.gain * s.gain_ee_inter * M_EE / self.nE[None, :]     # times w (normalized) times nu r_j
        self.A_EI = s.gain * s.gain_ei * self.counts["EI"] / self.nI[None, :]
        self.A_IE = s.gain * s.gain_ie * abs(s.w_ie) * self.counts["IE"] / self.nE[None, :]
        # intra-group E -> E: weights = w_intra_ee_total / in-degree (typed_weights), times gain (set_gains,
        # no gain_ee_inter within an assembly): summed input when the whole group fires = total * gain
        self.intra = np.where(self.counts["EE"].diagonal() > 0, s.w_intra_ee_total * s.gain, 0.0)
        # delays (assoc_engine.rewire_by_distance): round((D - 1) * d / d_max)
        D = s.D
        dmax = self.dist.max()
        self.delay = (np.rint((D - 1) * self.dist / max(dmax, 1e-9)).astype(int)
                      if s.use_delays else np.zeros((G, G), dtype=int))
        self.D = D
        self.H = max(2 * int(self.delay.max()) + 2, 2 * D + 2, s.window + 2)   # history length
        self.nu = s.nu_act
        self.c1 = ChemicalFieldLattice(s.grid_dim, s.c1["k"], s.c1["decay"], vox_per_cell=s.vox_per_cell)
        self.c2 = ChemicalFieldLattice(s.grid_dim, s.c2["k"], s.c2["decay"], vox_per_cell=s.vox_per_cell)
        if s.transfer == "izhikevich":
            self._curve_E = smoothed_rate_curve("E", s.noise_sigma, s.i_min if s.i_min is not None else -100.0, s.i_max if s.i_max is not None else 100.0)
            self._curve_I = smoothed_rate_curve("I", s.noise_sigma, s.i_min if s.i_min is not None else -100.0, s.i_max if s.i_max is not None else 100.0)
        if s.transfer == "izhikevich":
            self._nuA_E = activity_from_rate_table("E", s.window, s.noise_sigma)
        self._noise_floor = 1.0 / (1.0 + math.exp(s.beta * s.theta))     # sigmoid(-beta theta)
        self.reset_plasticity()
        self.reset_dynamics()
        self.fast_decay = math.exp(-1.0 / s.tau_fast) if s.tau_fast > 0 else 0.0

    # -- state ------------------------------------------------------------------------------------
    def reset_dynamics(self):
        self.rE = np.zeros(self.G)
        self.rI = np.zeros(self.G)
        self.hE = np.zeros((self.H, self.G))
        self.hI = np.zeros((self.H, self.G))
        self.t = 0

    def reset_plasticity(self):
        G, s = self.G, self.spec
        self.wf_ee = np.zeros((G, G))
        self.wp_ee = np.full((G, G), s.w_ee)
        self.wf_ei = np.zeros((G, G))
        self.wp_ei = np.full((G, G), s.w_ei)

    def reset_all(self):
        self.c1.reset()
        self.c2.reset()
        self.reset_plasticity()
        self.reset_dynamics()

    # -- transfer function ------------------------------------------------------------------------
    def transfer(self, x: np.ndarray, kind: str = "E") -> np.ndarray:
        """Target r (rate relative to nu_act) for input current x. 'izhikevich': derived curve of the population type,
        r = rate / nu_act (spikes per step of the population over the measured rate of an active neuron)."""
        s = self.spec
        if s.transfer == "izhikevich":
            grid, rate = self._curve_E if kind == "E" else self._curve_I
            return np.interp(s.input_scale * x, grid, rate) / s.nu_act
        z = np.clip(s.beta * (x - s.theta), -50.0, 50.0)
        sig = 1.0 / (1.0 + np.exp(-z))
        if s.transfer == "sigmoid":
            return sig
        if s.transfer == "sigmoid0":
            f = self._noise_floor
            return np.clip((sig - f) / (1.0 - f), 0.0, 1.0) * (x > 0)
        raise ValueError(f"unknown transfer {s.transfer!r}")

    def activity(self, r: np.ndarray) -> np.ndarray:
        """A_g (fraction of E neurons that fired in the window) for a rate r (relative to nu_act); identity for the
        round-2 transfer forms, where r itself is the active fraction."""
        if self.spec.transfer != "izhikevich":
            return r
        nu, A = self._nuA_E
        return np.interp(self.spec.nu_act * r, nu, A)

    # -- effective weights -------------------------------------------------------------------------
    def weights(self, mode: str = "effective") -> Tuple[np.ndarray, np.ndarray]:
        """(w_ee, w_ei) normalized weights: 'effective' = clip(w_perm + w_fast), 'perm' = w_perm only."""
        s = self.spec
        if mode == "perm":
            return np.clip(self.wp_ee, s.w_lo, s.w_hi), np.clip(self.wp_ei, s.w_lo, s.w_hi)
        return (np.clip(self.wp_ee + self.wf_ee, s.w_lo, s.w_hi), np.clip(self.wp_ei + self.wf_ei, s.w_lo, s.w_hi))

    # -- one step ----------------------------------------------------------------------------------
    def _delayed(self, hist: np.ndarray, rows: np.ndarray) -> np.ndarray:
        """(len(rows), G): r[rows[a]] at lag delay[rows[a], g]."""
        lag = self.delay[rows]                                   # (na, G)
        return hist[(self.t - lag) % self.H, rows[:, None]]

    def step(self, inj: Optional[np.ndarray] = None, w_ee: Optional[np.ndarray] = None,
             w_ei: Optional[np.ndarray] = None, learn: bool = False, consolidate: bool = False,
             release1: bool = False, release2: bool = False, chem: bool = True):
        s = self.spec
        act = np.nonzero(self.hE.max(axis=0) > s.active_eps)[0]
        actI = np.nonzero(self.hI.max(axis=0) > s.active_eps)[0]
        xE = self.intra * self.nu * self.rE
        xI = np.zeros(self.G)
        if len(act):
            if w_ee is None:       # effective weights of the active presynaptic rows only
                we = np.clip(self.wp_ee[act] + self.wf_ee[act], s.w_lo, s.w_hi)
                wi = np.clip(self.wp_ei[act] + self.wf_ei[act], s.w_lo, s.w_hi)
            else:
                we, wi = w_ee[act], w_ei[act]
            rdE = self._delayed(self.hE, act)                      # (na, G) delayed r_E of presynaptic groups
            xE += (self.A_EE[act] * we * rdE).sum(axis=0) * self.nu
            xI += (self.A_EI[act] * wi * rdE).sum(axis=0) * self.nu
        if len(actI):
            rdI = self._delayed(self.hI, actI)
            xE -= (self.A_IE[actI] * rdI).sum(axis=0) * self.nu
        if inj is not None:
            xE += inj
        if s.i_min is not None or s.i_max is not None:
            xE = np.clip(xE, s.i_min, s.i_max)
            xI = np.clip(xI, s.i_min, s.i_max)
        tE = self.transfer(xE, "E")
        if inj is not None and s.injection_mode == "subpop":
            f = np.clip(inj / s.inject_current, 0.0, 1.0)          # fraction of the group's E neurons that is injected
            tE = np.where(f > 0, (1.0 - f) * tE + f * self.transfer(np.minimum(xE + s.inject_current, s.i_max if s.i_max is not None else 1e9), "E"), tE)
        tI = self.transfer(xI, "I")
        newE = self.rE + (tE - self.rE) / s.tau
        newI = self.rI + (tI - self.rI) / (s.tau_i if s.tau_i is not None else s.tau * s.tau_i_ratio)
        self.rE, self.rI = newE, newI
        self.t += 1
        self.hE[self.t % self.H] = self.rE      # so plasticity sees the updated rates at lag 0
        self.hI[self.t % self.H] = self.rI
        if chem:
            spk = self.nu * (self.nE * self.rE + self.nI * self.rI)
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

    # -- plasticity --------------------------------------------------------------------------------
    def _plasticity(self, learn: bool, consolidate: bool):
        """assoc_plasticity.GatedPlasticity.step with spike products replaced by rate products."""
        s = self.spec
        if learn:
            act = np.nonzero(self.hE.max(axis=0) > s.active_eps)[0]
            g1 = gate(self.c1.flat(), s.theta1, s.soft1)
            if len(act):
                nu_r = self.nu * self.rE
                rule = s.plasticity_rule
                mats = [("ee", self.wf_ee, self.wp_ee)]
                if s.plastic_ei:
                    mats.append(("ei", self.wf_ei, self.wp_ei))
                for name, wf, wp in mats:
                    eff = np.clip(wp[act] + wf[act], s.w_lo, s.w_hi)
                    shape = eff * (s.w_hi - eff)
                    dw = np.zeros_like(eff)
                    if rule in ("pre_c1", "both"):
                        dw += (s.a_pre * nu_r[act] * g1[act])[:, None] * g1[None, :] * shape
                    if rule in ("stdp", "both"):
                        dw += self._stdp(act, shape, g1)
                    if name == "ee":
                        dw[np.arange(len(act)), act] = 0.0       # intra-group E -> E is fixed
                    wf[act] += dw
        if learn or consolidate:
            if consolidate:
                g12 = gate(self.c1.flat(), s.theta1, s.soft1) * gate(self.c2.flat(), s.theta2, s.soft2)
                for wf, wp in ((self.wf_ee, self.wp_ee), (self.wf_ei, self.wp_ei)):
                    moved = s.kappa * g12[None, :] * wf
                    wp += moved
                    wf -= moved
                np.clip(self.wp_ee, s.w_lo, s.w_hi, out=self.wp_ee)
                np.clip(self.wp_ei, s.w_lo, s.w_hi, out=self.wp_ei)
            self.wf_ee *= self.fast_decay
            self.wf_ei *= self.fast_decay

    def _stdp(self, act: np.ndarray, shape: np.ndarray, g1: np.ndarray) -> np.ndarray:
        """
        Rate form of the STDP terms for presynaptic groups `act` (rows) onto the active groups `act`
        (columns; the terms vanish where the post unit is silent), returned as an (na, G) array:
        potentiation: post fires now, pre fired within the last 2D + 1 steps;
        depression: a pre spike arrives now (fired delay steps ago) and post fired in the delay steps before it.
        Spike probabilities per step are nu * r; independent steps; probabilities of 'fired within a window'
        from the product of (1 - nu r) over the window.
        """
        s = self.spec
        H, t = self.H, self.t
        W = 2 * self.D + 1
        ks = (t - np.arange(W)) % H
        hist_act = self.hE[:, act]                                                                           # (H, na)
        pf_pre = 1.0 - np.exp(np.log1p(-np.minimum(self.nu * hist_act[ks], 0.99)).sum(axis=0))                               # (na,)
        ltp = s.a_plus * (self.nu * self.rE[act])[None, :] * pf_pre[:, None]                               # (na, na)
        lag = self.delay[np.ix_(act, act)]
        r_pre = hist_act[(t - lag) % H, np.arange(len(act))[:, None]]
        cum = np.concatenate([np.zeros((1, len(act))),
                              np.cumsum(np.log1p(-np.minimum(self.nu * hist_act[(t - np.arange(H)) % H], 0.99)), axis=0)], axis=0)
        hi_k = np.minimum(2 * lag + 1, H)
        lo_k = np.minimum(lag + 1, H)
        cols = np.broadcast_to(np.arange(len(act))[None, :], lag.shape)
        pf_post = 1.0 - np.exp(cum[hi_k, cols] - cum[lo_k, cols])
        ltd = s.a_minus * self.nu * r_pre * pf_post
        out = np.zeros((len(act), self.G))
        out[:, act] = (ltp - ltd) * shape[:, act] * g1[None, act]
        return out

    # -- helpers for the protocol ---------------------------------------------------------------------
    def injection(self, groups: List[int]) -> np.ndarray:
        """Mean current per excitatory neuron from injecting k neurons of each group at the given current."""
        inj = np.zeros(self.G)
        for g in groups:
            k = min(self.spec.k_inject, self.nE[g])
            inj[g] = k * self.spec.inject_current / self.nE[g]
        return inj


# --------------------------------------------------------------------------------------------------
# Protocol (assoc_protocol.py: AssocRun.test, protocol_body)
# --------------------------------------------------------------------------------------------------

def path_groups(coords: np.ndarray, a: int, b: int, radius: float = 1.0) -> List[int]:
    """assoc_protocol.AssocRun.path_groups: groups (other than A, B) within `radius` cells of segment A-B."""
    pa, pb = coords[a], coords[b]
    ab = pb - pa
    t = np.clip(((coords - pa) @ ab) / max(ab @ ab, 1e-9), 0.0, 1.0)
    d = np.linalg.norm(coords - (pa + t[:, None] * ab), axis=1)
    return [int(g) for g in np.nonzero(d <= radius + 1e-6)[0] if g not in (a, b)]


def run_test(net: RateNetwork, src: int, dst: int, mode: str, exclude: List[int]) -> dict:
    """Inject into src alone, everything frozen; B must reach r >= active within the window (AssocRun.test)."""
    s = net.spec
    net.reset_dynamics()
    w_ee, w_ei = net.weights(mode)
    inj = net.injection([src])
    gmax = np.zeros(net.G)
    for i in range(s.test_window):
        net.step(inj=inj if i < s.inject_steps else None, w_ee=w_ee, w_ei=w_ei, chem=False)
        np.maximum(gmax, net.activity(net.rE), out=gmax)
    outside = np.ones(net.G, dtype=bool)
    outside[[src, dst] + [g for g in exclude if g not in (src, dst)]] = False
    n_out = int((outside & (gmax >= s.active)).sum())
    return {"src_max": float(gmax[src]), "dst_max": float(gmax[dst]), "success": bool(gmax[dst] >= s.active),
            "n_active_outside": n_out, "bounded": n_out <= s.stray_limit,
            "mean_rE_end": float(net.rE.mean())}


def run_round(net: RateNetwork, groups: List[int], learn: bool, consolidate: bool, release1: bool, release2: bool):
    """One round: injection for inject_steps, then the gap (injection off); dynamics reset at the start."""
    s = net.spec
    net.reset_dynamics()
    inj = net.injection(groups)
    for i in range(s.inject_steps + s.gap_steps):
        net.step(inj=inj if i < s.inject_steps else None, learn=learn, consolidate=consolidate,
                 release1=release1, release2=release2)


def run_pair_protocol(net: RateNetwork, a: int, b: int, c2_stage: bool = True, control0: bool = True) -> dict:
    """
    The passing protocol on one pair: joint rounds with learning (rule "both") and a test of A alone on
    w_fast + w_perm after each round, until the first transfer (B active) or max_c1_rounds; then, if
    c2_stage, the short circuit stage (consolidation of w_fast under C2, no new learning) and the final
    strict tests. Class by the first transfer: 'contained' (n_active_outside <= stray limit), 'ignition',
    or 'none'.
    """
    s = net.spec
    net.reset_all()
    path = path_groups(net.coords, a, b)
    out = {"A": a, "B": b, "path": path}
    if control0:
        out["control0"] = {"A_to_B": run_test(net, a, b, "perm", path), "B_to_A": run_test(net, b, a, "perm", path)}
    rounds, first = 0, None
    while rounds < s.max_c1_rounds:
        run_round(net, [a, b], learn=True, consolidate=False, release1=True, release2=False)
        rounds += 1
        t = run_test(net, a, b, "effective", path)
        if t["success"]:
            first = t
            break
    out["c1_rounds"] = rounds
    if first is None:
        out["class"] = "none"
        out["strays"] = None
        return out
    out["class"] = "contained" if first["bounded"] else "ignition"
    out["strays"] = first["n_active_outside"]
    out["first_transfer"] = first
    if not c2_stage:
        return out
    n_c2, final = 0, None
    limit = s.c2_rounds + s.max_extra_c2_rounds
    while n_c2 < limit:
        run_round(net, [a, b], learn=False, consolidate=True, release1=True, release2=True)
        n_c2 += 1
        if n_c2 >= s.c2_rounds:
            final = {"A_to_B": run_test(net, a, b, "perm", path), "B_to_A": run_test(net, b, a, "perm", path)}
            if final["A_to_B"]["success"] or final["B_to_A"]["success"]:
                break
    out["c2_rounds"] = n_c2
    out["final"] = final
    out["association"] = bool(final and any(final[d]["success"] and final[d]["bounded"]
                                            for d in ("A_to_B", "B_to_A")))
    return out


def pick_pairs(spec: Spec, n_pairs: int, margin: int, seed: int) -> List[Tuple[int, int, int]]:
    """
    Pairs at `pair_distance` cells, A and B at least `margin` cells from every face (AssocRun.pick_pair):
    A uniform among the allowed groups, B among the groups nearest to the distance, C one of the 5 groups
    farthest from both.
    """
    rng = np.random.default_rng(seed)
    dim = spec.grid_dim
    cells = lattice_coords(dim)
    inner = ((cells >= margin) & (cells <= dim - 1 - margin)).all(axis=1)
    idx = np.nonzero(inner)[0]
    pairs = []
    while len(pairs) < n_pairs:
        ia = int(idx[rng.integers(len(idx))])
        d = np.linalg.norm(cells - cells[ia], axis=1)
        err = np.abs(d - spec.pair_distance)
        err[ia] = np.inf
        err[~inner] = np.inf
        cand = np.nonzero(err <= err.min() + 1e-6)[0]
        ib = int(rng.choice(cand))
        dab = np.minimum(d, np.linalg.norm(cells - cells[ib], axis=1))
        order = np.argsort(-dab)[:max(1, min(5, dim ** 3 // 10))]
        ic = int(rng.choice(order))
        pairs.append((ia, ib, ic))
    return pairs
