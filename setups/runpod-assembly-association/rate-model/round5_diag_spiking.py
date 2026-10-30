"""
round5_diag_spiking.py

Round 5, model B: runs the C1 stage of the protocol on 9 x 9 x 9 (or another grid) for the 24 pair positions of
the spiking s73 d 4 runs (../archive-pre-engine-fix/rate-model/s73_g9_d4_pairs.json; group indices x * dim^2 + y * dim + z as in the engine) and records the
per-round quantities that the spiking job JSONs hold, so that the two can be compared round by round:
training-round spikes, others_max / path_max of the training round, and for the A-alone test after each round
the groups active outside A, B and the route, B's maximum, the spikes and the mean |w_fast|.

  python round5_diag_spiking.py --out RESULT.json [--seeds 0,1,2] [--pairs 0-23] [--workers 4]
         [--set key=value ...]            spec overrides (SpikeSpec fields), e.g. syn_scale=0.25 ei_inter_scale=0.7
Results are written to --out after every finished job (so a partial run is usable).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

from admission_test import SESSION
from spiking_group_model import SpikeSpec, SpikingNetwork, run_pair_protocol

HERE = os.path.dirname(os.path.abspath(__file__))
GRID = 9
G9 = dict(grid_dim=9, neurons_per_group=42500 / 729.0, max_active_frac=34 / 729.0, n_delays=16)


def make_spec(over: dict, grid: int = 9) -> SpikeSpec:
    kw = dict(G9) if grid == 9 else {}
    kw.update(over)
    return SpikeSpec.from_session(SESSION, **kw)


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


def _job(args):
    over, seed, pair, c2_stage = args
    spec = make_spec(over)
    t0 = time.perf_counter()
    net = SpikingNetwork(spec, seed=seed)
    tb = time.perf_counter() - t0
    trace = []
    r = run_pair_protocol(net, pair["A"], pair["B"], c2_stage=c2_stage, control0=True, trace=trace, c=pair["C"])
    out = {"seed": seed, "pair": pair["name"], "A": pair["A"], "B": pair["B"], "class": r["class"], "c1_rounds": r["c1_rounds"],
           "strays": r["strays"], "runaway_round": r.get("runaway_round"), "trace": trace, "seconds": r["seconds"],
           "build_seconds": tb, "steps": r["steps"],
           "control0": {k: {kk: v[kk] for kk in ("src_max", "dst_max", "n_active_outside", "n_above_inactive_outside", "spikes")}
                        for k, v in r["control0"].items()}}
    if c2_stage:
        out["association"] = r.get("association")
    return out


def _calib_job(args):
    """Single injected group (k neurons, inject_current for inject_steps), 100-step test, plasticity off."""
    over, seed, groups = args
    spec = make_spec(over, grid=GRID)
    t0 = time.perf_counter()
    net = SpikingNetwork(spec, seed=seed)
    tb = time.perf_counter() - t0
    rows = []
    for g in groups:
        net.reset_dynamics()
        inj = net.inject_idx(int(g))
        n_tot = n_in_e = n_in_i = n_out_e = n_out_i = 0
        gmax = np.zeros(net.G)
        for i in range(spec.test_window):
            A, nf = net.step(spec.window, False, False, 1.0, False, False, False, inj if i < spec.inject_steps else None)
            f = net.recent[0]
            n_tot += len(f)
            own = net.grp[f] == g
            e = net.isE[f]
            n_in_e += int((own & e).sum()); n_in_i += int((own & ~e).sum())
            n_out_e += int((~own & e).sum()); n_out_i += int((~own & ~e).sum())
            np.maximum(gmax, A, out=gmax)
        others = np.delete(gmax, g)
        rows.append({"seed": seed, "group": int(g), "spikes": n_tot, "A_max": float(gmax[g]), "others_max": float(others.max()),
                     "n_ge_0.1": int((others > 0.1).sum()), "n_ge_0.5": int((others >= 0.5).sum()),
                     "e_in": n_in_e, "i_in": n_in_i, "e_out": n_out_e, "i_out": n_out_i})
    return {"seed": seed, "build_seconds": tb, "rows": rows}


def calib_main(a, over):
    pairs_all = json.load(open(os.path.join(HERE, "..", "archive-pre-engine-fix", "rate-model", "s73_g9_d4_pairs.json")))
    if GRID == 9:
        groups = sorted({p["A"] for p in pairs_all} | {p["B"] for p in pairs_all})
    else:
        groups = [int(x) for x in np.random.default_rng(5).choice(GRID ** 3, 48, replace=False)]
    seeds = [int(x) for x in a.seeds.split(",")]
    jobs = [(over, s, groups) for s in seeds]
    t0 = time.time()
    if a.workers > 1:
        import multiprocessing as mp
        with mp.Pool(a.workers) as pool:
            out = pool.map(_calib_job, jobs, chunksize=1)
    else:
        out = [_calib_job(j) for j in jobs]
    rows = [r for o in out for r in o["rows"]]
    q = lambda k: np.percentile([r[k] for r in rows], [10, 50, 90]).tolist()
    summ = {k: q(k) for k in ("spikes", "e_in", "i_in", "e_out", "i_out", "others_max", "n_ge_0.1", "n_ge_0.5", "A_max")}
    with open(a.out, "w") as f:
        json.dump({"settings": {"overrides": over, "grid": G9, "seeds": seeds, "n_groups": len(groups)}, "summary_q10_50_90": summ,
                   "build_seconds": [o["build_seconds"] for o in out], "rows": rows, "elapsed_s": time.time() - t0}, f)
    print(json.dumps({"overrides": over, "summary_q10_50_90": summ, "elapsed_s": time.time() - t0}), flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", default="0")
    ap.add_argument("--pairs", default="0-23")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--c2", action="store_true")
    ap.add_argument("--grid", type=int, default=9)
    ap.add_argument("--calib", action="store_true", help="single-group response instead of the protocol")
    ap.add_argument("--set", nargs="*", default=[])
    a = ap.parse_args(argv)
    over = parse_set(a.set)
    global GRID
    GRID = a.grid
    if a.calib:
        return calib_main(a, over)
    pairs_all = json.load(open(os.path.join(HERE, "..", "archive-pre-engine-fix", "rate-model", "s73_g9_d4_pairs.json")))
    if "-" in a.pairs and "," not in a.pairs:
        lo, hi = a.pairs.split("-")
        idx = list(range(int(lo), int(hi) + 1))
    else:
        idx = [int(x) for x in a.pairs.split(",")]
    seeds = [int(x) for x in a.seeds.split(",")]
    jobs = [(over, s, pairs_all[i], a.c2) for s in seeds for i in idx]
    res = []
    t0 = time.time()
    meta = {"overrides": over, "grid": G9, "seeds": seeds, "pairs": idx, "c2_stage": a.c2}

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
