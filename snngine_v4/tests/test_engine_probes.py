"""
Tests of the engine's other CUDA paths, on probes recorded by engine_probes.py (GPU; skipped unless
SNN_ENGINE_TESTS=1): presynaptic indices, the engine's STDP, the spike ring buffer under near-total activity, the
chemical concentration update, thalamic and sensory input, and the removal of synapses to a group.

  SNN_ENGINE_TESTS=1 PYTHONPATH=<repo root> python -m unittest discover -s snngine_v4/tests -p "test_engine_probes.py" -v

Not covered: SnnRepresentation.swap_groups (no Python caller; its inputs come from commented-out code in
synapses.py) and the plot kernels (visual only).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from reference_dynamics import ReferenceNetwork   # noqa: E402

ENABLED = os.environ.get("SNN_ENGINE_TESTS") == "1"
F32 = np.float32

# name: (n_neurons, n_synapses, n_delays or None, chemistry grid, seed); the grid is an edge length (cube) or
# (height, width, depth). 96^3 needs more thread blocks than a GPU runs at once (a block that read its
# neighbours' cells after they were updated would show; the grid's max_z = 100 limits the size); 30 x 22 x 38
# has three different sizes, none a multiple of the kernel's block (32 x 4 x 4), so a mixed-up axis in the
# kernel's indexing or launch shows (a cube cannot tell width from depth)
# "ring16": D 16 as in the 9 x 9 x 9 assembly networks, where 90 % activity reaches the spike buffer's rewind in
# fewer than D steps
CONFIGS = {"small": (2000, 200, None, 96, 0), "odd": (3001, 150, None, (30, 22, 38), 1),
           "ring16": (8000, 200, 16, 32, 2)}
_cache: dict = {}


def probes(name):
    if name in _cache:
        if isinstance(_cache[name], Exception):   # failed once: do not rerun the probes for every test
            raise _cache[name]
        return _cache[name]
    n, s, d, chem, seed = CONFIGS[name]
    base = os.environ.get("SNN_ENGINE_EXPORT_DIR") or tempfile.mkdtemp(prefix="snn_engine_probes_")
    out = os.path.join(base, f"probes_{name}")
    shutil.rmtree(out, ignore_errors=True)       # a reused export directory: never test an older run's files
    cmd = [sys.executable, os.path.join(HERE, "engine_probes.py"), "--n-neurons", str(n), "--n-synapses", str(s),
           "--seed", str(seed), "--out", out] + (["--n-delays", str(d)] if d else []) \
        + (["--chem-shape", *map(str, chem)] if isinstance(chem, tuple) else ["--chem-dim", str(chem)])
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    failed = f"probes {name} failed:\n{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}" if proc.returncode != 0 else None
    if not os.path.exists(os.path.join(out, "probes.npz")):
        _cache[name] = RuntimeError(failed or f"probes {name}: no results")
        raise _cache[name]
    # engine_probes.py saves before its removal steps: after a failure there, the earlier probes are still tested
    z = np.load(os.path.join(out, "probes.npz"))
    p = {k: z[k] for k in z.files}
    p["meta"] = json.loads(open(os.path.join(out, "probes.json")).read())
    p["probe_error"] = failed
    _cache[name] = p
    return p


def need(p, *keys):
    """Fail (not error) with the probe script's own error when a probe's results are missing."""
    missing = [k for k in keys if k not in p and k not in p["meta"]]
    if missing:
        raise AssertionError(f"no results for {missing}; the probe run failed:\n{p.get('probe_error')}")


def selected():
    sel = os.environ.get("SNN_ENGINE_CONFIGS")
    return [c for c in CONFIGS if not sel or c in sel.split(",")]


def presynaptic_violations(post, pre, idcs, counts):
    """The presynaptic index: counts are the cumulative in-degrees; the entries of neuron m list exactly the
    synapses (index n + N s) whose target is m, and pre holds their source neuron."""
    N, S = post.shape
    out = []
    flat = post.ravel()
    valid = flat >= 0                               # deleted synapses (-1, -2) are not listed
    indeg = np.bincount(flat[valid], minlength=N)
    if counts[0] != 0 or not np.array_equal(np.diff(counts), indeg):
        out.append("counts are not the cumulative in-degrees")
        return out
    syn_idx = (np.arange(N)[:, None] + np.arange(S)[None, :] * N).ravel()[valid]
    expected = syn_idx[np.argsort(flat[valid], kind="stable")]
    for m in range(N):
        lo, hi = counts[m], counts[m + 1]
        if set(idcs[lo:hi].tolist()) != set(expected[lo:hi].tolist()):
            out.append(f"neuron {m}: listed synapses differ")
            break
    n_valid = int(valid.sum())
    if not np.array_equal(pre[:n_valid], idcs[:n_valid] % N):
        out.append("pre is not the source neuron of the listed synapse")
    return out


def chem_reference(c, steps, k, dep, source=None):
    c = c.astype(F32).copy()
    src = np.zeros_like(c) if source is None else source
    for _ in range(steps):
        p = np.pad(c, 1, mode="edge")
        s = (p[2:, 1:-1, 1:-1] + p[:-2, 1:-1, 1:-1] + p[1:-1, 2:, 1:-1] + p[1:-1, :-2, 1:-1]
             + p[1:-1, 1:-1, 2:] + p[1:-1, 1:-1, :-2])
        new = np.clip(c + F32(k) * (s - F32(6) * c) - F32(dep), 0, 2000).astype(F32)
        c = np.where(src > 0, src, new).astype(F32)
    return c


@unittest.skipUnless(ENABLED, "set SNN_ENGINE_TESTS=1 on a GPU machine")
class PresynapticIndex(unittest.TestCase):

    def test_built_with_the_network(self):
        """The engine's STDP reads the presynaptic index; it must exist once the network is built."""
        for name in selected():
            with self.subTest(config=name):
                p = probes(name)
                self.assertEqual(presynaptic_violations(p["post"], p["built_pre"], p["built_pre_idcs"],
                                                        p["built_pre_counts"]), [])

    def test_actualize_kernel(self):
        for name in selected():
            with self.subTest(config=name):
                p = probes(name)
                self.assertEqual(presynaptic_violations(p["post"], p["actualized_pre"], p["actualized_pre_idcs"],
                                                        p["actualized_pre_counts"]), [])


@unittest.skipUnless(ENABLED, "set SNN_ENGINE_TESTS=1 on a GPU machine")
class Stdp(unittest.TestCase):
    """One excitatory -> excitatory synapse A -> B, reward configuration (1) for every group pair."""

    def _expected(self, w0, a, params):
        dw = params["phi_r"] * a * abs(w0) * (abs(params["max_w_exc"]) - abs(w0))
        return float(np.clip(w0 + dw, params["min_w_exc"], params["max_w_exc"]))

    def test_causal_pair_potentiates(self):
        for name in selected():
            with self.subTest(config=name):
                m = probes(name)["meta"]["stdp"]
                w0, w1, n_a, n_b = m["causal"]
                self.assertEqual((n_a, n_b), (1, 1), "A and B must fire exactly once")
                self.assertAlmostEqual(w1, self._expected(w0, m["params"]["a_r_p"], m["params"]), places=5)

    def test_anticausal_pair_depresses(self):
        for name in selected():
            with self.subTest(config=name):
                m = probes(name)["meta"]["stdp"]
                w0, w1, n_a, n_b = m["anticausal"]
                self.assertEqual((n_a, n_b), (1, 1), "A and B must fire exactly once")
                self.assertAlmostEqual(w1, self._expected(w0, m["params"]["a_r_m"], m["params"]), places=5)

    def test_inhibitory_weight_bounded_by_its_own_type(self):
        """Potentiation of an inhibitory -> excitatory weight uses the inhibitory bound |min_w_inh| (the weight's
        own type), not the excitatory max_w_exc (set to 0.8 for this probe so the two differ)."""
        for name in selected():
            with self.subTest(config=name):
                m = probes(name)["meta"]["stdp_inh"]
                pr = m["params"]
                w0, w1, n_a, n_b = m["causal"]
                self.assertEqual((n_a, n_b), (1, 1), "A and B must fire exactly once")
                dw = pr["phi_r"] * pr["a_r_p"] * abs(w0) * (abs(pr["min_w_inh"]) - abs(w0))
                self.assertAlmostEqual(w1, float(np.clip(w0 + dw, pr["min_w_inh"], pr["max_w_inh"])), places=5)

    def test_unconfigured_pair_unchanged(self):
        for name in selected():
            with self.subTest(config=name):
                w0, w1, _, _ = probes(name)["meta"]["stdp"]["causal_config0"]
                self.assertEqual(w0, w1)


@unittest.skipUnless(ENABLED, "set SNN_ENGINE_TESTS=1 on a GPU machine")
class RingBuffer(unittest.TestCase):

    def test_delivery_under_near_total_activity(self):
        """With most neurons firing every step (several rewinds of the spike buffer), every step's synaptic input
        equals the delivery of exactly the spikes of the last D steps."""
        for name in selected():
            with self.subTest(config=name):
                p = probes(name)
                need(p, "ring_fired", "ring_input")
                N = len(p["types"])
                ref = ReferenceNetwork(p["post"], p["bnd"], p["w"], np.zeros((N, 4), F32), np.zeros(N), np.zeros(N))
                offs = p["ring_offsets"]
                for t in range(len(offs) - 1):
                    exp = ref.deliver(p["ring_fired"][offs[t]:offs[t + 1]])
                    scale = max(1.0, float(np.abs(exp).max()))
                    np.testing.assert_allclose(p["ring_input"][t], exp, atol=1e-4 * scale,
                                               err_msg=f"{name}: step {t}")


@unittest.skipUnless(ENABLED, "set SNN_ENGINE_TESTS=1 on a GPU machine")
class Chemistry(unittest.TestCase):
    """update_chemical_concentrations_: explicit diffusion step, edges reflecting, clipped to [0, 2000], minus the
    depreciation; cells with a positive source hold the source value."""

    def test_one_step(self):
        for name in selected():
            with self.subTest(config=name):
                p, m = probes(name), probes(name)["meta"]["chem"]
                exp = chem_reference(p["chem_field0"], 1, m["k_val"], m["depreciation"])
                np.testing.assert_allclose(p["chem_1_current"], exp, atol=1e-3)
                np.testing.assert_allclose(p["chem_1_next"], exp, atol=1e-3)

    def test_ten_steps(self):
        for name in selected():
            with self.subTest(config=name):
                p, m = probes(name), probes(name)["meta"]["chem"]
                exp = chem_reference(p["chem_field0"], 10, m["k_val"], m["depreciation"])
                np.testing.assert_allclose(p["chem_10_current"], exp, atol=1e-2)

    def test_deterministic(self):
        for name in selected():
            with self.subTest(config=name):
                p = probes(name)
                np.testing.assert_array_equal(p["chem_10_current"], p["chem_10_current_repeat"])

    def test_mass_conserved_without_depreciation(self):
        for name in selected():
            with self.subTest(config=name):
                p, m = probes(name), probes(name)["meta"]["chem"]
                if m["depreciation"] != 0.0:
                    self.skipTest("depreciation configured")
                self.assertAlmostEqual(float(p["chem_10_current"].sum()) / float(p["chem_field0"].sum()), 1.0,
                                       places=4)

    def test_point_source(self):
        for name in selected():
            with self.subTest(config=name):
                p, m = probes(name), probes(name)["meta"]["chem"]
                src = np.zeros_like(p["chem_field0"])
                src[tuple(m["source"])] = 500.0
                exp = chem_reference(p["chem_field0"], 10, m["k_val"], m["depreciation"], source=src)
                np.testing.assert_allclose(p["chem_src_current"], exp, atol=1e-2)


@unittest.skipUnless(ENABLED, "set SNN_ENGINE_TESTS=1 on a GPU machine")
class Inputs(unittest.TestCase):

    def test_thalamic_currents_by_type(self):
        """pt 1: every neuron gets a current uniform in (0, current of its type]."""
        for name in selected():
            with self.subTest(config=name):
                p = probes(name)
                th, x = p["meta"]["thalamic"], p["input_thalamic_pt1"]
                e, i = p["types"] == 2, p["types"] == 1
                self.assertTrue((x[e] > 0).all() and (x[e] <= th["exc_current"] + 1e-4).all())
                self.assertTrue((x[i] > 0).all() and (x[i] <= th["inh_current"] + 1e-4).all())
                self.assertAlmostEqual(float(x[e].mean()) / (th["exc_current"] / 2), 1.0, delta=0.1)
                self.assertAlmostEqual(float(x[i].mean()) / (th["inh_current"] / 2), 1.0, delta=0.1)

    def test_thalamic_probability(self):
        for name in selected():
            with self.subTest(config=name):
                frac = float((probes(name)["input_thalamic_pt03"] > 0).mean())
                self.assertAlmostEqual(frac, 0.3, delta=0.05)

    def test_sensory_input(self):
        for name in selected():
            with self.subTest(config=name):
                p = probes(name)
                m, x = p["meta"]["sensory"], p["input_sensory"]
                ids = p["sensory_ids"]
                in_t1 = p["groups"][ids] == m["group_type1"]
                np.testing.assert_allclose(x[ids[in_t1]], m["current1"], atol=1e-5)
                np.testing.assert_allclose(x[ids[~in_t1]], m["current0"], atol=1e-5)
                others = np.setdiff1d(np.arange(len(x)), ids)
                np.testing.assert_allclose(x[others], 0.0, atol=1e-5)


@unittest.skipUnless(ENABLED, "set SNN_ENGINE_TESTS=1 on a GPU machine")
class Removal(unittest.TestCase):

    def test_nullify_weights_to_group(self):
        for name in selected():
            with self.subTest(config=name):
                p = probes(name)
                need(p, "removal", "nullified_w")
                g = p["meta"]["removal"]["group"]
                to_g = p["groups"][p["post"]] == g
                self.assertTrue((p["nullified_w"][to_g] == 0).all())
                np.testing.assert_array_equal(p["nullified_w"][~to_g], p["w"][~to_g])

    def test_remove_synapses_to_group(self):
        for name in selected():
            with self.subTest(config=name):
                p = probes(name)
                need(p, "removal", "removed_post")
                g = p["meta"]["removal"]["group"]
                to_g = p["groups"][p["post"]] == g
                self.assertTrue((p["removed_post"][to_g] == -2).all())
                np.testing.assert_array_equal(p["removed_post"][~to_g], p["post"][~to_g])

    def test_remove_marks_presynaptic_entries(self):
        """The presynaptic entries of the group's neurons are marked -2, and no other entry changes."""
        for name in selected():
            with self.subTest(config=name):
                p = probes(name)
                need(p, "removal", "before_removal_pre", "after_removal_pre")
                g = p["meta"]["removal"]["group"]
                counts = p["before_removal_pre_counts"]
                mask = np.zeros(len(p["before_removal_pre"]), bool)
                for m in np.nonzero(p["groups"] == g)[0]:
                    mask[counts[m]:counts[m + 1]] = True
                after, before = p["after_removal_pre"], p["before_removal_pre"]
                self.assertTrue((after[mask] == -2).all(), "entries of the group's neurons not marked")
                np.testing.assert_array_equal(after[~mask], before[~mask], err_msg="other entries changed")

    def test_operations_with_deleted_synapses(self):
        """A second removal and zeroing weights after a removal change nothing; the presynaptic index rebuilt with
        deleted synapses lists exactly the remaining ones."""
        for name in selected():
            with self.subTest(config=name):
                p = probes(name)
                need(p, "removed_twice_post", "rebuilt_after_removal_pre")
                np.testing.assert_array_equal(p["removed_twice_post"], p["removed_post"])
                np.testing.assert_array_equal(p["nullified_after_removal_w"], p["nullified_w"])
                self.assertEqual(presynaptic_violations(p["removed_post"], p["rebuilt_after_removal_pre"],
                                                        p["rebuilt_after_removal_pre_idcs"],
                                                        p["rebuilt_after_removal_pre_counts"]), [])


if __name__ == "__main__":
    unittest.main()
