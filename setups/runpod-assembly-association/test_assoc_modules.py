#!/usr/bin/env python3
"""
Analytic checks for the engine-independent modules (assoc_fields.py, assoc_plasticity.py),
and for the numerical safeguards (input-current clamp, runaway stop in AssocRun.run) on a
stub engine. They do not touch snngine_v4. Run:  python test_assoc_modules.py [--device cpu|cuda]
Prints one PASS/FAIL line per check and exits non-zero if any check fails.
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import torch

from assoc_fields import (ChemicalField, EnergyField, FuelField, GroupActivity, VoxelMap,
                          laplacian_zero_flux)
from assoc_plasticity import GatedPlasticity, delays_from_N_delays, gate

CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


def close(a, b, tol=1e-4):
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(a)), abs(float(b)))


# ---------------------------------------------------------------- fields

@check
def laplacian_matches_naive_loop(dev):
    torch.manual_seed(0)
    c = torch.rand((4, 5, 3), device=dev)
    lap = laplacian_zero_flux(c)
    X, Y, Z = c.shape
    for i in range(X):
        for j in range(Y):
            for k in range(Z):
                s = 0.0
                for di, dj, dk in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                    a, b, e = i + di, j + dj, k + dk
                    inside = 0 <= a < X and 0 <= b < Y and 0 <= e < Z
                    s += float(c[a, b, e]) if inside else float(c[i, j, k])
                assert close(lap[i, j, k], s - 6 * float(c[i, j, k]), 1e-5)


@check
def conservation_without_decay(dev):
    torch.manual_seed(1)
    f = ChemicalField((9, 7, 8), dev, k=0.16)
    f.c = torch.rand(f.dims, device=dev) * 100
    m0 = f.c.sum().item()
    f.diffuse(200)
    assert close(f.c.sum().item(), m0, 1e-4), (f.c.sum().item(), m0)


@check
def symmetric_diffusion(dev):
    f = ChemicalField((11, 11, 11), dev, k=0.16)
    f.c[5, 5, 5] = 1000.0
    f.diffuse(30)
    c = f.c
    for flipped in (c.flip(0), c.flip(1), c.flip(2), c.permute(1, 0, 2), c.permute(2, 1, 0)):
        assert torch.allclose(c, flipped, atol=1e-4)
    assert c[5, 5, 5] > c[5, 5, 7] > c[5, 5, 9] > 0


@check
def release_proportional_to_spikes(dev):
    pos = torch.tensor([[0.1, 0.1, 0.1], [0.12, 0.1, 0.1], [0.9, 0.9, 0.9]], device=dev)
    vm = VoxelMap(pos, (1, 1, 1), (4, 4, 4))
    assert vm.lin.tolist() == [0, 0, 63]
    f = ChemicalField((4, 4, 4), dev)
    for scale in (1.0, 3.0):
        f.reset()
        spikes = torch.tensor([True, True, False], device=dev)
        f.release(vm.counts(spikes), gain=2.5 * scale)
        assert close(f.c[0, 0, 0], 5.0 * scale) and close(f.c.sum(), 5.0 * scale)


@check
def release_saturates(dev):
    f = ChemicalField((2, 2, 2), dev)
    counts = torch.zeros((2, 2, 2), device=dev)
    counts[0, 0, 0] = 1
    f.release(counts, gain=1.0, saturation=4.0)       # 1 * (1 - 0/4) = 1
    assert close(f.c[0, 0, 0], 1.0)
    f.release(counts, gain=1.0, saturation=4.0)       # + 1 * (1 - 1/4) = 1.75
    assert close(f.c[0, 0, 0], 1.75)
    for _ in range(200):
        f.release(counts * 5, gain=1.0, saturation=4.0)
    assert float(f.c[0, 0, 0]) <= 4.0 + 1e-5 and close(f.c[0, 1, 0], 0.0)


@check
def exponential_decay(dev):
    f = ChemicalField((3, 3, 3), dev, k=0.0, decay=0.01)
    f.c.fill_(100.0)
    f.diffuse(50)
    assert torch.allclose(f.c, torch.full_like(f.c, 100 * 0.99 ** 50), rtol=1e-4)


@check
def clamped_source_and_cap(dev):
    f = ChemicalField((7, 7, 7), dev, k=0.16, c_max=2000.0)
    f.source[3, 3, 3] = 2000.0
    f.c[3, 3, 3] = 2000.0
    f.diffuse(40)
    assert close(f.c[3, 3, 3], 2000.0) and f.c.max() <= 2000.0 and f.c[3, 3, 5] > 0


@check
def unstable_k_rejected(dev):
    try:
        ChemicalField((3, 3, 3), dev, k=0.2)
    except ValueError:
        return
    raise AssertionError("k > 1/6 accepted")


@check
def energy_consumption_proportional(dev):
    e = EnergyField((2, 2, 2), dev, consume=0.1, recover=0.05)
    counts = torch.zeros((2, 2, 2), device=dev)
    counts[0, 0, 0] = 1
    counts[1, 1, 1] = 3
    e.step(counts)
    assert close(e.e[0, 0, 0], 0.9) and close(e.e[1, 1, 1], 0.7) and close(e.e[0, 1, 0], 1.0)


@check
def energy_recovers_after_activity_stops(dev):
    e = EnergyField((2, 2, 2), dev, consume=0.5, recover=0.05)
    counts = torch.ones((2, 2, 2), device=dev)
    e.step(counts)
    e0 = e.e[0, 0, 0].item()
    zero = torch.zeros_like(counts)
    for _ in range(100):
        e.step(zero)
    expected = 1.0 - (1.0 - e0) * 0.95 ** 100
    assert close(e.e[0, 0, 0], expected, 1e-4) and e.e[0, 0, 0] > 0.99


@check
def fuel_rests_at_reference_with_fixed_total_supply(dev):
    f = FuelField((4, 4, 4), dev, supply=0.02, decay=0.01, consume=0.0)
    zero = torch.zeros((4, 4, 4), device=dev)
    for _ in range(50):
        f.step(zero)
    assert close(f.c_ref, 2.0) and torch.allclose(f.e, torch.ones_like(f.e), atol=1e-5)   # resting level
    counts = torch.zeros_like(zero)
    counts[0, 0, 0] = 3.0
    f.step(counts)
    assert close(float((f.supply * f.share()).sum()), 0.02 * 64, 1e-4)    # total delivery independent of activity


@check
def fuel_delivered_where_used_and_depleted_globally(dev):
    zero = torch.zeros((4, 4, 4), device=dev)
    active = zero.clone()
    active[:2] = 1.0                                            # half of the voxels fire every step
    # no consumption: delivery follows use, so the active half gains fuel and the quiet half loses it
    f = FuelField((4, 4, 4), dev, supply=0.01, decay=0.01, consume=0.0, tau=20.0, floor=0.1)
    for _ in range(300):
        f.step(active)
    assert float(f.e[:2].mean()) > 1.5 and float(f.e[2:].mean()) < 0.5, (float(f.e[:2].mean()), float(f.e[2:].mean()))
    # everything active with consumption: the fixed total supply cannot keep up, fuel drops everywhere
    g = FuelField((4, 4, 4), dev, supply=0.01, decay=0.01, consume=0.02)
    for _ in range(300):
        g.step(torch.ones_like(zero))
    assert float(g.e.max()) < 0.5, float(g.e.max())
    vm = type("VM", (), {"sample": staticmethod(lambda field: field.reshape(-1))})()
    assert float(f.excitability(vm).max()) <= f.cap + 1e-6     # capped excitability


@check
def fuel_mode_selected_by_energy_params(dev):
    from assoc_protocol import AssocRun
    eng = StubEngine(dev)
    run = AssocRun(eng, {"k_inject": 2, "energy": {"enabled": True, "mode": "fuel", "supply": 0.02, "decay": 0.01,
                                                   "consume": 0.5, "beta": 2.0}})
    assert isinstance(run.E, FuelField) and close(run.E.c_ref, 2.0) and run.E.beta == 2.0
    assert isinstance(AssocRun(StubEngine(dev), {"k_inject": 2}).E, EnergyField)


@check
def group_activity_window(dev):
    groups = torch.tensor([0, 0, 0, 0, 1, 1], device=dev)
    ga = GroupActivity(groups, 2, window=20)
    spikes = torch.tensor([True, True, False, False, False, False], device=dev)
    a = ga.update(spikes, 0)
    assert close(a[0], 0.5) and close(a[1], 0.0)
    none = torch.zeros(6, dtype=torch.bool, device=dev)
    for t in range(1, 20):
        a = ga.update(none, t)
    assert close(a[0], 0.5)
    a = ga.update(none, 20)
    assert close(a[0], 0.0)


# ---------------------------------------------------------------- plasticity

def tiny_network(dev, D=5):
    """3 neurons, S = 2: 0 -> 1 (delay 0), 0 -> 2 (delay 2), 1 -> 2 (delay 0), 1 -> 0 (delay 1),
    2 -> 0 (delay 0), 2 -> 1 (delay 3). All excitatory."""
    n_rep = torch.tensor([[1, 2, 0], [2, 0, 1]], device=dev)
    # bucket boundaries (D + 1, N): neuron 0: s0 in d0, s1 in d2; neuron 1: s0 in d0, s1 in d1;
    # neuron 2: s0 in d0, s1 in d3
    n_delays = torch.tensor([[0, 0, 0], [1, 1, 1], [1, 2, 1], [2, 2, 1], [2, 2, 2], [2, 2, 2]], device=dev)
    delay = delays_from_N_delays(n_delays, 2)
    w = torch.full((2, 3), 0.5, device=dev)
    return n_rep, delay, w


def make_plasticity(dev, **kw):
    n_rep, delay, w = tiny_network(dev)
    pre_exc = torch.ones(3, dtype=torch.bool, device=dev)
    params = dict(a_plus=0.1, a_minus=0.1, tau_fast=100.0, kappa=0.5, theta1=1.0, theta2=1.0)
    params.update(kw)
    return GatedPlasticity(n_rep, delay, pre_exc, w, D=5, **params)


def run_spikes(p, schedule, steps, c1, c2, learn=True, consolidate=False):
    for t in range(steps):
        spikes = torch.zeros(3, dtype=torch.bool, device=p.dev)
        for n in schedule.get(t, []):
            spikes[n] = True
        p.step(spikes, t, c1, c2, learn=learn, consolidate=consolidate)


@check
def delay_buckets_decoded(dev):
    _, delay, _ = tiny_network(dev)
    assert delay.tolist() == [[0, 0, 0], [2, 1, 3]], delay.tolist()


@check
def causal_pair_potentiates(dev):
    p = make_plasticity(dev, tau_fast=0)  # tau_fast <= 0: w_fast must not persist ...
    p.fast_decay = 1.0                     # ... so disable decay explicitly for this check
    hi = torch.full((3,), 5.0, device=dev)
    run_spikes(p, {0: [0], 3: [1]}, 4, hi, hi)
    w = p.w_fast
    assert w[0, 0] > 0, w           # 0 -> 1: pre at 0, post at 3 -> potentiation
    expected = 0.1 * 0.5 * (1.0 - 0.5)
    assert close(w[0, 0], expected, 1e-5), (w[0, 0].item(), expected)
    # 2 -> 1 never had a pre spike: unchanged
    assert w[1, 2] == 0


@check
def acausal_pair_depresses(dev):
    p = make_plasticity(dev)
    p.fast_decay = 1.0
    hi = torch.full((3,), 5.0, device=dev)
    # synapse 0 -> 2 has delay 2: pre fires at t=5, arrives at t=7; post 2 fired at t=4 (in [3, 5))
    run_spikes(p, {4: [2], 5: [0]}, 8, hi, hi)
    assert p.w_fast[1, 0] < 0, p.w_fast
    assert close(p.w_fast[1, 0], -0.1 * 0.25, 1e-5)


@check
def no_change_when_gate_off(dev):
    p = make_plasticity(dev)
    zero = torch.zeros(3, device=dev)
    run_spikes(p, {0: [0], 1: [1, 2], 3: [0, 1], 5: [2]}, 10, zero, zero, consolidate=True)
    assert torch.count_nonzero(p.w_fast) == 0 and torch.equal(p.w_perm, torch.full((2, 3), 0.5, device=dev))


@check
def only_gated_region_changes(dev):
    p = make_plasticity(dev)
    p.fast_decay = 1.0
    c1 = torch.tensor([0.0, 5.0, 0.0], device=dev)  # only neuron 1 sits in a high-C1 region
    sched = {t: [0, 1, 2] for t in range(0, 30, 3)}
    run_spikes(p, sched, 30, c1, c1)
    changed = p.w_fast != 0
    post_in_gate = (p.post == 1)
    assert bool(changed.any()) and not bool((changed & ~post_in_gate).any()), (changed, p.post)


@check
def bounds_respected(dev):
    p = make_plasticity(dev, a_plus=5.0, a_minus=0.0, kappa=1.0)
    p.fast_decay = 1.0
    hi = torch.full((3,), 5.0, device=dev)
    sched = {t: [0, 1, 2] for t in range(0, 300)}
    run_spikes(p, sched, 300, hi, hi, consolidate=True)
    w = p.effective()
    assert float(w.max()) <= 1.0 + 1e-6 and float(w.min()) >= 0.05 - 1e-6
    assert float(p.w_perm.max()) <= 1.0 + 1e-6


@check
def fast_weights_decay_as_specified(dev):
    p = make_plasticity(dev, tau_fast=50.0)
    p.w_fast.fill_(0.2)
    hi = torch.full((3,), 5.0, device=dev)
    run_spikes(p, {}, 100, hi, hi)  # learning on, no spikes: pure decay
    assert torch.allclose(p.w_fast, torch.full_like(p.w_fast, 0.2 * math.exp(-100 / 50.0)), rtol=1e-4)
    frozen = p.w_fast.clone()
    run_spikes(p, {}, 20, hi, hi, learn=False, consolidate=False)
    assert torch.equal(p.w_fast, frozen)  # frozen phase: no decay, no change


@check
def permanent_weights_persist(dev):
    p = make_plasticity(dev, tau_fast=20.0, kappa=0.5)
    p.w_fast.fill_(0.2)
    hi = torch.full((3,), 5.0, device=dev)
    run_spikes(p, {}, 1, hi, hi, consolidate=True)
    perm = p.w_perm.clone()
    assert torch.allclose(perm, torch.full_like(perm, 0.6))
    zero = torch.zeros(3, device=dev)
    run_spikes(p, {}, 500, zero, zero, consolidate=True)
    assert torch.equal(p.w_perm, perm) and float(p.w_fast.abs().max()) < 1e-6


@check
def consolidation_onto_excitatory_only(dev):
    n_rep, delay, w = tiny_network(dev)
    pre_exc = torch.tensor([True, True, False], device=dev)   # neuron 2 inhibitory
    hi = torch.full((3,), 5.0, device=dev)
    for ee_only in (False, True):
        p = GatedPlasticity(n_rep, delay, pre_exc, w, D=5, kappa=0.5, theta1=1.0, theta2=1.0,
                            consolidate_ee_only=ee_only)
        p.w_fast.fill_(0.2)
        run_spikes(p, {}, 1, hi, hi, consolidate=True)
        exc_pre = pre_exc.view(1, 3).expand(2, 3)
        onto_inh = exc_pre & (p.post == 2)                     # 0 -> 2, 1 -> 2: E -> I
        onto_exc = exc_pre & (p.post != 2)
        assert torch.allclose(p.w_perm[onto_exc], torch.full_like(p.w_perm[onto_exc], 0.6))
        want = 0.5 if ee_only else 0.6
        assert torch.allclose(p.w_perm[onto_inh], torch.full_like(p.w_perm[onto_inh], want)), (ee_only, p.w_perm)


@check
def fixed_synapses_neither_plastic_nor_clipped(dev):
    n_rep, delay, w = tiny_network(dev)
    w[0, 0] = 5.0  # 0 -> 1 boosted above the bound (shortcut 1)
    fixed = torch.zeros_like(w, dtype=torch.bool)
    fixed[0, 0] = True
    p = GatedPlasticity(n_rep, delay, torch.ones(3, dtype=torch.bool, device=dev), w, D=5,
                        a_plus=0.1, a_minus=0.1, kappa=0.5, fixed=fixed)
    hi = torch.full((3,), 5.0, device=dev)
    run_spikes(p, {t: [0, 1, 2] for t in range(0, 30, 3)}, 30, hi, hi, consolidate=True)
    assert float(p.effective()[0, 0]) == 5.0 and float(p.w_fast[0, 0]) == 0.0
    assert float(p.w_perm[0, 0]) == 5.0
    assert bool((p.w_fast[~fixed] != 0).any())


@check
def pre_c1_rule_needs_no_post_spike(dev):
    # neuron 0 fires alone, inside high C1; its targets (1 and 2) never fire
    for post_gate, c1, expect_changed in (
            (False, [5.0, 0.0, 0.0], [(0, 0), (1, 0)]),   # every outgoing synapse of 0
            (True, [5.0, 5.0, 0.0], [(0, 0)]),            # only 0 -> 1 (target in high C1)
            (True, [0.0, 5.0, 5.0], [])):                 # pre outside high C1: nothing
        p = make_plasticity(dev, rule="pre_c1", a_pre=0.2, pre_post_gate=post_gate)
        p.fast_decay = 1.0
        c = torch.tensor(c1, device=dev)
        run_spikes(p, {0: [0]}, 1, c, c)
        changed = sorted(tuple(int(x) for x in ij) for ij in torch.nonzero(p.w_fast).tolist())
        assert changed == expect_changed, (post_gate, c1, changed)
        for s, n in changed:
            assert close(p.w_fast[s, n], 0.2 * 0.25, 1e-5)


@check
def weight_dependence_upper(dev):
    hi = torch.full((3,), 5.0, device=dev)
    # causal 0 -> 1 potentiates by a_plus (1 - w); acausal 0 -> 2 depresses by a_minus w (w = 0.5)
    p = make_plasticity(dev, weight_dep="upper")
    p.fast_decay = 1.0
    run_spikes(p, {0: [0], 3: [1]}, 4, hi, hi)
    assert close(p.w_fast[0, 0], 0.1 * 0.5, 1e-5), p.w_fast
    p = make_plasticity(dev, weight_dep="upper")
    p.fast_decay = 1.0
    run_spikes(p, {4: [2], 5: [0]}, 8, hi, hi)
    assert close(p.w_fast[1, 0], -0.1 * 0.5, 1e-5), p.w_fast
    # at the lower bound 0.05 the presynaptic rule is 1 / 0.05 = 20 times faster than "mult"
    n_rep, delay, _ = tiny_network(dev)
    w0 = torch.full((2, 3), 0.05, device=dev)
    dws = {}
    for dep in ("mult", "upper"):
        q = GatedPlasticity(n_rep, delay, torch.ones(3, dtype=torch.bool, device=dev), w0, D=5,
                            rule="pre_c1", a_pre=0.2, theta1=1.0, weight_dep=dep)
        q.fast_decay = 1.0
        run_spikes(q, {0: [0]}, 1, hi, hi)
        dws[dep] = float(q.w_fast[0, 0])
    assert close(dws["upper"], 0.2 * 0.95, 1e-5) and close(dws["upper"] / dws["mult"], 20.0, 1e-3), dws


@check
def normalization_caps_input_sums(dev):
    p = make_plasticity(dev, a_plus=5.0, a_minus=0.0, norm_factor=1.0)
    p.fast_decay = 1.0
    hi = torch.full((3,), 5.0, device=dev)
    run_spikes(p, {t: [0, 1, 2] for t in range(0, 30, 3)}, 30, hi, hi)
    sums = p._input_sums(p.effective())
    assert bool((sums <= p.norm_target + 1e-5).all()), (sums, p.norm_target)
    q = make_plasticity(dev, a_plus=5.0, a_minus=0.0)            # without: the sums grow
    q.fast_decay = 1.0
    run_spikes(q, {t: [0, 1, 2] for t in range(0, 30, 3)}, 30, hi, hi)
    assert bool((q._input_sums(q.effective()) > p.norm_target + 1e-3).any())


@check
def transmission_events_and_capture(dev):
    p = make_plasticity(dev)
    s0 = torch.tensor([True, False, False], device=dev)
    p.observe(s0, 0)                                              # neuron 0 fires at t = 0
    ev = p.ltp_events(torch.tensor([False, True, False], device=dev), 3)   # neuron 1 fires at t = 3
    assert bool(ev[0, 0]) and int(ev.sum()) == 1, ev               # only 0 -> 1 transmitted
    p.w_fast.fill_(0.2)
    w0 = p.w_perm.clone()
    p.capture(ev, 1.0)
    assert close(p.w_perm[0, 0], 0.7) and close(p.w_fast[0, 0], 0.0)
    assert torch.equal(p.w_perm[~ev], w0[~ev]) and bool((p.w_fast[~ev] == 0.2).all())


@check
def soft_gate_shape(dev):
    c = torch.tensor([0.0, 1.0, 1.5, 2.0, 3.0], device=dev)
    assert gate(c, 1.0, 0.0).tolist() == [0, 1, 1, 1, 1]
    assert gate(c, 1.0, 1.0).tolist() == [0, 0, 0.5, 1, 1]


# ---------------------------------------------------------------- safeguards (stub engine)

class StubEngine:
    """
    Stands in for AssocEngine (no snngine_v4): N neurons in G location groups along x, all
    excitatory, S = 2 synapses each. step() fires the neurons listed in `fire[t]` (default: none).
    """

    def __init__(self, dev, N=40, G=4, fire=None):
        from assoc_engine import ROW_I
        self.device, self.N, self.S, self.D, self.G = dev, N, 2, 3, G
        self.seg, self.reservoir_shape = (G, 1, 1), (1.0, 1.0, 1.0)
        self.groups = torch.arange(N, device=dev) * G // N
        self.pos = torch.stack([(self.groups.float() + 0.5) / G, torch.full((N,), 0.5, device=dev),
                                torch.full((N,), 0.5, device=dev)], dim=1)
        self.exc = torch.ones(N, dtype=torch.bool, device=dev)
        self.n_rep = torch.stack([(torch.arange(N, device=dev) + 1) % N, (torch.arange(N, device=dev) + 2) % N])
        self._delay_cache = torch.zeros((self.S, N), dtype=torch.long, device=dev)
        self.group_cell = torch.stack([torch.arange(G, device=dev), torch.zeros(G, dtype=torch.long, device=dev),
                                       torch.zeros(G, dtype=torch.long, device=dev)], dim=1)
        self.cell_size = torch.tensor([1.0 / G, 1.0, 1.0], device=dev)
        self.states = torch.zeros((8, N), device=dev)
        self.row_i = ROW_I
        self.weights = torch.full((self.S, N), 0.5, device=dev)
        self.fire = fire or {}
        self.t = 0

    def step(self):
        self.t += 1
        s = torch.zeros(self.N, dtype=torch.bool, device=self.device)
        s[self.fire.get(self.t, [])] = True
        self.states[self.row_i].zero_()
        return s

    seed = 0

    def set_noise(self, **kw): self.noise = kw
    def set_gains(self, *a): pass

    def typed_weights(self, **kw):
        w = torch.full((self.S, self.N), 0.5, device=self.device)
        return self.draw_inter_ee(w, kw["inter_ee"]) if kw.get("inter_ee") else w

    def inter_ee_mask(self):
        from assoc_engine import AssocEngine
        return AssocEngine.inter_ee_mask(self)

    def intra_ee_mask(self):
        from assoc_engine import AssocEngine
        return AssocEngine.intra_ee_mask(self)

    def draw_inter_ee(self, w, spec):
        from assoc_engine import AssocEngine
        return AssocEngine.draw_inter_ee(self, w, spec)
    def write_weights(self, w): self.weights.copy_(w)
    def read_weights(self): return self.weights.clone()
    def reset_dynamics(self): pass
    def add_current(self, idx, current): self.states[self.row_i, idx] += float(current)
    def add_current_vector(self, current): self.states[self.row_i] += current
    def input_current(self): return self.states[self.row_i]
    def scale_current(self, f): self.states[self.row_i] *= f

    def clamp_current(self, i_min=None, i_max=None):
        from assoc_engine import AssocEngine
        AssocEngine.clamp_current(self, i_min, i_max)

    assembly = None

    def set_assemblies(self, mask):
        from assoc_engine import AssocEngine
        AssocEngine.set_assemblies(self, mask)

    def assembly_of_neuron(self):
        from assoc_engine import AssocEngine
        return AssocEngine.assembly_of_neuron(self)


@check
def input_current_clamped_both_ways(dev):
    eng = StubEngine(dev, N=4)
    row = torch.tensor([-500.0, -50.0, 50.0, 7800.0], device=dev)
    for i_min, i_max, want in ((-100.0, 100.0, [-100, -50, 50, 100]), (-100.0, None, [-100, -50, 50, 7800]),
                               (None, 100.0, [-500, -50, 50, 100])):
        eng.states[eng.row_i] = row
        eng.clamp_current(i_min, i_max)
        assert eng.states[eng.row_i].tolist() == want, (i_min, i_max, eng.states[eng.row_i].tolist())


def stub_run(dev, fire, **params):
    from assoc_protocol import AssocRun
    eng = StubEngine(dev, fire=fire)
    base = {"inject_steps": 5, "gap_steps": 5, "test_window": 10, "k_inject": 2}
    base.update(params)
    return eng, AssocRun(eng, base)


@check
def runaway_detector_stops_phase(dev):
    fire = {t: [0, 1] for t in range(1, 30)}
    fire[6] = list(range(30))                                # 30 of 40 neurons fire in step 6
    for frac, want_steps in ((0.5, 6), (None, 20), (0.8, 20)):
        eng, run = stub_run(dev, fire, runaway_frac=frac)
        at, ao, ns = run.run(20, track=[0])
        assert at.shape == (want_steps, 1) and ao.shape == (want_steps,) and eng.t == want_steps, (frac, at.shape)
        if want_steps == 6:
            assert run.stopped["step"] == 5 and close(run.stopped["fraction"], 0.75), run.stopped
            assert len(run.runaway_events) == 1 and ns == 2 * 5 + 30 and ao[-1] > 0.5
        else:
            assert run.stopped is None and not run.runaway_events
    _, run = stub_run(dev, {3: list(range(20))}, runaway_frac=0.5)   # exactly half: not more than half
    run.run(10)
    assert run.stopped is None


@check
def runaway_in_training_stops_before_consolidation(dev):
    from assoc_protocol import protocol_body
    # round 1: steps 1-10, test after it: 11-20, round 2: 21-30; everything fires in step 25
    eng, run = stub_run(dev, {25: list(range(40))}, runaway_frac=0.5,
                        protocol={"max_c1_rounds": 5, "c2_after_max_rounds": True})
    out = protocol_body(run, 0, 1, 3)
    assert out["runaway_round"] == 2 and out["c1_rounds"] == 2 and "c2_rounds" not in out, out["runaway_round"]
    assert out["c1_log"][-1]["runaway"]["engine_t"] == 25
    assert torch.equal(run.P.w_perm, run.base_w)               # nothing consolidated
    assert out["final"]["A_to_B"]["runaway"] is None and len(out["runaway_events"]) == 1


@check
def intra_weights_normalized_by_in_degree(dev):
    from assoc_engine import AssocEngine
    eng = StubEngine(dev)          # n -> n+1, n -> n+2; groups of 10 neurons
    eng.built_weights = torch.full((eng.S, eng.N), 0.3, device=dev)
    for cap, want_single in ((None, 1.0), (0.6, 0.6)):
        w = AssocEngine.typed_weights(eng, w_intra_ee_total=1.0, w_intra_ee_cap=cap)
        post = eng.n_rep
        same = eng.groups[post] == eng.groups.view(1, -1)
        # in-degree within the group: 0 for the first neuron, 1 for the second, 2 for the rest
        for s, n in ((0, 0), (0, 4), (1, 3), (0, 9), (1, 8)):
            p = int(post[s, n])
            if not bool(same[s, n]):
                assert close(w[s, n], 0.3), (s, n, float(w[s, n]))          # between groups: unchanged
            elif p % 10 == 1:
                assert close(w[s, n], want_single), (s, n, float(w[s, n]))  # sole intra input
            else:
                assert close(w[s, n], 0.5), (s, n, float(w[s, n]))          # two intra inputs share 1.0


@check
def inter_group_gain_only_between_groups(dev):
    from assoc_engine import AssocEngine
    eng = StubEngine(dev)          # all excitatory; n -> n+1, n -> n+2; groups of 10
    AssocEngine.set_gains(eng, 4.0, 1.0, 1.0, 2.0)
    same = eng.groups[eng.n_rep] == eng.groups.view(1, -1)
    assert torch.equal(eng.gain_map[same], torch.full_like(eng.gain_map[same], 4.0))
    assert torch.equal(eng.gain_map[~same], torch.full_like(eng.gain_map[~same], 8.0)) and bool((~same).any())
    # sparse assemblies: synapses within a non-assembly group are ordinary synapses too
    eng.set_assemblies(torch.tensor([True, False, True, False], device=dev))
    AssocEngine.set_gains(eng, 4.0, 1.0, 1.0, 2.0)
    in_asm = same & eng.assembly[eng.groups].view(1, -1)
    assert bool((eng.gain_map[in_asm] == 4.0).all()) and bool((eng.gain_map[~in_asm] == 8.0).all())


@check
def inter_group_inhibition_gains_only_between_groups(dev):
    from assoc_engine import AssocEngine
    eng = StubEngine(dev)          # n -> n+1, n -> n+2; groups of 10; positions 0, 2, 4, 6, 9 excitatory
    r = torch.arange(eng.N, device=dev) % 10
    eng.exc = (r == 0) | (r == 2) | (r == 4) | (r == 6) | (r == 9)
    AssocEngine.set_gains(eng, 4.0, 1.0, 2.0, 1.0, False, 0.5, 0.25)
    post = eng.n_rep.long()
    pre_exc = eng.exc.view(1, -1).expand_as(post)
    post_exc = eng.exc[post]
    between = eng.groups[post] != eng.groups.view(1, -1)
    ei, ie = pre_exc & ~post_exc, ~pre_exc & post_exc
    assert bool((eng.gain_map[ie & between] == 4.0 * 2.0 * 0.25).all()) and bool((ie & between).any())
    assert bool((eng.gain_map[ei & between] == 4.0 * 0.5).all()) and bool((ei & between).any())
    assert bool((eng.gain_map[ie & ~between] == 8.0).all()) and bool((ei & ~between).any())
    assert bool((eng.gain_map[ei & ~between] == 4.0).all())
    assert bool((eng.gain_map[pre_exc & post_exc] == 4.0).all())


@check
def inter_group_gain_normalized_by_in_degree(dev):
    from assoc_engine import AssocEngine
    eng = StubEngine(dev)          # n -> n+1, n -> n+2; groups of 10: neurons 0, 10, 20, 30 receive two
    AssocEngine.set_gains(eng, 4.0, 1.0, 1.0, 2.0, True)   # inter-group inputs, 1, 11, 21, 31 one
    post = eng.n_rep.long()
    inter = eng.groups[post] != eng.groups.view(1, -1)
    tot = torch.zeros(eng.N, device=dev).index_add_(0, post[inter], eng.gain_map[inter])
    n_in = torch.zeros(eng.N, device=dev).index_add_(0, post[inter], torch.ones_like(eng.gain_map[inter]))
    # mean in-degree 1.5: every receiving neuron's summed inter-group gain is 4 * 2 * 1.5 = 12
    assert torch.allclose(tot[n_in > 0], torch.full_like(tot[n_in > 0], 12.0)), tot
    assert sorted(set(n_in[n_in > 0].tolist())) == [1.0, 2.0]
    assert bool((eng.gain_map[~inter] == 4.0).all())


@check
def assembly_layouts_keep_one_cell_apart(dev):
    from assoc_protocol import assembly_layout
    r = torch.arange(7, device=dev)
    cells = torch.stack(torch.meshgrid(r, r, r, indexing="ij"), dim=-1).view(-1, 3)
    assert assembly_layout(cells, {"layout": "all"}) is None
    for spec, n in (({"layout": "lattice", "spacing": 2}, 64), ({"layout": "random", "count": 30, "seed": 3}, 30)):
        m = assembly_layout(cells, spec)
        assert int(m.sum()) == n, (spec, int(m.sum()))
        c = cells[m]
        cheb = (c.view(-1, 1, 3) - c.view(1, -1, 3)).abs().max(dim=2).values
        cheb.fill_diagonal_(99)
        assert int(cheb.min()) >= 2, (spec, int(cheb.min()))   # at least one non-assembly cell between


@check
def intra_boost_only_inside_assemblies(dev):
    from assoc_engine import AssocEngine
    eng = StubEngine(dev)          # groups of 10 along x: 0, 1, 2, 3
    eng.built_weights = torch.full((eng.S, eng.N), 0.3, device=dev)
    eng.set_assemblies(torch.tensor([True, False, True, False], device=dev))
    w = AssocEngine.typed_weights(eng, w_intra_ee=5.0)
    same = eng.groups[eng.n_rep] == eng.groups.view(1, -1)
    in_asm = eng.assembly[eng.groups].view(1, -1).expand_as(same)
    assert bool((w[same & in_asm] == 5.0).all()) and bool((w[same & ~in_asm] == 0.3).all())
    assert bool((w[~same] == 0.3).all())
    fixed = AssocEngine.intra_ee_mask(eng)
    assert torch.equal(fixed, same & in_asm)


@check
def pairs_and_path_with_sparse_assemblies(dev):
    from assoc_protocol import AssocRun
    eng = StubEngine(dev, N=60, G=6)                 # cells (0..5, 0, 0)
    run = AssocRun(eng, {"assemblies": {"layout": "lattice", "spacing": 2}, "k_inject": 2})
    assert run.asm == [0, 2, 4]
    for _ in range(10):
        a, b, c = run.pick_pair(2.0)
        assert {a, b, c} <= {0, 2, 4} and a != b and abs(a - b) == 2
    assert run.path_groups(0, 4, radius=0.5) == [1, 3]   # assembly 2 on the line is not path
    full = AssocRun(eng, {"k_inject": 2})
    assert full.asm == list(range(6)) and full.path_groups(0, 4, radius=0.5) == [1, 2, 3]
    # bridges (iteration 47): assembly 2 on the route counts as path
    br = AssocRun(eng, {"assemblies": {"layout": "lattice", "spacing": 2}, "k_inject": 2, "bridges": True})
    assert br.path_groups(0, 4, radius=0.5) == [1, 2, 3]


@check
def energy_per_phase(dev):
    _, run = stub_run(dev, {}, energy={"enabled": False, "in_c2": True})
    assert [run.phase_energy(ph) for ph in ("c1", "c2", "test")] == [False, True, False]
    _, run = stub_run(dev, {}, energy={"enabled": True, "in_test": False})
    assert [run.phase_energy(ph) for ph in ("c1", "c2", "test")] == [True, True, False]


@check
def uncontained_transfer_accepted_on_request(dev):
    from assoc_protocol import protocol_body
    # everything fires during the first C1-phase test (steps 11 to 20): B active, C active as well
    for accept in (False, True):
        eng, run = stub_run(dev, {t: list(range(40)) for t in range(11, 21)},
                            protocol={"max_c1_rounds": 3, "accept_uncontained": accept})
        out = protocol_body(run, 0, 1, 3)
        assert out["c1_rounds"] == 1 and not out["c1_log"][0]["test_A_to_B"]["contained"]
        if accept:
            assert out["c1_test_passed"] and out["runaway_round"] is None and out["c2_rounds"] >= 5, out["c2_rounds"]
        else:
            assert out["runaway_round"] == 1 and "c2_rounds" not in out


@check
def containment_relative_to_control0(dev):
    # group 3 spills in every test (as in the untrained baseline); group 2 only in the third
    g2, g3 = list(range(20, 30)), list(range(30, 40))
    _, run = stub_run(dev, {5: g3, 15: g3, 25: g2 + g3})
    t0 = run.test(0, 1, None, strict=True)
    run.baselines[(0, 1)] = run.last_group_max.clone()
    assert "others_excess_over_control0" not in t0 and not t0["contained"]
    t1 = run.test(0, 1, None, strict=True)
    assert not t1["contained"] and t1["contained_rel_control0"] and close(t1["others_excess_over_control0"], 0.0)
    t2 = run.test(0, 1, None, strict=True)
    assert not t2["contained_rel_control0"] and close(t2["others_excess_over_control0"], 1.0)


@check
def inject_end_hook_called_once(dev):
    eng, run = stub_run(dev, {})
    calls = []
    run.run(10, inject_steps=5, on_inject_end=lambda: calls.append(eng.t))
    assert calls == [5], calls
    run.run(10, inject_steps=0, on_inject_end=lambda: calls.append(eng.t))
    assert calls == [5], calls                                   # no injection: never called


@check
def weight_change_split_adds_up(dev):
    eng, run = stub_run(dev, {})
    eng.exc[5] = False                                          # one inhibitory target
    w0 = run.base_w.clone()
    w1 = w0.clone()
    w1[0, :] += 0.1                                             # every n -> n+1 synapse changes
    st = run.weight_change_stats(w0, w1, 0, 2)
    sp = st["split"]
    tot = sum(sp[b]["post_exc"] + sp[b]["post_inh"] for b in sp)
    assert close(tot, st["sum_dw"], 1e-3), (tot, st["sum_dw"])
    along = sum(sum(sp[b]["along"].values()) for b in sp)
    assert close(along, st["sum_dw"], 1e-3), (along, st["sum_dw"])
    assert close(sp["on_line"]["post_inh"] + sp["off_line"]["post_inh"], 0.1, 1e-5)   # only 4 -> 5
    assert sp["on_line"]["n_post_exc"] + sp["off_line"]["n_post_exc"] + 1 == st["n_changed"]


@check
def direct_synapses_found_and_frozen(dev):
    eng, run = stub_run(dev, {})           # n -> n+1, n -> n+2; groups of 10 along x
    m = run.direct_mask(0, 1)
    pairs = sorted((int(n), int(eng.n_rep[s, n])) for s, n in zip(*torch.nonzero(m, as_tuple=True)))
    assert pairs == [(8, 10), (9, 10), (9, 11)], pairs
    st = run.direct_stats(0, 1)
    assert st["A_to_B"]["n"] == 3 and st["B_to_A"]["n"] == 0 and close(st["A_to_B"]["w_exc_sum"], 1.5)
    assert bool(run.P.plastic[m].all())
    run.frozen_pair = (0, 1)
    run.reset_all()
    assert not bool(run.P.plastic[m].any()) and bool(run.P.plastic[~m & run.P.valid].all())


def rewired_stub(dev, lam, N=80, G=4, inh=(0, 1, 40, 41)):
    from assoc_engine import AssocEngine
    from assoc_plasticity import delays_from_N_delays
    eng = StubEngine(dev, N=N, G=G)
    eng.exc[list(inh)] = False
    eng.n_rep[:, list(inh)] = (eng.n_rep[:, list(inh)] + 3) % N     # inhibitory sources ...
    eng.n_rep[:, list(inh)] = torch.where(eng.exc[eng.n_rep[:, list(inh)]], eng.n_rep[:, list(inh)],
                                          (eng.n_rep[:, list(inh)] + 1) % N)   # ... onto excitatory targets
    eng.n_delays = torch.zeros((eng.D + 1, N), dtype=torch.int32, device=dev)
    eng.n_delays[1:] = eng.S
    eng.weights = torch.rand((eng.S, N), device=dev)
    before = (eng.exc[eng.n_rep.long()].clone(), eng.weights.clone())
    AssocEngine.rewire_by_distance(eng, lam=lam, seed=1)
    return eng, before, delays_from_N_delays(eng.n_delays, eng.S)


@check
def rewiring_keeps_types_and_delays(dev):
    for lam in (0.05, 100.0):
        eng, (tgt_exc0, w0), d = rewired_stub(dev, lam)
        post = eng.n_rep.long()
        pre = torch.arange(eng.N, device=dev).view(1, -1).expand_as(post)
        assert bool((post != pre).all())                                       # no autapses
        assert torch.equal(eng.exc[post].sort(dim=0).values, tgt_exc0.sort(dim=0).values)  # types per neuron
        assert bool((eng.exc[post] | eng.exc.view(1, -1)).all())               # inhibitory -> excitatory only
        assert torch.allclose(eng.weights.sort(dim=0).values, w0.sort(dim=0).values)        # weights moved with
        cells = eng.group_cell.float()
        dist = torch.cdist(cells, cells)
        want = torch.round((eng.D - 1) * dist[eng.groups[pre], eng.groups[post]] / dist.max()).long()
        assert torch.equal(d, want), (d, want)                                 # bucket = engine delay rule
        assert bool((d[1:] >= d[:-1]).all())                                   # sorted per neuron
        same = eng.groups[post] == eng.groups[pre]
        if lam < 1:   # steep: own group (every group has excitatory neurons, not every one inhibitory)
            assert bool(same[eng.exc[post]].all()), float(same.float().mean())
        else:
            assert float(same.float().mean()) < 0.6                            # flat: spread over groups


@check
def gate_profile_categories(dev):
    eng, run = stub_run(dev, {})
    run.C1.c.fill_(20.0)
    run.C2.c.fill_(20.0)
    g = run.gate_profile(0, 3, [1])
    assert set(g) == {"AB", "path", "other"} and g["AB"]["n"] == 20 and g["path"]["n"] == 10
    assert all(close(g[k]["g12"], 1.0) and close(g[k]["frac_g12_open"], 1.0) for k in g)
    run.C2.c.zero_()
    g = run.gate_profile(0, 3, [1])
    assert all(close(g[k]["g12"], 0.0) and close(g[k]["g1"], 1.0) for k in g)


@check
def oracle_tube_fixed_and_restored(dev):
    from assoc_plasticity import gate
    pl = {"theta1": 1.0, "theta2": 1.0, "soft1": 1.0, "soft2": 1.0}
    fire = {t: list(range(60)) for t in range(1, 20)}               # everything fires: release would show
    eng = StubEngine(dev, N=60, G=6, fire=fire)                     # cells (0..5, 0, 0), x = g + 0.5
    from assoc_protocol import AssocRun
    run = AssocRun(eng, {"oracle": {"radius": 1.0}, "plasticity": pl, "k_inject": 2})
    run.set_oracle(0, 3)
    g1 = gate(run.vmap.sample(run.C1.c), 1.0, 1.0)
    want = (eng.groups <= 3).float()                                # groups 0..3 on the segment; 4 at 1.14
    assert torch.equal(g1, want), g1.view(6, 10)[:, 0].tolist()
    c1, c2 = run.C1.c.clone(), run.C2.c.clone()
    run.run(10, release1=True, release2=True)                        # no release, diffusion or decay
    assert torch.equal(run.C1.c, c1) and torch.equal(run.C2.c, c2)
    run.reset_all()
    assert torch.equal(run.C1.c, c1) and torch.equal(run.C2.c, c2)


def region_stub(dev):
    from assoc_protocol import AssocRun
    eng = StubEngine(dev, N=60, G=6)                                 # x = g + 0.5 in cell units
    eng.pos[1::2, 1] = 2.5                                           # odd neurons 2 cells off the line
    return eng, AssocRun(eng, {"sel_radius": 0.5, "k_inject": 2})


@check
def selectivity_regions_middle_and_shell(dev):
    eng, run = region_stub(dev)                                      # A = group 0, B = group 5, d = 5
    nm, ns = run.regions(0, 5)["neuron"]
    n = torch.arange(eng.N, device=dev)
    even = n % 2 == 0
    # M: on the line, x in [1.75, 4.25]; Sh: 2 cells off the line, 1.25 to 2.55 cells from A or B
    # (no neuron on a region boundary, where rounding differs between devices)
    assert torch.equal(nm, even & (eng.groups >= 2) & (eng.groups <= 3))
    assert torch.equal(ns, ~even & ((eng.groups <= 1) | (eng.groups >= 4)))
    sm, ss = run.regions(0, 5)["synapse"]
    assert bool(sm[1, 20]) and not bool(ss[1, 20])                  # 20 -> 22: both on the line, x 2.5
    assert bool(ss[0, 20]) and not bool(sm[0, 20])                  # 20 -> 21: midpoint 1 cell off, 2.24 from A
    run.spike_acc = torch.zeros(eng.N, device=dev)
    run.spike_acc[nm] = 2.0
    run.spike_acc[ns] = 1.0
    sel = run.selectivity(0, 5)
    assert close(sel["M"]["spikes_per_exc"], 2.0) and close(sel["ratio"]["spikes_per_exc"], 2.0), sel


@check
def propagation_survey_counts(dev):
    from assoc_protocol import prop_survey
    # 7 groups along x, every neuron fires every step: identical activity in all three conditions,
    # so M = round length per neuron and convergence = M / (M + M) = 0.5; distance 5 keeps every
    # neuron off the region boundaries
    eng = StubEngine(dev, N=70, G=7, fire={t: list(range(70)) for t in range(1, 200)})
    eng.seed = 0
    res = prop_survey(eng, {"inject_steps": 5, "gap_steps": 5, "k_inject": 2,
                            "protocol": {"pair_distance": 5.0}}, "", n_pairs=2)
    assert res["n_pairs"] == 2 and eng.t == 2 * 4 * 10, eng.t
    for r in res["pairs"]:
        assert abs(r["pair"][0] - r["pair"][1]) == 5 and r["dist"] == 5.0
        for cond in ("joint", "A", "B", "none"):
            assert close(r[cond]["M"], 10.0) and not r[cond]["runaway"], r
            assert close(r[cond]["exc_out"], 10.0) and r[cond]["inh_out"] is None, r   # stub: all excitatory
        assert close(r["convergence"], 0.5), r
    assert close(res["summary"]["M_joint"], 10.0) and res["summary"]["runaway_pairs"] == 0


@check
def bridge_activity_per_condition(dev):
    from assoc_protocol import prop_survey
    # 7 groups along x, lattice spacing 2: assemblies 0, 2, 4, 6; a pair at distance 4 has one bridge
    # in the middle. Groups 2 and 4 fire only during the joint condition (steps 1 to 10), so the bridge
    # is active under joint injection and inactive under A, B and none (activity is reset in between)
    eng = StubEngine(dev, N=70, G=7, fire={t: list(range(20, 30)) + list(range(40, 50)) for t in range(1, 11)})
    eng.seed = 0
    p = {"inject_steps": 5, "gap_steps": 5, "k_inject": 2, "protocol": {"pair_distance": 4.0},
         "assemblies": {"layout": "lattice", "spacing": 2}}
    r = prop_survey(eng, dict(p, bridges=True), "", n_pairs=1)["pairs"][0]
    a, b = r["pair"][:2]
    assert r["bridges"] == [(a + b) // 2], r["bridges"]
    assert close(r["joint"]["bridge_max"], 1.0), r["joint"]
    assert all(r[c]["bridge_max"] == 0.0 for c in ("A", "B", "none")), r
    assert r["joint"]["others_max"] <= 1.0 and r["A"]["others_max"] == 0.0
    # off-route assemblies (iteration 52): of 0, 2, 4, 6 only the one beyond A or B; group 2 or 4
    # fires under joint injection, but it is A, B or the bridge, never off the route
    assert all(r[c]["off_asm_max"] == 0.0 for c in ("joint", "A", "B", "none")), r
    eng = StubEngine(dev, N=70, G=7)
    eng.seed = 0
    r = prop_survey(eng, dict(p, bridges=False), "", n_pairs=1)["pairs"][0]
    assert r["bridges"] == [] and r["joint"]["bridge_max"] is None    # without bridges: no bridge telemetry


@check
def background_current_and_warmup(dev):
    eng = StubEngine(dev, N=40)
    eng.exc[30:] = False                                            # 10 inhibitory neurons
    from assoc_protocol import AssocRun
    run = AssocRun(eng, {"inject_steps": 5, "gap_steps": 5, "k_inject": 2,
                         "bg": {"mu_e": 5.0, "sigma_e": 0.0, "mu_i": 2.0, "sigma_i": 0.0, "warmup": 7}})
    run.reset_dynamics()
    assert eng.t == 7 and run.steps_run == 0, (eng.t, run.steps_run)   # warm-up steps, not counted
    run.run(1)
    row = eng.states[eng.row_i]
    assert torch.equal(row[:30], torch.full((30,), 5.0, device=dev)) and torch.equal(row[30:], torch.full((10,), 2.0, device=dev))
    eng2 = StubEngine(dev, N=4000)
    run2 = AssocRun(eng2, {"k_inject": 2, "bg": {"mu_e": 1.0, "sigma_e": 3.0, "mu_i": 1.0, "sigma_i": 3.0}})
    run2.run(1)
    r = eng2.states[eng2.row_i]
    assert abs(float(r.mean()) - 1.0) < 0.2 and abs(float(r.std()) - 3.0) < 0.2, (float(r.mean()), float(r.std()))
    # targets "ordinary" (iteration 52): lattice spacing 2 on 4 groups, assemblies 0 and 2 get nothing
    eng3 = StubEngine(dev, N=40)
    run3 = AssocRun(eng3, {"k_inject": 2, "assemblies": {"layout": "lattice", "spacing": 2},
                           "bg": {"mu_e": 5.0, "sigma_e": 0.0, "mu_i": 5.0, "sigma_i": 0.0, "targets": "ordinary"}})
    run3.run(1)
    r = eng3.states[eng3.row_i]
    asm = (eng3.groups == 0) | (eng3.groups == 2)
    assert bool((r[asm] == 0.0).all()) and bool((r[~asm] == 5.0).all()), r


@check
def input_survey_two_sided_signal(dev):
    from assoc_protocol import input_survey

    class InputStub(StubEngine):
        def step(self):                       # every neuron receives synaptic input 1 per step
            s = super().step()
            self.states[self.row_i] += 1.0
            return s

    eng = InputStub(dev, N=70, G=7)
    eng.seed = 0
    res = input_survey(eng, {"inject_steps": 5, "k_inject": 2, "protocol": {"pair_distance": 5.0}}, "", n_pairs=2)
    assert res["n_pairs"] == 2 and eng.t == 2 * 3 * 5, eng.t
    for r in res["pairs"]:
        m = r["M"]
        assert m["n"] > 0 and close(m["I_A"], 1.0) and close(m["I_joint"], 1.0), m
        assert close(m["coinc"], 1.0) and close(m["interaction"], -1.0) and close(m["frac_coinc_over"]["0.5"], 1.0), m
        assert close(m["E_A"], 0.0) and close(m["Inh_A"], 0.0)          # no spikes in the stub: no E / I input
        assert len(r["profile"]) == 8


@check
def capture_protocol_path(dev):
    from assoc_protocol import protocol_body
    # everything fires during the first C1-phase test (steps 11 to 20): B active, every synapse transmits
    eng, run = stub_run(dev, {t: list(range(40)) for t in range(11, 21)},
                        protocol={"max_c1_rounds": 3, "capture": {"kappa": 1.0}, "c2_rounds": 0,
                                  "max_extra_c2_rounds": 0})
    out = protocol_body(run, 0, 1, 3)
    c0, c1 = out["c1_log"][0]["capture"], out["c1_log"][1]["capture"]
    assert c0["captured"] and c0["n_eligible"] > 0 and not c1["captured"], (c0, c1)
    assert out["c1_rounds"] == 3 and not out["c1_test_passed"] and out["final"]["A_to_B"]["dst_max"] == 0.0


@check
def bounded_criterion_counts_active_groups(dev):
    # groups 2 and 3 fire in every step; A = 0, B = 1, path = [2]: one group (3) active outside
    fire = {t: list(range(20, 40)) for t in range(1, 100)}
    for frac, want in ((0.1, False), (0.25, True)):      # limit int(frac * 4 groups): 0, then 1
        _, run = stub_run(dev, fire, protocol={"max_active_frac": frac})
        t = run.test(0, 1, None, strict=True, exclude=[2])
        assert t["n_active_outside"] == 1 and t["active_outside"] == [3] and t["bounded"] is want, (frac, t)
        assert not t["contained"]
    _, run = stub_run(dev, fire)
    t = run.test(0, 1, None, strict=True)                # without a path, groups 2 and 3 both count
    assert t["n_active_outside"] == 2 and t["n_above_inactive_outside"] == 2, t


@check
def capture_control_runs_capture_loop(dev):
    from assoc_protocol import AssocRun, control_run
    # everything fires during the first C1-phase test of the control (steps 11 to 20)
    params = {"inject_steps": 5, "gap_steps": 5, "test_window": 10, "k_inject": 2,
              "protocol": {"capture": {"kappa": 1.0}, "c2_rounds": 0, "max_extra_c2_rounds": 0}}
    eng = StubEngine(dev, fire={t: list(range(40)) for t in range(11, 21)})
    eng.seed = 0
    run = AssocRun(eng, params)
    inj = {0: run.inject_idx_cached(0), 1: run.inject_idx_cached(1)}
    res = control_run(eng, params, 0, 1, 3, 2, mode="gating_off", inj=inj)
    # capture loop limited to the main run's 2 rounds; the capture in round 1 does not give a strict
    # transfer (nothing fires afterwards)
    assert res["body"] == "capture" and res["rounds"] == 2 and not res["c1_test_passed"], res
    assert res["stopped_in"] is None and res["final"]["A_to_B"]["dst_max"] == 0.0
    plain = dict(params, protocol={"c2_rounds": 0})
    eng2 = StubEngine(dev)
    eng2.seed = 0
    res = control_run(eng2, plain, 0, 1, 3, 2, mode="no_chemistry", inj=inj)
    assert res["body"] == "fixed_rounds" and res["rounds"] == 2, res


@check
def separate_control_alternates_injection(dev):
    from assoc_protocol import AssocRun, control_run, round_inject
    assert round_inject({}, 0, "A", "B") == ["A", "B"] and round_inject({"inject_mode": "alternate"}, 3, "A", "B") == ["B"]
    params = {"inject_steps": 5, "gap_steps": 5, "test_window": 10, "k_inject": 2, "protocol": {"c2_rounds": 0}}
    eng = StubEngine(dev)
    eng.seed = 0
    calls = []
    add = eng.add_current
    eng.add_current = lambda idx, cur: (calls.append((eng.t, tuple(idx.tolist()))), add(idx, cur))
    run = AssocRun(eng, params)
    inj = {0: run.inject_idx_cached(0), 1: run.inject_idx_cached(1)}
    calls.clear()
    res = control_run(eng, params, 0, 1, 3, 2, mode="separate", inj=inj)
    a, b = tuple(inj[0].tolist()), tuple(inj[1].tolist())
    train = [c for c in calls if c[0] <= 20]         # two training rounds of 10 steps, then the final tests
    assert [t for t, _ in train] == [1, 2, 3, 4, 5, 11, 12, 13, 14, 15], train
    assert all(i == a for t, i in train if t <= 5) and all(i == b for t, i in train if t >= 11), train
    assert res["body"] == "fixed_rounds" and res["rounds"] == 2, res


@check
def weight_selectivity_per_synapse(dev):
    eng, run = region_stub(dev)
    sm, ss = run.regions(0, 5)["synapse"]
    dw = torch.zeros_like(run.base_w)
    dw[sm] = 0.3
    dw[ss] = 0.1
    ws = run.weight_selectivity(0, 5, dw)
    assert close(ws["M"]["dw_ee"], 0.3) and close(ws["Sh"]["dw_ee"], 0.1) and close(ws["ratio"]["dw_ee"], 3.0)
    assert ws["M"]["n_ei"] == 0 and ws["M"]["dw_ei"] is None and ws["ratio"]["dw_ei"] is None


def _rollback_params(**protocol):
    pr = {"max_active_frac": 0.1, "c2_after_max_rounds": False, "accept_uncontained": True}
    pr.update(protocol)
    # rule pre_c1: one change per spike, linear in the rate scale ("both" adds the STDP change first and
    # computes the presynaptic one from the updated weights, so halving the rates is not exactly linear)
    return {"protocol": pr, "plasticity": {"rule": "pre_c1", "a_pre": 0.1, "theta1": -1.0, "soft1": 0.0}}


@check
def rollback_restores_fast_weights_and_scales_rate(dev):
    from assoc_protocol import protocol_body
    # rounds: steps 1-10, 21-30; tests: 11-20, 31-40. Neurons 0-9 fire once in each round (steps 3, 23);
    # everything fires in test 1 (not bounded: group 3 active outside A = 0, B = 1 and the path)
    fire = {3: list(range(10)), 23: list(range(10))}
    fire.update({t: list(range(40)) for t in range(11, 21)})
    _, ref = stub_run(dev, {3: list(range(10))}, **_rollback_params(max_c1_rounds=1))
    protocol_body(ref, 0, 1, 3)                                  # one round, no rollback: reference w_fast
    assert ref.P.w_fast.abs().sum() > 0
    _, run = stub_run(dev, fire, **_rollback_params(max_c1_rounds=2, rollback={"factor": 0.5, "min_scale": 0.1}))
    out = protocol_body(run, 0, 1, 3)
    l0, l1 = out["c1_log"]
    assert l0["rolled_back"] and l0["scale"] == 1.0 and not l1["rolled_back"] and l1["scale"] == 0.5, (l0, l1)
    assert out["rollback"] == {"n": 1, "exhausted": False, "final_scale": 0.5}, out["rollback"]
    assert out["c1_rounds"] == 2 and not out["c1_test_passed"] and run.P.rate_scale == 1.0
    # round 1 undone, round 2 learned the same spikes at half the rate
    assert torch.allclose(run.P.w_fast, 0.5 * ref.P.w_fast, atol=1e-7)


@check
def rollback_stops_at_min_scale_and_counts_rounds(dev):
    from assoc_protocol import protocol_body
    every_test = {t: list(range(40)) for t in range(1, 200) if ((t - 1) // 10) % 2 == 1}
    rb = {"factor": 0.5, "min_scale": 0.25}
    _, run = stub_run(dev, every_test, **_rollback_params(max_c1_rounds=10, rollback=rb))
    out = protocol_body(run, 0, 1, 3)                            # scales 1, 0.5, 0.25, then below the minimum
    assert out["c1_rounds"] == 3 and out["rollback"] == {"n": 3, "exhausted": True, "final_scale": 0.25}, out["rollback"]
    assert [x["scale"] for x in out["c1_log"]] == [1.0, 0.5, 0.25] and not out["c1_test_passed"]
    _, run = stub_run(dev, every_test, **_rollback_params(max_c1_rounds=2, rollback=rb))
    out = protocol_body(run, 0, 1, 3)                            # the round cap counts rolled-back rounds
    assert out["c1_rounds"] == 2 and out["rollback"] == {"n": 2, "exhausted": False, "final_scale": 0.25}
    # a training round that runs away is undone too (no test after it), instead of ending the phase
    _, run = stub_run(dev, {5: list(range(40))}, runaway_frac=0.5, **_rollback_params(max_c1_rounds=2, rollback=rb))
    out = protocol_body(run, 0, 1, 3)
    assert out["runaway_round"] is None and out["c1_log"][0]["rolled_back"] and "runaway" in out["c1_log"][0]
    assert out["c1_rounds"] == 2 and out["rollback"]["n"] == 1 and out["c1_log"][1]["scale"] == 0.5


@check
def local_inhibition_scales_with_group_activity(dev):
    eng, run = stub_run(dev, {1: list(range(10)) + [10, 11]}, local_inh={"gain": 10.0, "a0": 0.2})
    mask = eng.exc.float()
    mask[5] = 0.0                                                # as if neuron 5 were inhibitory: none
    run.local_inh = (10.0, 0.2, mask)
    run.run(1)
    i = eng.input_current()                                      # group 0 all fired (A 1.0), group 1 2 of 10
    want = torch.zeros(eng.N, device=dev)
    want[:10] = -10.0 * 0.8
    want[5] = 0.0
    assert torch.allclose(i, want, atol=1e-5), i.tolist()


@check
def depression_scales_outgoing_weights_and_restores_them(dev):
    eng, run = stub_run(dev, {1: [0, 2], 2: [0, 2]}, std={"U": 0.5, "tau_rec": 1e9})
    mask = eng.exc.clone()
    mask[2] = False                                              # as if neuron 2 were inhibitory
    run.std = (0.5, 1e9, mask)
    seen = {}
    run.run(3, inject_steps=2, on_inject_end=lambda: seen.update(w=eng.weights.clone()))
    want = torch.full((eng.S, eng.N), 0.5, device=dev)
    want[:, 0] = 0.5 * 0.25                                      # two spikes at U 0.5, no recovery
    assert torch.allclose(seen["w"], want, atol=1e-6), seen["w"][:, :3].tolist()
    assert torch.allclose(eng.weights, torch.full_like(eng.weights, 0.5))   # undepressed after the run


@check
def round_injection_length_leaves_tests_unchanged(dev):
    from assoc_protocol import protocol_body
    _, run = stub_run(dev, {}, gap_steps=0, round_inject_steps=10, **_rollback_params(max_c1_rounds=2))
    calls, real = [], run.run
    def spy(steps, *a, **kw):
        calls.append((kw.get("header", ""), steps, kw.get("inject_steps")))
        return real(steps, *a, **kw)
    run.run = spy
    protocol_body(run, 0, 1, 3)
    rounds = [c for c in calls if "C1 round" in c[0]]
    tests = [c for c in calls if "C1 test" in c[0]]
    assert rounds and all(c[1:] == (10, 10) for c in rounds), rounds    # continuous: no gap
    assert tests and all(c[2] is None for c in tests), tests            # tests: default inject_steps


@check
def uniform_c2_holds_every_voxel_while_released(dev):
    eng, run = stub_run(dev, {1: [0, 1, 2]}, c2={"uniform": 1.5})
    run.run(2, release2=True)
    assert torch.allclose(run.C2.c, torch.full_like(run.C2.c, 1.5))
    run.C2.c.zero_()
    run.run(1, release2=False)                                   # not released: untouched
    assert float(run.C2.c.abs().max()) == 0.0


def _all_ordinary(eng):
    eng.set_assemblies(torch.zeros(eng.G, dtype=torch.bool, device=eng.device))
    return eng


@check
def inter_ee_lognormal_mean_cap_and_unclipped_bounds(dev):
    eng = _all_ordinary(StubEngine(dev, N=400))
    w0 = torch.full((eng.S, eng.N), 0.05, device=dev)
    x = eng.draw_inter_ee(w0, {"kind": "lognormal", "sigma": 1.0, "mean": 0.05, "cap": 0.3,
                               "normalize_out": False})
    assert bool((x > 0).all()) and float(x.max()) <= 0.3 + 1e-6 and float(x.std()) > 0.01
    y = eng.draw_inter_ee(w0, {"kind": "lognormal", "sigma": 1.0, "mean": 0.05})
    assert torch.allclose(y.mean(dim=0), torch.full((eng.N,), 0.05, device=dev), atol=1e-5)   # no hubs
    # initial weights above the plasticity bound 1 and below 0.05 stay as drawn (bounds act on changes)
    from assoc_protocol import AssocRun
    spec = {"kind": "lognormal", "sigma": 1.5, "mean": 1.0, "seed": 3, "normalize_out": False}
    run = AssocRun(eng, {"weights": {"inter_ee": spec}, "assemblies": {"layout": "lattice", "spacing": 2}})
    assert float(run.base_w.max()) > 1.0 and float(run.base_w.min()) < 0.05
    assert torch.allclose(run.P.effective(), run.base_w)


@check
def inter_ee_powerlaw_tail_above_threshold(dev):
    eng = _all_ordinary(StubEngine(dev, N=4000))                  # 2 inter-group synapses per neuron
    w0 = torch.full((eng.S, eng.N), 0.05, device=dev)
    spec = {"kind": "powerlaw", "lam_sup": 0.2, "w_thr": 6.8, "mean": 2.0, "cap": 50.0, "normalize_out": False}
    x = eng.draw_inter_ee(w0, spec)
    frac = float((x > 6.8).float().mean())
    assert abs(frac - 0.1) < 0.015, frac                         # 0.2 per neuron of 2 synapses
    assert abs(float(x.mean()) - 2.0) < 0.2, float(x.mean())
    y = eng.draw_inter_ee(w0, dict(spec, normalize_out=True))
    assert abs(float((y > 6.8).float().mean()) - frac) < 1e-6    # normalization scales the bulk only
    try:
        eng.draw_inter_ee(w0, dict(spec, mean=0.05, cap=None))
        raise AssertionError("an infeasible tail must be refused")
    except ValueError:
        pass


@check
def k5_masks_injected_neurons_in_c2_release_only(dev):
    out = {}
    for k5 in (False, True):
        eng, run = stub_run(dev, {1: [0, 1, 2], 2: [0, 1, 2]}, c2={"no_injected": k5})
        run.run(2, inject=[torch.tensor([0, 1], device=dev)], inject_steps=2, release1=True, release2=True)
        out[k5] = (float(run.C1.c.sum()), float(run.C2.c.sum()))
    assert close(out[True][0], out[False][0])                     # C1 unchanged
    assert close(out[True][1], out[False][1] / 3, tol=1e-4)       # C2 from neuron 2 only


@check
def uniform_c1_holds_every_voxel_while_released(dev):
    eng, run = stub_run(dev, {1: [0, 1, 2]}, c1={"uniform": 0.7})
    run.run(2, release1=True)
    assert torch.allclose(run.C1.c, torch.full_like(run.C1.c, 0.7))
    run.C1.c.zero_()
    run.run(1, release1=False)
    assert float(run.C1.c.abs().max()) == 0.0


@check
def s4_factor_is_one_without_c1_and_at_full_activity(dev):
    eng, run = stub_run(dev, {}, transmission={"gain": 1.0, "c1_half": 0.5, "u_ref": 0.9})
    a0 = torch.zeros(eng.G, device=dev)
    assert torch.allclose(run.transmission_factor(a0), torch.ones(eng.S, eng.N, device=dev))   # C1 = 0
    run.C1.c.fill_(1.0)
    assert torch.allclose(run.transmission_factor(a0), torch.full((eng.S, eng.N), 1 + 1 / 1.5, device=dev))
    assert torch.allclose(run.transmission_factor(torch.full((eng.G,), 0.9, device=dev)),
                          torch.ones(eng.S, eng.N, device=dev))                                # u = 1
    seen = {}
    run.run(3, inject_steps=2, on_inject_end=lambda: seen.update(w=eng.weights.clone()))
    assert float(seen["w"].max()) > 0.5 + 1e-3                                                 # modulated
    assert torch.allclose(eng.weights, torch.full_like(eng.weights, 0.5))                       # restored


@check
def s5_silent_synapses_gated_by_voltage_and_unsilenced(dev):
    eng = _all_ordinary(StubEngine(dev))
    from assoc_protocol import AssocRun
    run = AssocRun(eng, {"silent": {"frac": 1.0, "v_half": -52.5, "v_width": 2.5, "unsilence_w": 0.4}})
    assert bool(run.silent.any()) and bool((run.silent == eng.inter_ee_mask()).all())
    a0 = torch.zeros(eng.G, device=dev)
    eng.states[2].fill_(-65.0)
    f = run.transmission_factor(a0)
    assert float(f[run.silent].max()) < 0.01 and bool((f[~run.silent] == 1).all())             # rest: silent
    eng.states[2].fill_(-40.0)
    assert float(run.transmission_factor(a0)[run.silent].min()) > 0.99                          # depolarized
    run.unsilence()                                               # effective weight 0.5 > 0.4
    assert not bool(run.silent.any())


@check
def hysteresis_and_threshold_jobs_run_and_restore(dev):
    from assoc_protocol import hysteresis_test, single_synapse_threshold
    eng = StubEngine(dev, fire={t: [10, 11] for t in range(1, 10 ** 4)})   # two ordinary neurons fire
    lat = {"assemblies": {"layout": "lattice", "spacing": 2}}                 # groups 1 and 3 ordinary
    r = hysteresis_test(eng, dict(lat, hyst_levels=[0.0, 1.0, 2.0], hyst_steps=10, hyst_measure=5), "")
    assert [x["mu"] for x in r["levels"]] == [0.0, 1.0, 2.0, 1.0, 0.0]          # up, then down
    assert close(r["levels"][0]["rate_ordinary_exc"], 2 / 20) and close(r["loop_area"], 0.0)
    s = single_synapse_threshold(eng, dict(lat, ss_currents=[5.0, 10.0]), "", n_neurons=5)
    assert s["n"] == 5 and torch.allclose(eng.weights, torch.full_like(eng.weights, 0.5))  # base weights back


@check
def assessment_recorder_tracks_permanent_changes(dev):
    import os
    import tempfile
    import numpy as np
    eng, run = stub_run(dev, {})
    eng.group_centroid = torch.stack([(torch.arange(eng.G, device=dev).float() + 0.5) / eng.G,
                                      torch.full((eng.G,), 0.5, device=dev), torch.full((eng.G,), 0.5, device=dev)], 1)
    from assoc_assessment import AssessmentRecorder, PHASE_INDEX
    rec = AssessmentRecorder(run, {"A": 0, "B": 2, "C": 3})     # stub: injection in steps 0 to 4
    a = np.zeros(eng.G, dtype=np.float32)
    for st in (0, 2, 6):
        rec.add(a, None, None, f"main C1 round 1  step {st}/10  t={st}")
    for st in (0, 2):
        rec.add(a, None, None, f"main C2 round 1  step {st}/10  t={20 + st}")
    run.P.w_perm[1, 7] += 0.3                                    # consolidated during the C2 round
    rec.add(a, None, None, "main final A->B  step 0/10  t=40")  # phase change: snapshot at frame 5
    with tempfile.TemporaryDirectory() as tmp:
        n = rec.write(os.path.join(tmp, "v.mp4"), fps=10)
        d = np.load(os.path.join(tmp, "v.npz"))
        assert n == 6 and os.path.getsize(os.path.join(tmp, "v.mp4")) > 0
        J, G = PHASE_INDEX["joint"], PHASE_INDEX["gap"]
        assert d["phase"].tolist() == [J, J, G, PHASE_INDEX["c2"], PHASE_INDEX["c2"], PHASE_INDEX["final"]]
        assert d["pre"].tolist() == [7] and d["post"].tolist() == [int(run.P.post[1, 7])]
        assert d["snap_frames"].tolist() == [0, 5] and abs(float(d["snap_dw"][-1][0]) - 0.3) < 1e-3
        assert float(d["snap_dw"][0][0]) == 0.0                  # unchanged before the C2 round ended


@check
def pair_margin_keeps_pairs_off_the_surface(dev):
    from assoc_protocol import AssocRun

    def grid_run(margin):
        eng = StubEngine(dev, N=250, G=125)                      # stub groups on a 5 x 5 x 5 grid
        eng.seg = (5, 5, 5)
        eng.group_cell = torch.stack(torch.meshgrid(*(torch.arange(5, device=dev),) * 3, indexing="ij"),
                                     dim=-1).view(-1, 3)
        return AssocRun(eng, {"protocol": {"pair_margin": margin}})

    run = grid_run(1)
    for _ in range(30):                                          # from the centre cell the nearest is sqrt(3)
        a, b, c = run.pick_pair(2.0)
        assert min(run.face_margin(a), run.face_margin(b)) >= 1 and abs(run.group_dist(a, b) - 2.0) < 0.3
    run = grid_run(0)
    assert min(min(run.face_margin(g) for g in run.pick_pair(2.0)[:2]) for _ in range(30)) == 0
    try:
        grid_run(2).pick_pair(2.0)                               # only the centre cell is 2 from every face
        raise AssertionError("no error at margin 2")
    except RuntimeError:
        pass


@check
def activity_by_distance_and_intra_density_per_group(dev):
    from assoc_protocol import activity_by_distance, intra_ee_per_group
    cells = torch.tensor([[x, 0, 0] for x in range(5)], device=dev)          # 5 groups along x
    gmax = torch.tensor([0.9, 0.6, 0.05, 0.2, 0.0], device=dev)
    r = activity_by_distance(gmax, cells, 0, inactive=0.1, active=0.5)
    assert sorted(r["by_distance"]) == ["1", "2", "3", "4"] and r["spread_cells"] == 3, r
    d1 = r["by_distance"]["1"]
    assert d1["groups"] == 1 and close(d1["mean"], 0.6) and close(d1["max"], 0.6), r
    assert d1["n_above_inactive"] == 1 and d1["n_active"] == 1, r
    assert r["by_distance"]["2"]["n_above_inactive"] == 0 and r["n_above_inactive"] == 2 and r["n_active"] == 1
    r = activity_by_distance(gmax, cells, 2, inactive=0.1, active=0.5)       # from the middle: 1, 3 and 0, 4
    assert r["by_distance"]["1"]["groups"] == 2 and close(r["by_distance"]["1"]["mean"], 0.4), r
    assert close(r["by_distance"]["2"]["max"], 0.9) and r["spread_cells"] == 2 and r["n_active"] == 2, r
    # stub: neuron i -> i + 1, i + 2 (mod 40), groups of 10: 9 + 8 synapses stay inside each group
    eng = StubEngine(dev)
    assert torch.allclose(intra_ee_per_group(eng), torch.full((4,), 1.7, device=dev)), intra_ee_per_group(eng)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu")
    dev = torch.device(ap.parse_args().device)
    n_fail = 0
    for fn in CHECKS:
        try:
            fn(dev)
            print(f"PASS {fn.__name__}")
        except Exception:
            n_fail += 1
            print(f"FAIL {fn.__name__}")
            traceback.print_exc()
    print(f"{len(CHECKS) - n_fail}/{len(CHECKS)} module checks passed on {dev}")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
