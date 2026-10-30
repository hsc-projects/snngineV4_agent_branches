"""
Engine tests on a GPU: build networks of several configurations (each in its own process, engine_export.py), then
check them with the invariants (network_invariants.py), the delivery probe and the reference dynamics
(reference_dynamics.py). Skipped unless SNN_ENGINE_TESTS=1 (they need the CUDA backend and a GPU).

  SNN_ENGINE_TESTS=1 PYTHONPATH=<repo root> python -m unittest discover -s snngine_v4/tests -p "test_engine.py" -v
  optional: SNN_ENGINE_CONFIGS=small,odd  (subset), SNN_ENGINE_EXPORT_DIR=/path (keep the exports)

Configurations are chosen to break symmetries that hide layout errors: N != S, N not a multiple of the GPU block
size, the two assembly-task sizes, and the delay count set by assoc_build.build_network(n_delays=...).
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

import network_invariants as inv                  # noqa: E402
from reference_dynamics import ReferenceNetwork  # noqa: E402

ENABLED = os.environ.get("SNN_ENGINE_TESTS") == "1"

# name: (n_neurons, n_synapses, n_delays or None, seed, reservoir shape)
CONFIGS = {
    "small": (2000, 200, None, 0, (1, 1, 1)),
    "odd": (3001, 150, None, 1, (1, 1, 1)),
    # several groups at delay 0, the own group not first among them (the autapse search in connector.cu), and source
    # groups without any group at the last delays
    "elongated": (3000, 150, 4, 2, (6, 1, 1)),
    "asm7": (20000, 2000, None, 0, (1, 1, 1)),
    "asm9": (42500, 2000, 16, 0, (1, 1, 1)),
}

_cache: dict = {}


def export(name):
    """Build and export one configuration (once per test run)."""
    if name in _cache:
        if isinstance(_cache[name], Exception):   # failed once: do not rebuild for every test
            raise _cache[name]
        return _cache[name]
    n, s, d, seed, shape = CONFIGS[name]
    base = os.environ.get("SNN_ENGINE_EXPORT_DIR") or tempfile.mkdtemp(prefix="snn_engine_tests_")
    out = os.path.join(base, name)
    shutil.rmtree(out, ignore_errors=True)       # a reused export directory: never test an older run's files
    cmd = [sys.executable, os.path.join(HERE, "engine_export.py"), "--n-neurons", str(n), "--n-synapses", str(s),
           "--seed", str(seed), "--out", out, "--reservoir-shape", *map(str, shape)] \
        + (["--n-delays", str(d)] if d else [])
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if proc.returncode != 0:
        _cache[name] = RuntimeError(f"export {name} failed:\n{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}")
        raise _cache[name]
    z = np.load(os.path.join(out, "network.npz"))
    meta = json.loads(open(os.path.join(out, "meta.json")).read())
    ex = {k: z[k] for k in z.files}
    D = int(meta["D"])
    ex.update({"D": D, "shape": meta["shape"], "seg": meta["seg"], "conns": meta["conns"], "meta": meta,
               "count_tables": {(1, 2): ex["table_1_2"], (2, 1): ex["table_2_1"], (2, 2): ex["table_2_2"]}})
    _cache[name] = ex
    return ex


def selected():
    sel = os.environ.get("SNN_ENGINE_CONFIGS")
    return [c for c in CONFIGS if not sel or c in sel.split(",")]


@unittest.skipUnless(ENABLED, "set SNN_ENGINE_TESTS=1 on a GPU machine")
class Construction(unittest.TestCase):

    _results: dict = {}

    def _check(self, check_name):
        for name in selected():
            with self.subTest(config=name):
                if name not in self._results:
                    self._results[name] = inv.all_checks(export(name))
                res = self._results[name]
                self.assertEqual(res[check_name], [], f"{name}: {json.dumps(res[check_name])[:2000]}")

    def test_targets_valid(self):
        self._check("targets_valid")

    def test_type_counts(self):
        self._check("type_counts")

    def test_delay_buckets(self):
        self._check("delay_buckets")

    def test_groups(self):
        self._check("groups")

    def test_delays(self):
        self._check("delays")

    def test_weights_by_type(self):
        self._check("weights")

    def test_count_tables(self):
        self._check("count_tables")

    def test_profile_decreases(self):
        self._check("profile")


@unittest.skipUnless(ENABLED, "set SNN_ENGINE_TESTS=1 on a GPU machine")
class Delivery(unittest.TestCase):

    def test_probe(self):
        """A single spike reaches exactly the targets of each delay bucket, with their weights, at that delay."""
        for name in selected():
            with self.subTest(config=name):
                ex = export(name)          # a failed build fails only this configuration's case
            if not isinstance(_cache.get(name), dict):
                continue
            N, D = len(ex["types"]), ex["D"]
            for j, n in enumerate(ex["probe_ids"]):
                with self.subTest(config=name, neuron=int(n)):
                    got = ex[f"probe_{j}_input"]
                    for k in range(D + 1):
                        e = np.zeros(N)
                        if k < D:
                            lo, hi = ex["bnd"][n, k], ex["bnd"][n, k + 1]
                            np.add.at(e, ex["post"][n, lo:hi], ex["w"][n, lo:hi])
                        np.testing.assert_allclose(got[k], e, atol=1e-4, err_msg=f"{name} neuron {n} step {k}")


@unittest.skipUnless(ENABLED, "set SNN_ENGINE_TESTS=1 on a GPU machine")
class Dynamics(unittest.TestCase):

    def test_neuron_model_flag(self):
        for name in selected():
            with self.subTest(config=name):
                self.assertTrue((export(name)["model_flag"] == 0).all())

    def test_reference(self):
        """The engine's injected run equals the numpy reference: input currents within float32 summation rounding
        until the first step whose spike set differs, and that step (if any) not before step 20."""
        for name in selected():
            with self.subTest(config=name):
                ex = export(name)
                meta = ex["meta"]
                net = ReferenceNetwork(ex["post"], ex["bnd"], ex["w"], ex["abcd"], ex["v0"], ex["u0"])
                ref_fired, ref_in = net.run(meta["sim_steps"], ex["sim_inject"], meta["inject_current"],
                                            meta["inject_steps"])
                offs = ex["sim_offsets"]
                eng_fired = [np.sort(ex["sim_fired"][offs[t]:offs[t + 1]]) for t in range(len(offs) - 1)]
                first = next((t for t in range(len(eng_fired)) if not np.array_equal(eng_fired[t], np.sort(ref_fired[t]))),
                             None)
                upto = len(eng_fired) if first is None else first
                for t in range(upto):
                    scale = max(1.0, float(np.abs(ex["sim_input"][t]).max()))
                    np.testing.assert_allclose(ex["sim_input"][t], ref_in[t], atol=1e-4 * scale,
                                               err_msg=f"{name}: input at step {t}")
                self.assertTrue(first is None or first >= 20, f"{name}: spike sets differ from step {first}")
                self.assertGreater(len(ex["sim_fired"]), 0, f"{name}: injected run without spikes")


if __name__ == "__main__":
    unittest.main()
