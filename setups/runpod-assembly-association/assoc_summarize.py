#!/usr/bin/env python3
"""
Host-side summaries of downloaded session results (output/<session>/), no GPU or engine needed.

  python assoc_summarize.py runs   <session dir>...     one line per protocol run (substep4)
  python assoc_summarize.py rates  <dir pattern>...     pass / failure counts per session and distance
  python assoc_summarize.py regime <session dir>...     Substep 1 counts and saturation diagnostics

Failure kinds in `rates`: ignite = stopped by the runaway check during the C1 rounds (no
consolidation); no_transfer = no association in the final test; other = association but a check
failed (containment, control 2, control 1).
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re

SHORT = {"association": "assoc", "control0_no_association_before": "c0", "control2_C_inactive": "c2",
         "association_contained": "cont", "control1_no_chemistry": "c1chem", "control1_gating_off": "c1gate"}


def _jobs(d: str, prefix: str):
    for f in sorted(glob.glob(os.path.join(d, prefix + "*.json"))):
        if not f.endswith(".summary.json"):
            yield os.path.basename(f)[:-5], json.load(open(f))


def runs(dirs):
    for d in dirs:
        for name, r in _jobs(d, "s4-"):
            if "error" in r:
                print(os.path.basename(d), name, "ERROR", r["error"].strip().splitlines()[-1])
                continue
            m, fz = r["main"], r["main"]["final"]
            best = max(("A_to_B", "B_to_A"), key=lambda k: (fz[k]["contained"], fz[k]["dst_max"]))
            b = fz[best]
            state = "ignite" if m["runaway_round"] else ("c1ok" if m["c1_test_passed"] else "-")
            fails = [SHORT.get(k, k) for k, v in r["checks"].items() if not v]
            print("%-36s %-30s %3d->%-3d C1 rounds %-2d %-6s best %s %.2f others %.2f C %.2f | %s" % (
                os.path.basename(d), name, r["pair"]["A"], r["pair"]["B"], m["c1_rounds"], state, best,
                b["dst_max"], b["others_max"], b["c_max"] or 0.0, "PASS" if r["pass"] else "fail: " + ",".join(fails)))


def rates(patterns):
    tab = collections.defaultdict(collections.Counter)
    for pat in patterns:
        for d in sorted(glob.glob(pat)):
            for name, r in _jobs(d, "s4-"):
                m = re.search(r"s4-d(\d+)", name)
                c = tab[(os.path.basename(d), m.group(1) if m else "?")]
                c["n"] += 1
                if "error" in r:
                    c["error"] += 1
                elif r["pass"]:
                    c["pass"] += 1
                    c["rounds"] += r["main"]["c1_rounds"]
                elif r["main"]["runaway_round"]:
                    c["ignite"] += 1
                elif not r["checks"]["association"]:
                    c["no_transfer"] += 1
                else:
                    c["other"] += 1
    for (d, dist), c in sorted(tab.items()):
        mean = c["rounds"] / c["pass"] if c["pass"] else float("nan")
        print("%-40s d%s  pass %2d/%-2d  ignite %2d  no_transfer %2d  other %2d  error %d  C1 rounds (passes) %.1f" % (
            d, dist, c["pass"], c["n"], c["ignite"], c["no_transfer"], c["other"], c["error"], mean))


def regime(dirs):
    for d in dirs:
        for name, r in _jobs(d, "s1-"):
            c = r.get("counts")
            if c:
                print("%-36s %-34s Substep 1 pass %d/%d  under-recruited %d  spilling %d" % (
                    os.path.basename(d), name, c["n_pass"], c["n_groups"], c["n_under_recruited"], c["n_spill"]))
        for name, r in _jobs(d, "diag-"):
            if "fraction_by_check" in r:
                fb = r["fraction_by_check"]
                print("%-36s %-34s diagnostic pass %.1f  transfer at saturation %.1f  C inactive %.1f" % (
                    os.path.basename(d), name, r["fraction_pass"], fb["transfer_at_max_weights"], fb["saturated_C_inactive"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=("runs", "rates", "regime"))
    ap.add_argument("paths", nargs="+")
    a = ap.parse_args()
    {"runs": runs, "rates": rates, "regime": regime}[a.what](a.paths)


if __name__ == "__main__":
    main()
