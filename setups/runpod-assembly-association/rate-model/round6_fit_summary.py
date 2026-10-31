"""
round6_fit_summary.py

Round 6 step 3, fit (round6-report.md, "Step 3"), and the checks after the review of 2026-10-31: model B's results
per pair against the spiking runs, for each model B result (round6_regime_precheck.py export, rows matched to the
spiking per-job result files by job name), one summary per job family (the name after the pair index). Per model B
result and family:

  * first transfer in the joint rounds (any class) and rollbacks (n, exhausted), both sides;
  * associations: a successful final test without a runaway and with at most 10 % of all groups active outside A,
    B and the route (34, 72, 133 at 7^3, 9^3, 11^3; --stray-frac), both sides counted with that limit; per pair,
    "best final strays" is the smaller stray count of the successful final tests;
  * the C2 stage: the step at which the runaway stop ended each C2 round, and the consolidated share of w_fast on and
    off the route (w_perm change over w_fast after the joint rounds, synapses onto excitatory neurons; the review's
    0.26 and 0.08), where both sides recorded them.

  python round6_fit_summary.py --spiking DIR [DIR ...] --model LABEL=FILE[=DIR,DIR] [...] [--out R.json]
  (a model's own spiking directories after a second "=", none if empty, else those of --spiking)

Standard library only.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re

STRAY_FRAC = 0.1


def _size(name: str) -> int:
    m = re.search(r"-g(\d+)(?=[-.]|$)", name)
    return int(m.group(1)) if m else 7


def _limit(size: int, frac: float) -> int:
    return int(frac * size ** 3)                                 # Spec.stray_limit


def _median(v: list):
    v = sorted(x for x in v if x is not None)
    return v[len(v) // 2] if v else None


def _share(fast: dict, perm: dict, band: str):
    f = fast["split"][band]["post_exc"] if "split" in fast else fast[band]
    p = perm["split"][band]["post_exc"] if "split" in perm else perm[band]
    return p / f if f else None


def spiking(dirs: list, frac: float) -> dict:
    """{job name: record} from the per-job result files (assoc_protocol substep4 output, block "main")."""
    out = {}
    for d in dirs:
        for f in glob.glob(os.path.join(d, "*.json")):
            if f.endswith(".summary.json"):
                continue
            j = json.load(open(f))
            b = j.get("main") if isinstance(j.get("main"), dict) else (
                j if "c1_rounds" in j else next((v for v in j.values() if isinstance(v, dict) and "c1_rounds" in v), None))
            if b is None:
                continue
            name = os.path.basename(f)[:-5]
            lim = _limit(_size(name), frac)
            fin = b.get("final")
            ok = [x for x in ("A_to_B", "B_to_A") if fin and fin[x]["success"]]
            rec = {"transfer": bool(b.get("c1_test_passed")), "c1_rounds": b.get("c1_rounds"), "rollback": b.get("rollback"),
                   "association": any(fin[x]["runaway"] is None and fin[x]["n_active_outside"] <= lim for x in ok),
                   "best": min(fin[x]["n_active_outside"] for x in ok) if ok else None,
                   "c2_stops": [(e.get("runaway") or {}).get("step") for e in b.get("c2_log") or []] or None}
            if b.get("c2_log") and b.get("w_fast_after_c1", {}).get("split") and b.get("w_perm_change", {}).get("split"):
                rec["share_route"] = _share(b["w_fast_after_c1"], b["w_perm_change"], "on_line")
                rec["share_off_route"] = _share(b["w_fast_after_c1"], b["w_perm_change"], "off_line")
            out[name] = rec
    return out


def model_record(r: dict, frac: float) -> dict:
    lim = _limit(_size(r["job"]), frac)
    fin = r.get("final")
    ok = [x for x in ("A_to_B", "B_to_A") if fin and fin[x]["success"]]
    c = r.get("consolidated") or {}
    return {"transfer": r["class"] != "none", "class": r["class"], "c1_rounds": r.get("c1_rounds"), "rollback": r.get("rollback"),
            "association": any(not fin[x].get("runaway", False) and fin[x]["strays"] <= lim for x in ok),
            "best": min(fin[x]["strays"] for x in ok) if ok else None, "c2_stops": r.get("c2_stops"),
            "share_route": c.get("share_route"), "share_off_route": c.get("share_off_route")}


def family(name: str) -> str:
    """The job family: the name after the pair index (proto, U12, E0, L1a-s3b, L0rb-s3b-g9, ...)."""
    m = re.search(r"-pair\d+-(.+)$", name)
    return m.group(1) if m else ""


def summarize(label: str, rows: list, sp: dict, frac: float) -> dict:
    size = _size(rows[0]["job"])
    pairs, diffs = {}, []
    for r in rows:
        m = model_record(r, frac)
        s = sp.get(r["job"])
        pairs[r["job"]] = {"model": m, "spiking": s}
        if s is not None and m["best"] is not None and s["best"] is not None:
            diffs.append(m["best"] - s["best"])
    keys = sorted(pairs)
    both = [k for k in keys if pairs[k]["spiking"] is not None]
    side = lambda who, f: [pairs[k][who][f] for k in both if pairs[k][who] is not None]
    count = lambda who, f: sum(bool(x) for x in side(who, f))
    rb = lambda who: [x for x in side(who, "rollback") if x]
    res = {"label": label, "size": size, "stray_limit": _limit(size, frac), "pairs": len(keys), "pairs_with_spiking": len(both),
           "model": {"transfers": sum(pairs[k]["model"]["transfer"] for k in keys),
                     "associations": sum(pairs[k]["model"]["association"] for k in keys),
                     "rollbacks": sum(x["n"] for x in (pairs[k]["model"]["rollback"] for k in keys) if x),
                     "rollback_exhausted": sum(bool(x and x["exhausted"]) for x in (pairs[k]["model"]["rollback"] for k in keys)),
                     "median_c1_rounds": _median([pairs[k]["model"]["c1_rounds"] for k in keys])}}
    if both:
        diffs.sort()
        res["spiking"] = {"transfers": count("spiking", "transfer"), "associations": count("spiking", "association"),
                          "rollbacks": sum(x["n"] for x in rb("spiking")),
                          "rollback_exhausted": sum(bool(x["exhausted"]) for x in rb("spiking")),
                          "median_c1_rounds": _median(side("spiking", "c1_rounds"))}
        res["model_on_spiking_pairs"] = {"transfers": count("model", "transfer"), "associations": count("model", "association")}
        res["association_agreement"] = sum(pairs[k]["spiking"]["association"] == pairs[k]["model"]["association"]
                                           for k in both) / len(both)
        res["transfer_agreement"] = sum(pairs[k]["spiking"]["transfer"] == pairs[k]["model"]["transfer"] for k in both) / len(both)
        res["best_final_strays_model_minus_spiking"] = {"n": len(diffs), "median": diffs[len(diffs) // 2] if diffs else None,
                                                        "min": diffs[0] if diffs else None, "max": diffs[-1] if diffs else None}
        first = lambda who: [pairs[k][who]["c2_stops"][0] for k in both if pairs[k][who]["c2_stops"]]
        res["first_c2_round_stop_step"] = {"model_median": _median(first("model")), "spiking_median": _median(first("spiking")),
                                           "model_stopped": sum(x is not None for x in first("model")),
                                           "spiking_stopped": sum(x is not None for x in first("spiking"))}
    for f in ("share_route", "share_off_route"):
        res.setdefault("consolidated_share_median", {})[f] = {
            "model": _median([pairs[k]["model"][f] for k in keys]),
            "spiking": _median([pairs[k]["spiking"][f] for k in both if pairs[k]["spiking"].get(f) is not None])}
    res["per_pair"] = pairs
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--spiking", nargs="*", default=[])
    ap.add_argument("--model", nargs="+", required=True)
    ap.add_argument("--stray-frac", type=float, default=STRAY_FRAC)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    common = spiking(a.spiking, a.stray_frac)
    res = []
    for m in a.model:
        parts = m.split("=")
        label, path = parts[0], parts[1]
        sp = spiking([d for d in parts[2].split(",") if d], a.stray_frac) if len(parts) > 2 else common
        groups = {}
        for row in json.load(open(path))["rows"]:
            groups.setdefault(family(row["job"]), []).append(row)
        for fam, rows in sorted(groups.items()):
            r = summarize(f"{label}/{fam}" if len(groups) > 1 else label, rows, sp, a.stray_frac)
            res.append(r)
            print(json.dumps({k: v for k, v in r.items() if k != "per_pair"}))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
