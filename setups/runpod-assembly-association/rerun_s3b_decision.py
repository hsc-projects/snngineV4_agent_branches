"""
rerun_s3b_decision.py

Step 7's S3b decision (engine-fix-rerun-log.md, "Step 7, S3b decision"), standard library only; run it where the
results are. Per lambda, over the pairs of both seeds (propagation survey; M and Sh spikes per excitatory neuron
per round in the route middle and the off-route shell):

  summation    D = M joint - (M A + M B)
  selectivity  D = M joint - Sh joint
  corrected    D = M joint + M none - M A - M B   (reported, not deciding)

count of pairs with D > 0 against D < 0 (ties left out) and the 95 % Wilson interval of the fraction with D > 0;
a test holds if the interval's lower bound lies above 0.5. Also per seed, medians, distinct pairs, runaways, and
the hysteresis loops of S3b and S0 (rerun7a, rerun7b for seed 0 of the earlier step 7 sessions).

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
    rows = defaultdict(list)      # lambda -> [(seed, pair row)]
    loops = {}
    for path in sorted(glob.glob(os.path.join(root, pattern, "*.json")) +
                       glob.glob(os.path.join(root, "rerun7[ab]*", "*hysteresis.json"))):
        base = os.path.basename(path)[:-5]
        # rerun7a names S0's jobs without the substrate (sp1-lam0.4-hysteresis)
        mt = re.match(r"sp[12]-lam([\d.]+)(?:-(S0|S3b))?(?:-sig1)?(?:-s(\d))?-(prop_survey|hysteresis)$", base)
        if not mt:
            continue
        lam, sub, seed, typ = mt.group(1), mt.group(2) or "S0", int(mt.group(3) or 0), mt.group(4)
        r = json.load(open(path))
        if "error" in r:
            print(f"ERROR {base}: {str(r['error']).strip().splitlines()[-1][:100]}")
            continue
        if typ == "hysteresis":
            loops[(lam, sub, seed, os.path.basename(os.path.dirname(path))[:7])] = r.get("loop_max")
        elif sub == "S3b" and mt.group(3) is not None:
            rows[lam] += [(seed, p) for p in r["pairs"]]
    f = lambda x: "-" if x is None else f"{x:.3f}"
    for lam in sorted(rows):
        rs = rows[lam]
        print(f"### lambda {lam}: {len(rs)} pairs, distinct per seed "
              + ", ".join(f"s{s} {len({tuple(sorted(p['pair'][:2])) for t, p in rs if t == s})}"
                          for s in sorted({t for t, _ in rs}))
              + f", runaway pairs {sum(any(p[k]['runaway'] for k in ('joint', 'A', 'B')) for _, p in rs)}")
        tests = {"summation": lambda p: m(p["joint"]) - m(p["A"]) - m(p["B"]),
                 "selectivity": lambda p: m(p["joint"]) - (p["joint"]["Sh"] or 0.0),
                 "corrected": lambda p: m(p["joint"]) + m(p["none"]) - m(p["A"]) - m(p["B"])}
        for name, fn in tests.items():
            for label, sel in [("both", None)] + [(f"s{s}", s) for s in sorted({t for t, _ in rs})]:
                c = count([fn(p) for t, p in rs if sel is None or t == sel])
                print(f"  {name:11} {label:4}  D>0 {c['pos']:2}  D<0 {c['neg']:2}  ties {c['ties']:2}  "
                      f"Wilson95 [{f(c['lo'])}, {f(c['hi'])}]  median D {f(c['median'])}"
                      + ("  HOLDS" if c["holds"] and label == "both" and name != "corrected" else ""))
        print("  medians: M joint {}  M A+B {}  Sh joint {}  M none {}".format(
            f(median([m(p["joint"]) for _, p in rs])), f(median([m(p["A"]) + m(p["B"]) for _, p in rs])),
            f(median([p["joint"]["Sh"] for _, p in rs])), f(median([m(p["none"]) for _, p in rs]))))
    print("### hysteresis loop max (lambda, substrate, seed, session)")
    for k in sorted(loops):
        print(f"  {k}: {f(loops[k])}")


if __name__ == "__main__":
    main()
