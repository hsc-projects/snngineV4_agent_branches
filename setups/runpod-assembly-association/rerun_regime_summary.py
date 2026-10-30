"""
rerun_regime_summary.py

Step 3 of engine-fix-rerun-task.md (operating regime), on the host (standard library only): one line per
configuration (wiring, network seed, gain, gain_ee_inter, gain_ie, intra-group total) of the rerun3* sessions.

  python rerun_regime_summary.py OUTPUT_DIR [SESSION_GLOB] [--json out.json]

Per configuration: Substep 1 on 100 groups (pass = recruited, nothing else above `inactive`, no runaway;
under-recruited, spilling and runaway groups; spread in cells, median and largest), and the saturated-path
diagnostic at d 4 and 6 (6 pairs each): untrained transfer (must not happen), transfer with the path at the
upper weight bound (wanted), C quiet. A regime is a candidate when Substep 1 passes for nearly every group and
a saturated path transmits while an untrained one does not.
"""

from __future__ import annotations

import glob
import json
import os
import re
import statistics
import sys

TAG = re.compile(r"g(?P<gain>[\d.]+)-ee(?P<gee>[\d.]+)-ie(?P<gie>[\d.]+)-T(?P<tot>[\d.]+)$")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    out_json = None
    if "--json" in argv:
        i = argv.index("--json")
        out_json = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    root, pattern = argv[0], (argv[1] if len(argv) > 1 else "rerun3*")
    rows = {}
    for path in sorted(glob.glob(os.path.join(root, pattern, "*.json"))):
        if path.endswith(".summary.json") or os.path.basename(path) == "summary.json":
            continue
        r = json.load(open(path))
        job = r.get("job", {})
        m = TAG.search(job.get("name", ""))
        if not m:
            continue
        rw = job["engine"].get("rewire")
        key = ("own" if not rw else f"lam{rw['lam']:g}", job["engine"].get("seed"),
               float(m["gain"]), float(m["gee"]), float(m["gie"]), float(m["tot"]))
        row = rows.setdefault(key, {})
        if "error" in r:
            row.setdefault("errors", []).append(job["name"])
            continue
        if job["type"] == "substep1":
            c = r["counts"]
            sp = c.get("spread_cells") or [0]
            row["s1"] = {"pass": c["n_pass"], "n": c["n_groups"], "under": c["n_under_recruited"],
                         "spill": c["n_spill"], "runaway": c["n_runaway"],
                         "spread_median": statistics.median(sp), "spread_max": max(sp),
                         "baseline_others_max": r["baseline"]["others_max"]}
        elif job["type"] == "diag_saturated_path":
            d = "d" + str(int(float(job["params"]["protocol"]["pair_distance"])))
            fb = r.get("fraction_by_check", {})
            row[d] = {"pass": r.get("fraction_pass"), "untrained_quiet": fb.get("no_transfer_untrained"),
                      "saturated_transfer": fb.get("transfer_at_max_weights"),
                      "saturated_C_quiet": fb.get("saturated_C_inactive")}
    print("wiring seed gain ee ie T | S1 pass/under/spill/runaway spread med/max | d4 untrained-quiet saturated-transfer |"
          " d6 untrained-quiet saturated-transfer")
    f = lambda x: "-" if x is None else f"{x:.2f}"
    table = []
    for key in sorted(rows):
        row = rows[key]
        s1, d4, d6 = row.get("s1"), row.get("d4", {}), row.get("d6", {})
        s1s = (f"{s1['pass']:>3}/{s1['under']:>2}/{s1['spill']:>2}/{s1['runaway']:>2} {s1['spread_median']:g}/{s1['spread_max']}"
               if s1 else "missing")
        print(f"{key[0]:<7} s{key[1]} {key[2]:<3g} {key[3]:<4g} {key[4]:<2g} {key[5]:<3g} | {s1s:<26} | "
              f"{f(d4.get('untrained_quiet'))} {f(d4.get('saturated_transfer'))} | "
              f"{f(d6.get('untrained_quiet'))} {f(d6.get('saturated_transfer'))}"
              + (f"  errors {row['errors']}" if row.get("errors") else ""))
        table.append({"wiring": key[0], "seed": key[1], "gain": key[2], "gain_ee_inter": key[3], "gain_ie": key[4],
                      "intra_total": key[5], **row})
    if out_json:
        with open(out_json, "w") as fh:
            json.dump(table, fh, indent=1)


if __name__ == "__main__":
    main()
