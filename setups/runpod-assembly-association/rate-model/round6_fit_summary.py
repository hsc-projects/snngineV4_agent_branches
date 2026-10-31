"""
round6_fit_summary.py

Round 6 step 3, fit (round6-report.md, "Step 3"): model B's final strays and associations per pair against the
spiking runs, for each model B result (round6_regime_precheck.py export --c2, rows with "final"). Spiking side:
the per-job result files of the rerun (assoc_protocol output, "final" per direction). Per pair, "best final strays"
is the smaller stray count of the successful final tests; an association needs a successful final test with at
most 34 strays.

  python round6_fit_summary.py --spiking DIR [DIR ...] --model LABEL=FILE [LABEL=FILE ...] [--out R.json]

Standard library only.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re

STRAY_LIMIT = 34


def _key(name: str) -> str:
    m = re.search(r"-s(\d+)-pair(\d+)-", name)
    return f"s{m.group(1)}p{m.group(2)}"


def _size(name: str) -> int:
    m = re.search(r"-g(\d+)-", name)
    return int(m.group(1)) if m else 7


def _best(final: dict, field: str):
    v = [final[d][field] for d in ("A_to_B", "B_to_A") if final[d]["success"]]
    return min(v) if v else None


def spiking(dirs: list) -> dict:
    """{grid size: {pair key: {"best", "association"}}} from the per-job result files."""
    out = {}
    for d in dirs:
        for f in glob.glob(os.path.join(d, "*.json")):
            if f.endswith(".summary.json"):
                continue
            j = json.load(open(f))
            b = j if "final" in j else next((v for v in j.values() if isinstance(v, dict) and "final" in v), None)
            if b is None:
                continue
            size = _size(os.path.basename(f))
            fin = b["final"]
            assoc = any(fin[x]["success"] and fin[x]["n_active_outside"] <= STRAY_LIMIT for x in ("A_to_B", "B_to_A"))
            out.setdefault(size, {})[_key(os.path.basename(f))] = {"best": _best(fin, "n_active_outside"),
                                                                   "association": assoc}
    return out


def summarize(label: str, path: str, sp: dict) -> dict:
    rows = json.load(open(path))["rows"]
    size = _size(rows[0]["job"])
    ref = sp[size]
    pairs, diffs = {}, []
    for r in rows:
        k = _key(r["job"])
        mb = None if r.get("final") is None else _best(r["final"], "strays")
        pairs[k] = {"spiking": ref[k], "model": {"best": mb, "association": bool(r.get("association"))}}
        if mb is not None and ref[k]["best"] is not None:
            diffs.append(mb - ref[k]["best"])
    diffs.sort()
    keys = sorted(pairs)
    agree = sum(pairs[k]["spiking"]["association"] == pairs[k]["model"]["association"] for k in keys)
    return {"label": label, "size": size, "pairs": len(keys),
            "associations_spiking": sum(pairs[k]["spiking"]["association"] for k in keys),
            "associations_model": sum(pairs[k]["model"]["association"] for k in keys),
            "association_agreement": agree / len(keys),
            "best_final_strays_model_minus_spiking": {"n": len(diffs), "median": diffs[len(diffs) // 2] if diffs else None,
                                                      "min": diffs[0] if diffs else None, "max": diffs[-1] if diffs else None},
            "per_pair": pairs}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--spiking", nargs="+", required=True)
    ap.add_argument("--model", nargs="+", required=True)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    sp = spiking(a.spiking)
    res = []
    for m in a.model:
        label, path = m.split("=", 1)
        r = summarize(label, path, sp)
        res.append(r)
        d = r["best_final_strays_model_minus_spiking"]
        print(f"{label}: {r['size']}^3, {r['pairs']} pairs; associations spiking {r['associations_spiking']}, model "
              f"{r['associations_model']} (agreement {r['association_agreement']:.2f}); best final strays model minus "
              f"spiking median {d['median']} ({d['min']} to {d['max']}, {d['n']} pairs)")
    if a.out:
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
