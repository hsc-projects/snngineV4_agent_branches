"""
admission_test.py

Substep 3 of rate-model-task.md (round 2): admission test of the rate model against the spiking runs
(s71 E0, d 4, 24 pairs; ../archive-pre-engine-fix/rate-model/s71_ground_truth.json).

Each pair is classified by its first transfer in the joint rounds: contained (A alone activates B with at
most 34 groups active outside A, B and the route), ignition (more), or none. Spiking reference:
7 contained, 10 ignition, 7 none of 24.

Requirements (decided before use):
  1. Class fractions over `--realizations` x 24 pairs at d 4 on 7 x 7 x 7 (fresh realizations 5 to 9): each class's
     fraction lies within the 95 % Clopper-Pearson interval of the spiking fraction (7/24, 10/24, 7/24).
  2. Grid size (iteration 61): on 9 x 9 x 9 with pairs at least 2 cells from the surface, the ignition fraction is at
     most the 95 % upper bound of 0 of 24 (0.142) and the transfer fraction at most the 95 % upper bound of
     5 of 24; (spiking: 17 of 24 transfers on 7^3, 5 on 9^3; 9 and 0 ignitions).
  3. Uniform C2 (iteration 64): holding C2 at 1.2 where released gives the same associations as activity-dependent
     C2: the 95 % interval of the paired difference of association indicators (per pair and realization) contains
     0 and the absolute difference of the association fractions is at most 0.10 (spiking: 6 and 7 of 24).
  Per-pair kappa against the ground truth is reported as information only.

Fit only theta, beta, tau on the 12 pair positions of seed 0 and realizations 0 to 4 (objective: L1 distance of
the predicted class fractions from the seed-0 reference fractions); evaluation on all 24 positions with
fresh realizations (5 to 9).

Usage (numpy, see the .venv in this folder):
  python admission_test.py fit   --out RESULT.json [--taus 1,2,3,5 --thetas ... --betas ... --prescreen 1 --top 3]
  python admission_test.py eval  --theta T --beta B --tau U --out RESULT.json [--realizations 5,6,7,8,9]
  python admission_test.py sanity --theta T --beta B --tau U --out RESULT.json --realizations 0,1
  python admission_test.py grid  --theta T --beta B --tau U --out RESULT.json
  python admission_test.py uniform --theta T --beta B --tau U --out RESULT.json
Results go to --out (outside the repository when possible); numbers are copied into ../archive-pre-engine-fix/rate-model/rate-model-report.md.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import sys
import time
from dataclasses import replace
from typing import Dict, List, Tuple

import numpy as np

from rate_model import RateNetwork, Spec, pick_pairs, run_pair_protocol

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION = os.path.join(os.path.dirname(HERE), "archive-pre-engine-fix", "params", "session69a-stage2.json")
CLASSES = ("contained", "ignition", "none")
REFERENCE_COUNTS = {"contained": 7, "ignition": 10, "none": 7}      # s71 E0, 24 pairs


def load_ground_truth() -> Dict[str, dict]:
    with open(os.path.join(HERE, "..", "archive-pre-engine-fix", "rate-model", "s71_ground_truth.json")) as f:
        return json.load(f)


def cohens_kappa(confusion: List[List[int]]) -> float:
    """Rows: ground truth, columns: prediction, classes in CLASSES order."""
    n = sum(sum(r) for r in confusion)
    if n == 0:
        return 0.0
    p_o = sum(confusion[i][i] for i in range(len(confusion))) / n
    rows = [sum(r) for r in confusion]
    cols = [sum(confusion[i][j] for i in range(len(confusion))) for j in range(len(confusion))]
    p_e = sum(r * c for r, c in zip(rows, cols)) / (n * n)
    return 1.0 if math.isclose(p_e, 1.0) else (p_o - p_e) / (1.0 - p_e)


def _binom_cdf(k: int, n: int, p: float) -> float:
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, k + 1))


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> Tuple[float, float]:
    """Exact two-sided binomial interval (bisection on the binomial CDF)."""
    def solve(f):
        lo, hi = 0.0, 1.0
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if f(mid) else (lo, mid)
        return 0.5 * (lo + hi)
    lower = 0.0 if k == 0 else solve(lambda p: 1.0 - _binom_cdf(k - 1, n, p) < alpha / 2)
    upper = 1.0 if k == n else solve(lambda p: _binom_cdf(k, n, p) > alpha / 2)
    return lower, upper


GLOBAL_OVER: dict = {}      # set from the command line (transfer form, noise_sigma, injection_mode, ...)
WORKERS = 1


def make_spec(theta: float, beta: float, tau: float, **over) -> Spec:
    """theta and beta are used by the round-2 sigmoid forms only; in round 3 the fitted parameters are noise_sigma and tau."""
    kw = dict(GLOBAL_OVER)
    kw.update(over)
    return Spec.from_session(SESSION, theta=theta, beta=beta, tau=tau, **kw)


def _job(args):
    spec, pr, seed, c2_stage, i = args
    r = simulate(spec, pr, seed, c2_stage=c2_stage)
    r.update(seed=seed, pair_index=i, A=pr[0], B=pr[1])
    return r


def simulate(spec: Spec, pair: Tuple[int, int, int], seed: int, c2_stage: bool = False, control0: bool = False) -> dict:
    net = RateNetwork(spec, seed=seed)
    r = run_pair_protocol(net, pair[0], pair[1], c2_stage=c2_stage, control0=control0)
    return {k: r[k] for k in ("class", "c1_rounds", "strays") if k in r} | (
        {"association": r.get("association")} if c2_stage else {}) | (
        {"control0_transfer": bool(r["control0"]["A_to_B"]["success"] or r["control0"]["B_to_A"]["success"])}
        if control0 else {})


def run_set(spec: Spec, pairs: List[Tuple[int, int, int]], seeds: List[int], c2_stage: bool = False,
            label: str = "", log=print) -> List[dict]:
    t0 = time.time()
    jobs = [(spec, pr, seed, c2_stage, i) for seed in seeds for i, pr in enumerate(pairs)]
    if WORKERS > 1:
        import multiprocessing as mp
        with mp.Pool(WORKERS) as pool:
            out = pool.map(_job, jobs, chunksize=1)
    else:
        out = [_job(j) for j in jobs]
    for seed in seeds:
        log(f"  {label} realization {seed}: " + str(count_classes([x for x in out if x['seed'] == seed]))
            + f"  ({time.time() - t0:.0f} s)")
    return out


def count_classes(results: List[dict]) -> Dict[str, int]:
    return {c: sum(1 for r in results if r["class"] == c) for c in CLASSES}


def fractions(results: List[dict]) -> Dict[str, float]:
    n = max(1, len(results))
    return {c: v / n for c, v in count_classes(results).items()}


def reference_fractions(keys: List[str]) -> Dict[str, float]:
    gt = load_ground_truth()
    n = len(keys)
    return {c: sum(1 for k in keys if gt[k]["ground_truth"] == c) / n for c in CLASSES}


def seed_pairs(seed: int | None) -> Tuple[List[str], List[Tuple[int, int, int]]]:
    gt = load_ground_truth()
    keys = [k for k, v in gt.items() if seed is None or v["seed"] == seed]
    return keys, [(gt[k]["A"], gt[k]["B"], gt[k]["C"]) for k in keys]


# ------------------------------------------------------------------------------------------------ fit

def fit(thetas, betas, taus, fit_seeds, prescreen_seeds, top, out_path, log=print, sigmas=(None,)) -> dict:
    keys, pairs = seed_pairs(0)
    ref = reference_fractions(keys)
    log(f"fit on {len(pairs)} pair positions of seed 0, reference fractions {ref}")
    rows = []
    grid = list(itertools.product(taus, thetas, betas, sigmas))
    for n, (tau, th, be, sg) in enumerate(grid):
        spec = make_spec(th, be, tau, **({} if sg is None else {'noise_sigma': sg}))
        res = run_set(spec, pairs, prescreen_seeds, label=f"[{n + 1}/{len(grid)}] tau {tau} theta {th} beta {be} sigma {sg}", log=log)
        fr = fractions(res)
        dist = sum(abs(fr[c] - ref[c]) for c in CLASSES)
        rows.append({"tau": tau, "theta": th, "beta": be, "sigma": sg, "stage": "prescreen", "seeds": prescreen_seeds, "counts": count_classes(res),
                     "fractions": fr, "l1": dist})
        log(f"  -> fractions {fr}  L1 {dist:.3f}")
        _dump(out_path, {"rows": rows})
    finalists = sorted(rows, key=lambda r: r["l1"])[:top]
    final = []
    if set(prescreen_seeds) == set(fit_seeds):          # the screen already used the fit realizations
        best = finalists[0]
        result = {"reference_seed0": ref, "rows": rows, "final": [], "best": best}
        _dump(out_path, result)
        return result
    for f in finalists:
        spec = make_spec(f["theta"], f["beta"], f["tau"], **({} if f.get("sigma") is None else {'noise_sigma': f["sigma"]}))
        res = run_set(spec, pairs, fit_seeds, label=f"finalist tau {f['tau']} theta {f['theta']} beta {f['beta']}", log=log)
        fr = fractions(res)
        dist = sum(abs(fr[c] - ref[c]) for c in CLASSES)
        final.append({"tau": f["tau"], "theta": f["theta"], "beta": f["beta"], "stage": "fit", "seeds": fit_seeds,
                      "counts": count_classes(res), "fractions": fr, "l1": dist})
        log(f"  finalist -> {fr}  L1 {dist:.3f}")
        _dump(out_path, {"rows": rows, "final": final})
    best = min(final, key=lambda r: r["l1"]) if final else None
    result = {"reference_seed0": ref, "rows": rows, "final": final, "best": best}
    _dump(out_path, result)
    return result


# ------------------------------------------------------------------------------------------------ eval

def evaluate(theta, beta, tau, realizations, out_path, log=print, **over) -> dict:
    keys, pairs = seed_pairs(None)
    spec = make_spec(theta, beta, tau, **over)
    res = run_set(spec, pairs, realizations, label="eval 7^3", log=log)
    counts, fr = count_classes(res), fractions(res)
    n = len(res)
    intervals = {c: clopper_pearson(REFERENCE_COUNTS[c], 24) for c in CLASSES}
    passed = {c: intervals[c][0] <= fr[c] <= intervals[c][1] for c in CLASSES}
    # information: per-pair kappa (modal predicted class over realizations vs ground truth)
    gt = load_ground_truth()
    conf = [[0] * 3 for _ in range(3)]
    per_pair = {}
    for i, k in enumerate(keys):
        preds = [r["class"] for r in res if r["pair_index"] == i]
        modal = max(CLASSES, key=lambda c: (preds.count(c), -CLASSES.index(c)))
        conf[CLASSES.index(gt[k]["ground_truth"])][CLASSES.index(modal)] += 1
        per_pair[k] = {"ground_truth": gt[k]["ground_truth"], "predicted": preds}
    kappa_modal = cohens_kappa(conf)
    conf_all = [[0] * 3 for _ in range(3)]
    for r in res:
        conf_all[CLASSES.index(gt[keys[r["pair_index"]]]["ground_truth"])][CLASSES.index(r["class"])] += 1
    out = {"settings": {"theta": theta, "beta": beta, "tau": tau, "realizations": realizations, **over},
           "n_simulations": n, "counts": counts, "fractions": fr,
           "reference_counts": REFERENCE_COUNTS, "reference_intervals_95_clopper_pearson": intervals,
           "within_interval": passed, "pass": all(passed.values()),
           "kappa_modal_class_per_pair": kappa_modal, "confusion_modal": conf,
           "kappa_all_simulations": cohens_kappa(conf_all), "confusion_all": conf_all,
           "per_pair": per_pair,
           "mean_c1_rounds": float(np.mean([r["c1_rounds"] for r in res]))}
    _dump(out_path, out)
    return out


# ------------------------------------------------------------------------------------------------ sanity

def sanity(theta, beta, tau, realizations, out_path, n_groups=5, log=print, **over) -> dict:
    """
    Substep 2 checks: (1) an injected group activates (A_max >= 0.5) while every other group stays <= 0.1, for
    n_groups random groups per realization; (2) ordinary groups stay quiet without injection (300 steps);
    (3) under joint injection of the 24 pairs at d 4 (training rounds, learning on) activity spreads beyond A
    and B: groups other than A and B that reach r >= 0.1 / >= 0.5 in some round, per realization.
    """
    spec = make_spec(theta, beta, tau, **over)
    keys, pairs = seed_pairs(None)
    rows = []
    for seed in realizations:
        net = RateNetwork(spec, seed=seed)
        rng = np.random.default_rng(1000 + seed)
        quiet = RateNetwork(spec, seed=seed)
        for _ in range(300):
            quiet.step(chem=False)
        act = []
        for g in rng.choice(spec.G, size=n_groups, replace=False):
            net.reset_dynamics()
            inj = net.injection([int(g)])
            gmax = np.zeros(spec.G)
            for i in range(spec.inject_steps + spec.gap_steps):
                net.step(inj=inj if i < spec.inject_steps else None, chem=False)
                np.maximum(gmax, net.activity(net.rE), out=gmax)
            others = np.delete(gmax, g)
            act.append({"group": int(g), "A_max": float(gmax[g]), "A_end": float(net.rE[g]),
                        "others_max": float(others.max()),
                        "pass": bool(gmax[g] >= spec.active and others.max() <= spec.inactive)})
        spread = []
        for (a, b, c) in pairs:
            net.reset_all()
            hi01 = hi05 = 0
            seen01, seen05 = set(), set()
            for rnd in range(spec.max_c1_rounds):
                net.reset_dynamics()
                inj = net.injection([a, b])
                for i in range(spec.inject_steps + spec.gap_steps):
                    net.step(inj=inj if i < spec.inject_steps else None, learn=True, release1=True)
                    m = net.activity(net.rE)
                    m[[a, b]] = 0.0
                    seen01.update(np.nonzero(m >= 0.1)[0].tolist())
                    seen05.update(np.nonzero(m >= 0.5)[0].tolist())
            spread.append({"groups_ge_0.1": len(seen01), "groups_ge_0.5": len(seen05)})
        rows.append({"seed": seed, "quiet_max_rE": float(quiet.rE.max()), "quiet_max_over_steps": 0.0,
                     "activation": act, "n_activation_pass": sum(x["pass"] for x in act),
                     "joint_spread": spread,
                     "pairs_with_spread_ge_0.5": sum(1 for x in spread if x["groups_ge_0.5"] > 0),
                     "pairs_with_spread_ge_0.1": sum(1 for x in spread if x["groups_ge_0.1"] > 0)})
        log(f"  sanity realization {seed}: activation {rows[-1]['n_activation_pass']}/{n_groups}, quiet max "
            f"{rows[-1]['quiet_max_rE']:.3g}, pairs with spread >=0.5: {rows[-1]['pairs_with_spread_ge_0.5']}/24, "
            f">=0.1: {rows[-1]['pairs_with_spread_ge_0.1']}/24")
    out = {"settings": {"theta": theta, "beta": beta, "tau": tau, **over}, "rows": rows}
    _dump(out_path, out)
    return out


# ------------------------------------------------------------------------------------------------ grid size

def grid_check(theta, beta, tau, realizations, n_pairs, out_path, seven=None, log=print) -> dict:
    """9 x 9 x 9, pairs >= 2 cells from the surface, 24 pairs per realization (pair_margin 2)."""
    # stray limit kept at 34 groups as in the spiking 9^3 runs (max_active_frac 0.0467, archive-pre-engine-fix/params/session73-g9-*.json)
    spec9 = make_spec(theta, beta, tau, grid_dim=9, max_active_frac=34 / 729)
    pairs = pick_pairs(spec9, n_pairs, margin=2, seed=0)
    res = run_set(spec9, pairs, realizations, label="9^3", log=log)
    counts, fr = count_classes(res), fractions(res)
    n = len(res)
    transfer = (counts["contained"] + counts["ignition"]) / n
    ign = counts["ignition"] / n
    ign_bound = clopper_pearson(0, 24)[1]
    tr_bound = clopper_pearson(5, 24)[1]
    out = {"settings": {"theta": theta, "beta": beta, "tau": tau, "realizations": realizations, "n_pairs": n_pairs,
                        "margin": 2},
           "n_simulations": n, "counts": counts, "fractions": fr, "transfer_fraction": transfer,
           "ignition_fraction": ign, "ignition_upper_bound_0_of_24": ign_bound,
           "transfer_upper_bound_5_of_24": tr_bound,
           "pass": ign <= ign_bound and transfer <= tr_bound}
    if seven:
        out["seven_cubed_transfer_fraction"] = seven
    _dump(out_path, out)
    return out


# ------------------------------------------------------------------------------------------------ uniform C2

def uniform_check(theta, beta, tau, realizations, out_path, uniform=1.2, log=print) -> dict:
    keys, pairs = seed_pairs(None)
    base = make_spec(theta, beta, tau)
    uni = make_spec(theta, beta, tau, c2_uniform=uniform)
    a = run_set(base, pairs, realizations, c2_stage=True, label="activity-dependent C2", log=log)
    b = run_set(uni, pairs, realizations, c2_stage=True, label=f"uniform C2 {uniform}", log=log)
    xa = np.array([1.0 if r.get("association") else 0.0 for r in a])
    xb = np.array([1.0 if r.get("association") else 0.0 for r in b])
    diff = xb - xa
    n = len(diff)
    se = diff.std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")
    lo, hi = diff.mean() - 1.96 * se, diff.mean() + 1.96 * se
    out = {"settings": {"theta": theta, "beta": beta, "tau": tau, "realizations": realizations, "uniform": uniform},
           "n_simulations": n, "associations_activity_dependent": int(xa.sum()), "associations_uniform": int(xb.sum()),
           "fraction_activity_dependent": float(xa.mean()), "fraction_uniform": float(xb.mean()),
           "paired_difference": float(diff.mean()), "paired_ci95": [float(lo), float(hi)],
           "discordant_pairs": int((diff != 0).sum()),
           "transfers_equal": all(p["class"] == q["class"] for p, q in zip(a, b)),
           "pass": bool((lo <= 0.0 <= hi or float(diff.std()) == 0.0) and abs(diff.mean()) <= 0.10)}
    _dump(out_path, out)
    return out


def _dump(path: str, obj: dict):
    if path:
        with open(path, "w") as f:
            json.dump(obj, f, indent=1)


def _floats(s: str) -> List[float]:
    return [float(x) for x in s.split(",")]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["fit", "eval", "grid", "uniform", "sanity"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--theta", type=float, default=0.0)
    ap.add_argument("--beta", type=float, default=0.0)
    ap.add_argument("--tau", type=float)
    ap.add_argument("--sigma", type=float, default=None, help="noise_sigma (round 3)")
    ap.add_argument("--sigmas", default="5")
    ap.add_argument("--transfer", default=None)
    ap.add_argument("--input-scale", type=float, default=None)
    ap.add_argument("--injection", default=None)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--thetas", default="0")
    ap.add_argument("--betas", default="0")
    ap.add_argument("--taus", default="1,2,4")
    ap.add_argument("--fit-seeds", default="0,1,2,3,4")
    ap.add_argument("--prescreen", default="0")
    ap.add_argument("--top", type=int, default=2)
    ap.add_argument("--realizations", default="5,6,7,8,9")
    ap.add_argument("--n-pairs", type=int, default=24)
    a = ap.parse_args(argv)
    global WORKERS
    WORKERS = a.workers
    if a.transfer:
        GLOBAL_OVER["transfer"] = a.transfer
    if a.injection:
        GLOBAL_OVER["injection_mode"] = a.injection
    if a.input_scale is not None:
        GLOBAL_OVER["input_scale"] = a.input_scale
    if a.sigma is not None:
        GLOBAL_OVER["noise_sigma"] = a.sigma
    ints = lambda s: [int(x) for x in s.split(",")]
    if a.mode == "fit":
        fit(_floats(a.thetas), _floats(a.betas), _floats(a.taus), ints(a.fit_seeds), ints(a.prescreen), a.top, a.out, sigmas=_floats(a.sigmas))
    elif a.mode == "eval":
        r = evaluate(a.theta, a.beta, a.tau, ints(a.realizations), a.out)
        print(json.dumps({k: r[k] for k in ("counts", "fractions", "within_interval", "pass", "kappa_modal_class_per_pair")}))
    elif a.mode == "sanity":
        sanity(a.theta, a.beta, a.tau, ints(a.realizations), a.out)
    elif a.mode == "grid":
        r = grid_check(a.theta, a.beta, a.tau, ints(a.realizations), a.n_pairs, a.out)
        print(json.dumps(r))
    elif a.mode == "uniform":
        r = uniform_check(a.theta, a.beta, a.tau, ints(a.realizations), a.out)
        print(json.dumps(r))


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    main()
