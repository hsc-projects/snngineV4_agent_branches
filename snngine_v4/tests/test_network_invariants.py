"""
Tests of the invariant checks and the reference dynamics themselves, on small synthetic networks (numpy only, no
engine, no GPU). A correctly built synthetic network must pass every check; each known construction error,
reproduced on it (mutation), must be caught by the check meant for it.

  PYTHONPATH=<repo root> python -m unittest discover -s snngine_v4/tests -p "test_network_invariants.py" -v
"""

from __future__ import annotations

import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import network_invariants as inv          # noqa: E402
from reference_dynamics import ReferenceNetwork, single_neuron_rate   # noqa: E402

INH, EXC = inv.INH, inv.EXC


def synthetic_network(dim=3, n_inh=4, n_exc=16, S=50, D=4, seed=0):
    """A correctly built network in the engine's conventions: neurons ordered inhibitory first, then excitatory,
    each sorted by group; excitatory neurons have S/5 inhibitory and 4 S/5 excitatory targets, inhibitory ones S
    excitatory targets; targets drawn from groups weighted by exp(-delay); synapses sorted by delay, then by target;
    weights by type pair."""
    rng = np.random.default_rng(seed)
    G = dim ** 3
    shape, seg = (1.0, 1.0, 1.0), (dim, dim, dim)
    cell = np.array([(x, y, z) for z in range(dim) for y in range(dim) for x in range(dim)])  # engine order z, y, x
    types = np.concatenate([np.full(n_inh * G, INH), np.full(n_exc * G, EXC)])
    groups = np.concatenate([np.repeat(np.arange(G), n_inh), np.repeat(np.arange(G), n_exc)])
    N = len(types)
    pos = (cell[groups] + rng.uniform(0.05, 0.95, (N, 3))) / dim
    rule, _ = inv.delay_rule(cell, D)
    conns = [{"src_type": INH, "snk_type": EXC, "n_synapses": S, "w0": -0.44},
             {"src_type": EXC, "snk_type": INH, "n_synapses": S // 5, "w0": 0.45},
             {"src_type": EXC, "snk_type": EXC, "n_synapses": S - S // 5, "w0": 0.47}]
    post = np.zeros((N, S), np.int64)
    w = np.zeros((N, S), np.float32)
    for n in range(N):
        targets = []
        for c in conns:
            if c["src_type"] != types[n]:
                continue
            cand = np.nonzero((types == c["snk_type"]) & (np.arange(N) != n))[0]
            p = np.exp(-rule[groups[n], groups[cand]].astype(float))
            targets.append(rng.choice(cand, c["n_synapses"], replace=False, p=p / p.sum()))
        t = np.concatenate(targets)
        order = np.lexsort((t, rule[groups[n], groups[t]]))
        post[n] = t[order]
    delay = rule[groups[:, None], groups[post]]
    bnd = np.stack([(delay < r).sum(axis=1) for r in range(D + 1)], axis=1)
    for c in conns:
        m = (types[:, None] == c["src_type"]) & (types[post] == c["snk_type"])
        w[m] = c["w0"]
    # construction tables, as the engine's: cumulative synapses per source group and delay, per connection
    L = np.zeros((2 + 2 * D, G), np.int64)
    L[0] = np.bincount(groups[types == INH], minlength=G)
    L[1] = np.bincount(groups[types == EXC], minlength=G)
    for d in range(D):
        near = rule == d
        L[2 + d] = near.astype(np.int64) @ L[0]
        L[2 + D + d] = near.astype(np.int64) @ L[1]
    tables = {}
    for c in conns:
        T = np.zeros((D + 1, G), np.int64)
        rep = np.nonzero(types == c["src_type"])[0]
        for g in range(G):
            n = rep[groups[rep] == g][0]
            m = types[post[n]] == c["snk_type"]
            T[1:, g] = np.cumsum([(m & (delay[n] == d)).sum() for d in range(D)])
        tables[(c["src_type"], c["snk_type"])] = T
    return {"post": post, "bnd": bnd, "w": w, "types": types, "groups": groups, "pos": pos, "shape": shape,
            "seg": seg, "D": D, "conns": conns, "g2g_delay": rule, "L": L, "count_tables": tables}


def old_transpose(post_ns):
    """The construction's old conversion: memory written as (N, S) row-major, read through an (S, N) view and
    converted with .T.reshape((S, N)); returns the resulting table as (N, S)."""
    N, S = post_ns.shape
    mem = post_ns.reshape(-1)
    return mem.reshape(S, N).T.reshape(S, N).T.copy()


class InvariantsOnCorrectNetwork(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ex = synthetic_network()

    def test_all_checks_pass(self):
        res = inv.all_checks(self.ex)
        for name, violations in res.items():
            self.assertEqual(violations, [], f"{name}: {violations}")


class InvariantsCatchKnownErrors(unittest.TestCase):

    def setUp(self):
        self.ex = synthetic_network()

    def test_transpose_error_is_caught(self):
        ex = dict(self.ex, post=old_transpose(self.ex["post"]))
        res = inv.all_checks(ex)
        self.assertTrue(res["type_counts"], "the old transpose must break the per-neuron type counts")
        self.assertTrue(res["delays"], "the old transpose must break the delays of the synapses")

    def test_weights_by_slot_are_caught(self):
        w = self.ex["w"].copy()
        exc = self.ex["types"] == EXC
        n_ei = self.ex["conns"][1]["n_synapses"]
        w[exc, :n_ei] = 0.45                       # slot ranges of the configuration, after the sort by delay
        w[exc, n_ei:] = 0.47
        res = inv.all_checks(dict(self.ex, w=w))
        self.assertTrue(res["weights"])

    def test_negative_bucket_is_caught(self):
        tables = {k: v.copy() for k, v in self.ex["count_tables"].items()}
        T = tables[(INH, EXC)]
        T[2, 0] = T[1, 0] - 1                      # a cumulative row below the previous one
        res = inv.check_count_tables(tables, self.ex["L"], self.ex["D"], self.ex["conns"])
        self.assertTrue(any("negative" in v["message"] for v in res))

    def test_overfull_bucket_is_caught(self):
        tables = {k: v.copy() for k, v in self.ex["count_tables"].items()}
        T = tables[(EXC, INH)]
        T[1:, 0] += self.ex["L"][2, 0] + 5         # delay 0 asks for more inhibitory targets than exist
        T[-1, 0] = self.ex["conns"][1]["n_synapses"]
        res = inv.check_count_tables(tables, self.ex["L"], self.ex["D"], self.ex["conns"])
        self.assertTrue(res)

    def test_autapse_is_caught(self):
        post = self.ex["post"].copy()
        post[5, 0] = 5
        self.assertTrue(inv.check_targets_valid(post, self.ex["types"]))

    def test_wrong_delay_bucket_is_caught(self):
        bnd = self.ex["bnd"].copy()
        n = int(np.nonzero(np.diff(bnd[:, :3], axis=1).min(axis=1) > 0)[0][0])
        bnd[n, 1] += 1                              # one synapse moved from delay 1 to delay 0
        res = inv.check_delays(self.ex["post"], bnd, self.ex["groups"],
                               inv.group_cells(self.ex["pos"], self.ex["groups"], self.ex["shape"], self.ex["seg"]),
                               self.ex["D"])
        self.assertTrue(res)

    def test_old_transpose_flattens_profile(self):
        gc = inv.group_cells(self.ex["pos"], self.ex["groups"], self.ex["shape"], self.ex["seg"])

        def ratio(post):
            prof = inv.ee_profile(post, self.ex["types"], self.ex["groups"], gc)
            d = sorted(prof)
            return prof[d[0]] / max(prof[d[-1]], 1.0)

        self.assertEqual(inv.check_profile_decreases(self.ex["post"], self.ex["types"], self.ex["groups"], gc), [])
        self.assertLess(ratio(old_transpose(self.ex["post"])), ratio(self.ex["post"]))


class ReferenceDynamics(unittest.TestCase):

    def test_single_neuron(self):
        self.assertEqual(single_neuron_rate(0.02, 0.2, -65.0, 8.0, 0.0), 0)
        self.assertGreater(single_neuron_rate(0.02, 0.2, -65.0, 8.0, 10.0), 0)
        self.assertGreater(single_neuron_rate(0.02, 0.2, -65.0, 8.0, 20.0),
                           single_neuron_rate(0.02, 0.2, -65.0, 8.0, 10.0))

    def test_delivery_matches_buckets(self):
        ex = synthetic_network(dim=2, n_inh=2, n_exc=6, S=12, D=3)
        N = len(ex["types"])
        abcd = np.tile(np.array([[0.02, 0.2, -65.0, 8.0]], np.float32), (N, 1))
        net = ReferenceNetwork(ex["post"], ex["bnd"], ex["w"], abcd, np.full(N, -65.0), np.full(N, -13.0))
        n = 3
        expected = []
        for k in range(ex["D"]):
            e = np.zeros(N)
            lo, hi = ex["bnd"][n, k], ex["bnd"][n, k + 1]
            np.add.at(e, ex["post"][n, lo:hi], ex["w"][n, lo:hi])
            expected.append(e)
        got = [net.deliver(np.array([n]))] + [net.deliver(np.zeros(0, np.int64)) for _ in range(ex["D"] - 1)]
        for k in range(ex["D"]):
            np.testing.assert_allclose(got[k], expected[k], atol=1e-6)


if __name__ == "__main__":
    unittest.main()
