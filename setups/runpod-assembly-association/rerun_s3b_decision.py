"""
rerun_s3b_decision.py

Step 7's S3b decision and screening (engine-fix-rerun-log.md, "Step 7, S3b decision" and "Step 7, S3b
screening"), standard library only; run it where the results are. Per setting (the job name without its type and
without a trailing seed, -s0 / -s1, so a decision pools its seeds), over the pairs of the propagation survey (M
and Sh spikes per excitatory neuron per round in the route middle and the off-route shell):

  summation    D = M joint - (M A + M B)
  selectivity  D = M joint - Sh joint
  corrected    D = M joint + M none - M A - M B   (reported, not deciding)

count of pairs with D > 0 against D < 0 (ties left out) and the 95 % Wilson interval of the fraction with D > 0;
a test holds if the interval's lower bound lies above 0.5. Also per seed, medians, distinct pairs, runaways, the
off-route assemblies under joint injection, and the hysteresis loops of S0 and S3b (with those of the step 7
sessions rerun7a and rerun7b).

  python rerun_s3b_decision.py OUTPUT_DIR [SESSION_GLOB, default rerun7[d-g]*]
"""

from __future__ import annotations

import glob
import json
import math
import os
import re
import sys
from collections import defaultdict

Z = 1.959964
TYPES = ("prop_survey", "hysteresis")


def wilson(k: int, n: int):
    if n == 0:
        return None, None
    p = k / n
    den = 1 + Z * Z / n
    mid = (p + Z * Z / (2 * n)) / den
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / den
    return mid - half, mid + half


def median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else 0.5 * (xs[m - 1] + xs[m])


def count(ds):
    pos = sum(d > 0 for d in ds)
    neg = sum(d < 0 for d in ds)
    lo, hi = wilson(pos, pos + neg)
    return {"pos": pos, "neg": neg, "ties": len(ds) - pos - neg, "lo": lo, "hi": hi,
            "holds": lo is not None and lo > 0.5, "median": median(ds)}


def m(cond):
    return cond["M"] or 0.0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root, pattern = argv[0], (argv[1] if len(argv) > 1 else "rerun7[d-g]*")
    rows = defaultdict(list)      # setting -> [(seed, pair row)]
    loops = {}
    paths = glob.glob(os.path.join(root, pattern, "*.json"))
    # step 7's own hysteresis jobs of S0 (rerun7a names them sp1-lam<x>-hysteresis) and S3b
    paths += [p for p in glob.glob(os.path.join(root, "rerun7[ab]*", "*hysteresis.json"))
              if re.search(r"(sp1-lam[\d.]+|S3b-sig1)-hysteresis\.json$", p)]
    for path in sorted(set(paths)):
        base = os.path.basename(path)[:-5]
        typ = next((t for t in TYPES if base.endswith("-" + t)), None)
        if typ is None or not base.startswith("sp"):
            continue
        setting = base[: -len(typ) - 1]
        ms = re.match(r"(.*)-s(\d)$", setting)
        group, seed = (ms.group(1), int(ms.group(2))) if ms else (setting, 0)
        r = json.load(open(path))
        if "error" in r:
            print(f"ERROR {base}: {str(r['error']).strip().splitlines()[-1][:100]}")
            continue
        if typ == "hysteresis":
            loops[(setting, os.path.basename(os.path.dirname(path))[:7])] = r.get("loop_max")
        elif "S3b" in group:
            rows[group] += [(seed, p) for p in r["pairs"]]
    f = lambda x: "-" if x is None else f"{x:.3f}"
    for group in sorted(rows):
        rs = rows[group]
        seeds = sorted({t for t, _ in rs})
        offs = [p["joint"].get("off_asm_max") for _, p in rs]
        print(f"### {group}: {len(rs)} pairs, distinct per seed "
              + ", ".join(f"s{s} {len({tuple(sorted(p['pair'][:2])) for t, p in rs if t == s})}" for s in seeds)
              + f", runaway pairs {sum(any(p[k]['runaway'] for k in ('joint', 'A', 'B')) for _, p in rs)}"
              + f", off-route assembly max (joint) median {f(median(offs))}, pairs >= 0.5: "
              + f"{sum(1 for x in offs if x is not None and x >= 0.5)}")
        tests = {"summation": lambda p: m(p["joint"]) - m(p["A"]) - m(p["B"]),
                 "selectivity": lambda p: m(p["joint"]) - (p["joint"]["Sh"] or 0.0),
                 "corrected": lambda p: m(p["joint"]) + m(p["none"]) - m(p["A"]) - m(p["B"])}
        for name, fn in tests.items():
            for label, sel in [("all", None)] + ([(f"s{s}", s) for s in seeds] if len(seeds) > 1 else []):
                c = count([fn(p) for t, p in rs if sel is None or t == sel])
                print(f"  {name:11} {label:4}  D>0 {c['pos']:2}  D<0 {c['neg']:2}  ties {c['ties']:2}  "
                      f"Wilson95 [{f(c['lo'])}, {f(c['hi'])}]  median D {f(c['median'])}"
                      + ("  HOLDS" if c["holds"] and label == "all" and name != "corrected" else ""))
        print("  medians: M joint {}  M A+B {}  Sh joint {}  M none {}".format(
            f(median([m(p["joint"]) for _, p in rs])), f(median([m(p["A"]) + m(p["B"]) for _, p in rs])),
            f(median([p["joint"]["Sh"] for _, p in rs])), f(median([m(p["none"]) for _, p in rs]))))
    print("### hysteresis loop max (setting, session)")
    for k in sorted(loops):
        print(f"  {k}: {f(loops[k])}")


if __name__ == "__main__":
    main()
