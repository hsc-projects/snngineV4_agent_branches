#!/usr/bin/env python3
"""
Protocol sweeps (iterations 54 to 57): one line per configuration, over the pairs of a session glob.

  python assoc_sweep_summary.py output ["<session glob>", default "s67*-c2e"]

Job names end in pair<k>-<configuration>. Columns: pairs; transfers in the C1 phase (A alone activates
B on w_fast); associations in the final test (w_perm only, energy off: a direction with B >= 0.5 and
bounded); lost (transfer in the C1 phase, no association, no unbounded transfer); unbounded transfers;
median strays of the associations and of the C1-phase transfers; medians over pairs of the route /
shell ratios of C2 and of spikes at the end of the injection in the last short-circuit round
(telemetry `sel_inject_end`); the associated pairs.
"""
import glob
import json
import os
import re
import statistics
import sys
from collections import defaultdict

base = sys.argv[1]


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def f(x, w=6, p=2):
    return f"{x:{w}.{p}f}" if isinstance(x, (int, float)) else f"{'-':>{w}}"


cfg = defaultdict(list)
pattern = sys.argv[2] if len(sys.argv) > 2 else "s67*-c2e"
for fn in sorted(glob.glob(os.path.join(base, pattern, "s4-*.json"))):
    if fn.endswith(".summary.json"):
        continue
    m = re.search(r"pair(\d+)-(.+)$", os.path.basename(fn)[:-5])
    pair, name = int(m.group(1)), m.group(2)
    r = json.load(open(fn))
    if "error" in r:
        cfg[name].append({"pair": pair, "error": r["error"].strip().splitlines()[-1]})
        continue
    main = r["main"]
    log = main["c1_log"]
    t = log[-1]["test_A_to_B"] if log else None
    c1_ok = main["c1_test_passed"]
    fin = main["final"]
    assoc = [d for d in ("A_to_B", "B_to_A") if fin[d]["success"] and fin[d]["bounded"]]
    best = min((fin[d] for d in assoc), key=lambda x: x["n_active_outside"]) if assoc else None
    c2sel = spksel = None
    if main.get("c2_log"):
        sel = main["c2_log"][-1].get("sel_inject_end") or {}
        c2sel = (sel.get("ratio") or {}).get("C2")
        spksel = (sel.get("ratio") or {}).get("spikes_per_exc")
    cfg[name].append({"pair": pair, "c1_ok": c1_ok, "c1_strays": t["n_active_outside"] if (t and c1_ok) else None,
                      "assoc": bool(assoc), "strays": best["n_active_outside"] if best else None,
                      "unbounded": any(fin[d]["success"] and not fin[d]["bounded"] for d in fin),
                      "rounds": main["c1_rounds"], "c2_rounds": main.get("c2_rounds"), "c2sel": c2sel,
                      "spksel": spksel})

print(f"{'config':16} {'n':>2} {'c1ok':>4} {'assoc':>5} {'lost':>4} {'unbd':>4} {'strays':>8} {'c1str':>6} "
      f"{'C2 M/Sh':>7} {'spk M/Sh':>8}  assoc pairs")
for name in sorted(cfg):
    rows = cfg[name]
    errs = [x for x in rows if "error" in x]
    ok = [x for x in rows if "error" not in x]
    assoc = [x for x in ok if x["assoc"]]
    lost = [x for x in ok if x["c1_ok"] and not x["assoc"] and not x["unbounded"]]
    print(f"{name:16} {len(ok):2d} {sum(x['c1_ok'] for x in ok):4d} {len(assoc):5d} {len(lost):4d} "
          f"{sum(x['unbounded'] for x in ok):4d} {f(med([x['strays'] for x in assoc]), 8, 1)} "
          f"{f(med([x['c1_strays'] for x in ok]), 6, 1)} {f(med([x['c2sel'] for x in ok]), 7)} "
          f"{f(med([x['spksel'] for x in ok]), 8)}  "
          f"{[x['pair'] for x in assoc]}" + (f"  ERRORS {len(errs)}: {errs[0]['error']}" if errs else ""))
