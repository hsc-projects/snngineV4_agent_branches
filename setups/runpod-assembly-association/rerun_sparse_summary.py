"""
rerun_sparse_summary.py

Step 7 of engine-fix-rerun-task.md (sparse substrate SP1 to SP3), standard library only; run it where the
results are (a pod: the sessions write about 100 jobs each). One line per setting (job name without its type),
in the columns of the archived sparse report's Substep 2 table (archive-pre-engine-fix/sparse-tuning-log.md,
entry 4):

  python rerun_sparse_summary.py OUTPUT_DIR [SESSION_GLOB, default rerun7*]

M / Sh: spikes per excitatory neuron per round in the route middle and in the off-route shell (prop_survey
medians over pairs; joint injection, and A alone + B alone); E and Inh: excitatory and inhibitory input per step
to the excitatory neurons of M (input_survey: under joint injection, and E under A alone), and their ratio;
off-route assemblies and runaways under joint injection; the hysteresis loop (largest rate difference of
ordinary excitatory neurons, down minus up, at equal background current).
"""

from __future__ import annotations

import glob
import json
import os
import sys
from collections import defaultdict

TYPES = ("prop_survey", "input_survey", "hysteresis")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root, pattern = argv[0], (argv[1] if len(argv) > 1 else "rerun7*")
    rows = defaultdict(dict)
    for path in sorted(glob.glob(os.path.join(root, pattern, "*.json"))):
        base = os.path.basename(path)[:-5]
        if base.endswith(".summary") or base.startswith("summary"):   # the queue's session summaries
            continue
        typ = next((t for t in TYPES if base.endswith("-" + t)), None)
        if typ is None:
            continue
        setting = base[: -len(typ) - 1]
        r = json.load(open(path))
        if "error" in r:
            rows[setting][typ] = {"error": str(r["error"]).strip().splitlines()[-1][:80]}
            continue
        if typ != "hysteresis" and "summary" not in r:
            rows[setting][typ] = {"error": "no summary; keys " + ",".join(sorted(r))[:60]}
            continue
        if typ == "prop_survey":
            s = r["summary"]
            rows[setting][typ] = {"M_joint": s.get("M_joint"), "M_A_plus_B": s.get("M_A_plus_B"),
                                  "Sh_joint": s.get("Sh_joint"), "off_asm": max((p["joint"].get("off_asm_max") or 0.0)
                                                                              for p in r["pairs"]),
                                  "runaway_pairs": s.get("runaway_pairs")}
        elif typ == "input_survey":
            m = r["summary"]["M"]
            e, i = m.get("E_joint"), m.get("Inh_joint")
            rows[setting][typ] = {"E_joint": e, "E_A": m.get("E_A"), "Inh_joint": i,
                                  "inh_over_exc": (abs(i) / e) if (e and i is not None) else None}
        else:
            rows[setting][typ] = {"loop_max": r.get("loop_max"),
                                  "runaway": any(x.get("runaway") for x in r.get("levels", []))}
    f = lambda x, p=3: "-" if x is None else (f"{x:.{p}f}" if isinstance(x, float) else str(x))
    print(f"{'setting':34} {'M joint':>8} {'M A+B':>7} {'Sh joint':>8} {'E M joint/A':>13} {'Inh M joint':>11} "
          f"{'Inh/E':>7} {'off-asm':>7} {'runaw':>5} {'loop max':>8}")
    for setting in sorted(rows):
        p, i, h = (rows[setting].get(t, {}) for t in TYPES)
        err = "; ".join(f"{t}: {rows[setting][t]['error']}" for t in TYPES if "error" in rows[setting].get(t, {}))
        print(f"{setting:34} {f(p.get('M_joint')):>8} {f(p.get('M_A_plus_B')):>7} {f(p.get('Sh_joint')):>8} "
              f"{f(i.get('E_joint'), 2) + ' / ' + f(i.get('E_A'), 2):>13} {f(i.get('Inh_joint'), 1):>11} "
              f"{f(i.get('inh_over_exc'), 0):>7} {f(p.get('off_asm'), 2):>7} {f(p.get('runaway_pairs')):>5} "
              f"{f(h.get('loop_max')):>8}" + (" runaway" if h.get("runaway") else "") + (f"  ERROR {err}" if err else ""))


if __name__ == "__main__":
    main()
