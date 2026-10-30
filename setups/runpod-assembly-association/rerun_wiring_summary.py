"""
rerun_wiring_summary.py

Step 2 of engine-fix-rerun-task.md (wiring decision), on the host (standard library only): summarizes the
conn_survey and substep1 jobs of the rerun2* sessions.

  python rerun_wiring_summary.py OUTPUT_DIR [SESSION_GLOB] [--json out.json]

Connectivity: E -> E synapses per group pair by cell distance (median over pairs) and the effective lambda, from a
least-squares fit of ln(median) = a - d / lambda over the distances 1 to d_max - 1 with a non-zero median (the
largest distance, the corner-to-corner pairs, is left out: in the unrewired builds it holds more synapses than
the next distance, step 1). The same fit on the rewired profiles should give back their lambda.
Activity: per substep1 job, the injected groups recruited (A_max >= active) and without runaway, the spread
(largest cell distance at which another group exceeds `inactive`), the mean peak activity of other groups by
distance, and the intra-group E -> E density over all groups (A2).
"""

from __future__ import annotations

import glob
import json
import math
import os
import statistics
import sys


def fit_lambda(by_d: dict) -> float | None:
    pts = sorted((int(d), v["median"]) for d, v in by_d.items() if int(d) >= 1)
    if len(pts) < 3:
        return None
    pts = [(d, m) for d, m in pts[:-1] if m > 0]
    if len(pts) < 2:
        return None
    xs, ys = [d for d, _ in pts], [math.log(m) for _, m in pts]
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return -1.0 / slope if slope < 0 else None


def wiring_of(job: dict) -> str:
    rw = job.get("engine", {}).get("rewire")
    return "unrewired" if not rw else f"lam{rw['lam']:g}"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    out_json = None
    if "--json" in argv:
        i = argv.index("--json")
        out_json = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    root = argv[0]
    pattern = argv[1] if len(argv) > 1 else "rerun2*"
    conn, act = [], []
    for path in sorted(glob.glob(os.path.join(root, pattern, "*.json"))):
        if path.endswith(".summary.json") or os.path.basename(path) == "summary.json":
            continue
        r = json.load(open(path))
        job = r.get("job", {})
        if "error" in r:
            print(f"ERROR {job.get('name', path)}: {str(r['error']).strip().splitlines()[-1]}")
            continue
        size = f"{r.get('seg', [None])[0]}^3" if "seg" in r else None
        if job.get("type") == "conn_survey":
            by_d = r["ee_synapses_by_cell_distance"]
            conn.append({"job": job["name"], "size": size, "seed": job["engine"].get("seed"), "wiring": wiring_of(job),
                         "lambda_eff": fit_lambda(by_d),
                         "median_by_distance": {d: v["median"] for d, v in sorted(by_d.items(), key=lambda x: int(x[0]))}})
        elif job.get("type") == "substep1":
            p = job["params"]
            rows = r["groups"]
            n = r["network"]
            seg = round((n["G"]) ** (1 / 3))
            dists = sorted({int(d) for g in rows for d in g["spread"]["by_distance"]})
            prof = {d: statistics.fmean(g["spread"]["by_distance"][str(d)]["mean"] for g in rows
                                        if str(d) in g["spread"]["by_distance"]) for d in dists}
            ok = [g for g in rows if g["runaway"] is None and g["A_max"] >= 0.5]
            act.append({"job": job["name"], "size": f"{seg}^3", "seed": job["engine"].get("seed"),
                        "wiring": wiring_of(job), "gain": p.get("gain"), "n_groups": len(rows),
                        "n_recruited_no_runaway": len(ok),
                        "n_runaway": sum(g["runaway"] is not None for g in rows),
                        "spread_cells": [g["spread"]["spread_cells"] for g in rows],
                        "spread_cells_recruited": [g["spread"]["spread_cells"] for g in ok],
                        "n_active_others_median": statistics.median(g["spread"]["n_active"] for g in rows),
                        "spikes_median": statistics.median(g["spikes"] for g in rows),
                        "mean_peak_by_distance": prof,
                        "baseline_others_max": r["baseline"]["others_max"],
                        "intra_ee_per_exc_neuron_by_group": n.get("intra_ee_per_exc_neuron_by_group")})
    print("connectivity: E -> E synapses per group pair (median) by cell distance; effective lambda")
    for c in sorted(conn, key=lambda c: (c["size"], c["wiring"], c["seed"])):
        md = c["median_by_distance"]
        lam = "-" if c["lambda_eff"] is None else f"{c['lambda_eff']:.2f}"
        print(f"  {c['size']} s{c['seed']} {c['wiring']:<9} lambda_eff {lam:>5}  " +
              " ".join(f"{d}:{v:g}" for d, v in md.items()))
    print("activity: recruited without runaway / groups; spread (cells) of recruited groups; median spikes; "
          "mean peak A of other groups at distance 1, 2, 3, 4, 6")
    for a in sorted(act, key=lambda a: (a["size"], a["wiring"], a["gain"], a["seed"])):
        pr = a["mean_peak_by_distance"]
        ig = a["intra_ee_per_exc_neuron_by_group"] or {}
        print(f"  {a['size']} s{a['seed']} {a['wiring']:<9} gain {a['gain']:<3g} {a['n_recruited_no_runaway']}/{a['n_groups']}"
              f" runaway {a['n_runaway']} spread {sorted(a['spread_cells_recruited'])} spikes {a['spikes_median']:g}"
              f" peaks " + " ".join(f"{pr[d]:.2f}" if d in pr else "-" for d in (1, 2, 3, 4, 6)) +
              f" | intra/exc min {ig.get('min', float('nan')):.1f} med {ig.get('median', float('nan')):.1f}"
              f" max {ig.get('max', float('nan')):.1f}")
    if out_json:
        with open(out_json, "w") as f:
            json.dump({"connectivity": conn, "activity": act}, f, indent=1)


if __name__ == "__main__":
    main()
