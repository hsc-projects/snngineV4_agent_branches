"""
sparse_c1_levels.py

Sparse task, Substep 3: C1's level in the spiking runs, for the C1 thresholds of L2 to L5 (`sparse-tuning-log.md`,
entry 2). Standard library only; run it where the results are. Per session glob, the medians over pairs of C1 at
A, at the midpoint of the segment A-B, and the field's mean and maximum, after joint rounds 1, 3, 5, 10, 20 and
30 (the telemetry `chem` of each round's log entry, after the round's gap), and the ratio midpoint / A; and C1
in the route middle M and the off-route shell Sh at the end of the round's injection (`sel_inject_end`), with
their ratio; and with the protocol option `c1_open`, the thresholded readout: the fraction of M and Sh voxels at
C1 >= f times Sh's mean C1 (`c1_open`, gate form G4), the reservoir's mean C1 (`c1_open_mean`, G1) or the voxel's
own slow average of C1 (`c1_open_rise`, G3), per factor f.

  python sparse_c1_levels.py OUTPUT_DIR "SESSION_GLOB" [...]
"""

from __future__ import annotations

import glob
import json
import os
import sys

ROUNDS = (1, 3, 5, 10, 20, 30)
READOUTS = {"C1_open": "Sh's mean (G4)", "C1_open_mean": "the reservoir's mean (G1)",
            "C1_open_rise": "the voxel's own slow average (G3)"}


def median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else 0.5 * (xs[m - 1] + xs[m])


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = argv[0]
    f = lambda x: "-" if x is None else f"{x:.4g}"
    for pattern in argv[1:]:
        per_round = {r: {"A": [], "mid": [], "mean": [], "max": [], "M": [], "Sh": [], "M/Sh": [],
                         "open": {k: {} for k in READOUTS}} for r in ROUNDS}
        n = 0
        for path in sorted(glob.glob(os.path.join(root, pattern, "s4-*.json"))):
            if path.endswith(".summary.json"):
                continue
            r = json.load(open(path))
            if "error" in r:
                continue
            n += 1
            for e in r["main"]["c1_log"]:
                c = (e.get("chem") or {}).get("C1")
                if c is None or e["round"] not in per_round:
                    continue
                d = per_round[e["round"]]
                d["A"].append(c["along_AB"][0])
                d["mid"].append(c["along_AB"][5])
                d["mean"].append(c["mean"])
                d["max"].append(c["max"])
                sel = e.get("sel_inject_end") or {}
                if sel.get("M", {}).get("C1") is not None and sel.get("Sh", {}).get("C1") is not None:
                    d["M"].append(sel["M"]["C1"])
                    d["Sh"].append(sel["Sh"]["C1"])
                    if sel["Sh"]["C1"] > 0:
                        d["M/Sh"].append(sel["M"]["C1"] / sel["Sh"]["C1"])
                for key in READOUTS:
                    for row in sel.get(key) or []:
                        o = d["open"][key].setdefault(row["f"], {"M": [], "Sh": []})
                        o["M"].append(row["M"])
                        o["Sh"].append(row["Sh"])
        print(f"### {pattern}: {n} pairs; medians over the pairs still in the joint rounds")
        print(f"  {'round':>5} {'pairs':>5} {'C1 at A':>9} {'C1 mid':>9} {'mid / A':>8} {'C1 mean':>9} {'C1 max':>9}"
              f" {'C1 in M':>9} {'C1 in Sh':>9} {'M / Sh':>7}")
        for rnd in ROUNDS:
            d = per_round[rnd]
            a, mid = median(d["A"]), median(d["mid"])
            print(f"  {rnd:>5} {len(d['A']):>5} {f(a):>9} {f(mid):>9} {f(mid / a if a and mid is not None else None):>8} "
                  f"{f(median(d['mean'])):>9} {f(median(d['max'])):>9} {f(median(d['M'])):>9} {f(median(d['Sh'])):>9}"
                  f" {f(median(d['M/Sh'])):>7}")
        for key, label in READOUTS.items():
            if not any(per_round[r]["open"][key] for r in ROUNDS):
                continue
            print(f"  thresholded readout ({key}): open fraction of M / Sh voxels at C1 >= f x {label}, medians")
            for rnd in ROUNDS:
                rows = per_round[rnd]["open"][key]
                if rows:
                    cells = []
                    for fac in sorted(rows):
                        m_, s_ = median(rows[fac]["M"]), median(rows[fac]["Sh"])
                        cells.append(f"f {fac:g}: {f(m_)} / {f(s_)}")
                    print(f"  round {rnd:>2}: " + "   ".join(cells))


if __name__ == "__main__":
    main()
