"""
round6_admission_compare.py

Round 6 (rate-model-task.md), admission on the engine-fix rerun's networks: model B against the spiking runs, pair by
pair. Model B ran on exports of the rerun's own networks with the engine's injected neurons
(round6_regime_precheck.py export), so each pair is the same network, pair and stimulus in both.

Spiking side: the rerun's sweep summaries (assoc_sweep_summary.py output, e.g. output/rerun5-summary.txt,
output/rerun67-summary.txt), one per-pair line "sXpY:rN STRAYS->RESULT" or "sXpY:none" and the list of
associated pairs. First-transfer class: none, contained (strays <= 34) or ignition.

  python round6_admission_compare.py --out R.json COMPARISON [COMPARISON ...]
  COMPARISON = label:summary_file:section:config:model_json   (section: text after "### sweep ")

Standard library only.
"""

from __future__ import annotations

import argparse
import ast
import json
import re

CLASSES = ("contained", "ignition", "none")
STRAY_LIMIT = 34


def spiking_pairs(path: str, section: str, config: str) -> dict:
    """{pair key: {"class", "association"}} from one section and config of a sweep summary."""
    lines = open(path, encoding="utf-8").read().splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("### ") and section in l)
    assoc, per_pair = None, None
    for l in lines[start + 1:]:
        if l.startswith("### "):
            break
        if not l.startswith(config + " "):
            continue
        if "[" in l and assoc is None:
            assoc = set(ast.literal_eval(l[l.index("["):]))
        elif re.search(r"s\d+p\d+:", l) and per_pair is None:
            per_pair = re.findall(r"(s\d+p\d+):(none|r\d+ (\d+)->(\S+))", l)
    out = {}
    for key, whole, strays, _ in per_pair:
        cls = "none" if whole == "none" else ("contained" if int(strays) <= STRAY_LIMIT else "ignition")
        out[key] = {"class": cls, "association": key in assoc}
    return out


def model_pairs(path: str) -> dict:
    d = json.load(open(path))
    out = {}
    for r in d["rows"]:
        if "job" in r:
            m = re.search(r"-s(\d+)-pair(\d+)-", r["job"])
            key = f"s{m.group(1)}p{m.group(2)}"
        else:   # rows written before the job name was recorded: the exported jobs are pairs 0 to 11 in order
            key = f"s{re.search(r'-s(\d+)$', r['source']).group(1)}p{r['pair_index']}"
        out[key] = {"class": r["class"], "association": r.get("association")}
    return out


def kappa(pairs: list, labels: tuple) -> dict:
    n = len(pairs)
    conf = [[sum(1 for a, b in pairs if a == x and b == y) for y in labels] for x in labels]
    p_o = sum(conf[i][i] for i in range(len(labels))) / n
    rows = [sum(r) for r in conf]
    cols = [sum(conf[i][j] for i in range(len(labels))) for j in range(len(labels))]
    p_e = sum(r * c for r, c in zip(rows, cols)) / (n * n)
    k = 1.0 if abs(p_e - 1.0) < 1e-12 else (p_o - p_e) / (1.0 - p_e)
    return {"n": n, "agreement": p_o, "kappa": k, "labels": list(labels), "confusion_rows_spiking_cols_model": conf}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("comparisons", nargs="+")
    a = ap.parse_args(argv)
    res = []
    for c in a.comparisons:
        label, summ, section, config, model = c.split(":")
        sp, mo = spiking_pairs(summ, section, config), model_pairs(model)
        keys = sorted(set(sp) & set(mo))
        row = {"label": label, "pairs": len(keys), "missing_in_model": sorted(set(sp) - set(mo)),
               "class": kappa([(sp[k]["class"], mo[k]["class"]) for k in keys], CLASSES),
               "counts_spiking": {x: sum(1 for k in keys if sp[k]["class"] == x) for x in CLASSES},
               "counts_model": {x: sum(1 for k in keys if mo[k]["class"] == x) for x in CLASSES}}
        if all(mo[k]["association"] is not None for k in keys):
            row["association"] = kappa([(sp[k]["association"], bool(mo[k]["association"])) for k in keys], (True, False))
            row["associations_spiking"] = sum(1 for k in keys if sp[k]["association"])
            row["associations_model"] = sum(1 for k in keys if mo[k]["association"])
        row["per_pair"] = {k: {"spiking": sp[k], "model": mo[k]} for k in keys}
        res.append(row)
        msg = (f"{label}: {len(keys)} pairs; class agreement {row['class']['agreement']:.2f}, kappa "
               f"{row['class']['kappa']:.2f}; spiking {row['counts_spiking']}, model {row['counts_model']}")
        if "association" in row:
            msg += (f"; associations spiking {row['associations_spiking']}, model {row['associations_model']}, "
                    f"agreement {row['association']['agreement']:.2f}, kappa {row['association']['kappa']:.2f}")
        print(msg)
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
