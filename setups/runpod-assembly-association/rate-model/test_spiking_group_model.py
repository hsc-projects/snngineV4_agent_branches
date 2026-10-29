"""
test_spiking_group_model.py

Module checks of the reduced spiking network (spiking_group_model.py, model B of round 4). They compare the
model with the engine's code, not with the model's own formulas:

 1. source lines of the engine that the model transliterates are present (kernel update, delivery, presets,
    rewire, gains, plasticity, activity);
 2. the Izhikevich update equals a scalar float32 transliteration of update_N_state_;
 3. the neuron parameters equal the engine's `default_init`, executed from its source text;
 4. the sampled wiring follows rewire_by_distance (types kept, no autapses, group frequencies by distance shell
    against an independent plain-Python computation, delays and delay buckets, in-degree against the engine's
    measured 892.7 intra-group excitatory synapses per excitatory neuron);
 5. engine weights equal a numpy transliteration of typed_weights / set_gains / write_weights (times the
    reduction factor S_type / S'_type, divided out);
 6. spike rasters equal a plain-Python transliteration of the engine's update order (update_N_state_,
    update_current_ with its delay windows, input clamp, injection) on a small network;
 7. the event-based plasticity equals a dense numpy transliteration of GatedPlasticity.step (STDP, presynaptic
    C1 term, decay, consolidation);
 8. the activity measure equals GroupActivity.update; protocol determinism and class logic;
 9. (only when torch is importable, i.e. on the pod) the same plasticity, activity and weight comparisons against
    the real classes assoc_plasticity.GatedPlasticity, assoc_fields.GroupActivity and
    assoc_engine.AssocEngine.typed_weights / set_gains / write_weights.

Run with the venv of this folder: .venv/Scripts/python.exe -m unittest test_spiking_group_model
"""

import ast
import json
import math
import os
import re
import sys
import unittest

import numpy as np

from rate_model import Spec, group_distances, lattice_coords
from spiking_group_model import (SpikeSpec, SpikingNetwork, Izhikevich, neuron_parameters, F32, KIND_EE,
                                 KIND_EE_INTRA, KIND_EI, KIND_IE, KIND_EI_INTER, PLASTIC_LUT, run_pair_protocol,
                                 run_test)

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(PARENT))
SESSION = os.path.join(PARENT, "params", "session69a-stage2.json")
KERNEL = os.path.join(REPO, "snngine_v4", "nn", "cuda_backend", "src", "simulation", "snn_simulation.cu")
PRESETS = os.path.join(REPO, "snngine_v4", "nn", "config_models", "neurons", "presets", "izhikevich_presets.py")


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def small_spec(**over):
    kw = dict(grid_dim=3, neuron_scale=0.25, syn_scale=0.05, ei_inter_scale=1.0)
    kw.update(over)
    return SpikeSpec.from_session(SESSION, **kw)


class TestEngineSources(unittest.TestCase):
    def test_kernel_lines(self):
        k = read(KERNEL)
        for frag in ("v = v + 0.5f * (0.04f * v * v + 5 * v + 140 - u + i);", "u = u + a * (b * v - u);",
                     "if (v > 30.f)", "v = c;", "u = u + d;", "N_states[n + 7 * N] = 0.f;",
                     "const int delay_idx = n + N * (time_since_firing);",
                     "int s_end = N_delays[delay_idx + N];", "atomicAdd(&N_states[snk_N + 7 * N], w1);"):
            self.assertIn(frag, k)

    def test_engine_python_sources(self):
        eng = read(os.path.join(PARENT, "assoc_engine.py"))
        for frag in ("kern = torch.exp(-dist / float(lam))", "prob = kern.double() * counts.double().view(1, -1)",
                     "delay = torch.round((D - 1) * dist[pre_g, self.groups[new_post]] / dist.max().clamp(min=1e-9)).long()",
                     "m[pre_exc & ~post_exc] *= float(gain_ei)", "m[~pre_exc & post_exc] *= float(gain_ie)",
                     "m[inter] *= float(gain_ee_inter)", "vals = float(w_intra_ee_total) / indeg[post[m]]"):
            self.assertIn(frag, eng)
        pl = read(os.path.join(PARENT, "assoc_plasticity.py"))
        for frag in ("ltp = post_now & (dt_pre >= 0) & (dt_pre <= 2 * self.D)",
                     "ltd = arrived & (last_post < t_fire) & (last_post >= t_fire - self.delay)",
                     "dw = (self.a_plus * ltp.float() - self.a_minus * ltd.float()) * w * (self.bound - w)",
                     "dw = self.a_pre * g * (self.bound - w) * (1.0 if self.weight_dep == \"upper\" else w)",
                     "moved = self.kappa * g12 * self.w_fast"):
            self.assertIn(frag, pl)


class TestNeuron(unittest.TestCase):
    def test_update_equals_scalar_kernel(self):
        rng = np.random.default_rng(1)
        n = 12
        isE = np.arange(n) < 8
        a, b, c, d = neuron_parameters(rng, isE)
        nn = Izhikevich(a, b, c, d)
        v = [F32(-65.0)] * n
        u = [F32(b[j]) * F32(-65.0) for j in range(n)]
        for t in range(400):
            i = (rng.random(n) * 40 - 10).astype(F32) * (1 if t % 7 else 5)
            fired = nn.step(i)
            ref = []
            for j in range(n):
                if v[j] > F32(30.0):
                    v[j] = c[j]
                    u[j] = u[j] + d[j]
                    ref.append(j)
                for _ in range(2):
                    v[j] = v[j] + F32(0.5) * (F32(0.04) * v[j] * v[j] + F32(5) * v[j] + F32(140) - u[j] + i[j])
                u[j] = u[j] + a[j] * (b[j] * v[j] - u[j])
            self.assertEqual(list(fired), ref, f"step {t}")
            np.testing.assert_array_equal(nn.v, np.array(v, dtype=F32))
            np.testing.assert_array_equal(nn.u, np.array(u, dtype=F32))

    def test_parameters_equal_engine_default_init(self):
        """Execute the engine's own default_init from the source text on dict-backed columns."""
        tree = ast.parse(read(PRESETS))
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "default_init")
        for a_ in fn.args.args:
            a_.annotation = None
        fn.returns = None
        src = ast.unparse(ast.Module(body=[fn], type_ignores=[]))
        ns = {}
        exec(src, ns)
        rng = np.random.default_rng(3)
        n = 500
        isE = np.arange(n) < 400
        r = rng.random(n).astype(F32)
        df = {}
        ns["default_init"](None, df, isE == False, isE, r)       # noqa: E712 (self, df_props, mask_inh, mask_exc, r)
        # model's own draw uses its rng; reproduce r
        rng2 = np.random.default_rng(3)
        a, b, c, d = neuron_parameters(rng2, isE)
        # neuron_parameters draws r first from the rng; the test's first draw above was the same stream
        np.testing.assert_allclose(a, df["a"], rtol=1e-6)
        np.testing.assert_allclose(b, df["b"], rtol=1e-6)
        np.testing.assert_allclose(c, df["c"], rtol=1e-6)
        np.testing.assert_allclose(d, df["d"], rtol=1e-6)


class TestWiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = SpikeSpec.from_session(SESSION, neuron_scale=1.0, syn_scale=0.05)
        cls.net = SpikingNetwork(cls.spec, seed=2)

    def test_counts_types_and_autapses(self):
        net, s = self.net, self.spec
        S = net.S
        self.assertEqual(net.post.shape, (net.N, S))
        pre = np.repeat(np.arange(net.N), S).reshape(net.N, S)
        self.assertFalse((net.post == pre).any())
        pre_e = net.isE[pre]
        post_e = net.isE[net.post]
        # E -> E and E -> I per excitatory neuron, I -> E only for inhibitory
        self.assertTrue(post_e[~pre_e].all())
        self.assertEqual(int((pre_e & post_e).sum(axis=1)[:net.nE_tot].min()), s.S_ee)
        self.assertEqual(int((pre_e & ~post_e).sum(axis=1)[:net.nE_tot].max()), s.S_ei)
        self.assertEqual(s.S_ee + s.S_ei, S)
        self.assertEqual(s.S_ee, 80)       # 0.8 * 100
        same = net.grp[pre] == net.grp[net.post]
        self.assertTrue(((net.kind == KIND_EE_INTRA) == (pre_e & post_e & same)).all())
        self.assertTrue(((net.kind == KIND_EI_INTER) == (pre_e & ~post_e & ~same)).all())

    def test_group_frequencies_follow_rewire_rule(self):
        """E -> E synapses per distance shell against an independent plain-Python evaluation of the rule."""
        net, s = self.net, self.spec
        G = net.G
        coords = [(x, y, z) for x in range(7) for y in range(7) for z in range(7)]
        dist = group_distances(7)
        d2 = np.rint(dist ** 2).astype(int)
        pre = np.repeat(np.arange(net.N), net.S).reshape(net.N, net.S)
        m = (net.kind == KIND_EE) | (net.kind == KIND_EE_INTRA)
        obs = np.zeros(d2.max() + 1)
        exp = np.zeros(d2.max() + 1)
        nE = net.nE
        for j in range(G):
            w = np.array([nE[g] * math.exp(-math.dist(coords[j], coords[g]) / s.lam) for g in range(G)])
            p = w / w.sum()
            n_syn = nE[j] * s.S_ee
            for cls in np.unique(d2[j]):
                exp[cls] += n_syn * p[d2[j] == cls].sum()
        sel = m & net.isE[pre]
        g_pre, g_post = net.grp[pre][sel], net.grp[net.post][sel]
        np.add.at(obs, d2[g_pre, g_post], 1)
        for cls in range(d2.max() + 1):
            if exp[cls] > 2000:
                self.assertLess(abs(obs[cls] - exp[cls]) / exp[cls], 0.05, f"d^2={cls}: {obs[cls]} vs {exp[cls]:.0f}")

    def test_delays_and_buckets(self):
        net = self.net
        pre = np.repeat(np.arange(net.N), net.S).reshape(net.N, net.S)
        dist = group_distances(7)
        want = np.rint((net.D - 1) * dist[net.grp[pre], net.grp[net.post]] / dist.max())
        np.testing.assert_array_equal(net.delay, want)
        self.assertEqual(net.D, 13)
        self.assertTrue((np.diff(net.delay, axis=1) >= 0).all())
        for r in range(net.D + 1):
            np.testing.assert_array_equal(net.bnd[:, r], (net.delay < r).sum(axis=1))
        self.assertTrue((net.bnd[:, 0] == 0).all() and (net.bnd[:, -1] == net.S).all())

    def test_intra_group_indegree_matches_engine_measurement(self):
        """Measured in the spiking 7^3 build (output/s47survey-rewired, S 2000): 892.7 intra-group E -> E synapses per
        excitatory neuron; here in-degree / syn_scale."""
        net, s = self.net, self.spec
        kinds = (net.kind == KIND_EE_INTRA)
        per_neuron = kinds[:net.nE_tot].sum() / net.nE_tot / s.syn_scale
        self.assertLess(abs(per_neuron - 892.7) / 892.7, 0.06, per_neuron)

    def test_group_sizes(self):
        net = self.net
        self.assertEqual(net.nE.sum(), 16000)
        self.assertEqual(net.nI.sum(), 4000)


class TestWeightsAgainstEngineRules(unittest.TestCase):
    def _engine_weights_numpy(self, net, spec):
        """numpy transliteration of typed_weights + set_gains + write_weights (assoc_engine.py) on net's synapses."""
        N, S = net.N, net.S
        pre = np.repeat(np.arange(N), S).reshape(N, S)
        post = net.post
        pre_exc = net.isE[pre]
        post_exc = net.isE[post]
        w = np.where(pre_exc & ~post_exc, 0.45, np.where(~pre_exc & post_exc, -0.44, 0.47))     # built weights
        w[pre_exc & post_exc] = 0.05                                                            # w_ee
        same = (net.grp[post] == net.grp[pre])
        m_intra = pre_exc & post_exc & same
        indeg = np.bincount(post[m_intra], minlength=N).astype(float)
        w[m_intra] = spec.w_intra_ee_total / indeg[post[m_intra]]
        gm = np.full(w.shape, spec.gain)
        gm[pre_exc & ~post_exc] *= spec.gain_ei
        gm[~pre_exc & post_exc] *= spec.gain_ie
        gm[pre_exc & post_exc & ~same] *= spec.gain_ee_inter
        return w * gm, pre_exc, post_exc, same

    def test_engine_weights_equal_transliteration(self):
        spec = small_spec()
        net = SpikingNetwork(spec, seed=1)
        ref, pre_exc, post_exc, same = self._engine_weights_numpy(net, spec)
        ids = np.arange(net.N * net.S)
        got = net.engine_weights(ids, 0.0).reshape(net.N, net.S).astype(float)
        factor = np.where(pre_exc & ~post_exc, spec.S * spec.frac_E_to_I / spec.S_ei,
                          np.where(~pre_exc & post_exc, spec.S / spec.S_red,
                                   np.where(pre_exc & post_exc & ~same, spec.S * (1 - spec.frac_E_to_I) / spec.S_ee, 1.0)))
        np.testing.assert_allclose(got, ref * factor, rtol=1e-5)

    def test_reduction_preserves_expected_input(self):
        """Summed engine weight onto a neuron per volley of its presynaptic groups is the same at syn_scale 0.05 and 0.2."""
        out = []
        for ss in (0.05, 0.2):
            sp = SpikeSpec.from_session(SESSION, grid_dim=7, neuron_scale=0.5, syn_scale=ss)
            net = SpikingNetwork(sp, seed=0)
            ids = np.arange(net.N * net.S)
            w = net.engine_weights(ids, 0.0).reshape(net.N, net.S)
            tot = np.zeros(net.N)
            np.add.at(tot, net.post.ravel(), w.ravel())
            kinds = [(net.kind == k) for k in (KIND_EE, KIND_EI, KIND_IE)]
            res = []
            for kk in kinds:
                t = np.zeros(net.N)
                np.add.at(t, net.post.ravel(), np.where(kk, w, 0.0).ravel())
                res.append(t[net.isE].mean() if kk is not kinds[1] else t[~net.isE].mean())
            out.append(res)
        for a, b in zip(*out):
            self.assertLess(abs(a - b) / abs(b), 0.08, out)


class PlainEngine:
    """Plain-Python transliteration of the engine's update order for one small network (scalar loops)."""

    def __init__(self, net, weights):
        self.net = net
        self.w = weights
        n = net.N
        self.v, self.u = [F32(x) for x in net.init_state[0]], [F32(x) for x in net.init_state[1]]
        self.hist = [[] for _ in range(net.D)]
        self.I = np.zeros(n, dtype=F32)

    def step(self, inj):
        net = self.net
        n = net.N
        fired = []
        a, b, c, d = net.neurons.a, net.neurons.b, net.neurons.c, net.neurons.d
        for j in range(n):
            v, u, i = self.v[j], self.u[j], self.I[j]
            if v > F32(30.0):
                v = c[j]
                u = u + d[j]
                fired.append(j)
            v = v + F32(0.5) * (F32(0.04) * v * v + F32(5) * v + F32(140) - u + i)
            v = v + F32(0.5) * (F32(0.04) * v * v + F32(5) * v + F32(140) - u + i)
            u = u + a[j] * (b[j] * v - u)
            self.v[j], self.u[j] = v, u
        self.hist.insert(0, fired)
        self.hist.pop()
        arr = np.zeros(n)
        for lag, lst in enumerate(self.hist):
            for j in lst:
                for s in range(net.S):
                    if net.delay[j, s] == lag:
                        arr[net.post[j, s]] += self.w[j, s]
        spec = net.spec
        arr = np.clip(arr, spec.i_min, spec.i_max).astype(F32)
        for j in inj:
            arr[j] += F32(spec.inject_current)
        self.I = arr
        return fired


class TestAgainstPlainEngine(unittest.TestCase):
    def test_spike_raster_equals_plain_engine(self):
        spec = small_spec(syn_scale=0.04, neuron_scale=0.3, ei_inter_scale=1.0)
        net = SpikingNetwork(spec, seed=4)
        g = 13
        inj = net.inject_idx(g)
        w = net.engine_weights(np.arange(net.N * net.S), 1.0).reshape(net.N, net.S)
        ref = PlainEngine(net, w)
        net.reset_dynamics()
        net.neurons.set_state(*net.init_state)
        total = 0
        for t in range(120):
            A, nf = net.step(20, False, False, 1.0, False, False, False, inj if t < 50 else None)
            mine = list(net.recent[0])
            theirs = ref.step(inj if t < 50 else [])
            self.assertEqual(mine, theirs, f"step {t}")
            total += len(mine)
        self.assertGreater(total, 20)


def dense_plasticity_reference(net, spikes_by_step, c2_open, consolidate_from, T, spec):
    """Dense numpy transliteration of assoc_plasticity.GatedPlasticity.step (rule 'both', C1 gate open)."""
    N, S, D = net.N, net.S, net.D
    pre = np.repeat(np.arange(N), S).reshape(N, S)
    post = net.post
    delay = net.delay.astype(int)
    kind = net.kind
    plastic = PLASTIC_LUT[kind]
    fixed = kind == KIND_EE_INTRA
    wp = net.wp0.astype(np.float64).copy()
    wf = np.zeros((N, S))
    lo, hi, bound = spec.w_lo, spec.w_hi, 1.0
    H = 2 * D + 2
    hist = np.zeros((H, N), dtype=bool)
    last = np.full(N, -10 ** 6)
    n_idx = pre
    fd = math.exp(-1.0 / spec.tau_fast)

    def eff():
        w = np.where(net.isE[pre], np.clip(wp + wf, lo, hi), np.clip(wp + wf, -1.0, -0.05))
        return np.where(~fixed, w, wp)

    for t in range(1, T + 1):
        sp = np.zeros(N, dtype=bool)
        sp[spikes_by_step[t]] = True
        learn = t < consolidate_from
        cons = t >= consolidate_from
        if learn:
            lastc = last.copy()
            lastc[sp] = t
            post_now = sp[post]
            dt_pre = t - lastc[pre[:, :]]
            ltp = post_now & (dt_pre >= 0) & (dt_pre <= 2 * D)
            t_fire = t - delay
            h2 = hist.copy()
            h2[t % H] = sp
            arrived = h2[np.remainder(t_fire, H), n_idx] & (delay > 0)
            last_post = last[post]
            ltd = arrived & (last_post < t_fire) & (last_post >= t_fire - delay)
            w = np.abs(eff())
            dw = (spec.a_plus * ltp - spec.a_minus * ltd) * w * (bound - w)
            wf += np.where(plastic, dw, 0.0)
            w = np.abs(eff())
            dw = spec.a_pre * sp[pre] * (bound - w) * w
            wf += np.where(plastic, dw, 0.0)
        if cons:
            g12 = np.clip((c2_open - spec.theta2) / spec.soft2, 0, 1)
            moved = spec.kappa * g12 * wf
            wp += moved
            wf -= moved
            exc_pre = net.isE[pre]
            wp = np.where(fixed, wp, np.where(exc_pre, np.clip(wp, lo, hi), np.clip(wp, -1.0, -0.05)))
        wf *= fd
        hist[t % H] = sp
        last[sp] = t
    return wp, wf


class TestPlasticity(unittest.TestCase):
    def test_event_plasticity_equals_dense_transliteration(self):
        spec = small_spec(syn_scale=0.06, neuron_scale=0.3)
        net = SpikingNetwork(spec, seed=5)
        net.reset_all()
        ga, gb = 4, 22
        injs = [net.inject_idx(ga), net.inject_idx(gb)]
        inj_all = np.concatenate(injs)
        spikes = {}
        T, T_learn = 120, 80
        net.reset_dynamics()
        for t in range(1, T + 1):
            if t == T_learn:
                net.c2.c[:] = 1.2
            net.step(20, learn=(t < T_learn), consolidate=(t >= T_learn), fmult=1.0, release1=False,
                     release2=False, chem=False, inj=inj_all if t <= 50 else None)
            spikes[t] = net.recent[0].copy()
        self.assertGreater(sum(len(v) for v in spikes.values()), 200)
        wp_ref, wf_ref = dense_plasticity_reference(net, spikes, 1.2, T_learn, T, spec)
        wf_mine = net.F.astype(np.float64) * net.m
        np.testing.assert_allclose(wf_mine, wf_ref, atol=2e-6)
        np.testing.assert_allclose(net.wp.astype(np.float64), wp_ref, atol=2e-6)
        self.assertGreater(np.abs(wf_ref).max(), 1e-3)
        self.assertGreater(np.abs(wp_ref - net.wp0).max(), 1e-4)       # consolidation moved something
        eff = net.effective_normalized(np.flatnonzero(net.touched_f))
        self.assertTrue(((eff >= spec.w_lo) & (eff <= spec.w_hi)).all())

    def test_fast_part_decays_only_in_learning_steps(self):
        spec = small_spec()
        net = SpikingNetwork(spec, seed=6)
        m0 = net.m
        net.step(20, False, False, 1.0, False, False, False, None)
        self.assertEqual(net.m, m0)
        net.step(20, True, False, 1.0, False, False, False, None)
        self.assertAlmostEqual(net.m, m0 * math.exp(-1 / 2000.0))


class TestActivityAndProtocol(unittest.TestCase):
    def test_activity_equals_group_activity(self):
        spec = small_spec()
        net = SpikingNetwork(spec, seed=7)
        net.reset_dynamics()
        inj = net.inject_idx(5)
        last = np.full(net.N, -10 ** 9)
        for t in range(1, 90):
            A, nf = net.step(20, False, False, 1.0, False, False, False, inj if t <= 50 else None)
            f = net.recent[0]
            last[f] = t
            recent = ((t - last) < 20) & net.isE
            ref = np.bincount(net.grp[recent], minlength=net.G) / np.maximum(net.nE, 1)
            np.testing.assert_allclose(A, ref, atol=1e-12, err_msg=f"step {t}")

    def test_quiet_without_injection(self):
        net = SpikingNetwork(small_spec(), seed=8)
        net.reset_dynamics()
        res = net.run(300, chem=False)
        self.assertEqual(res["spikes"], 0)

    def test_protocol_deterministic_and_classes(self):
        spec = small_spec(max_c1_rounds=2)
        outs = []
        for _ in range(2):
            net = SpikingNetwork(spec, seed=9)
            outs.append(run_pair_protocol(net, 3, 21, c2_stage=False, control0=True))
        for k in ("class", "c1_rounds", "strays"):
            self.assertEqual(outs[0][k], outs[1][k])
        self.assertIn(outs[0]["class"], ("none", "contained", "ignition"))

    def test_injection_scaling_and_release(self):
        spec = SpikeSpec.from_session(SESSION, neuron_scale=0.5, syn_scale=0.05)
        self.assertEqual(spec.k_red, 6)
        net = SpikingNetwork(spec, seed=0)
        self.assertAlmostEqual(net.release_scale, 2.0, places=2)
        self.assertEqual(len(net.inject_idx(100)), 6)


try:
    import torch
except Exception:                                    # host: torch is not installed
    torch = None


@unittest.skipUnless(torch is not None, "torch not installed (run on the pod)")
class TestAgainstRealEngineClasses(unittest.TestCase):
    """The real assoc_plasticity.GatedPlasticity, assoc_fields.GroupActivity and assoc_engine weight methods."""

    def test_gated_plasticity_equals_real_class(self):
        sys.path.insert(0, PARENT)
        from assoc_plasticity import GatedPlasticity
        spec = small_spec(syn_scale=0.06, neuron_scale=0.3)
        net = SpikingNetwork(spec, seed=5)
        net.reset_all()
        inj_all = np.concatenate([net.inject_idx(4), net.inject_idx(22)])
        n_rep = torch.as_tensor(net.post.T.astype(np.int64))
        delay = torch.as_tensor(net.delay.T.astype(np.int64))
        P = GatedPlasticity(n_rep, delay, torch.as_tensor(net.isE), torch.as_tensor(net.wp0.T.copy()), net.D,
                            a_plus=spec.a_plus, a_minus=spec.a_minus, tau_fast=spec.tau_fast, kappa=spec.kappa,
                            theta1=spec.theta1, theta2=spec.theta2, soft1=spec.soft1, soft2=spec.soft2,
                            fixed=torch.as_tensor((net.kind == KIND_EE_INTRA).T.copy()), rule="both", a_pre=spec.a_pre)
        net.reset_dynamics()
        c1 = torch.zeros(net.N)
        T, T_learn = 120, 80
        for t in range(1, T + 1):
            if t == T_learn:
                net.c2.c[:] = 1.2
            net.step(20, learn=(t < T_learn), consolidate=(t >= T_learn), fmult=1.0, release1=False,
                     release2=False, chem=False, inj=inj_all if t <= 50 else None)
            sp = torch.zeros(net.N, dtype=torch.bool)
            sp[torch.as_tensor(net.recent[0])] = True
            c2 = torch.full((net.N,), 1.2 if t >= T_learn else 0.0)
            P.step(sp, t, c1, c2, learn=(t < T_learn), consolidate=(t >= T_learn))
        np.testing.assert_allclose(P.w_fast.numpy().T, net.F.astype(np.float64) * net.m, atol=3e-6)
        np.testing.assert_allclose(P.w_perm.numpy().T, net.wp, atol=3e-6)

    def test_group_activity_equals_real_class(self):
        sys.path.insert(0, PARENT)
        from assoc_fields import GroupActivity
        net = SpikingNetwork(small_spec(), seed=7)
        net.reset_dynamics()
        ga = GroupActivity(torch.as_tensor(net.grp), net.G, window=20, member_mask=torch.as_tensor(net.isE))
        inj = net.inject_idx(5)
        for t in range(1, 80):
            A, nf = net.step(20, False, False, 1.0, False, False, False, inj if t <= 50 else None)
            sp = torch.zeros(net.N, dtype=torch.bool)
            sp[torch.as_tensor(net.recent[0])] = True
            np.testing.assert_allclose(A, ga.update(sp, t).numpy(), atol=1e-6)

    def test_weights_equal_real_engine_methods(self):
        sys.path.insert(0, PARENT)
        from assoc_engine import AssocEngine
        spec = small_spec()
        net = SpikingNetwork(spec, seed=1)

        class Stub:
            pass

        e = Stub()
        e.device = torch.device("cpu")
        e.N, e.S, e.G = net.N, net.S, net.G
        e.n_rep = torch.as_tensor(net.post.T.astype(np.int64))
        e.exc = torch.as_tensor(net.isE)
        e.groups = torch.as_tensor(net.grp)
        e.assembly = None
        e.assembly_of_neuron = lambda: torch.ones(e.N, dtype=torch.bool)
        pre = np.repeat(np.arange(net.N), net.S).reshape(net.N, net.S)
        pe, po = net.isE[pre], net.isE[net.post]
        built = np.where(pe & ~po, 0.45, np.where(~pe & po, -0.44, 0.47)).astype(np.float32)
        e.built_weights = torch.as_tensor(built.T.copy())
        e.weights = torch.zeros_like(e.built_weights)
        e.gain_map = None
        e.gain = 1.0
        w = AssocEngine.typed_weights(e, w_ee=0.05, w_intra_ee_total=40.0)
        AssocEngine.set_gains(e, spec.gain, spec.gain_ei, spec.gain_ie, spec.gain_ee_inter)
        AssocEngine.write_weights(e, w)
        real = e.weights.numpy().T.astype(float)
        same = net.grp[pre] == net.grp[net.post]
        factor = np.where(pe & ~po, spec.S * spec.frac_E_to_I / spec.S_ei,
                          np.where(~pe & po, spec.S / spec.S_red,
                                   np.where(pe & po & ~same, spec.S * (1 - spec.frac_E_to_I) / spec.S_ee, 1.0)))
        got = net.engine_weights(np.arange(net.N * net.S), 0.0).reshape(net.N, net.S).astype(float)
        np.testing.assert_allclose(got, real * factor, rtol=1e-5)


if __name__ == "__main__":
    unittest.main()
