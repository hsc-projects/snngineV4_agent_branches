"""
admission_spiking_group.py

Substeps 2 and 3 of rate-model-task.md for model B (reduced spiking network, spiking_group_model.py). The
criteria are those of admission_test.py (imported, not changed): class fractions of the first transfer in the
joint rounds against the 95 % Clopper-Pearson intervals of the spiking 7 / 10 / 7 of 24; 9 x 9 x 9 check;
uniform-C2 check; per-pair kappa as information.

Modes (numpy; results to --out as JSON, numbers are copied into round4-spiking-report.md):
  calib   single-group activation against the spiking runs (spikes, A_max, spill, inhibitory spikes outside)
  sanity  Substep 2: activation, quiet network, spread under joint injection
  fit     class fractions on the 12 seed-0 positions x realizations 0..4 for lists of the free parameters
  eval    24 positions x realizations 5..9 on 7^3 (class fractions, kappa)
  grid    9^3, pairs >= 2 cells from the surface
  uniform activity-dependent against uniform C2 (C2 stage on)
Every job is one (realization, pair); jobs run in a multiprocessing pool (--workers).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from typing import Dict, List, Tuple

import numpy as np

from admission_test import (CLASSES, REFERENCE_COUNTS, SESSION, clopper_pearson, cohens_kappa, load_ground_truth,
                            reference_fractions, seed_pairs, _dump)
from rate_model import pick_pairs
from spiking_group_model import SpikeSpec, SpikingNetwork, run_pair_protocol, run_round

OVER: dict = {}          # spec overrides from the command line
WORKERS = 1


def make_spec(**over) -> SpikeSpec:
    kw = dict(OVER)
    kw.update(over)
    return SpikeSpec.from_session(SESSION, **kw)


def _job(args):
    spec, pr, seed, c2_stage, i = args
    t0 = time.perf_counter()
    net = SpikingNetwork(spec, seed=seed)
    tb = time.perf_counter() - t0
    r = run_pair_protocol(net, pr[0], pr[1], c2_stage=c2_stage, control0=False)
    out = {k: r[k] for k in ("class", "c1_rounds", "strays", "steps", "seconds") if k in r}
    if c2_stage:
        out["association"] = r.get("association")
    out.update(seed=seed, pair_index=i, A=pr[0], B=pr[1], build_seconds=tb, runaway_round=r.get("runaway_round"))
    return out


def run_set(spec, pairs, seeds, c2_stage=False, label="", log=print) -> List[dict]:
    t0 = time.time()
    jobs = [(spec, pr, seed, c2_stage, i) for seed in seeds for i, pr in enumerate(pairs)]
    if WORKERS > 1:
        import multiprocessing as mp
        with mp.Pool(WORKERS) as pool:
            out = pool.map(_job, jobs, chunksize=1)
    else:
        out = [_job(j) for j in jobs]
    for seed in seeds:
        sub = [x for x in out if x["seed"] == seed]
        log(f"  {label} realization {seed}: {count_classes(sub)}  ({time.time() - t0:.0f} s)")
    return out


def count_classes(results):
    return {c: sum(1 for r in results if r["class"] == c) for c in CLASSES}


def fractions(results):
    n = max(1, len(results))
    return {c: v / n for c, v in count_classes(results).items()}


def timing(results) -> dict:
    sec = [r["seconds"] + r["build_seconds"] for r in results]
    steps = [r["steps"] for r in results]
    return {"mean_seconds_per_simulation": float(np.mean(sec)), "max_seconds": float(np.max(sec)),
            "mean_steps": float(np.mean(steps)), "seconds_per_step": float(np.sum(sec) / max(1, np.sum(steps)))}


def evaluate(realizations, out_path, log=print) -> dict:
    keys, pairs = seed_pairs(None)
    spec = make_spec()
    res = run_set(spec, pairs, realizations, label="eval 7^3", log=log)
    counts, fr = count_classes(res), fractions(res)
    intervals = {c: clopper_pearson(REFERENCE_COUNTS[c], 24) for c in CLASSES}
    passed = {c: intervals[c][0] <= fr[c] <= intervals[c][1] for c in CLASSES}
    gt = load_ground_truth()
    conf = [[0] * 3 for _ in range(3)]
    conf_all = [[0] * 3 for _ in range(3)]
    per_pair = {}
    for i, k in enumerate(keys):
        preds = [r["class"] for r in res if r["pair_index"] == i]
        modal = max(CLASSES, key=lambda c: (preds.count(c), -CLASSES.index(c)))
        conf[CLASSES.index(gt[k]["ground_truth"])][CLASSES.index(modal)] += 1
        per_pair[k] = {"ground_truth": gt[k]["ground_truth"], "predicted": preds}
    for r in res:
        conf_all[CLASSES.index(gt[keys[r["pair_index"]]]["ground_truth"])][CLASSES.index(r["class"])] += 1
    out = {"settings": _settings(realizations), "n_simulations": len(res), "counts": counts, "fractions": fr,
           "reference_counts": REFERENCE_COUNTS, "reference_intervals_95_clopper_pearson": intervals,
           "within_interval": passed, "pass": all(passed.values()),
           "kappa_modal_class_per_pair": cohens_kappa(conf), "confusion_modal": conf,
           "kappa_all_simulations": cohens_kappa(conf_all), "confusion_all": conf_all, "per_pair": per_pair,
           "mean_c1_rounds": float(np.mean([r["c1_rounds"] for r in res])), "timing": timing(res),
           "runaway_rounds": int(sum(1 for r in res if r.get("runaway_round"))), "results": res}
    _dump(out_path, out)
    return out


def _settings(realizations=None, **extra):
    s = dict(OVER)
    if realizations is not None:
        s["realizations"] = realizations
    s.update(extra)
    return s


def fit(realizations, ei_list, w_list, learn_list, out_path, log=print) -> dict:
    keys, pairs = seed_pairs(0)
    ref = reference_fractions(keys)
    log(f"fit on {len(pairs)} seed-0 positions, reference {ref}")
    rows = []
    for ei in ei_list:
        for wi in w_list:
            for ls in learn_list:
                spec = make_spec(ei_inter_scale=ei, w_inter_scale=wi, learn_scale=ls)
                res = run_set(spec, pairs, realizations, label=f"ei {ei} w {wi} learn {ls}", log=log)
                fr = fractions(res)
                rows.append({"ei_inter_scale": ei, "w_inter_scale": wi, "learn_scale": ls, "counts": count_classes(res),
                             "fractions": fr, "l1": sum(abs(fr[c] - ref[c]) for c in CLASSES), "timing": timing(res),
                             "realizations": realizations})
                log(f"  -> {fr}  L1 {rows[-1]['l1']:.3f}")
                _dump(out_path, {"reference_seed0": ref, "rows": rows})
    best = min(rows, key=lambda r: r["l1"])
    out = {"reference_seed0": ref, "rows": rows, "best": best}
    _dump(out_path, out)
    return out


def grid_check(realizations, n_pairs, out_path, log=print) -> dict:
    spec9 = make_spec(grid_dim=9, max_active_frac=34 / 729)
    pairs = pick_pairs(spec9, n_pairs, margin=2, seed=0)
    res = run_set(spec9, pairs, realizations, label="9^3", log=log)
    counts, fr = count_classes(res), fractions(res)
    n = len(res)
    transfer = (counts["contained"] + counts["ignition"]) / n
    ign = counts["ignition"] / n
    ib, tb = clopper_pearson(0, 24)[1], clopper_pearson(5, 24)[1]
    out = {"settings": _settings(realizations, n_pairs=n_pairs, margin=2), "n_simulations": n, "counts": counts,
           "fractions": fr, "transfer_fraction": transfer, "ignition_fraction": ign,
           "ignition_upper_bound_0_of_24": ib, "transfer_upper_bound_5_of_24": tb,
           "pass": ign <= ib and transfer <= tb, "timing": timing(res), "results": res}
    _dump(out_path, out)
    return out


def uniform_check(realizations, out_path, uniform=1.2, log=print) -> dict:
    keys, pairs = seed_pairs(None)
    a = run_set(make_spec(), pairs, realizations, c2_stage=True, label="activity-dependent C2", log=log)
    b = run_set(make_spec(c2_uniform=uniform), pairs, realizations, c2_stage=True, label=f"uniform C2 {uniform}", log=log)
    xa = np.array([1.0 if r.get("association") else 0.0 for r in a])
    xb = np.array([1.0 if r.get("association") else 0.0 for r in b])
    diff = xb - xa
    n = len(diff)
    se = diff.std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")
    lo, hi = diff.mean() - 1.96 * se, diff.mean() + 1.96 * se
    out = {"settings": _settings(realizations, uniform=uniform), "n_simulations": n,
           "transfers_activity_dependent": count_classes(a), "associations_activity_dependent": int(xa.sum()),
           "associations_uniform": int(xb.sum()), "fraction_activity_dependent": float(xa.mean()),
           "fraction_uniform": float(xb.mean()), "paired_difference": float(diff.mean()),
           "paired_ci95": [float(lo), float(hi)], "discordant": int((diff != 0).sum()),
           "pass": bool((lo <= 0.0 <= hi or float(diff.std()) == 0.0) and abs(diff.mean()) <= 0.10),
           "timing": timing(a + b), "results_a": a, "results_b": b}
    _dump(out_path, out)
    return out


# ---------------------------------------------------------------------------------- single-group checks

def _calib_job(args):
    spec, seed, groups = args
    net = SpikingNetwork(spec, seed=seed)
    rows = []
    for g in groups:
        net.reset_dynamics()
        inj = net.inject_idx(int(g))
        n_tot = n_out_i = n_out_e = 0
        gmax = np.zeros(net.G)
        for i in range(spec.test_window):
            A, nf = net.step(spec.window, False, False, 1.0, False, False, False, inj if i < spec.inject_steps else None)
            f = net.recent[0]
            n_tot += len(f)
            out = net.grp[f] != g
            n_out_i += int((out & ~net.isE[f]).sum())
            n_out_e += int((out & net.isE[f]).sum())
            np.maximum(gmax, A, out=gmax)
        others = np.delete(gmax, g)
        rows.append({"seed": seed, "group": int(g), "A_max": float(gmax[g]), "others_max": float(others.max()),
                     "n_strays_ge_0.5": int((others >= 0.5).sum()), "spikes_full_scale": n_tot / spec.neuron_scale,
                     "inh_spikes_outside_full_scale": n_out_i / spec.neuron_scale,
                     "exc_spikes_outside_full_scale": n_out_e / spec.neuron_scale})
    return rows


def calib(realizations, n_groups, out_path, log=print) -> dict:
    spec = make_spec()
    rng = np.random.default_rng(123)
    jobs = [(spec, s, rng.choice(spec.G, n_groups, replace=False)) for s in realizations]
    if WORKERS > 1:
        import multiprocessing as mp
        with mp.Pool(WORKERS) as pool:
            rows = sum(pool.map(_calib_job, jobs, chunksize=1), [])
    else:
        rows = sum([_calib_job(j) for j in jobs], [])
    a = np.array([r["A_max"] for r in rows])
    o = np.array([r["others_max"] for r in rows])
    sp = np.array([r["spikes_full_scale"] for r in rows])
    iso = (a >= 0.9) & (o <= 0.1)
    out = {"settings": _settings(realizations, n_groups=n_groups), "n_tests": len(rows),
           "fraction_A_max_ge_0.9": float((a >= 0.9).mean()), "fraction_spill_others_ge_0.5": float((o >= 0.5).mean()),
           "fraction_isolated": float(iso.mean()),
           "isolated_spikes_quantiles_0_10_25_50_75_90_100": np.percentile(sp[iso], [0, 10, 25, 50, 75, 90, 100]).tolist() if iso.any() else None,
           "median_inh_spikes_outside": float(np.median([r["inh_spikes_outside_full_scale"] for r in rows])),
           "median_exc_spikes_outside": float(np.median([r["exc_spikes_outside_full_scale"] for r in rows])),
           "spiking_reference": {"isolated_spikes_median": 431, "isolated_q10_q90": [260, 620],
                                 "spill_fraction": 9 / 48, "A_max_ge_0.9_fraction": 1.0,
                                 "median_inh_spikes_outside_s57": 212, "median_total_s57": 438},
           "rows": rows}
    log(json.dumps({k: v for k, v in out.items() if k not in ("rows", "settings")}))
    _dump(out_path, out)
    return out


def _sanity_job(args):
    spec, seed, pair, n_rounds = args
    net = SpikingNetwork(spec, seed=seed)
    net.reset_all()
    a, b, _ = pair
    seen01, seen05 = set(), set()
    for _ in range(n_rounds):
        net.reset_dynamics()
        inj = [net.inject_idx(a), net.inject_idx(b)]
        for i in range(spec.inject_steps + spec.gap_steps):
            A, nf = net.step(spec.window, True, False, 1.0, True, False, True,
                             np.concatenate(inj) if i < spec.inject_steps else None)
            m = A.copy()
            m[[a, b]] = 0.0
            seen01.update(np.nonzero(m >= 0.1)[0].tolist())
            seen05.update(np.nonzero(m >= 0.5)[0].tolist())
    return {"seed": seed, "pair": [a, b], "groups_ge_0.1": len(seen01), "groups_ge_0.5": len(seen05)}


def sanity(realizations, n_groups, n_rounds, out_path, log=print) -> dict:
    spec = make_spec()
    keys, pairs = seed_pairs(None)
    cal = calib(realizations, n_groups, None, log=log)
    quiet = []
    for s in realizations:
        net = SpikingNetwork(spec, seed=s)
        net.reset_dynamics()
        quiet.append({"seed": s, "spikes_in_300_quiet_steps": net.run(300, chem=False)["spikes"]})
    jobs = [(spec, s, pr, n_rounds) for s in realizations for pr in pairs]
    if WORKERS > 1:
        import multiprocessing as mp
        with mp.Pool(WORKERS) as pool:
            spread = pool.map(_sanity_job, jobs, chunksize=1)
    else:
        spread = [_sanity_job(j) for j in jobs]
    per_seed = {}
    for s in realizations:
        sub = [x for x in spread if x["seed"] == s]
        per_seed[s] = {"pairs_with_spread_ge_0.1": sum(1 for x in sub if x["groups_ge_0.1"] > 0),
                       "pairs_with_spread_ge_0.5": sum(1 for x in sub if x["groups_ge_0.5"] > 0), "n_pairs": len(sub)}
    out = {"settings": _settings(realizations, n_groups=n_groups, joint_rounds=n_rounds), "activation": {
        k: cal[k] for k in ("fraction_A_max_ge_0.9", "fraction_isolated", "fraction_spill_others_ge_0.5")},
           "quiet": quiet, "joint_spread_per_realization": per_seed, "joint_spread_rows": spread}
    log(json.dumps({k: out[k] for k in ("activation", "quiet", "joint_spread_per_realization")}))
    _dump(out_path, out)
    return out


def _ints(s):
    return [int(x) for x in s.split(",")]


def _floats(s):
    return [float(x) for x in s.split(",")]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["calib", "sanity", "fit", "eval", "grid", "uniform"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--neuron-scale", type=float, default=None)
    ap.add_argument("--syn-scale", type=float, default=None)
    ap.add_argument("--ei-inter", type=float, default=None)
    ap.add_argument("--w-inter", type=float, default=None)
    ap.add_argument("--learn", type=float, default=None)
    ap.add_argument("--w-inh", type=float, default=None)
    ap.add_argument("--realizations", default="5,6,7,8,9")
    ap.add_argument("--n-pairs", type=int, default=24)
    ap.add_argument("--n-groups", type=int, default=8)
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--ei-list", default="1.0")
    ap.add_argument("--w-list", default="1.0")
    ap.add_argument("--learn-list", default="1.0")
    a = ap.parse_args(argv)
    global WORKERS
    WORKERS = a.workers
    for key, val in (("neuron_scale", a.neuron_scale), ("syn_scale", a.syn_scale), ("ei_inter_scale", a.ei_inter),
                     ("w_inter_scale", a.w_inter), ("learn_scale", a.learn), ("w_inh_scale", a.w_inh)):
        if val is not None:
            OVER[key] = val
    r = _ints(a.realizations)
    if a.mode == "calib":
        calib(r, a.n_groups, a.out)
    elif a.mode == "sanity":
        sanity(r, a.n_groups, a.rounds, a.out)
    elif a.mode == "fit":
        fit(r, _floats(a.ei_list), _floats(a.w_list), _floats(a.learn_list), a.out)
    elif a.mode == "eval":
        o = evaluate(r, a.out)
        print(json.dumps({k: o[k] for k in ("counts", "fractions", "within_interval", "pass", "kappa_modal_class_per_pair", "timing")}))
    elif a.mode == "grid":
        o = grid_check(r, a.n_pairs, a.out)
        print(json.dumps({k: v for k, v in o.items() if k != "results"}))
    elif a.mode == "uniform":
        o = uniform_check(r, a.out)
        print(json.dumps({k: v for k, v in o.items() if not k.startswith("results")}))


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    main()
