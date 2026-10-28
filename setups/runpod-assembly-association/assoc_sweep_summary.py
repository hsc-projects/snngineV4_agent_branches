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

Iteration 59: job names may carry a seed (`s4-d6-s1-pair3-<configuration>`; pairs then print as s1p3).
Added columns: median C1 rounds of the transfers; median route / shell ratio of the energy or C3 level
(`E`) at the end of the injection in the last joint round and in the last short-circuit round; `filt`,
the associations whose final strays are at most half the strays of their C1-phase transfer (the short
circuit stage narrowed the transfer). With `-v` as the third argument, one line per pair: C1 rounds,
strays of the C1-phase transfer -> strays of the final association (or lost / unbounded).
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
verbose = len(sys.argv) > 3 and sys.argv[3] == "-v"
for fn in sorted(glob.glob(os.path.join(base, pattern, "s4-*.json"))):
    if fn.endswith(".summary.json"):
        continue
    m = re.search(r"pair(\d+)-(.+)$", os.path.basename(fn)[:-5])
    sd = re.search(r"-s(\d+)-pair", os.path.basename(fn))
    pair, name = (f"s{sd.group(1)}p{m.group(1)}" if sd else int(m.group(1))), m.group(2)
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
    c2sel = spksel = esel2 = None
    if main.get("c2_log"):
        sel = main["c2_log"][-1].get("sel_inject_end") or {}
        c2sel = (sel.get("ratio") or {}).get("C2")
        spksel = (sel.get("ratio") or {}).get("spikes_per_exc")
        esel2 = (sel.get("ratio") or {}).get("E")
    esel1 = ((log[-1].get("sel_inject_end") or {}).get("ratio") or {}).get("E") if log else None
    cfg[name].append({"pair": pair, "c1_ok": c1_ok, "c1_strays": t["n_active_outside"] if (t and c1_ok) else None,
                      "assoc": bool(assoc), "strays": best["n_active_outside"] if best else None,
                      "unbounded": any(fin[d]["success"] and not fin[d]["bounded"] for d in fin),
                      "rounds": main["c1_rounds"], "c2_rounds": main.get("c2_rounds"), "c2sel": c2sel,
                      "spksel": spksel, "esel1": esel1, "esel2": esel2})

print(f"{'config':16} {'n':>2} {'c1ok':>4} {'assoc':>5} {'lost':>4} {'unbd':>4} {'strays':>8} {'c1str':>6} "
      f"{'C2 M/Sh':>7} {'spk M/Sh':>8} {'rnd':>4} {'E1 M/Sh':>7} {'E2 M/Sh':>7} {'filt':>4}  assoc pairs")
for name in sorted(cfg):
    rows = cfg[name]
    errs = [x for x in rows if "error" in x]
    ok = [x for x in rows if "error" not in x]
    assoc = [x for x in ok if x["assoc"]]
    lost = [x for x in ok if x["c1_ok"] and not x["assoc"] and not x["unbounded"]]
    print(f"{name:16} {len(ok):2d} {sum(x['c1_ok'] for x in ok):4d} {len(assoc):5d} {len(lost):4d} "
          f"{sum(x['unbounded'] for x in ok):4d} {f(med([x['strays'] for x in assoc]), 8, 1)} "
          f"{f(med([x['c1_strays'] for x in ok]), 6, 1)} {f(med([x['c2sel'] for x in ok]), 7)} "
          f"{f(med([x['spksel'] for x in ok]), 8)} {f(med([x['rounds'] for x in ok if x['c1_ok']]), 4, 0)} "
          f"{f(med([x['esel1'] for x in ok]), 7)} {f(med([x['esel2'] for x in ok]), 7)} "
          f"{sum(1 for x in assoc if x['c1_strays'] is not None and 2 * x['strays'] <= x['c1_strays']):4d}  "
          f"{[x['pair'] for x in assoc]}" + (f"  ERRORS {len(errs)}: {errs[0]['error']}" if errs else ""))

if verbose:
    for name in sorted(cfg):
        cells = []
        for x in cfg[name]:
            if "error" in x:
                cells.append(f"{x['pair']}:ERR")
            elif not x["c1_ok"]:
                cells.append(f"{x['pair']}:none")
            else:
                end = (str(x["strays"]) if x["assoc"] else "unbd" if x["unbounded"] else "lost")
                cells.append(f"{x['pair']}:r{x['rounds']} {x['c1_strays']}->{end}")
        print(f"{name:16} " + "  ".join(cells))
