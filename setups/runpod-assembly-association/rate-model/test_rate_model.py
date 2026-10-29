"""
test_rate_model.py

Module checks of the rate model (rate_model.py), round 2. They compare the model with the spiking
network's code and parameters (re-read from the source files, or re-implemented independently here), not
with the model's own formulas:

 1. lattice mapping and the 24 reference pairs' distances;
 2. expected synapse counts against an independent plain-Python re-implementation of rewire_by_distance
    (centre, face, edge, corner source groups; E -> E, E -> I, I -> E);
 3. sampled synapse counts: per-neuron totals exact, mean over realizations within 5 % of the expected counts
    (summed over groups at the same distance), group sizes multinomial;
 4. own-group share of E -> E synapses against the measured 867 / 851 intra-group synapses per excitatory
    neuron of the 9^3 / 11^3 spiking builds (tuning-log.md, iteration 61);
 5. every derived constant against the spiking source (params JSON, assoc_*.py, snngine_v4 config), parsed;
 6. the coupling matrices against the engine's weight formulas (typed_weights, set_gains) applied to a small
    synthetic network with explicit synapses;
 7. delays and delay count against the engine's rules;
 8. ChemicalField against an independent re-implementation, and the cell-lattice conversion;
 9. transfer function, plasticity (rate products, bounds, decay, consolidation), protocol helpers.

Run with the venv of this folder: .venv/Scripts/python.exe -m unittest test_rate_model
"""

import glob
import json
import math
import os
import random
import re
import statistics
import unittest

import numpy as np

from rate_model import (
    DERIVED, Spec, RateNetwork, ChemicalFieldLattice, delay_count, expected_counts, sample_counts, group_sizes,
    group_distances, lattice_coords, gate, path_groups, pick_pairs, run_round, run_test, run_pair_protocol,
    synapse_kernel, izh_params, izh_rates, raw_rate_curve, smoothed_rate_curve, per_neuron_rates,
    activity_from_rate_table, CURVE_GRID,
)
from dataclasses import replace

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(PARENT))
SESSION = os.path.join(PARENT, "params", "session69a-stage2.json")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestLatticeAndCounts(unittest.TestCase):

    def test_lattice_mapping_and_reference_pairs(self):
        c = lattice_coords(7)
        self.assertEqual(c.shape, (343, 3))
        self.assertEqual(tuple(c[5 * 49 + 4 * 7 + 3]), (5, 4, 3))
        gt = json.load(open(os.path.join(HERE, "s71_ground_truth.json"), encoding="utf-8"))
        d = group_distances(7)
        for k, v in gt.items():
            self.assertAlmostEqual(d[v["A"], v["B"]], 4.0, places=9, msg=k)

    def test_expected_counts_match_independent_rewire_rule(self):
        """rewire_by_distance, written out in plain loops: P(g | j) ~ n_target(g) * exp(-d / lam)."""
        spec = Spec()
        lam = spec.lam
        n_exc, n_inh = np.full(343, 16000 / 343), np.full(343, 4000 / 343)
        exp = expected_counts(spec, n_exc, n_inh, group_distances(7))
        coords = [(x, y, z) for x in range(7) for y in range(7) for z in range(7)]
        for src in [(3, 3, 3), (0, 3, 3), (0, 0, 3), (0, 0, 0)]:
            j = src[0] * 49 + src[1] * 7 + src[2]
            for key, n_t, per_neuron, pre_n in (("EE", n_exc, 1600, n_exc[0]), ("EI", n_inh, 400, n_exc[0]),
                                                ("IE", n_exc, 2000, n_inh[0])):
                w = [n_t[g] * math.exp(-math.dist(src, coords[g]) / lam) for g in range(343)]
                tot = sum(w)
                for g in range(343):
                    want = pre_n * per_neuron * w[g] / tot
                    got = exp[key][j, g]
                    self.assertAlmostEqual(got, want, delta=1e-9 * max(1.0, want), msg=f"{key} {src} -> {g}")

    def test_sampled_counts_totals_and_means(self):
        spec = Spec(sample_sizes=False)
        dist = group_distances(7)
        n_exc, n_inh = group_sizes(spec, None)
        exp = expected_counts(spec, n_exc, n_inh, dist)
        R = 30
        acc = {k: np.zeros((343, 343)) for k in exp}
        for r in range(R):
            cnt = sample_counts(spec, n_exc, n_inh, dist, np.random.default_rng(r))
            for k in exp:
                acc[k] += cnt[k]
                n_pre = n_inh if k == "IE" else n_exc
                per = {"EE": 1600, "EI": 400, "IE": 2000}[k]
                np.testing.assert_allclose(cnt[k].sum(axis=1), np.rint(n_pre * per), atol=1.0)
        d2 = np.rint(dist ** 2).astype(int)
        for k in exp:
            mean = acc[k] / R
            for cls in np.unique(d2):
                m = d2 == cls
                e = exp[k][m].sum()
                if e < 400:         # classes with too few expected synapses to estimate within 5 %
                    continue
                self.assertLess(abs(mean[m].sum() - e) / e, 0.05, f"{k} d^2={cls}: {mean[m].sum():.1f} vs {e:.1f}")

    def test_sampled_group_sizes(self):
        spec = Spec()
        mins, means = [], []
        for r in range(5):
            ne, ni = group_sizes(spec, np.random.default_rng(r))
            self.assertEqual(ne.sum(), 16000)
            self.assertEqual(ni.sum(), 4000)
            mins.append((ne + ni).min())
            means.append((ne + ni).mean())
        self.assertAlmostEqual(statistics.mean(means), 20000 / 343, places=6)
        # spiking builds: smallest group 34 (N = 42,500, 729 groups) to 38 (77,600); here 343 groups
        self.assertTrue(28 <= statistics.mean(mins) <= 42, mins)

    def test_own_group_share_matches_measured_intra_group_synapses(self):
        """tuning-log.md iteration 61 (s73): intra-group E-E synapses per excitatory neuron 867 (9^3), 851 (11^3)."""
        for dim, measured in ((9, 867.0), (11, 851.0)):
            spec = Spec(grid_dim=dim, sample_sizes=False)
            n_exc, n_inh = group_sizes(spec, None)
            exp = expected_counts(spec, n_exc, n_inh, group_distances(dim))
            per_neuron = exp["EE"].diagonal().sum() / n_exc.sum()
            self.assertLess(abs(per_neuron - measured) / measured, 0.05, f"{dim}^3: {per_neuron:.1f} vs {measured}")


class TestDerivedConstants(unittest.TestCase):
    """Each derived constant re-read from its spiking source."""

    @classmethod
    def setUpClass(cls):
        cls.job = json.load(open(SESSION))["jobs"][0]
        cls.eng = json.load(open(SESSION))["engine"]
        cls.protocol_py = read(os.path.join(PARENT, "assoc_protocol.py"))
        cls.spec = Spec.from_session(SESSION)

    def defaults_number(self, key):
        m = re.search(r'"%s":\s*([0-9.]+)' % key, self.protocol_py)
        self.assertIsNotNone(m, key)
        return float(m.group(1))

    def test_session_parameters(self):
        p, s = self.job["params"], self.spec
        self.assertEqual(s.S, self.eng["n_synapses"])
        self.assertEqual(self.eng["n_neurons"], 20000)
        self.assertAlmostEqual(s.neurons_per_group, 20000 / 343)
        self.assertAlmostEqual(s.neurons_per_group, 58.3, places=1)
        self.assertEqual(s.lam, self.eng["rewire"]["lam"])
        for name in ("gain", "gain_ei", "gain_ie", "gain_ee_inter", "k_inject", "inject_current", "i_min", "i_max"):
            self.assertEqual(getattr(s, name), p[name], name)
        self.assertEqual(s.w_ee, p["weights"]["w_ee"])
        self.assertEqual(s.w_intra_ee_total, p["weights"]["w_intra_ee_total"])
        for name in ("a_pre", "a_plus", "a_minus", "tau_fast", "kappa", "theta1", "soft1", "theta2", "soft2"):
            self.assertEqual(getattr(s, name), p["plasticity"][name], name)
        self.assertEqual(p["plasticity"]["rule"], s.plasticity_rule)
        self.assertEqual(s.c1, p["c1"])
        self.assertEqual(s.c2, p["c2"])
        for name in ("max_c1_rounds", "c2_rounds", "max_extra_c2_rounds", "max_active_frac", "pair_distance"):
            self.assertEqual(getattr(s, name), p["protocol"][name], name)
        self.assertFalse(p["learn_in_c2"])
        # the Spec defaults are the same values (no drift between defaults and the session file)
        d = Spec()
        for name in ("S", "lam", "gain", "gain_ei", "gain_ie", "gain_ee_inter", "w_ee", "w_intra_ee_total",
                     "k_inject", "inject_current", "a_pre", "a_plus", "a_minus", "tau_fast", "kappa", "theta1",
                     "soft1", "theta2", "soft2", "max_c1_rounds", "c2_rounds", "max_extra_c2_rounds"):
            self.assertEqual(getattr(d, name), getattr(s, name), name)
        self.assertEqual(d.c1, s.c1)
        self.assertEqual(d.c2, s.c2)

    def test_protocol_defaults(self):
        d = Spec()
        for name in ("window", "active", "inactive", "inject_steps", "gap_steps", "test_window", "vox_per_cell"):
            self.assertEqual(getattr(d, name), self.defaults_number(name), name)

    def test_builder_weights(self):
        src = read(os.path.join(PARENT, "assoc_build.py"))
        w = {(int(a), int(b)): float(c) for a, b, c in re.findall(r"src=(\d+), snk=(\d+), w0=(-?[0-9.]+)", src)}
        d = Spec()
        self.assertEqual(w[(0, 1)], d.w_ie)       # inhibitory -> excitatory
        self.assertEqual(w[(1, 0)], d.w_ei)       # excitatory -> inhibitory

    def test_type_ratios(self):
        src = read(os.path.join(REPO, "snngine_v4", "nn", "config_models", "reservoir", "n_type_groups.py"))
        m = re.search(r"gen_factors: NonNegativeFloatList = Field\(\s*default_factory=lambda: \[(\d+), (\d+)\]", src)
        inh, exc = int(m.group(1)), int(m.group(2))
        d = Spec()
        self.assertAlmostEqual(d.exc_frac, exc / (inh + exc))
        self.assertAlmostEqual(d.frac_E_to_I, inh / (inh + exc))     # excitatory synapses split by gen_factors
        self.assertEqual(d.frac_I_to_E, 1.0)                          # one connection type for inhibitory neurons
        self.assertEqual(int(d.S * d.frac_E_to_I), 400)

    def test_weight_bounds(self):
        src = read(os.path.join(PARENT, "assoc_plasticity.py"))
        m = re.search(r"w_exc=\(([0-9.]+), ([0-9.]+)\)", src)
        d = Spec()
        self.assertEqual((d.w_lo, d.w_hi), (float(m.group(1)), float(m.group(2))))
        self.assertIn("math.exp(-1.0 / float(tau_fast))", src)

    def test_gain_rules_in_engine_source(self):
        src = read(os.path.join(PARENT, "assoc_engine.py"))
        self.assertIn("m[pre_exc & ~post_exc] *= float(gain_ei)", src)
        self.assertIn("m[~pre_exc & post_exc] *= float(gain_ie)", src)
        self.assertIn("m[inter] *= float(gain_ee_inter)", src)
        self.assertIn("vals = float(w_intra_ee_total) / indeg[post[m]]", src)
        self.assertIn("(D - 1) * dist[pre_g, self.groups[new_post]] / dist.max()", src)
        self.assertIn("kern = torch.exp(-dist / float(lam))", src)
        self.assertIn("prob = kern.double() * counts.double().view(1, -1)", src)

    def test_delay_count_rule_and_grids(self):
        src = read(os.path.join(REPO, "snngine_v4", "nn", "config_models", "reservoir", "nn_reservoir_config.py"))
        self.assertIn("n_delays = np.log10(n_neurons) * (1 + np.sqrt(np.log10(n_neurons)))", src)
        self.assertIn("return min(int(max(n_delays, min_)), max_)", src)
        # documented builds: N 20,000 -> D 13 (7^3), N 42,500 -> D 16 (9^3), N 77,600 -> D 20 (11^3)
        self.assertEqual(delay_count(20000), 13)
        self.assertEqual(int(delay_count(20000) / math.sqrt(3)), 7)
        self.assertEqual(delay_count(42500), 14)       # the rule alone gives 14 (grid 8): the 9^3 builds set D = 16
        self.assertEqual(Spec().D, 13)
        for dim, n_del in ((9, 16), (11, 20)):
            self.assertEqual(Spec(grid_dim=dim).D, n_del)
            p = json.load(open(os.path.join(PARENT, "params", f"session73-g{dim}-d4-s0-a.json")))
            self.assertEqual(p["jobs"][0]["engine"]["n_delays"], n_del)
            self.assertEqual(int(n_del / math.sqrt(3)), dim)

    def test_neuron_counts_by_type(self):
        """make_counts of the type groups: 4000 inhibitory, 16000 excitatory of 20,000."""
        d = Spec()
        self.assertEqual(round(d.N * d.exc_frac), 16000)
        self.assertEqual(d.N, 20000)
        self.assertAlmostEqual(Spec(grid_dim=9).N, 42500, delta=10)   # 58.3 neurons per group (documented N 42,500)

    @unittest.skipUnless(glob.glob(os.path.join(PARENT, "output", "s71-d4-s*-p*", "s4-*-E0.json")),
                         "spiking outputs (gitignored) not present")
    def test_nu_act_from_spiking_outputs(self):
        v = []
        for f in sorted(glob.glob(os.path.join(PARENT, "output", "s71-d4-s*-p*", "s4-d4-s*-pair*-E0.json"))):
            r = json.load(open(f))
            for d in ("A_to_B", "B_to_A"):
                t = r["control0_before"][d]
                if t["src_max"] >= 0.9 and t["n_above_inactive_outside"] == 0 and t["dst_max"] <= 0.1:
                    v.append(t["spikes"] / (100 * 58.3))
        self.assertEqual(len(v), 39)
        self.assertAlmostEqual(statistics.median(v), DERIVED["nu_act"][0], places=3)
        self.assertAlmostEqual(Spec().nu_act, DERIVED["nu_act"][0])


class TestCouplingAgainstEngineFormulas(unittest.TestCase):

    def test_coupling_matrices_equal_engine_weight_sums(self):
        """
        A small explicit synaptic network (3^3 groups, 4 neurons per type and group, 6 synapses per neuron),
        its weights built as typed_weights / set_gains do (w_ee for E -> E, built w0 for E -> I and I -> E, intra-group
        E -> E weights total / in-degree, gain times gain_ie / gain_ei / gain_ee_inter), then summed per
        (presynaptic group, postsynaptic neuron) and compared with the model's coupling matrices built from the
        same synapse counts.
        """
        rng = np.random.default_rng(3)
        dim, per = 3, 4
        G = dim ** 3
        spec = Spec(grid_dim=dim, S=6, w_intra_ee_total=40.0)
        n_neurons = G * 2 * per
        group = np.repeat(np.arange(G), 2 * per)
        is_exc = np.tile(np.array([True] * per + [False] * per), G)
        pre_list, post_list = [], []
        for n in range(n_neurons):
            for s in range(spec.S):
                if is_exc[n]:
                    tgt_exc = s < 5          # 5 E -> E, 1 E -> I per excitatory neuron (arbitrary split)
                else:
                    tgt_exc = True
                cand = np.nonzero(is_exc == tgt_exc)[0]
                cand = cand[cand != n]
                pre_list.append(n)
                post_list.append(int(rng.choice(cand)))
        pre, post = np.array(pre_list), np.array(post_list)
        # engine weights
        w = np.where(is_exc[pre] & is_exc[post], spec.w_ee, np.where(is_exc[pre], spec.w_ei, spec.w_ie))
        gain = np.where(is_exc[pre] & is_exc[post], spec.gain * spec.gain_ee_inter,
                        np.where(is_exc[pre], spec.gain * spec.gain_ei, spec.gain * spec.gain_ie))
        intra = (group[pre] == group[post]) & is_exc[pre] & is_exc[post]
        indeg = np.zeros(n_neurons)
        np.add.at(indeg, post[intra], 1.0)
        w_eff = w * gain
        w_eff[intra] = spec.w_intra_ee_total / indeg[post[intra]] * spec.gain
        # group-pair counts
        nE = np.full(G, float(per))
        nI = np.full(G, float(per))
        M = {k: np.zeros((G, G)) for k in ("EE", "EI", "IE")}
        for a, b in zip(pre, post):
            key = ("EE" if is_exc[b] else "EI") if is_exc[a] else "IE"
            M[key][group[a], group[b]] += 1
        net = RateNetwork(spec, counts=M, sizes=(nE, nI))
        # mean summed current into a postsynaptic neuron of group g from presynaptic group j (all firing once)
        for key, (src_exc, dst_exc, A) in {"EE": (True, True, net.A_EE), "EI": (True, False, net.A_EI),
                                           "IE": (False, True, net.A_IE)}.items():
            for j in range(G):
                for g in range(G):
                    m = (group[pre] == j) & (group[post] == g) & (is_exc[pre] == src_exc) & (is_exc[post] == dst_exc)
                    if key == "EE":
                        m &= ~intra
                    total = w_eff[m].sum() / per           # per postsynaptic neuron of that type
                    model = A[j, g] * {"EE": spec.w_ee, "EI": spec.w_ei, "IE": 1.0}[key]
                    self.assertAlmostEqual(model, abs(total), places=9, msg=f"{key} {j}->{g}")
        # intra-group E -> E: summed input of a neuron when its whole group fires = total * gain
        for g in range(G):
            m = intra & (group[post] == g)
            per_post = np.zeros(n_neurons)
            np.add.at(per_post, post[m], w_eff[m])
            tgt = np.nonzero((group == g) & is_exc & (indeg > 0))[0]
            for n in tgt:
                self.assertAlmostEqual(per_post[n], spec.w_intra_ee_total * spec.gain, places=9)
            if len(tgt):
                self.assertAlmostEqual(net.intra[g], spec.w_intra_ee_total * spec.gain, places=9)

    def test_delay_rule(self):
        net = RateNetwork(Spec(), seed=0)
        dmax = group_distances(7).max()
        self.assertAlmostEqual(dmax, math.sqrt(3) * 6)
        d = group_distances(7)
        for (i, j) in [(0, 1), (0, 49), (0, 342), (10, 200), (5, 5)]:
            self.assertEqual(net.delay[i, j], int(round((13 - 1) * d[i, j] / dmax + 1e-12)) if d[i, j] > 0 else 0)
        self.assertEqual(int(net.delay.max()), 12)


class TestChemistry(unittest.TestCase):

    def reference_field(self, n, k, decay, depr, cmax, c0, src, steps, releases):
        """Independent ChemicalField (assoc_fields.py): replicate padding, clamp, sources."""
        ref = c0.copy().tolist()

        def at(a, x, y, z):
            return a[min(max(x, 0), n - 1)][min(max(y, 0), n - 1)][min(max(z, 0), n - 1)]

        for step in range(steps):
            for (s_, x, y, z, amount, sat) in releases:
                if s_ == step:
                    cur = ref[x][y][z]
                    if sat is None:
                        ref[x][y][z] = min(cur + amount, cmax)
                    elif cur < sat:
                        ref[x][y][z] = min(cur + amount * max(0.0, 1.0 - cur / sat), sat)
            new = [[[0.0] * n for _ in range(n)] for _ in range(n)]
            for x in range(n):
                for y in range(n):
                    for z in range(n):
                        c = ref[x][y][z]
                        lap = (at(ref, x + 1, y, z) + at(ref, x - 1, y, z) + at(ref, x, y + 1, z)
                               + at(ref, x, y - 1, z) + at(ref, x, y, z + 1) + at(ref, x, y, z - 1) - 6.0 * c)
                        v = min(max((c + k * lap) * (1.0 - decay) - depr, 0.0), cmax)
                        new[x][y][z] = src[x][y][z] if src[x][y][z] > 0.0 else v
            ref = new
        return np.array(ref)

    def test_field_matches_independent_chemical_field(self):
        n, k, decay, depr, cmax = 5, 0.12, 0.03, 0.001, 2000.0
        rng = np.random.default_rng(1)
        c0 = rng.uniform(0, 5, (n, n, n))
        src = np.zeros((n, n, n))
        src[1, 2, 3], src[4, 0, 0] = 4.0, 1.5
        f = ChemicalFieldLattice(n, k, decay, depr, cmax, vox_per_cell=1)
        self.assertAlmostEqual(f.k, k)
        f.c = c0.copy()
        f.source = src.copy()
        f.release(np.zeros(n ** 3), 0.0)
        releases = [(10, 2, 2, 2, 3.0, None), (10, 0, 4, 1, 1.0, 2.0)]
        for step in range(40):
            if step == 10:
                sp = np.zeros((n, n, n))
                sp[2, 2, 2] = 3.0
                f.release(sp.reshape(-1), 1.0)
                sp = np.zeros((n, n, n))
                sp[0, 4, 1] = 1.0
                f.release(sp.reshape(-1), 1.0, saturation=2.0)
            f.diffuse()
        ref = self.reference_field(n, k, decay, depr, cmax, c0, src, 40, releases)
        np.testing.assert_allclose(f.c, ref, atol=1e-9)

    def test_lattice_conversion_conserves_mass_and_scales_k(self):
        f = ChemicalFieldLattice(7, k=0.02, decay=0.0, vox_per_cell=4)
        self.assertAlmostEqual(f.k, 0.02 / 16)
        spk = np.zeros(343)
        spk[171] = 64.0                       # 64 spikes = one unit per voxel on the cell's 4^3 voxels
        f.release(spk, 1.0)
        self.assertAlmostEqual(f.c.sum(), 1.0)
        for _ in range(200):
            f.diffuse()
        self.assertAlmostEqual(f.c.sum(), 1.0, places=10)       # zero-flux, no decay: mass conserved
        g = ChemicalFieldLattice(7, k=0.02, decay=0.01, vox_per_cell=4)
        g.release(spk, 1.0)
        for _ in range(10):
            g.diffuse()
        self.assertAlmostEqual(g.c.sum(), 0.99 ** 10, places=9)

    def test_fine_voxel_field_cell_mass_agrees(self):
        """Cell mass of a fine voxel field (the spiking grid) vs the lattice, without diffusion (k = 0)."""
        v = 4
        fine = ChemicalFieldLattice(7 * v, 0.0, 0.01, vox_per_cell=1)
        coarse = ChemicalFieldLattice(7, 0.0, 0.01, vox_per_cell=v)
        rng = np.random.default_rng(0)
        for _ in range(20):
            spk_cells = rng.poisson(3.0, 343).astype(float)
            # spiking release: spikes spread over the voxels of the cell (here uniformly)
            sp = np.zeros((7 * v,) * 3)
            for g in range(343):
                x, y, z = g // 49, (g // 7) % 7, g % 7
                sp[x * v:(x + 1) * v, y * v:(y + 1) * v, z * v:(z + 1) * v] = spk_cells[g] / v ** 3
            fine.release(sp.reshape(-1), 1.0)
            fine.diffuse()
            coarse.release(spk_cells, 1.0)
            coarse.diffuse()
        cell_mean = fine.c.reshape(7, v, 7, v, 7, v).mean(axis=(1, 3, 5))
        np.testing.assert_allclose(coarse.c, cell_mean, rtol=1e-9, atol=1e-12)

    def test_gate(self):
        c = np.array([-1.0, 0.0, 0.6, 0.9, 1.2, 5.0])
        np.testing.assert_allclose(gate(c, 0.6, 0.6), [0, 0, 0, 0.5, 1, 1])
        np.testing.assert_allclose(gate(c, -1.0, 0.0), [1, 1, 1, 1, 1, 1])


class TestDynamicsAndPlasticity(unittest.TestCase):

    def test_transfer_function(self):
        net = RateNetwork(replace(Spec(), theta=5.0, beta=0.7, transfer="sigmoid0"), seed=0)
        x = np.array([-10.0, 0.0, 1.0, 5.0, 10.0, 100.0])
        y = net.transfer(x)
        self.assertEqual(y[0], 0.0)
        self.assertEqual(y[1], 0.0)
        self.assertTrue(y[1] < y[2] < y[3] < y[4] <= y[5])
        self.assertLessEqual(y[-1], 1.0)
        self.assertAlmostEqual(y[3], (0.5 - 1 / (1 + math.exp(3.5))) / (1 - 1 / (1 + math.exp(3.5))))
        plain = RateNetwork(replace(Spec(), theta=5.0, beta=0.7, transfer="sigmoid"), seed=0).transfer(x)
        self.assertAlmostEqual(plain[3], 0.5)

    def test_quiet_without_injection(self):
        net = RateNetwork(replace(Spec(), noise_sigma=0.5, tau=2.0), seed=0)
        for _ in range(100):
            net.step(chem=False)
        self.assertLess(float(net.rE.max()), 1e-3)       # noise-smoothed curve: negligible rate at rest
        self.assertLess(float(net.rI.max()), 1e-2)

    def test_pre_term_is_rate_product(self):
        """One step, rule pre_c1, C1 gate open: dw = a_pre * nu * r * w * (hi - w) on every outgoing synapse."""
        spec = replace(Spec(), plasticity_rule="pre_c1", theta=3.0, beta=3.0, tau=2.0, tau_fast=1e12)
        net = RateNetwork(spec, seed=0)
        g = 100
        net.rE[g] = 0.8
        net.hE[:] = 0.0
        net.hE[net.t % net.H, g] = 0.8
        w = net.spec.w_ee
        net._plasticity(True, False)
        want = spec.a_pre * spec.nu_act * 0.8 * w * (spec.w_hi - w)
        self.assertAlmostEqual(net.wf_ee[g, 5], want, places=12)
        self.assertEqual(net.wf_ee[g, g], 0.0)           # intra-group E -> E is fixed
        self.assertEqual(net.wf_ee[7, 5], 0.0)           # silent presynaptic groups do not change
        want_ei = spec.a_pre * spec.nu_act * 0.8 * spec.w_ei * (spec.w_hi - spec.w_ei)
        self.assertAlmostEqual(net.wf_ei[g, g], want_ei, places=12)

    def test_fast_decay_and_consolidation(self):
        spec = Spec()
        net = RateNetwork(spec, seed=0)
        net.wf_ee[3, 4] = 0.2
        net._plasticity(False, True)                     # C2 zero: gate closed, only decay
        self.assertAlmostEqual(net.wf_ee[3, 4], 0.2 * math.exp(-1 / 2000), places=12)
        self.assertEqual(net.wp_ee[3, 4], spec.w_ee)
        net.c2.c[:] = 5.0                                # gate open
        before = net.wf_ee[3, 4]
        net._plasticity(False, True)
        moved = spec.kappa * before
        self.assertAlmostEqual(net.wp_ee[3, 4], spec.w_ee + moved, places=12)
        self.assertAlmostEqual(net.wf_ee[3, 4], (before - moved) * math.exp(-1 / 2000), places=12)

    def test_weights_stay_in_bounds(self):
        spec = replace(Spec(), theta=3.0, beta=3.0, tau=2.0)
        net = RateNetwork(spec, seed=0)
        net.reset_all()
        for _ in range(3):
            run_round(net, [100, 140], True, False, True, False)
        we, wi = net.weights("effective")
        self.assertGreaterEqual(we.min(), spec.w_lo)
        self.assertLessEqual(we.max(), spec.w_hi)
        self.assertGreaterEqual(wi.min(), spec.w_lo)
        self.assertLessEqual(wi.max(), spec.w_hi)
        self.assertTrue(np.isfinite(net.wf_ee).all() and np.isfinite(net.rE).all())

    def test_path_groups_and_pairs(self):
        c = lattice_coords(7)
        a, b = 1 * 49 + 3 * 7 + 3, 5 * 49 + 3 * 7 + 3
        route = path_groups(c, a, b)
        self.assertNotIn(a, route)
        self.assertIn(3 * 49 + 3 * 7 + 3, route)
        self.assertIn(3 * 49 + 4 * 7 + 3, route)
        self.assertNotIn(3 * 49 + 5 * 7 + 3, route)
        # independent: distance from the segment, plain loops
        for g in range(343):
            if g in (a, b):
                continue
            p = c[g]
            ab = c[b] - c[a]
            t = max(0.0, min(1.0, float((p - c[a]) @ ab) / float(ab @ ab)))
            d = float(np.linalg.norm(p - (c[a] + t * ab)))
            self.assertEqual(g in route, d <= 1.0 + 1e-6)

    def test_pick_pairs_distance_and_margin(self):
        spec = Spec(grid_dim=9)
        pairs = pick_pairs(spec, 24, margin=2, seed=0)
        c = lattice_coords(9)
        for a, b, cc in pairs:
            # nearest available distance to 4 (pick_pair of the spiking protocol): 4 or, near the margin, 4.12
            self.assertLess(abs(float(np.linalg.norm(c[a] - c[b])) - 4.0), 0.25)
            for g in (a, b):
                self.assertTrue(((c[g] >= 2) & (c[g] <= 6)).all())

    def test_protocol_runs_and_is_deterministic(self):
        spec = replace(Spec(), theta=3.0, beta=3.0, tau=2.0, max_c1_rounds=2, c2_rounds=1, max_extra_c2_rounds=0)
        a, b = 1 * 49 + 3 * 7 + 3, 5 * 49 + 3 * 7 + 3
        r1 = run_pair_protocol(RateNetwork(spec, seed=4), a, b)
        r2 = run_pair_protocol(RateNetwork(spec, seed=4), a, b)
        self.assertEqual(r1["class"], r2["class"])
        self.assertEqual(r1["c1_rounds"], r2["c1_rounds"])
        self.assertIn(r1["class"], ("none", "contained", "ignition"))
        n1, n2 = RateNetwork(spec, seed=4), RateNetwork(spec, seed=4)
        np.testing.assert_array_equal(n1.counts["EE"], n2.counts["EE"])
        n3 = RateNetwork(spec, seed=5)
        self.assertFalse(np.array_equal(n1.counts["EE"], n3.counts["EE"]))


class TestIzhikevichTransfer(unittest.TestCase):
    """Round 3: transfer curves derived from the engine's neuron model."""

    @staticmethod
    def direct(a, b, c, d, I, steps=3000, warm=1000):
        """Plain-Python Izhikevich neuron exactly as snn_simulation.cu update_N_state_ (float64)."""
        v, u, n = -65.0, b * -65.0, 0
        for t in range(steps):
            if v > 30.0:
                v, u = c, u + d
                if t >= warm:
                    n += 1
            v += 0.5 * (0.04 * v * v + 5 * v + 140 - u + I)
            v += 0.5 * (0.04 * v * v + 5 * v + 140 - u + I)
            u += a * (b * v - u)
        return n / (steps - warm)

    def test_engine_and_preset_source(self):
        cu = read(os.path.join(REPO, "snngine_v4", "nn", "cuda_backend", "src", "simulation", "snn_simulation.cu"))
        self.assertEqual(cu.count("v = v + 0.5f * (0.04f * v * v + 5 * v + 140 - u + i);"), 2)
        self.assertIn("u = u + a * (b * v - u);", cu)
        self.assertIn("if (v > 30.f)", cu)
        pre = read(os.path.join(REPO, "snngine_v4", "nn", "config_models", "neurons", "presets", "izhikevich_presets.py"))
        for line in ("df_props['v'] = -65.", "df_props['a'] = .02 + .08 * r * mask_inh",
                     "df_props['b'] = .2 + .05 * (1. - r) * mask_inh", "df_props['c'] = -65 + 15 * (r ** 2) * mask_exc",
                     "df_props['d'] = 2 * mask_inh + (8 - 6 * (r ** 2)) * mask_exc"):
            self.assertIn(line, pre)
        a, b, c, d = izh_params("E", 4)
        r = (np.arange(4) + 0.5) / 4
        np.testing.assert_allclose(c, -65 + 15 * r ** 2)
        np.testing.assert_allclose(d, 8 - 6 * r ** 2)
        a, b, c, d = izh_params("I", 4)
        np.testing.assert_allclose(a, 0.02 + 0.08 * r)
        np.testing.assert_allclose(b, 0.2 + 0.05 * (1 - r))
        np.testing.assert_allclose(d, 2.0)

    def test_numpy_rates_match_direct_simulation(self):
        for kind in ("E", "I"):
            a, b, c, d = izh_params(kind, 4)
            for I in (0.0, 5.0, 10.0, 30.0, 80.0):
                got = izh_rates(a, b, c, d, np.array([I]), dtype=np.float64)[0]
                for j in range(4):
                    want = self.direct(a[j], b[j], c[j], d[j], I)
                    self.assertAlmostEqual(got[j], want, places=9, msg=f"{kind} I={I} neuron {j}")
        # float32 (GPU precision) within one spike per 2000 steps
        a, b, c, d = izh_params("E", 4)
        g32 = izh_rates(a, b, c, d, np.array([30.0]))[0]
        g64 = izh_rates(a, b, c, d, np.array([30.0]), dtype=np.float64)[0]
        np.testing.assert_allclose(g32, g64, atol=0.005)

    def test_curve_properties(self):
        for kind in ("E", "I"):
            g, r = raw_rate_curve(kind)
            self.assertEqual(float(r[g <= 0].max()), 0.0)        # silent at rest and under inhibition
            self.assertTrue(np.all(np.diff(r) >= -3e-2))          # monotone up to a small dip of the inhibitory curve near I = 29 (model property)
            self.assertGreater(r[-1], 0.1)
        # at 20 current units the inhibitory population fires faster than the excitatory one
        self.assertGreater(raw_rate_curve("I")[1][120], raw_rate_curve("E")[1][120])

    def test_noise_smoothing(self):
        g, raw = raw_rate_curve("E")
        g0, s0 = smoothed_rate_curve("E", 0.0)
        np.testing.assert_array_equal(raw, s0)
        g1, s1 = smoothed_rate_curve("E", 5.0)
        self.assertGreater(s1[100], raw[100])                      # noise lifts the curve at threshold
        self.assertTrue(np.all(np.diff(s1) >= -1e-4))
        # mean over a symmetric far-from-edge linear stretch is preserved (rate ~ linear between I = 40 and 70)
        i = int(np.where(g == 55.0)[0][0])
        self.assertAlmostEqual(s1[i], raw[i], delta=0.01)

    def test_activity_map(self):
        nu, A = activity_from_rate_table("E", 20, 0.0)
        self.assertEqual(A[0], 0.0)
        self.assertTrue(np.all(np.diff(A) >= 0))
        rates = per_neuron_rates("E")
        i = 130
        want = float((1.0 - (1.0 - rates[i]) ** 20).mean())
        self.assertAlmostEqual(float(A[i]), want, places=9)
        net = RateNetwork(Spec(), seed=0)
        self.assertAlmostEqual(float(net.activity(np.array([0.0]))[0]), 0.0, places=6)
        self.assertGreater(float(net.activity(np.array([1.0]))[0]), 0.3)

    def test_network_uses_derived_curves(self):
        net = RateNetwork(Spec(noise_sigma=0.0), seed=0)
        x = np.array([-50.0, 0.0, 20.0, 60.0])
        g, rE = raw_rate_curve("E")
        g, rI = raw_rate_curve("I")
        np.testing.assert_allclose(net.transfer(x, "E"), np.interp(x, g, rE) / net.spec.nu_act)
        np.testing.assert_allclose(net.transfer(x, "I"), np.interp(x, g, rI) / net.spec.nu_act)
        self.assertEqual(float(net.transfer(np.array([-5.0]), "E")[0]), 0.0)


if __name__ == "__main__":
    unittest.main()
