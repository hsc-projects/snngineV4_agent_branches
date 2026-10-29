"""
test_popdensity_model.py

Module checks of popdensity_model.py (round 4, model A). They compare the model with independent code, not with its own
formulas: a plain-Python Izhikevich update, the engine source, a direct explicit-synapse simulation (below,
`direct_ref` section, written separately from the model) and Monte Carlo draws.

Run with the venv of this folder: .venv/Scripts/python.exe -m unittest test_popdensity_model
"""
import json
import math
import os
import random
import re
import unittest

import numpy as np

import popdensity_model as pm
from popdensity_model import PopSpec, PopNetwork, izh_advance, class_params, clipped_gauss_moments

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(PARENT))
SESSION = os.path.join(PARENT, "params", "session69a-stage2.json")

def izh_np(v, u, a, b, i):
    v = v + 0.5 * (0.04 * v * v + 5 * v + 140 - u + i)
    v = v + 0.5 * (0.04 * v * v + 5 * v + 140 - u + i)
    u = u + a * (b * v - u)
    return v, u


def build_region(net, g, radius, seed):
    """Explicit neurons and synapses for the groups within `radius` cells of group g, from the network's sampled counts."""
    rng = np.random.default_rng(seed)
    s = net.spec
    reg = np.nonzero(net.dist[g] <= radius + 1e-9)[0]
    # neurons
    ne = np.rint(net.nE[reg]).astype(int)
    ni = np.rint(net.nI[reg]).astype(int)
    gid, isE = [], []
    for k, j in enumerate(reg):
        gid += [k] * (ne[k] + ni[k])
        isE += [True] * ne[k] + [False] * ni[k]
    gid, isE = np.array(gid), np.array(isE)
    n = len(gid)
    r = rng.random(n)
    a = np.where(isE, 0.02, 0.02 + 0.08 * r)
    b = np.where(isE, 0.2, 0.2 + 0.05 * (1 - r))
    c = np.where(isE, -65 + 15 * r ** 2, -65.0)
    d = np.where(isE, 8 - 6 * r ** 2, 2.0)
    start = np.concatenate([[0], np.cumsum(ne + ni)])
    idxE = [np.arange(start[k], start[k] + ne[k]) for k in range(len(reg))]
    idxI = [np.arange(start[k] + ne[k], start[k + 1]) for k in range(len(reg))]
    pre, post, w, dly = [], [], [], []
    for key in ("EE", "EI", "IE"):
        M = net.counts[key]
        for kj, j in enumerate(reg):
            for kh, h in enumerate(reg):
                m = int(M[j, h])
                if m == 0:
                    continue
                src = idxE[kj] if key in ("EE", "EI") else idxI[kj]
                tgt = idxE[kh] if key in ("EE", "IE") else idxI[kh]
                if len(src) == 0 or len(tgt) == 0:
                    continue
                p_ = rng.choice(src, size=m)
                q_ = rng.choice(tgt, size=m)
                if key == "EE" and kj == kh:
                    # intra-group: weights = w_intra_total / in-degree of the postsynaptic neuron, times gain
                    indeg = np.bincount(q_, minlength=n)[q_]
                    ww = s.w_intra_ee_total / indeg * s.gain
                elif key == "EE":
                    ww = np.full(m, s.w_ee * s.gain * s.gain_ee_inter)
                elif key == "EI":
                    ww = np.full(m, s.w_ei * s.gain * s.gain_ei)
                else:
                    ww = np.full(m, s.w_ie * s.gain * s.gain_ie)
                pre.append(p_); post.append(q_); w.append(ww); dly.append(np.full(m, net.delay[j, h]))
    pre, post, w, dly = map(np.concatenate, (pre, post, w, dly))
    return dict(reg=reg, n=n, gid=gid, isE=isE, a=a, b=b, c=c, d=d, pre=pre, post=post, w=w, dly=dly.astype(int),
                idxE=idxE, start=start, rng=rng)


def run_direct(R, g, steps=100, inject_steps=50, k_inject=12, inj_cur=20.0, imin=-100.0, imax=100.0, init_rest=True):
    rng = R["rng"]
    n = R["n"]
    a, b, c, d = R["a"], R["b"], R["c"], R["d"]
    kg = int(np.nonzero(R["reg"] == g)[0][0])
    E_idx = R["idxE"][kg]
    inj = rng.choice(E_idx, size=min(k_inject, len(E_idx)), replace=False)
    v = np.full(n, -65.0)
    u = b * v
    for _ in range(5000):
        v, u = izh_np(v, u, a, b, 0.0)
    D = R["dly"].max() + 2
    ring = np.zeros((D + 1, n))
    sets = [(dl, R["pre"][R["dly"] == dl], R["post"][R["dly"] == dl], R["w"][R["dly"] == dl]) for dl in np.unique(R["dly"])]
    spk = np.zeros((steps, n), dtype=bool)
    for t in range(steps):
        i = ring[t % (D + 1)].copy()
        ring[t % (D + 1)] = 0.0
        i = np.clip(i, imin, imax)
        if t < inject_steps:
            i[inj] += inj_cur
        fired = v > 30.0
        v = np.where(fired, c, v)
        u = np.where(fired, u + d, u)
        v, u = izh_np(v, u, a, b, i)
        spk[t] = fired
        if fired.any():
            for dl, pre, post, w in sets:
                m = fired[pre]
                if m.any():
                    add = np.bincount(post[m], weights=w[m], minlength=n)
                    ring[(t + 1 + dl) % (D + 1)] += add
    return spk, inj


def summarize(R, spk, g, window=20):
    kg = int(np.nonzero(R["reg"] == g)[0][0])
    gid, isE = R["gid"], R["isE"]
    T = spk.shape[0]
    out = {}
    own = gid == kg
    out["own_E_per_step"] = spk[:, own & isE].sum(axis=1)
    out["own_I_per_step"] = spk[:, own & ~isE].sum(axis=1)
    out["other_E_total"] = spk[:, ~own & isE].sum()
    out["other_I_total"] = spk[:, ~own & ~isE].sum()
    # A_g over time for own group (E)
    idx = np.nonzero(own & isE)[0]
    last = np.full(len(idx), -10 ** 9)
    A = []
    for t in range(T):
        last[spk[t, idx]] = t
        A.append(float(((t - last) < window).mean()))
    out["A_own"] = np.array(A)
    # others' max A
    oth = np.nonzero(~own & isE)[0]
    lastO = np.full(len(oth), -10 ** 9)
    mx = 0.0
    for t in range(T):
        lastO[spk[t, oth]] = t
        rec = (t - lastO) < window
        for k in range(len(R["reg"])):
            if k == kg:
                continue
            sel = gid[oth] == k
            if sel.any():
                mx = max(mx, rec[sel].mean())
    out["others_max_A"] = mx
    return out


# ---------------------------------------------------------------------------------------- plain-Python engine
def py_step(v, u, a, b, i):
    """snn_simulation.cu:79-86 without the spike test, in plain Python floats."""
    v = v + 0.5 * (0.04 * v * v + 5 * v + 140 - u + i)
    v = v + 0.5 * (0.04 * v * v + 5 * v + 140 - u + i)
    u = u + a * (b * v - u)
    return v, u


def py_fires(v, u, a, b, steps=400):
    for _ in range(steps):
        v, u = py_step(v, u, a, b, 0.0)
        if v > 30.0:
            return True
    return False


class TestEngineMap(unittest.TestCase):
    def test_engine_source_lines(self):
        src = open(os.path.join(REPO, "snngine_v4", "nn", "cuda_backend", "src", "simulation", "snn_simulation.cu")).read()
        line = "v = v + 0.5f * (0.04f * v * v + 5 * v + 140 - u + i);"
        self.assertEqual(src.count(line), 2)
        self.assertIn("u = u + a * (b * v - u);", src)
        self.assertIn("if (v > 30.f)", src)

    def test_advance_equals_plain_python(self):
        rnd = random.Random(1)
        for _ in range(300):
            v, u = rnd.uniform(-90, 25), rnd.uniform(-20, 20)
            a, b, i = rnd.uniform(0.02, 0.1), rnd.uniform(0.2, 0.25), rnd.uniform(-100, 100)
            want = py_step(v, u, a, b, i)
            if not -400 < want[0] < 200:
                continue
            got = izh_advance(np.array([v]), np.array([u]), a, b, i)
            self.assertAlmostEqual(float(got[0][0]), want[0], places=7)
            self.assertAlmostEqual(float(got[1][0]), want[1], places=6)

    def test_class_parameters(self):
        aE, bE, cE, dE = class_params("E", 4)
        r = np.array([.125, .375, .625, .875])
        np.testing.assert_allclose(cE, -65 + 15 * r ** 2)
        np.testing.assert_allclose(dE, 8 - 6 * r ** 2)
        aI, bI, cI, dI = class_params("I", 4)
        np.testing.assert_allclose(aI, 0.02 + 0.08 * r)
        np.testing.assert_allclose(bI, 0.2 + 0.05 * (1 - r))
        src = open(os.path.join(REPO, "snngine_v4", "nn", "config_models", "neurons", "presets", "izhikevich_presets.py")).read()
        self.assertIn("default_init", src)

    def test_rest_state_and_separatrix_against_direct_simulation(self):
        tb = pm.tables(4)
        for ti, kind in enumerate(("E", "I")):
            a, b, c, d = class_params(kind, 4)
            for k in range(4):
                v, u = -65.0, b[k] * -65.0
                for _ in range(6000):
                    v, u = py_step(v, u, a[k], b[k], 0.0)
                self.assertAlmostEqual(v, tb[("rest_v", ti)][k], places=4)
                self.assertAlmostEqual(u, tb[("rest_u", ti)][k], places=4)
                for uu in (-18.0, -14.0, -10.0, -4.0, 4.0):
                    vs = float(np.interp(uu, pm.U_GRID, tb[("vsep", ti)][k]))
                    if vs <= -89.9:
                        continue
                    self.assertFalse(py_fires(vs - 0.05, uu, a[k], b[k]), (kind, k, uu, vs))
                    self.assertTrue(py_fires(vs + 0.05, uu, a[k], b[k]), (kind, k, uu, vs))

    def test_latency_against_direct_simulation(self):
        net = PopNetwork(PopSpec.from_session(SESSION, n_classes=4), seed=0)
        rnd = random.Random(3)
        for _ in range(60):
            kind, k = rnd.choice([(0, 0), (0, 3), (1, 1), (1, 2)])
            v0, u0, x = rnd.uniform(-52, -20), rnd.uniform(-15, 0), rnd.choice([0.0, 20.0, 60.0])
            lat, uf = net._latency(np.array([v0]), np.array([u0]), net.PA[kind, k], net.PB[kind, k], x)
            v, u, n = v0, u0, 1
            if v > 30.0:
                pass
            else:
                while n < net.spec.latency_max:
                    v, u = py_step(v, u, net.PA[kind, k], net.PB[kind, k], x)
                    n += 1
                    if v > 30.0:
                        break
            self.assertEqual(int(lat[0]), n)
            self.assertAlmostEqual(float(uf[0]), u, places=5)


class TestStatistics(unittest.TestCase):
    def test_clipped_gaussian_moments_monte_carlo(self):
        rng = np.random.default_rng(0)
        for mu, sg in ((0.0, 5.0), (-90.0, 30.0), (95.0, 10.0), (20.0, 80.0)):
            x = np.clip(rng.normal(mu, sg, 400000), -100, 100)
            m, s = clipped_gauss_moments(np.array([mu]), np.array([sg]), -100.0, 100.0)
            self.assertAlmostEqual(float(m[0]), x.mean(), delta=0.4)
            self.assertAlmostEqual(float(s[0]), x.std(), delta=0.4)

    def test_erf_approximation(self):
        z = np.linspace(-4, 4, 81)
        for zz, e in zip(z, pm._erf(z)):
            self.assertAlmostEqual(float(e), math.erf(zz), delta=2e-7)

    def test_input_mean_and_variance_against_explicit_synapses(self):
        """Mean and variance (over postsynaptic neurons) of the summed input for sampled synapse placements."""
        net = PopNetwork(PopSpec.from_session(SESSION, n_classes=4), seed=0)
        g = 175
        nb = int(np.argmax(net.counts["EE"][g] * (np.arange(net.G) != g)))
        nE_j, nE_g = int(net.nE[g]), int(net.nE[nb])
        M = int(net.counts["EE"][g, nb])
        spikes = np.zeros(nE_j, dtype=bool)
        spikes[:25] = True
        wgt = 0.3
        rng = np.random.default_rng(0)
        means, vars_ = [], []
        for _ in range(300):
            pre = rng.integers(0, nE_j, M)
            post = rng.integers(0, nE_g, M)
            cur = np.bincount(post[spikes[pre]], minlength=nE_g) * wgt * net.spec.gain * net.spec.gain_ee_inter
            means.append(cur.mean())
            vars_.append(cur.var())
        mean_want = net.A_EE[g, nb] * wgt * (25 / nE_j)
        var_want = net.B_EE[g, nb] * wgt ** 2 * 25
        self.assertAlmostEqual(float(np.mean(means)), mean_want, delta=0.03 * mean_want)
        self.assertAlmostEqual(float(np.mean(vars_)), var_want, delta=0.15 * var_want)

    def test_binomial_commitment_counts(self):
        rng = np.random.default_rng(5)
        n = rng.binomial(np.full(200000, 40), 0.3)
        self.assertAlmostEqual(n.mean(), 12.0, delta=0.05)
        self.assertAlmostEqual(n.var(), 40 * 0.3 * 0.7, delta=0.2)


class TestAgainstDirectSimulation(unittest.TestCase):
    """One injected group (k = 12 neurons, +20 for 50 steps): the model against the explicit-synapse simulation
    (neurons with their own r, synapse placement drawn from the same counts) on the 14 groups within 1.5 cells."""

    @classmethod
    def setUpClass(cls):
        cls.spec = PopSpec.from_session(SESSION)
        cls.net = PopNetwork(cls.spec, seed=0)
        g = 175
        cls.g = g
        reg = np.nonzero(cls.net.dist[g] <= 1.5 + 1e-9)[0]
        cls.oth = [x for x in reg if x != g]
        inj = cls.net.injection([g])
        cls.model = []
        for k in range(10):
            cls.net.rng = np.random.default_rng([k, 99])
            cls.net.reset_dynamics()
            E, I, A = [], [], []
            for i in range(100):
                cls.net.step(inj=inj if i < 50 else None, chem=False)
                E.append(cls.net.rE[g] * cls.net.nE[g]); I.append(cls.net.rI[g] * cls.net.nI[g]); A.append(cls.net.Ag[g])
            cls.model.append(dict(E=np.array(E), I=np.array(I), A=np.array(A), oE=cls.net.spk_E_total[cls.oth].sum(),
                                  oI=cls.net.spk_I_total[cls.oth].sum()))
        cls.direct = []
        for k in range(10):
            R = build_region(cls.net, g, 1.5, k)
            spk, _ = run_direct(R, g)
            cls.direct.append(summarize(R, spk, g))

    def test_first_ten_steps_match(self):
        mE = np.mean([r["E"][:10].sum() for r in self.model]); dE = np.mean([r["own_E_per_step"][:10].sum() for r in self.direct])
        mI = np.mean([r["I"][:10].sum() for r in self.model]); dI = np.mean([r["own_I_per_step"][:10].sum() for r in self.direct])
        self.assertAlmostEqual(mE, dE, delta=0.1 * dE)
        self.assertAlmostEqual(mI, dI, delta=0.1 * dI)

    def test_totals_over_100_steps(self):
        mE = np.mean([r["E"].sum() for r in self.model]); dE = np.mean([r["own_E_per_step"].sum() for r in self.direct])
        mI = np.mean([r["I"].sum() for r in self.model]); dI = np.mean([r["own_I_per_step"].sum() for r in self.direct])
        self.assertAlmostEqual(mE, dE, delta=0.3 * dE)
        self.assertAlmostEqual(mI, dI, delta=0.3 * dI)

    def test_activation_and_neighbours(self):
        self.assertGreaterEqual(min(r["A"].max() for r in self.model), 0.99)
        self.assertGreaterEqual(min(r["A_own"].max() for r in self.direct), 0.99)
        self.assertLess(np.mean([r["oE"] for r in self.model]), 0.15 * np.mean([r["E"].sum() for r in self.model]))
        dI = np.mean([r["other_I_total"] for r in self.direct]); mI = np.mean([r["oI"] for r in self.model])
        self.assertAlmostEqual(mI, dI, delta=0.5 * dI)           # known excess of the model (report)


class TestNetworkBehaviour(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.net = PopNetwork(PopSpec.from_session(SESSION), seed=1)

    def test_quiet_without_injection(self):
        self.net.reset_dynamics()
        for _ in range(300):
            self.net.step(chem=False)
        self.assertEqual(self.net.spk_E_total.sum() + self.net.spk_I_total.sum(), 0)
        self.assertEqual(len(self.net.bg), 0)

    def test_neuron_numbers_conserved(self):
        self.net.reset_dynamics()
        inj = self.net.injection([100])
        for i in range(60):
            self.net.step(inj=inj if i < 50 else None, chem=False)
            tot = np.zeros((3, self.net.G))
            np.add.at(tot, (self.net.bkind, self.net.bg), self.net.bm)
            q = self.net.qn.sum(axis=(0, 3)).reshape(self.net.qn.shape[1], self.net.G) if False else self.net.qn.sum(axis=(0, 3))
            ing = self.net.inlist
            want = self.net.class_counts.sum(axis=2)
            np.testing.assert_array_equal((tot + q)[:, ing], want[:, ing])

    def test_determinism(self):
        out = []
        for _ in range(2):
            self.net.rng = np.random.default_rng(7)
            self.net.reset_dynamics()
            inj = self.net.injection([100])
            for i in range(40):
                self.net.step(inj=inj if i < 50 else None, chem=False)
            out.append(self.net.spk_E_total.copy())
        np.testing.assert_array_equal(out[0], out[1])


if __name__ == "__main__":
    unittest.main()
