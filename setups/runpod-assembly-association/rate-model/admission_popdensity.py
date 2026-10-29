"""
admission_popdensity.py

Substeps 2 and 3 of rate-model-task.md for model A (popdensity_model.py), round 4. Same criteria as admission_test.py
(imported: class counting, Clopper-Pearson intervals, kappa, ground truth, pair picking):

  1. class fractions over realizations x 24 pairs at d 4 on 7x7x7 within the 95 % intervals of 7/24, 10/24, 7/24;
  2. 9x9x9, pairs >= 2 cells from the surface: ignition fraction <= 0.142, transfer fraction <= upper bound of 5/24;
  3. uniform C2 (1.2) gives the same associations as activity-dependent C2.
Per-pair kappa is information only.

Free parameters (at most three): sigma_scale (multiplier on the derived input fluctuation) and sigma_floor (mV, an
additional voltage spread of the neurons of a bin); both default to the derived values (1, 0).

Usage (numpy):
  python admission_popdensity.py sanity  --out R.json --realizations 0,1
  python admission_popdensity.py fit     --out R.json --settings 1:0,2:0,1:3 --prescreen 0 [--workers N]
  python admission_popdensity.py eval    --out R.json --sigma-scale S --sigma-floor F --realizations 5,6,7,8,9
  python admission_popdensity.py grid    --out R.json --sigma-scale S --sigma-floor F
  python admission_popdensity.py uniform --out R.json --sigma-scale S --sigma-floor F
"""

from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import os
import sys
import time
from typing import Dict, List, Tuple

import numpy as np

import admission_test as at
from admission_test import (CLASSES, REFERENCE_COUNTS, clopper_pearson, cohens_kappa, count_classes, fractions,
                            load_ground_truth, reference_fractions, seed_pairs)
from popdensity_model import PopNetwork, PopSpec
from rate_model import pick_pairs, run_pair_protocol

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION = os.path.join(os.path.dirname(HERE), "params", "session69a-stage2.json")
WORKERS = 1


PLAST = 1.0      # FREE PARAMETER 3 (plast_scale): multiplier on the three plasticity amplitudes a_pre, a_plus, a_minus


def make_spec(sigma_scale: float = 1.0, sigma_floor: float = 0.0, plast_scale: float = None, **over) -> PopSpec:
    ps = PLAST if plast_scale is None else plast_scale
    base = PopSpec.from_session(SESSION)
    return PopSpec.from_session(SESSION, sigma_scale=sigma_scale, sigma_floor=sigma_floor,
                                a_pre=base.a_pre * ps, a_plus=base.a_plus * ps, a_minus=base.a_minus * ps, **over)


def simulate(spec: PopSpec, pair, seed: int, c2_stage: bool = False, control0: bool = False) -> dict:
    t0 = time.time()
    net = PopNetwork(spec, seed=seed)
    r = run_pair_protocol(net, pair[0], pair[1], c2_stage=c2_stage, control0=control0)
    out = {k: r[k] for k in ("class", "c1_rounds", "strays") if k in r}
    if c2_stage:
        out["association"] = r.get("association")
    if control0:
        out["control0_transfer"] = bool(r["control0"]["A_to_B"]["success"] or r["control0"]["B_to_A"]["success"])
    out["seconds"] = time.time() - t0
    out["group_steps"] = net.n_steps_simulated
    return out


def _job(args):
    tag, spec, pair, seed, c2_stage, i = args
    r = simulate(spec, pair, seed, c2_stage=c2_stage)
    r.update(tag=tag, seed=seed, pair_index=i, A=pair[0], B=pair[1])
    return r


def run_jobs(jobs: List[tuple], log=print) -> List[dict]:
    t0 = time.time()
    if WORKERS > 1:
        out = []
        with mp.Pool(WORKERS) as pool:
            for k, r in enumerate(pool.imap_unordered(_job, jobs, chunksize=1)):
                out.append(r)
                if (k + 1) % max(1, len(jobs) // 10) == 0:
                    log(f"  {k + 1}/{len(jobs)} simulations ({time.time() - t0:.0f} s)")
    else:
        out = [_job(j) for j in jobs]
    return out


def _dump(path, obj):
    if path:
        with open(path, "w") as f:
            json.dump(obj, f, indent=1)


def timing(res: List[dict]) -> dict:
    return {"mean_seconds_per_simulation": float(np.mean([r["seconds"] for r in res])),
            "mean_group_steps": float(np.mean([r["group_steps"] for r in res])), "n": len(res)}


# ------------------------------------------------------------------------------------------------ fit
def fit(settings, seeds, out_path, log=print) -> dict:
    keys, pairs = seed_pairs(0)
    ref = reference_fractions(keys)
    jobs = []
    settings = [tuple(x) + (1.0,) * (3 - len(x)) for x in settings]
    for si, (ss, sf, ps) in enumerate(settings):
        spec = make_spec(ss, sf, ps)
        jobs += [((ss, sf, ps), spec, pr, seed, False, i) for seed in seeds for i, pr in enumerate(pairs)]
    res = run_jobs(jobs, log)
    rows = []
    for ss, sf, ps in settings:
        sub = [r for r in res if r["tag"] == (ss, sf, ps)]
        fr = fractions(sub)
        rows.append({"sigma_scale": ss, "sigma_floor": sf, "plast_scale": ps, "seeds": seeds, "counts": count_classes(sub), "fractions": fr,
                     "l1": sum(abs(fr[c] - ref[c]) for c in CLASSES), "timing": timing(sub)})
        log(f"  setting sigma_scale {ss} sigma_floor {sf} plast_scale {ps}: {rows[-1]['counts']} L1 {rows[-1]['l1']:.3f}")
    out = {"reference_seed0": ref, "rows": rows, "best": min(rows, key=lambda r: r["l1"])}
    _dump(out_path, out)
    return out


# ------------------------------------------------------------------------------------------------ eval
def evaluate(ss, sf, realizations, out_path, log=print) -> dict:
    keys, pairs = seed_pairs(None)
    spec = make_spec(ss, sf)
    res = run_jobs([("e", spec, pr, seed, False, i) for seed in realizations for i, pr in enumerate(pairs)], log)
    counts, fr = count_classes(res), fractions(res)
    intervals = {c: clopper_pearson(REFERENCE_COUNTS[c], 24) for c in CLASSES}
    passed = {c: intervals[c][0] <= fr[c] <= intervals[c][1] for c in CLASSES}
    gt = load_ground_truth()
    conf = [[0] * 3 for _ in range(3)]
    for i, k in enumerate(keys):
        preds = [r["class"] for r in res if r["pair_index"] == i]
        modal = max(CLASSES, key=lambda c: (preds.count(c), -CLASSES.index(c)))
        conf[CLASSES.index(gt[k]["ground_truth"])][CLASSES.index(modal)] += 1
    conf_all = [[0] * 3 for _ in range(3)]
    for r in res:
        conf_all[CLASSES.index(gt[keys[r["pair_index"]]]["ground_truth"])][CLASSES.index(r["class"])] += 1
    out = {"settings": {"sigma_scale": ss, "sigma_floor": sf, "plast_scale": PLAST, "realizations": realizations}, "n_simulations": len(res),
           "counts": counts, "fractions": fr, "reference_counts": REFERENCE_COUNTS,
           "reference_intervals_95_clopper_pearson": intervals, "within_interval": passed, "pass": all(passed.values()),
           "kappa_modal_class_per_pair": cohens_kappa(conf), "confusion_modal": conf,
           "kappa_all_simulations": cohens_kappa(conf_all), "confusion_all": conf_all,
           "mean_c1_rounds": float(np.mean([r["c1_rounds"] for r in res])),
           "mean_strays_of_transfers": float(np.mean([r["strays"] for r in res if r.get("strays") is not None] or [0])),
           "timing": timing(res), "results": res}
    _dump(out_path, out)
    return out


# ------------------------------------------------------------------------------------------------ 9^3
def grid_check(ss, sf, realizations, n_pairs, out_path, log=print) -> dict:
    spec9 = make_spec(ss, sf, grid_dim=9, max_active_frac=34 / 729)
    pairs = pick_pairs(spec9, n_pairs, margin=2, seed=0)
    res = run_jobs([("g", spec9, pr, seed, False, i) for seed in realizations for i, pr in enumerate(pairs)], log)
    counts, fr = count_classes(res), fractions(res)
    n = len(res)
    transfer = (counts["contained"] + counts["ignition"]) / n
    ign = counts["ignition"] / n
    ib, tb = clopper_pearson(0, 24)[1], clopper_pearson(5, 24)[1]
    out = {"settings": {"sigma_scale": ss, "sigma_floor": sf, "plast_scale": PLAST, "realizations": realizations, "n_pairs": n_pairs, "margin": 2},
           "n_simulations": n, "counts": counts, "fractions": fr, "transfer_fraction": transfer, "ignition_fraction": ign,
           "ignition_upper_bound_0_of_24": ib, "transfer_upper_bound_5_of_24": tb, "pass": ign <= ib and transfer <= tb,
           "timing": timing(res)}
    _dump(out_path, out)
    return out


# ------------------------------------------------------------------------------------------------ uniform C2
def uniform_check(ss, sf, realizations, out_path, uniform=1.2, log=print) -> dict:
    keys, pairs = seed_pairs(None)
    base, uni = make_spec(ss, sf), make_spec(ss, sf, c2_uniform=uniform)
    jobs = [("a", base, pr, seed, True, i) for seed in realizations for i, pr in enumerate(pairs)]
    jobs += [("u", uni, pr, seed, True, i) for seed in realizations for i, pr in enumerate(pairs)]
    res = run_jobs(jobs, log)
    key = lambda r: (r["seed"], r["pair_index"])
    a = sorted([r for r in res if r["tag"] == "a"], key=key)
    b = sorted([r for r in res if r["tag"] == "u"], key=key)
    xa = np.array([1.0 if r.get("association") else 0.0 for r in a])
    xb = np.array([1.0 if r.get("association") else 0.0 for r in b])
    diff = xb - xa
    n = len(diff)
    se = diff.std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")
    lo, hi = diff.mean() - 1.96 * se, diff.mean() + 1.96 * se
    out = {"settings": {"sigma_scale": ss, "sigma_floor": sf, "plast_scale": PLAST, "realizations": realizations, "uniform": uniform},
           "n_simulations": n, "associations_activity_dependent": int(xa.sum()), "associations_uniform": int(xb.sum()),
           "fraction_activity_dependent": float(xa.mean()), "fraction_uniform": float(xb.mean()),
           "paired_difference": float(diff.mean()), "paired_ci95": [float(lo), float(hi)],
           "discordant_pairs": int((diff != 0).sum()),
           "class_counts_activity_dependent": count_classes(a),
           "pass": bool((lo <= 0.0 <= hi or float(diff.std()) == 0.0) and abs(diff.mean()) <= 0.10),
           "timing": timing(res)}
    _dump(out_path, out)
    return out


# ------------------------------------------------------------------------------------------------ sanity
def sanity(ss, sf, realizations, out_path, n_groups=5, log=print) -> dict:
    spec = make_spec(ss, sf)
    keys, pairs = seed_pairs(None)
    rows = []
    for seed in realizations:
        net = PopNetwork(spec, seed=seed)
        rng = np.random.default_rng(1000 + seed)
        net.reset_dynamics()
        for _ in range(300):
            net.step(chem=False)
        quiet_spikes = float(net.spk_E_total.sum() + net.spk_I_total.sum())
        act = []
        for g in rng.choice(spec.G, size=n_groups, replace=False):
            net.reset_dynamics()
            inj = net.injection([int(g)])
            gmax = np.zeros(spec.G)
            for i in range(spec.inject_steps + spec.gap_steps):
                net.step(inj=inj if i < spec.inject_steps else None, chem=False)
                np.maximum(gmax, net.activity(), out=gmax)
            others = np.delete(gmax, g)
            act.append({"group": int(g), "A_max": float(gmax[g]), "A_end": float(net.Ag[g]), "others_max": float(others.max()),
                        "pass": bool(gmax[g] >= spec.active and others.max() <= spec.inactive)})
        spread = []
        for (a, b, c) in pairs:
            net.reset_all()
            seen01, seen05 = set(), set()
            for rnd in range(3):                                   # joint injection, rounds with learning
                net.reset_dynamics()
                inj = net.injection([a, b])
                for i in range(spec.inject_steps + spec.gap_steps):
                    net.step(inj=inj if i < spec.inject_steps else None, learn=True, release1=True)
                    m = net.activity()
                    m[[a, b]] = 0.0
                    seen01.update(np.nonzero(m >= 0.1)[0].tolist())
                    seen05.update(np.nonzero(m >= 0.5)[0].tolist())
            spread.append({"groups_ge_0.1": len(seen01), "groups_ge_0.5": len(seen05)})
        rows.append({"seed": seed, "quiet_spikes_300_steps": quiet_spikes, "activation": act,
                     "n_activation_pass": sum(x["pass"] for x in act),
                     "joint_spread_3_rounds": spread,
                     "pairs_with_spread_ge_0.5": sum(1 for x in spread if x["groups_ge_0.5"] > 0),
                     "pairs_with_spread_ge_0.1": sum(1 for x in spread if x["groups_ge_0.1"] > 0)})
        log(f"  sanity realization {seed}: activation {rows[-1]['n_activation_pass']}/{n_groups}, quiet spikes {quiet_spikes}, "
            f"pairs with spread >=0.5: {rows[-1]['pairs_with_spread_ge_0.5']}/24, >=0.1: {rows[-1]['pairs_with_spread_ge_0.1']}/24")
    out = {"settings": {"sigma_scale": ss, "sigma_floor": sf, "plast_scale": PLAST}, "rows": rows}
    _dump(out_path, out)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["fit", "eval", "grid", "uniform", "sanity"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--sigma-scale", type=float, default=1.0)
    ap.add_argument("--sigma-floor", type=float, default=0.0)
    ap.add_argument("--plast-scale", type=float, default=1.0)
    ap.add_argument("--settings", default="1:0", help="fit: comma list of sigma_scale:sigma_floor")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--prescreen", default="0")
    ap.add_argument("--realizations", default="5,6,7,8,9")
    ap.add_argument("--n-pairs", type=int, default=24)
    a = ap.parse_args(argv)
    global WORKERS, PLAST
    WORKERS = a.workers
    PLAST = a.plast_scale
    ints = lambda s: [int(x) for x in s.split(",")]
    if a.mode == "fit":
        st = [tuple(float(y) for y in x.split(":")) for x in a.settings.split(",")]  # sigma_scale:sigma_floor[:plast_scale]
        fit(st, ints(a.prescreen), a.out)
    elif a.mode == "eval":
        r = evaluate(a.sigma_scale, a.sigma_floor, ints(a.realizations), a.out)
        print(json.dumps({k: r[k] for k in ("counts", "fractions", "within_interval", "pass", "kappa_modal_class_per_pair", "timing")}))
    elif a.mode == "sanity":
        sanity(a.sigma_scale, a.sigma_floor, ints(a.realizations), a.out)
    elif a.mode == "grid":
        print(json.dumps(grid_check(a.sigma_scale, a.sigma_floor, ints(a.realizations), a.n_pairs, a.out)))
    elif a.mode == "uniform":
        print(json.dumps(uniform_check(a.sigma_scale, a.sigma_floor, ints(a.realizations), a.out)))


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    main()
