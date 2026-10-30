"""
rerun_build_audit.py

Step 1 of engine-fix-rerun-task.md: checks the invariants of a correct build
(snngine_v4/tests/network_invariants.py) on a network exported by rate-model/round6_export_engine.py (with arrays),
i.e. as the harness builds it, unrewired or rewired.

  python rerun_build_audit.py EXPORT_DIR [EXPORT_DIR ...] --out audit.json

Checks per export: targets valid (no deleted synapses, no autapses); synapses per neuron onto each type equal the
configured type connections (excitatory: S/5 onto inhibitory, 4 S/5 onto excitatory; inhibitory: S onto
excitatory, none onto inhibitory); delay buckets well formed; every synapse's delay equals round((D - 1) d / d_max)
of its group pair, where an exact tie (x.5) may round either way (the engine and the rewiring compute in float32);
excitatory -> excitatory synapses per group pair fall with distance (median at the nearest distance at least 3
times the one at the largest distances, as the engine tests). Weights are not checked: the harness rescales them.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("SNN_REPO", os.path.dirname(os.path.dirname(HERE)))   # SNN_REPO: when run from a copy
TESTS = os.path.join(REPO, "snngine_v4", "tests")
if TESTS not in sys.path:
    sys.path.insert(0, TESTS)

import network_invariants as inv  # noqa: E402


def configured_conns(S: int) -> list[dict]:
    """The engine's default type connections (n_type_groups.py; agents/mapping/synapse-construction.md)."""
    return [{"src_type": inv.EXC, "snk_type": inv.INH, "n_synapses": S // 5, "w0": None},
            {"src_type": inv.EXC, "snk_type": inv.EXC, "n_synapses": S - S // 5, "w0": None},
            {"src_type": inv.INH, "snk_type": inv.EXC, "n_synapses": S, "w0": None}]


def check_delays_tie_tolerant(post, bnd, groups, group_cell, D, seg):
    """Delay of every synapse against round((D - 1) d / d_max), d_max = the grid's diagonal; a synapse whose
    group pair lies exactly on a tie may differ by one. Returns (violations, number of synapses on a tie that
    rounded the other way)."""
    S = post.shape[1]
    c = group_cell.astype(np.float64)
    dist = np.linalg.norm(c[:, None, :] - c[None, :, :], axis=2)
    x = (D - 1) * dist / float(np.linalg.norm(np.asarray(seg, dtype=np.float64) - 1))
    rule = np.rint(x).astype(np.int16)
    tie = np.abs(x - np.floor(x) - 0.5) < 1e-6
    pc = np.clip(post, 0, len(groups) - 1)
    got = inv.synapse_delays(bnd, S)
    gi, gj = groups[:, None], groups[pc]
    diff = got - rule[gi, gj]                                    # int16: (N, S) arrays of 11^3 stay small
    on_tie = tie[gi, gj] & (np.abs(diff) == 1)
    bad = (diff != 0) & ~on_tie
    out = []
    if bad.any():
        out.append(inv._v("delays", "synapse delay differs from round((D-1) d / d_max)",
                          synapses_wrong=int(bad.sum()), fraction=float(bad.mean()),
                          neurons=np.unique(np.nonzero(bad)[0])[:10]))
    return out, int(on_tie.sum())


def audit(export_dir: str) -> dict:
    meta = json.load(open(os.path.join(export_dir, "meta.json")))
    post = np.load(os.path.join(export_dir, "post.npy"))
    bnd = np.load(os.path.join(export_dir, "bnd.npy"))
    types = np.load(os.path.join(export_dir, "types.npy")).astype(np.int64)
    groups = np.load(os.path.join(export_dir, "groups.npy")).astype(np.int64)
    group_cell = np.load(os.path.join(export_dir, "group_cell.npy")).astype(np.int64)
    S, D, seg = int(meta["S"]), int(meta["D"]), meta["seg"]
    conns = configured_conns(S)
    delays, ties = check_delays_tie_tolerant(post, bnd, groups, group_cell, D, seg)
    res = {
        "targets_valid": inv.check_targets_valid(post, types),
        "type_counts": inv.check_type_counts(post, types, conns),
        "delay_buckets": inv.check_delay_buckets(bnd, S),
        "delays": delays,
        "profile": inv.check_profile_decreases(post, types, groups, group_cell),
    }
    prof = inv.ee_profile(post, types, groups, group_cell)
    ds = sorted(prof)
    far = float(np.median([prof[d] for d in ds[-max(1, len(ds) // 5):]]))
    pa = meta.get("audit", {}).get("per_pre_neuron", {})
    return {
        "export": os.path.basename(export_dir.rstrip("/")), "N": int(meta["N"]), "S": S, "D": D, "G": int(meta["G"]),
        "seg": seg, "rewire": meta["engine"].get("rewire"), "build_seconds": meta.get("build_seconds"),
        "passed": all(not v for v in res.values()), "violations": res, "delay_ties_rounded_other_way": ties,
        "ee_profile_median_per_group_pair": {f"{d:.4f}": v for d, v in prof.items()},
        "ee_near_over_far": prof[ds[0]] / max(far, 1.0),
        "per_pre_neuron": {k: pa.get(k) for k in ("EE_all", "EI_all", "IE_all", "II", "EE_intra")},
        "intra_group_ee_per_exc_neuron": meta.get("structure_report", {}).get("intra_group_ee_synapses_per_exc_neuron"),
        "control0_spikes": {j["job"]: {d: j["tests"][d].get("spikes") for d in ("AB", "BA")} for j in meta["jobs"]},
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("exports", nargs="+")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    results = [audit(d) for d in args.exports]
    with open(args.out, "w") as f:
        json.dump(results, f, indent=1)
    for r in results:
        print(f"{r['export']}: {'PASS' if r['passed'] else 'FAIL'}; "
              f"violations {[k for k, v in r['violations'].items() if v]}; "
              f"E->E near/far {r['ee_near_over_far']:.1f}; delay ties {r['delay_ties_rounded_other_way']}", flush=True)
    print("AUDIT DONE")


if __name__ == "__main__":
    main()
