"""
sparse_route_selectivity.py

Sparse task, pass criterion 3: route selectivity `R_off` of the associated pairs, standard library only; run it where
the results are. Per pair whose final test associates (a direction with B >= 0.5 and bounded), R_off = the mean
permanent change per plastic E -> E synapse in the off-route shell Sh over the same in the route middle M (the run's
`sel_w_perm_change`; synapses by their midpoint, onto excitatory neurons of either kind, so not only onto ordinary
neurons as the criterion states). 1 is an even spread, 0 the route only; the target is a median <= 0.25.

  python sparse_route_selectivity.py OUTPUT_DIR "SESSION_GLOB" [...]
"""

from __future__ import annotations

import glob
import json
import os
import sys


def median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else 0.5 * (xs[m - 1] + xs[m])


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = argv[0]
    rows = []
    for pattern in argv[1:]:
        for path in sorted(glob.glob(os.path.join(root, pattern, "s4-*.json"))):
            if path.endswith(".summary.json"):
                continue
            r = json.load(open(path))
            if "error" in r:
                continue
            m = r["main"]
            fin = m["final"]
            if not any(fin[d]["success"] and fin[d]["bounded"] for d in ("A_to_B", "B_to_A")):
                continue
            sel = m.get("sel_w_perm_change") or {}
            dm, ds = (sel.get("M") or {}).get("dw_ee"), (sel.get("Sh") or {}).get("dw_ee")
            rows.append((os.path.basename(path)[:-5], dm, ds, ds / dm if (dm and ds is not None) else None))
    for name, dm, ds, r in rows:
        print(f"  {name:40} dw_ee M {dm:.4f}  Sh {ds:.4f}  R_off {r:.3f}" if r is not None else f"  {name:40} R_off -")
    vals = [r for *_, r in rows if r is not None]
    print(f"associated pairs {len(rows)}, median R_off {median(vals)}, above 0.5 (unselective): {sum(v > 0.5 for v in vals)}")


if __name__ == "__main__":
    main()
