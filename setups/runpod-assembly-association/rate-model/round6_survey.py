"""
round6_survey.py

Round 6 step 4 (rate-model-task.md): model B's propagation and input surveys without learning
(assoc_protocol.prop_survey, input_survey) on the sparse substrate, on networks exported with
round6_export_engine.py --survey. The export holds the surveys' pairs, injected neurons, path groups, bridges,
off-route assemblies and the regions M and Sh from the engine's own geometry, so model B runs the same pairs and
stimuli. Without background input (S3b) model B should reproduce the engine's spike counts per pair and
condition, as round 6 step 2 did for the A-alone test.

  python round6_survey.py run --exports DIR [DIR ...] --out OUTDIR [--set k=v ...] [--workers N]
      one JSON per survey job in OUTDIR, named and laid out like the spiking job's result, so the spiking
      summaries (e.g. ../rerun_s3b_decision.py OUTDIR "*") read them unchanged
  python round6_survey.py compare --spiking DIR [DIR ...] --model DIR [--out R.json]
      pair by pair: spikes per condition (equal or not), M, Sh, convergence and selectivity (standard library)
  python round6_survey.py replay --exports DIR [DIR ...] --model DIR [--out R.json]
      against the engine's own run of the conditions on the exported weights (export --survey --replay)

`run` needs numpy; `compare` the standard library only.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

THRESHOLDS = (0.5, 1.0, 2.0, 4.0)


def _mean(x):
    return float(x.mean()) if x.size else None


def _ratio(m, s):
    return m / s if (m is not None and s is not None and s > 0) else None


def _median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return float(xs[n // 2]) if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])


def _network(d: str, over: dict):
    from round6_compare import spec_for
    from spiking_group_model import SpikingNetwork
    meta = json.loads(open(os.path.join(d, "meta.json")).read())
    net = SpikingNetwork(spec_for(meta, export_dir=d, **over), seed=int(meta["seed"]))
    return meta, net


def _prepare(net, pr: dict):
    """Model groups of the pair and its path, bridges and off-route assemblies; the engine's injected neurons."""
    import numpy as np
    e2m = net.engine_to_model
    A, B = int(e2m[pr["A"]]), int(e2m[pr["B"]])
    net.set_injection(A, np.asarray(pr["inject"][str(pr["A"])]))
    net.set_injection(B, np.asarray(pr["inject"][str(pr["B"])]))
    return A, B, [int(e2m[g]) for g in pr["path"]], [int(e2m[g]) for g in pr["bridges"]], [int(e2m[g]) for g in pr["off_asm"]]


def prop_pair(net, pr: dict, m_mask, s_mask) -> dict:
    """assoc_protocol.prop_survey for one pair: joint, A, B and no injection, one round each, chemistry off."""
    import numpy as np
    s = net.spec
    A, B, path, bridges, off_asm = _prepare(net, pr)
    rnd = s.inject_steps + s.gap_steps
    ne_m, ne_s = m_mask & net.isE, s_mask & net.isE
    out = (net.grp != A) & (net.grp != B)
    out_e, out_i = out & net.isE, out & ~net.isE
    others = np.ones(net.G, dtype=bool)
    others[[A, B] + path] = False
    row = {"pair": [pr["A"], pr["B"], pr["C"]], "dist": pr["dist"], "n_path": len(pr["path"]), "bridges": pr["bridges"]}
    net.spike_acc = np.zeros(net.N, dtype=np.float64)
    for cond, inj in (("joint", (A, B)), ("A", (A,)), ("B", (B,)), ("none", ())):
        net.reset_dynamics()
        net.spike_acc[:] = 0.0
        res = net.run(rnd, inject=[net.inject_idx(g) for g in inj], inject_steps=s.inject_steps, chem=False)
        gm = res["gmax"]
        pm = gm[path] if path else np.zeros(1)
        row[cond] = {"M": float(net.spike_acc[ne_m].sum()) / max(1, int(ne_m.sum())),
                     "Sh": float(net.spike_acc[ne_s].sum()) / max(1, int(ne_s.sum())),
                     "A_max": float(gm[A]), "B_max": float(gm[B]), "path_max": float(pm.max()),
                     "path_mean_of_max": float(pm.mean()), "others_max": float(gm[others].max()) if others.any() else 0.0,
                     "spikes": int(res["spikes"]), "runaway": res["stopped"] is not None,
                     "bridge_max": float(gm[bridges].max()) if bridges else None,
                     "off_asm_max": float(gm[off_asm].max()) if off_asm else None,
                     "exc_out": _mean(net.spike_acc[out_e]), "inh_out": _mean(net.spike_acc[out_i])}
    net.spike_acc = None
    j, sa, sb = row["joint"], row["A"], row["B"]
    row["convergence"] = _ratio(j["M"], (sa["M"] or 0.0) + (sb["M"] or 0.0))
    row["selectivity"] = _ratio(j["M"], j["Sh"])
    return row


def input_pair(net, pr: dict, m_mask, s_mask, prof, edges, W) -> dict:
    """assoc_protocol.input_survey for one pair: A, B and joint injection, inject_steps steps each."""
    import numpy as np
    s = net.spec
    A, B, _, _, _ = _prepare(net, pr)
    n = int(s.inject_steps)
    pre_e = np.repeat(net.isE, net.S)                     # presynaptic type of each flat synapse
    I, S = {}, {}
    net.capture_raw = True
    net.spike_acc = np.zeros(net.N, dtype=np.float64)
    net.input_acc = np.zeros(net.N, dtype=np.float64)
    for cond, inj in (("A", (A,)), ("B", (B,)), ("joint", (A, B))):
        net.reset_dynamics()
        net.spike_acc[:] = 0.0
        net.input_acc[:] = 0.0
        net.run(n, inject=[net.inject_idx(g) for g in inj], inject_steps=s.inject_steps, chem=False)
        I[cond] = net.input_acc / n
        S[cond] = net.spike_acc.copy()
        sp = np.repeat(S[cond], net.S)                    # spikes of each flat synapse's presynaptic neuron
        for kind, mask in (("E", pre_e), ("Inh", ~pre_e)):
            I[f"{kind}_{cond}"] = np.bincount(net.post_f, weights=np.where(mask, W * sp, 0.0), minlength=net.N) / n
    net.capture_raw, net.spike_acc, net.input_acc = False, None, None
    out_e = (net.grp != A) & (net.grp != B) & net.isE
    coinc = np.minimum(np.clip(I["A"], 0.0, None), np.clip(I["B"], 0.0, None))
    coinc_e = np.minimum(I["E_A"], I["E_B"])

    def stats(mask):
        m = mask & out_e
        if not m.any():
            return {"n": 0}
        return {"n": int(m.sum()), "I_A": _mean(I["A"][m]), "I_B": _mean(I["B"][m]), "I_joint": _mean(I["joint"][m]),
                "coinc": _mean(coinc[m]), "interaction": _mean((I["joint"] - I["A"] - I["B"])[m]),
                "E_A": _mean(I["E_A"][m]), "E_B": _mean(I["E_B"][m]), "E_joint": _mean(I["E_joint"][m]),
                "Inh_A": _mean(I["Inh_A"][m]), "Inh_joint": _mean(I["Inh_joint"][m]), "coinc_E": _mean(coinc_e[m]),
                "spikes_joint": _mean(S["joint"][m]), "spikes_A": _mean(S["A"][m]), "spikes_B": _mean(S["B"][m]),
                "frac_coinc_over": {str(th): _mean((coinc[m] > th).astype(np.float64)) for th in THRESHOLDS}}

    row = {"pair": [pr["A"], pr["B"], pr["C"]], "dist": pr["dist"], "M": stats(m_mask), "Sh": stats(s_mask),
           "profile": [dict(t=[lo, hi], **stats(prof == i)) for i, (lo, hi) in enumerate(zip(edges[:-1], edges[1:]))]}
    row["coinc_ratio_M_Sh"] = _ratio(row["M"].get("coinc"), row["Sh"].get("coinc"))
    return row


def prop_summary(rows: list) -> dict:
    return {"M_joint": _median([r["joint"]["M"] for r in rows]),
            "M_A_plus_B": _median([(r["A"]["M"] or 0.0) + (r["B"]["M"] or 0.0) for r in rows]),
            "Sh_joint": _median([r["joint"]["Sh"] for r in rows]),
            "path_mean_of_max_joint": _median([r["joint"]["path_mean_of_max"] for r in rows]),
            "others_max_joint": _median([r["joint"]["others_max"] for r in rows]),
            "others_max_single": _median([max(r["A"]["others_max"], r["B"]["others_max"]) for r in rows]),
            "assembly_max_single": _median([min(r["A"]["A_max"], r["B"]["B_max"]) for r in rows]),
            "runaway_pairs": sum(any(r[k]["runaway"] for k in ("joint", "A", "B")) for r in rows),
            "exc_out_joint": _median([r["joint"]["exc_out"] for r in rows]),
            "inh_out_joint": _median([r["joint"]["inh_out"] for r in rows]),
            "convergence": _median([r["convergence"] for r in rows]),
            "selectivity": _median([r["selectivity"] for r in rows])}


def input_summary(rows: list, n_bins: int) -> dict:
    qs = ("I_A", "I_B", "I_joint", "coinc", "interaction", "spikes_joint", "E_A", "E_B", "E_joint", "Inh_A",
          "Inh_joint", "coinc_E")
    out = {k: {q: _median([rw[k].get(q) for rw in rows]) for q in qs} for k in ("M", "Sh")}
    out["coinc_E_ratio_M_Sh"] = _median([_ratio(rw["M"].get("coinc_E"), rw["Sh"].get("coinc_E")) for rw in rows])
    for key, q in (("profile_coinc_E", "coinc_E"), ("profile_E_A", "E_A"), ("profile_Inh_A", "Inh_A"),
                   ("profile_coinc", "coinc"), ("profile_I_A", "I_A")):
        out[key] = [_median([rw["profile"][i].get(q) for rw in rows]) for i in range(n_bins)]
    out["coinc_ratio_M_Sh"] = _median([rw["coinc_ratio_M_Sh"] for rw in rows])
    return out


def _pair_job(args):
    d, j, i, over = args
    import numpy as np
    t0 = time.perf_counter()
    meta, net = _network(d, over)
    job = meta["jobs"][j]
    z = np.load(os.path.join(d, f"survey_{job['job']}.npz"))
    pr = job["pairs"][i]
    if job["type"] == "prop_survey":
        row = prop_pair(net, pr, z["M"][i], z["Sh"][i])
    else:
        W = net.engine_weights(np.arange(net.N * net.S, dtype=np.int64), 1.0)
        row = input_pair(net, pr, z["M"][i], z["Sh"][i], z["profile"][i], job["profile_edges"], W)
    row["seconds"] = time.perf_counter() - t0
    return d, j, i, row


def cmd_run(a):
    from concurrent.futures import ProcessPoolExecutor
    from round5_diag_spiking import parse_set
    over = parse_set(a.set)
    tasks, metas = [], {}
    for d in a.exports:
        meta = json.loads(open(os.path.join(d, "meta.json")).read())
        metas[d] = meta
        tasks += [(d, j, i, over) for j, job in enumerate(meta["jobs"]) if job.get("survey")
                  for i in range(len(job["pairs"]))]
    rows = {}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for d, j, i, row in ex.map(_pair_job, tasks):
            rows.setdefault((d, j), {})[i] = row
    os.makedirs(a.out, exist_ok=True)
    for (d, j), byi in rows.items():
        job = metas[d]["jobs"][j]
        rs = [byi[i] for i in sorted(byi)]
        summ = prop_summary(rs) if job["type"] == "prop_survey" else input_summary(rs, len(job["profile_edges"]) - 1)
        res = {"pairs": rs, "summary": summ, "n_pairs": len(rs), "pass": True, "job": job["job"],
               "model": {"export": os.path.basename(d.rstrip("/")), "settings": over}}
        with open(os.path.join(a.out, f"{job['job']}.json"), "w") as f:
            json.dump(res, f, indent=1)
        print(f"{job['job']}: {len(rs)} pairs; {json.dumps(summ)[:400]}", flush=True)
    print(f"SURVEY DONE in {time.time() - t0:.0f} s")


PROP_KEYS = ("M", "Sh", "A_max", "B_max", "others_max", "exc_out", "inh_out")


def cmd_compare(a):
    def load(dirs):
        out = {}
        for d in dirs:
            for f in glob.glob(os.path.join(d, "*_survey.json")):
                r = json.load(open(f))
                j = r.get("job")                        # the spiking results hold the job's spec, model B its name
                out[(j.get("name") if isinstance(j, dict) else j) or os.path.basename(f)[:-5]] = r
        return out
    sp, mo = load(a.spiking), load([a.model])
    res = []
    for job in sorted(set(sp) & set(mo)):
        P, Q = sp[job]["pairs"], mo[job]["pairs"]
        key = lambda r: tuple(r["pair"])
        qi = {key(r): r for r in Q}
        pairs = [(p, qi[key(p)]) for p in P if key(p) in qi]
        row = {"job": job, "pairs": len(pairs), "missing": len(P) - len(pairs)}
        if job.endswith("prop_survey"):
            conds = ("joint", "A", "B", "none")
            row["spikes_equal"] = {c: sum(p[c]["spikes"] == q[c]["spikes"] for p, q in pairs) for c in conds}
            row["max_rel_spike_diff"] = max(abs(p[c]["spikes"] - q[c]["spikes"]) / max(1, p[c]["spikes"])
                                            for p, q in pairs for c in conds)
            row["summary"] = {k: (sp[job]["summary"].get(k), mo[job]["summary"].get(k)) for k in sp[job]["summary"]}
            for name, f in (("summation", lambda r: r["joint"]["M"] - (r["A"]["M"] + r["B"]["M"])),
                            ("selectivity", lambda r: r["joint"]["M"] - r["joint"]["Sh"])):
                row[f"{name}_sign_agreement"] = sum((f(p) > 0) == (f(q) > 0) and (f(p) < 0) == (f(q) < 0)
                                                    for p, q in pairs) / max(1, len(pairs))
        else:
            row["summary_M"] = {k: (sp[job]["summary"]["M"].get(k), mo[job]["summary"]["M"].get(k))
                                for k in sp[job]["summary"]["M"]}
            row["spikes_joint_M_equal"] = sum(p["M"].get("spikes_joint") == q["M"].get("spikes_joint") for p, q in pairs)
        res.append(row)
        print(json.dumps({k: v for k, v in row.items() if k not in ("summary", "summary_M")}))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1)


def cmd_replay(a):
    """Model B against the engine on the same exported weights (export --replay): spikes, M and Sh per condition."""
    res = []
    for d in a.exports:
        meta = json.loads(open(os.path.join(d, "meta.json")).read())
        for job in meta["jobs"]:
            if not job.get("survey") or "engine_replay" not in job["pairs"][0]:
                continue
            mo = json.load(open(os.path.join(a.model, f"{job['job']}.json")))
            q = {tuple(r["pair"]): r for r in mo["pairs"]}
            row = {"job": job["job"], "pairs": len(job["pairs"])}
            for c in ("joint", "A", "B"):
                pairs = [(pr["engine_replay"][c], q[(pr["A"], pr["B"], pr["C"])][c]) for pr in job["pairs"]]
                row[c] = {"spikes_equal": sum(e["spikes"] == m["spikes"] for e, m in pairs),
                          "max_rel_spike_diff": max(abs(e["spikes"] - m["spikes"]) / max(1, e["spikes"]) for e, m in pairs),
                          "M_equal": sum(abs(e["M"] - m["M"]) < 1e-9 for e, m in pairs)}
            res.append(row)
            print(json.dumps(row))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    rp = sub.add_parser("replay")
    rp.add_argument("--exports", nargs="+", required=True)
    rp.add_argument("--model", required=True)
    rp.add_argument("--out")
    rp.set_defaults(fn=cmd_replay)
    r = sub.add_parser("run")
    r.add_argument("--exports", nargs="+", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--set", nargs="*", default=None)
    r.add_argument("--workers", type=int, default=4)
    r.set_defaults(fn=cmd_run)
    c = sub.add_parser("compare")
    c.add_argument("--spiking", nargs="+", required=True)
    c.add_argument("--model", required=True)
    c.add_argument("--out")
    c.set_defaults(fn=cmd_compare)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
