"""
round6_test_construction_fix.py

Round 6: test of the fix of the synapse-table transpose in snngine_v4/nn/synapses.py (Synapses.fill_tensors). The
construction kernels write N_rep as (N, S) row-major; the old line `N_rep.gpu_values.T.reshape(N_rep.shape)` is a
transpose only for N == S and gave every neuron a mix of other neurons' synapse lists. Run on a GPU pod with the
fixed code first on PYTHONPATH (one engine configuration per process):

  python round6_test_construction_fix.py --n-neurons 20000 --seed 0 --out RESULT.json [--n-delays 16]
         [--old-export DIR]     round-6 export of the old engine, same N and seed (per-neuron comparison)

Builds the engine without rewiring and checks, on the fixed table and on the old line's result reconstructed from it:
  * inhibitory targets per neuron: configuration 400 per excitatory neuron (gen_factors 1 : 4), 0 per inhibitory one
  * the delay of every synapse (its N_delays bucket) against the engine's rule round((D - 1) d / d_max)
  * E -> E synapses per ordered group pair by cell distance (iteration 39 measured a flat profile)
  * built weights by type pair (written by slot range, n_type_groups.apply_init_weights)
  * with --old-export: per neuron, the old line's inhibitory-target count equals the old engine's (round-6 export,
    after rewiring, which keeps each target's type), i.e. the old line explains the old network exactly
Then a short simulation (A-alone injection through AssocRun, as the spiking jobs) checks that the fixed engine runs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
for _p in (HERE, PARENT):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def stats(x):
    x = np.asarray(x, dtype=np.float64)
    return {"mean": float(x.mean()), "min": float(x.min()), "max": float(x.max())} if x.size else {}


def composition(post_ns, isE):
    """Inhibitory targets per neuron, by presynaptic type."""
    n_inh = (~isE[post_ns]).sum(axis=1)
    return {"exc_neurons": stats(n_inh[isE]), "inh_neurons": stats(n_inh[~isE]),
            "exc_with_400": int((n_inh[isE] == 400).sum()), "n_exc": int(isE.sum()),
            "inh_with_0": int((n_inh[~isE] == 0).sum()), "n_inh": int((~isE).sum())}, n_inh


def delay_agreement(post_ns, bnd_nd, grp, dist_gg, D):
    S = post_ns.shape[1]
    delay = np.zeros(post_ns.shape, dtype=np.int16)
    cols = np.arange(S)[None, :]
    for r in range(1, D + 1):
        delay += (cols >= bnd_nd[:, r:r + 1])
    rule = np.rint((D - 1) * dist_gg[grp[:, None], grp[post_ns]] / dist_gg.max()).astype(np.int16)
    return float((delay == rule).mean())


def ee_profile(post_ns, isE, grp, dist_gg):
    """Median and mean E -> E synapses per ordered group pair, by cell distance (rounded to 0.1)."""
    G = dist_gg.shape[0]
    m = isE[:, None] & isE[post_ns]
    pre_g = np.broadcast_to(grp[:, None], post_ns.shape)[m]
    cnt = np.bincount(pre_g * G + grp[post_ns][m], minlength=G * G).reshape(G, G).astype(float)
    out = {}
    for d in (1.0, 2.0, 3.0, 4.0, 6.0):
        sel = np.abs(dist_gg - d) < 1e-6
        if sel.any():
            out[str(d)] = {"median": float(np.median(cnt[sel])), "mean": float(cnt[sel].mean())}
    far = dist_gg >= dist_gg.max() - 1.5
    out["farthest"] = {"median": float(np.median(cnt[far])), "mean": float(cnt[far].mean())}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-neurons", type=int, required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n-delays", type=int, default=None)
    ap.add_argument("--old-export", default=None)
    ap.add_argument("--params", default=None, help="spiking job params file for the simulation check (first job)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    import torch
    from assoc_engine import AssocEngine, FLAG_TYPE, FLAG_GROUP, TYPE_EXC
    import snngine_v4.nn.synapses as syn_mod
    t0 = time.time()
    eng = AssocEngine(torch.device("cuda:0"), n_neurons=a.n_neurons, seed=a.seed, n_synapses=2000, rewire=None,
                      n_delays=a.n_delays)
    N, S, D, G = eng.N, eng.S, eng.D, eng.G
    res = {"code": syn_mod.__file__, "fixed_line_present": "reshape(N, S).T" in open(syn_mod.__file__).read(),
           "N": N, "S": S, "D": D, "G": G, "seed": a.seed, "build_seconds": time.time() - t0}
    isE = (eng.flags[FLAG_TYPE] == TYPE_EXC).cpu().numpy()
    grp = eng.flags[FLAG_GROUP].cpu().numpy().astype(np.int64)
    gc = eng.group_cell.cpu().numpy().astype(float)
    dist_gg = np.linalg.norm(gc[:, None, :] - gc[None, :, :], axis=2)
    rep = eng.n_rep.cpu().numpy()                       # (S, N), fixed: synapse s of neuron n at [s, n]
    bnd = eng.n_delays.cpu().numpy().T.copy()           # (N, D + 1)
    w = eng.built_weights.cpu().numpy()                 # (S, N)
    post_fixed = rep.T.copy()                           # (N, S)
    # the old line's result, reconstructed: the pre-transpose memory is post_fixed in row-major order
    mem = post_fixed.reshape(-1)
    old = mem.reshape(S, N).T.reshape(S, N)             # gpu_values (S, N) view of that memory, .T.reshape(shape)
    post_old = old.T.copy()
    res["deleted_or_negative"] = int((rep < 0).sum())
    res["autapses_fixed"] = int((post_fixed == np.arange(N)[:, None]).sum())
    res["fixed"], n_inh_fixed = composition(post_fixed, isE)
    res["old_line"], n_inh_old = composition(post_old, isE)
    res["delay_rule_agreement"] = {"fixed": delay_agreement(post_fixed, bnd, grp, dist_gg, D),
                                   "old_line": delay_agreement(post_old, bnd, grp, dist_gg, D)}
    res["ee_per_group_pair_by_distance"] = {"fixed": ee_profile(post_fixed, isE, grp, dist_gg),
                                            "old_line": ee_profile(post_old, isE, grp, dist_gg)}
    wt = {}
    pre = np.broadcast_to(isE[None, :], rep.shape)
    pst = isE[rep]
    for name, m in (("EE", pre & pst), ("EI", pre & ~pst), ("IE", ~pre & pst), ("II", ~pre & ~pst)):
        if m.any():
            v, c = np.unique(np.round(w[m], 4), return_counts=True)
            wt[name] = {str(float(x)): int(k) for x, k in zip(v, c)}
    res["built_weights_fixed"] = wt
    if a.old_export:
        old_post = np.load(os.path.join(a.old_export, "post.npy"), mmap_mode="r")
        old_types = np.load(os.path.join(a.old_export, "types.npy"))
        same_types = bool(np.array_equal(old_types == TYPE_EXC, isE))
        n_inh_export = np.zeros(N, dtype=np.int64)
        for lo in range(0, N, 2000):
            n_inh_export[lo:lo + 2000] = (old_types[np.asarray(old_post[lo:lo + 2000])] != TYPE_EXC).sum(axis=1)
        res["old_export_comparison"] = {"same_neuron_types": same_types,
                                        "neurons_equal": int((n_inh_export == n_inh_old).sum()), "N": N,
                                        "max_abs_diff": int(np.abs(n_inh_export - n_inh_old).max())}
    # simulation check: A-alone injection through AssocRun with the spiking job's parameters, without rewiring
    if a.params:
        from assoc_protocol import AssocRun, DEFAULTS
        spec = json.loads(open(a.params).read())
        job = spec["jobs"][0]
        p = dict(job["params"])
        p["deadline"] = None
        run = AssocRun(eng, p, rng_seed=eng.seed + 4)
        run.reset_all()
        g = int(np.argmax(np.bincount(grp[isE], minlength=G)))
        _, _, ns = run.run(100, inject=[run.inject_idx_cached(g)], chem=False)
        res["simulation_check"] = {"group": g, "spikes_100_steps": int(ns), "runaway": run.stopped,
                                   "finite_v": bool(torch.isfinite(eng.states[2]).all())}
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: res[k] for k in ("N", "fixed_line_present", "fixed", "old_line", "delay_rule_agreement")},
                     indent=1))
    if "old_export_comparison" in res:
        print("old export comparison:", res["old_export_comparison"])
    print("E->E per group pair, fixed:", res["ee_per_group_pair_by_distance"]["fixed"])
    print("E->E per group pair, old:  ", res["ee_per_group_pair_by_distance"]["old_line"])
    print("built weights (fixed):", res["built_weights_fixed"])
    print("simulation:", res.get("simulation_check"))
    print("TEST DONE")


if __name__ == "__main__":
    main()
