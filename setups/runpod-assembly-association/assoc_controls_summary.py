#!/usr/bin/env python3
"""Protocol runs with controls (iteration 56): one line per pair; association, strays, controls 0, 1 and
joint activation; usage: python assoc_controls_summary.py output [session glob, default s69*-stage2]."""
import glob
import json
import os
import re
import sys

base = sys.argv[1]
rows = []
for f in sorted(glob.glob(os.path.join(base, sys.argv[2] if len(sys.argv) > 2 else "s69*-stage2", "s4-*.json"))):
    if f.endswith(".summary.json"):
        continue
    r = json.load(open(f))
    m = re.search(r"pair(\d+)-seed(\d+)", os.path.basename(f))
    pair, seed = int(m.group(1)), int(m.group(2))
    if "error" in r:
        print(f"seed {seed} pair {pair:2d} ERROR {r['error'].strip().splitlines()[-1]}")
        continue
    fin, ck = r["main"]["final"], r["checks"]

    def t(x):
        return f"{x['dst_max']:.2f}/{x['n_active_outside']:3d}{'b' if x['bounded'] else '-'}"

    def ctl(k):
        c = r.get(k)
        if not c:
            return "   -    "
        best = max((c["final"]["A_to_B"], c["final"]["B_to_A"]), key=lambda x: x["dst_max"])
        return f"{t(best)} r{c['rounds']:2d}"

    print(f"seed {seed} pair {pair:2d} r{r['main']['c1_rounds']:2d} c1ok {int(r['main']['c1_test_passed'])} | "
          f"A->B {t(fin['A_to_B'])} B->A {t(fin['B_to_A'])} | ctl0 {'ok' if ck['control0_no_association_before'] else 'FAIL'} "
          f"| noC2 {ctl('control1_no_chemistry')} | separate {ctl('control_separate')} | assoc {int(ck['association'])} "
          f"sep_ok {int(ck.get('control_separate', True))} | PASS {r['pass']}")
    rows.append((seed, pair, ck["association"], ck.get("control_separate"), ck.get("control1_no_chemistry"), r["pass"]))

for seed in (0, 1):
    rs = [x for x in rows if x[0] == seed]
    print(f"seed {seed}: n {len(rs)}, association {sum(x[2] for x in rs)}, separate control failed "
          f"{sum(x[3] is False for x in rs)} (of them with association {sum(x[2] and x[3] is False for x in rs)}), "
          f"no-C2 control failed {sum(x[4] is False for x in rs)}, pass {sum(x[5] for x in rs)}")
print("format: dst_max/strays, b = bounded; controls: best direction, r = C1 rounds")
