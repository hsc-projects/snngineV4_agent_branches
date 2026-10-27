#!/usr/bin/env python3
"""
Host-side summary of the path-selectivity telemetry (iteration 43), standard library only.

  python assoc_selectivity.py <session dir>...
  python assoc_selectivity.py --prop <session dir>...    (prop_survey jobs)
  python assoc_selectivity.py --bridge <session dir>...  (prop_survey jobs with bridges)

One line per variant (session): runs, passes, ignitions (runaway during C1), C1-phase tests
passed, and medians over the pairs of the M / Sh ratios (middle of the path against the
off-path shell at the same distance from A and B; > 1 means the path is preferred):
spikes per excitatory neuron and C1 gate at the end of injection (last C1 round), w_fast
per synapse after the C1 rounds (onto E and onto I), and the final strict transfer.
"""

from __future__ import annotations

import glob
import json
import os
import statistics
import sys


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def fmt(x, w=6):
    return f"{x:{w}.2f}" if isinstance(x, (int, float)) else f"{'-':>{w}}"


def summarize(d):
    rows = []
    for f in sorted(glob.glob(os.path.join(d, "s4-*.json"))):
        if f.endswith(".summary.json"):
            continue
        r = json.load(open(f))
        if "error" in r:
            rows.append({"error": r["error"].strip().splitlines()[-1]})
            continue
        m = r["main"]
        log = [e for e in m["c1_log"] if e.get("sel_inject_end")]
        last = log[-1]["sel_inject_end"] if log else None
        fin = m["final"]
        best = max(fin.values(), key=lambda t: (t["contained"], t["dst_max"]))
        rows.append({
            "pass": r["pass"], "ignite": m["runaway_round"] is not None, "c1_ok": m["c1_test_passed"],
            "rounds": m["c1_rounds"], "final": best["dst_max"], "others": best["others_max"],
            "spk": last["ratio"]["spikes_per_exc"] if last else None,
            "g1": last["ratio"]["g1"] if last else None,
            "g1_M": last["M"]["g1"] if last else None, "g1_Sh": last["Sh"]["g1"] if last else None,
            "wf_ee": m["sel_w_fast_after_c1"]["ratio"]["dw_ee"], "wf_ei": m["sel_w_fast_after_c1"]["ratio"]["dw_ei"],
            "wp_ee": m["sel_w_perm_change"]["ratio"]["dw_ee"],
        })
    return rows


def prop(dirs):
    """One line per prop_survey job (iteration 45): medians over its pairs."""
    keys = ("M_joint", "M_A_plus_B", "Sh_joint", "convergence", "selectivity", "path_mean_of_max_joint",
            "others_max_joint", "others_max_single", "assembly_max_single")
    print(f"{'job':44} {'run':>3} " + " ".join(f"{k[:9]:>9}" for k in keys))
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, "prop-*.json"))):
            if f.endswith(".summary.json"):
                continue
            r = json.load(open(f))
            if "error" in r:
                print(os.path.basename(f)[:-5], "ERROR", r["error"].strip().splitlines()[-1])
                continue
            s = r["summary"]
            print(f"{os.path.basename(f)[:-5]:44} {s['runaway_pairs']:3d} " + " ".join(fmt(s[k], 9) for k in keys))


def prop_classes(dirs, m_min=0.2, inactive=0.1):
    """
    Per prop_survey job, the pairs counted by kind: good = the path fires under joint injection
    (M >= m_min spikes per excitatory neuron), nothing beyond A, B and the path in any condition,
    more than both single injections together (super) and than the shell (sel); silent = M < 0.05
    under joint injection; explosive = any condition spreads beyond the path or runs away.
    """
    print(f"{'job':40} {'n':>2} {'good':>4} {'super':>5} {'sel':>3} {'silent':>6} {'expl':>4}  good pairs")
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, "prop-*.json"))):
            if f.endswith(".summary.json"):
                continue
            r = json.load(open(f))
            if "error" in r:
                continue
            good, sup, sel, silent, expl = [], 0, 0, 0, 0
            for i, p in enumerate(r["pairs"]):
                j, a, b = p["joint"], p["A"], p["B"]
                # with a "none" condition (background input), counts are taken above that baseline
                n = p.get("none", {"M": 0.0, "Sh": 0.0, "others_max": 0.0})
                m0, s0, o0 = n["M"] or 0.0, n["Sh"] or 0.0, n["others_max"]
                spread = any(c["others_max"] - o0 > inactive or c["runaway"] for c in (j, a, b))
                m = (j["M"] or 0.0) - m0
                if spread:
                    expl += 1
                elif m < 0.05:
                    silent += 1
                elif m >= m_min:
                    good.append(i)
                    sup += m > (a["M"] or 0.0) + (b["M"] or 0.0) - 2 * m0
                    sel += m > (j["Sh"] or 0.0) - s0
            print(f"{os.path.basename(f)[:-5]:40} {len(r['pairs']):2d} {len(good):4d} {sup:5d} {sel:3d} {silent:6d} "
                  f"{expl:4d}  {good}")


def bridge_classes(dirs, active=0.5, inactive=0.1):
    """
    Per prop_survey job with bridges (iteration 51), the pairs counted by how the bridge responds:
    AND = active under joint injection, inactive (<= inactive) under A alone and B alone; weak AND =
    active under joint, below active but above inactive under one alone; one-sided = active under A
    or B alone; silent = below active under joint; spread = any condition activates a group outside
    A, B and the path (bridges included in the path) or runs away. Medians of the bridge maxima.
    """
    print(f"{'job':40} {'n':>2} {'AND':>3} {'weak':>4} {'1side':>5} {'sil':>3} {'spr':>3} "
          f"{'br_j':>5} {'br_A':>5} {'br_B':>5} {'A_sgl':>5}  AND pairs")
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, "prop-*.json"))):
            if f.endswith(".summary.json"):
                continue
            r = json.load(open(f))
            if "error" in r:
                print(os.path.basename(f)[:-5], "ERROR", r["error"].strip().splitlines()[-1])
                continue
            n_and, weak, one, sil, spr = [], 0, 0, 0, 0
            for i, p in enumerate(r["pairs"]):
                j, a, b = p["joint"], p["A"], p["B"]
                if j.get("bridge_max") is None:
                    continue
                single = max(a["bridge_max"], b["bridge_max"])
                if any(c["others_max"] > inactive or c["runaway"] for c in (j, a, b)):
                    spr += 1
                elif single >= active:
                    one += 1
                elif j["bridge_max"] < active:
                    sil += 1
                elif single <= inactive:
                    n_and.append(i)
                else:
                    weak += 1
            ps = r["pairs"]
            print(f"{os.path.basename(f)[:-5]:40} {len(ps):2d} {len(n_and):3d} {weak:4d} {one:5d} {sil:3d} {spr:3d} "
                  f"{fmt(med([p['joint'].get('bridge_max') for p in ps]), 5)} "
                  f"{fmt(med([p['A'].get('bridge_max') for p in ps]), 5)} "
                  f"{fmt(med([p['B'].get('bridge_max') for p in ps]), 5)} "
                  f"{fmt(r['summary']['assembly_max_single'], 5)}  {n_and}")


def input_jobs(dirs):
    """One block per input_survey job (iteration 47): medians over pairs."""
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, "input-*.json"))):
            if f.endswith(".summary.json"):
                continue
            r = json.load(open(f))
            if "error" in r:
                print(os.path.basename(f)[:-5], "ERROR", r["error"].strip().splitlines()[-1])
                continue
            s = r["summary"]
            line = lambda k: " ".join(f"{q}={fmt(s[k][q], 7)}" for q in ("I_A", "I_B", "I_joint", "coinc", "spikes_joint"))
            print(f"{os.path.basename(f)[:-5]}  coinc M/Sh {fmt(s['coinc_ratio_M_Sh'])}")
            print(f"   M : {line('M')}")
            print(f"   Sh: {line('Sh')}")
            print("   profile t -0.5..1.5, coinc:", " ".join(fmt(x, 6) for x in s["profile_coinc"]))
            print("   profile t -0.5..1.5, I_A  :", " ".join(fmt(x, 6) for x in s["profile_I_A"]))


def main():
    if sys.argv[1] == "--input":
        return input_jobs(sys.argv[2:])
    if sys.argv[1] == "--prop":
        return prop(sys.argv[2:])
    if sys.argv[1] == "--propclass":
        return prop_classes(sys.argv[2:])
    if sys.argv[1] == "--bridge":
        return bridge_classes(sys.argv[2:])
    print(f"{'session':34} {'n':>2} {'pass':>4} {'ign':>3} {'c1ok':>4} {'rnds':>5} {'final':>6} {'other':>6} "
          f"{'spkM/S':>6} {'g1M/S':>6} {'g1 M':>6} {'g1 Sh':>6} {'wfEE':>6} {'wfEI':>6} {'wpEE':>6}")
    for d in sys.argv[1:]:
        rows = summarize(d)
        ok = [r for r in rows if "error" not in r]
        errs = len(rows) - len(ok)
        print(f"{os.path.basename(d.rstrip('/')):34} {len(ok):2d} {sum(r['pass'] for r in ok):4d} "
              f"{sum(r['ignite'] for r in ok):3d} {sum(r['c1_ok'] for r in ok):4d} "
              f"{fmt(med([r['rounds'] for r in ok]), 5)} {fmt(med([r['final'] for r in ok]))} "
              f"{fmt(med([r['others'] for r in ok]))} "
              + " ".join(fmt(med([r[k] for r in ok])) for k in ("spk", "g1", "g1_M", "g1_Sh", "wf_ee", "wf_ei", "wp_ee"))
              + (f"  ({errs} errors)" if errs else ""))


if __name__ == "__main__":
    main()
