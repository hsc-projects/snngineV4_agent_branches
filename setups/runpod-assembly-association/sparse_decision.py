"""
sparse_decision.py

Sparse task, Substep 3: a full decision (`sparse-tuning-log.md`, entry 7), standard library only; run it where the
results are. Paired by (seed, pair) over the main run's pairs: associations of the main run (with control 0 and
the separate-rounds control in its jobs), of a comparison run (the gate-open control) and of the baseline (L0),
McNemar's exact one-sided test on the discordant pairs (main associates, the other does not, and the reverse), and
the median final strays of the associations. An association is a final-test direction with B >= 0.5 and bounded,
as in `assoc_sweep_summary.py`.

  python sparse_decision.py OUTPUT_DIR MAIN_GLOB OPEN_GLOB BASELINE_GLOB [BASELINE_GLOB ...]
"""

from __future__ import annotations

import glob
import json
import math
import os
import re
import sys


def results(root: str, patterns) -> dict:
    out = {}
    for pattern in patterns:
        for path in glob.glob(os.path.join(root, pattern, "s4-*.json")):
            if path.endswith(".summary.json"):
                continue
            m = re.search(r"-s(\d+)-pair(\d+)-", os.path.basename(path))
            r = json.load(open(path))
            out[(int(m.group(1)), int(m.group(2)))] = r
    return out


def association(final: dict):
    """(associated, final strays of the best associated direction or None)."""
    ok = [final[d] for d in ("A_to_B", "B_to_A") if final[d]["success"] and final[d]["bounded"]]
    return (bool(ok), min(x["n_active_outside"] for x in ok) if ok else None)


def mcnemar(b: int, c: int) -> float:
    """One-sided exact p of at least b of the b + c discordant pairs going the main run's way."""
    n = b + c
    return 1.0 if n == 0 else sum(math.comb(n, k) for k in range(b, n + 1)) / 2 ** n


def median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else 0.5 * (xs[m - 1] + xs[m])


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root, main_glob, open_glob, base_globs = argv[0], argv[1], argv[2], argv[3:]
    M, O, B = results(root, [main_glob]), results(root, [open_glob]), results(root, base_globs)
    keys = sorted(M)
    err = {name: [k for k in keys if k in d and "error" in d[k]] for name, d in (("main", M), ("open", O), ("L0", B))}
    rows = {}
    for k in keys:
        rm = M[k]
        if "error" in rm:
            continue
        am, sm = association(rm["main"]["final"])
        sep = rm.get("control_separate")
        asep = association(sep["final"])[0] if sep else None
        ao, so = association(O[k]["main"]["final"]) if (k in O and "error" not in O[k]) else (None, None)
        ab, sb = association(B[k]["main"]["final"]) if (k in B and "error" not in B[k]) else (None, None)
        rows[k] = {"main": am, "strays": sm, "sep": asep, "open": ao, "open_strays": so, "L0": ab, "L0_strays": sb,
                   "ctl0": rm["checks"].get("control0_no_association_before")}
    n = len(rows)
    print(f"pairs {n} (main {len(M)}, gate open {len(O)}, L0 {len(B)}); errors {err}")
    for name, key in (("main (L3 under G1)", "main"), ("separate rounds", "sep"), ("gate open", "open"), ("L0", "L0")):
        have = [r[key] for r in rows.values() if r[key] is not None]
        print(f"  {name:20} associations {sum(have):2d} of {len(have)}")
    for name, key in (("L0", "L0"), ("gate open", "open"), ("separate rounds", "sep")):
        both = [r for r in rows.values() if r[key] is not None]
        b = sum(1 for r in both if r["main"] and not r[key])
        c = sum(1 for r in both if r[key] and not r["main"])
        print(f"  main against {name:16}: main only {b}, {name} only {c}, McNemar exact one-sided p {mcnemar(b, c):.4f}")
    print(f"  median final strays: main {median([r['strays'] for r in rows.values()])}, gate open "
          f"{median([r['open_strays'] for r in rows.values()])}, L0 {median([r['L0_strays'] for r in rows.values()])}")
    bad = [k for k, r in rows.items() if r["main"] and not r["ctl0"]]
    print(f"  control 0 fails in associated pairs: {bad or 'none'}")
    print("  associated pairs, main: " + ", ".join(f"s{s}p{p} ({r['strays']})" for (s, p), r in sorted(rows.items()) if r["main"]))
    print("  associated pairs, gate open: " + ", ".join(f"s{s}p{p} ({r['open_strays']})" for (s, p), r in sorted(rows.items()) if r["open"]))
    print("  associated pairs, L0: " + ", ".join(f"s{s}p{p} ({r['L0_strays']})" for (s, p), r in sorted(rows.items()) if r["L0"]))


if __name__ == "__main__":
    main()
