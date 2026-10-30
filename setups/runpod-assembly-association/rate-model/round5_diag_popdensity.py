"""
round5_diag_popdensity.py

Round 5, model A (population density): the C1 stage of the protocol on 9 x 9 x 9 for the 24 pair positions of the
spiking s73 d 4 runs (../archive-pre-engine-fix/rate-model/s73_g9_d4_pairs.json), recording per round the quantities the spiking job JSONs hold
(training-round spikes, others_max and path_max of the training round, and for the A-alone test after each round the
groups active outside A, B and the route, B's maximum and the spikes), so that round_by_round comparison with
output-round5/compare_traces.py is possible. Same output layout as round5_diag_spiking.py.

  python round5_diag_popdensity.py --out R.json [--seeds 0,1] [--pairs 0-23] [--workers 4] [--grid 9]
         [--set key=value ...]        PopSpec overrides (e.g. sigma_scale=0 plast_scale handled via a_pre/a_plus/a_minus:
                                      use --plast 0.31)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

from popdensity_model import PopNetwork, PopSpec
from rate_model import path_groups, run_test
from admission_test import SESSION

HERE = os.path.dirname(os.path.abspath(__file__))
GRID = 9


def make_spec(over: dict, plast: float = 1.0, grid: int = 9) -> PopSpec:
    base = PopSpec.from_session(SESSION)
    kw = {}
    if grid == 9:
        kw.update(grid_dim=9, neurons_per_group=42500 / 729.0, max_active_frac=34 / 729.0, n_delays=16)
    kw.update(over)
    kw.setdefault("sigma_scale", 0.0)
    kw.setdefault("sigma_floor", 0.0)
    return PopSpec.from_session(SESSION, a_pre=base.a_pre * plast, a_plus=base.a_plus * plast, a_minus=base.a_minus * plast, **kw)


def parse_set(items):
    out = {}
    for it in items or []:
        k, v = it.split("=", 1)
        try:
            out[k] = int(v)
        except ValueError:
            try:
                out[k] = float(v)
            except ValueError:
                out[k] = {"true": True, "false": False, "none": None}.get(v.lower(), v)
    return out


def total_spikes(net) -> int:
    return int(net.spk_E_total.sum() + net.spk_I_total.sum())


def traced_round(net, groups, learn=True, release1=True):
    s = net.spec
    net.reset_dynamics()
    inj = net.injection(groups)
    gmax = np.zeros(net.G)
    for i in range(s.inject_steps + s.gap_steps):
        net.step(inj=inj if i < s.inject_steps else None, learn=learn, consolidate=False, release1=release1, release2=False)
        np.maximum(gmax, net.activity(), out=gmax)
    return gmax, total_spikes(net)


def _job(args):
    over, plast, seed, pair, grid = args
    spec = make_spec(over, plast, grid)
    t0 = time.perf_counter()
    net = PopNetwork(spec, seed=seed)
    net.reset_all()
    a, b, c = pair["A"], pair["B"], pair["C"]
    path = path_groups(net.coords, a, b)
    ctl = {}
    for key, (src, dst) in (("A_to_B", (a, b)), ("B_to_A", (b, a))):
        t = run_test(net, src, dst, "perm", path)
        ctl[key] = {"src_max": t["src_max"], "dst_max": t["dst_max"], "n_active_outside": t["n_active_outside"],
                    "n_above_inactive_outside": 0, "spikes": total_spikes(net)}
    trace, rounds, first = [], 0, None
    while rounds < spec.max_c1_rounds:
        gmax, jsp = traced_round(net, [a, b])
        rounds += 1
        t = run_test(net, a, b, "effective", path)
        tsp = total_spikes(net)
        oth = np.ones(net.G, dtype=bool)
        oth[[a, b, c] + list(path)] = False
        trace.append({"round": rounds, "spikes": jsp, "others_max": float(gmax[oth].max()),
                      "n_others_ge_0.5": int((gmax[oth] >= spec.active).sum()),
                      "path_max": float(gmax[path].max()) if path else 0.0, "test_src_max": t["src_max"],
                      "test_dst_max": t["dst_max"], "test_out": t["n_active_outside"], "test_above_inactive": 0,
                      "test_spikes": tsp, "w_fast_abs_mean": float(((net.counts["EE"] * np.abs(net.wf_ee)).sum() + (net.counts["EI"] * np.abs(net.wf_ei)).sum())
                                               / ((net.nE.sum() + net.nI.sum()) * spec.S))})
        if t["success"]:
            first = t
            break
    cls = "none" if first is None else ("contained" if first["bounded"] else "ignition")
    return {"seed": seed, "pair": pair["name"], "A": a, "B": b, "class": cls, "c1_rounds": rounds,
            "strays": None if first is None else first["n_active_outside"], "trace": trace,
            "seconds": time.perf_counter() - t0, "control0": ctl}


def main(argv=None):
    global GRID
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", default="0")
    ap.add_argument("--pairs", default="0-23")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--grid", type=int, default=9)
    ap.add_argument("--plast", type=float, default=1.0)
    ap.add_argument("--set", nargs="*", default=[])
    a = ap.parse_args(argv)
    GRID = a.grid
    over = parse_set(a.set)
    pairs_all = json.load(open(os.path.join(HERE, "..", "archive-pre-engine-fix", "rate-model", "s73_g9_d4_pairs.json")))
    if "-" in a.pairs and "," not in a.pairs:
        lo, hi = a.pairs.split("-")
        idx = list(range(int(lo), int(hi) + 1))
    else:
        idx = [int(x) for x in a.pairs.split(",")]
    seeds = [int(x) for x in a.seeds.split(",")]
    jobs = [(over, a.plast, s, pairs_all[i], a.grid) for s in seeds for i in idx]
    res, t0 = [], time.time()
    meta = {"overrides": over, "plast": a.plast, "seeds": seeds, "pairs": idx, "grid": a.grid}

    def dump():
        with open(a.out, "w") as f:
            json.dump({"settings": meta, "results": res}, f)

    if a.workers > 1:
        import multiprocessing as mp
        with mp.Pool(a.workers) as pool:
            for r in pool.imap_unordered(_job, jobs, chunksize=1):
                res.append(r)
                print(f"{len(res)}/{len(jobs)} {r['pair']} seed {r['seed']}: {r['class']} rounds {r['c1_rounds']} ({r['seconds']:.0f} s, t={time.time() - t0:.0f})", flush=True)
                dump()
    else:
        for j in jobs:
            r = _job(j)
            res.append(r)
            print(f"{len(res)}/{len(jobs)} {r['pair']} seed {r['seed']}: {r['class']} rounds {r['c1_rounds']} ({r['seconds']:.0f} s)", flush=True)
            dump()
    dump()
    cnt = {c: sum(1 for r in res if r["class"] == c) for c in ("contained", "ignition", "none")}
    print(json.dumps({"counts": cnt, "n": len(res), "elapsed_s": time.time() - t0}))


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    main()
