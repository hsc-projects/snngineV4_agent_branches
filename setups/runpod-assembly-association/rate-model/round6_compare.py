"""
round6_compare.py

Round 6 (rate-model-task.md), steps 1 and 2: compare the engine's exported network (round6_export_engine.py) with
model B, first by structure, then by the A-alone test before learning, step by step.

  python round6_compare.py audit --export DIR --out RESULT.json [--seed 0]
      structure audit of the export (from meta.json) next to the same audit of model B's own network, drawn for
      the export's grid and size (seed: model B realization)
  python round6_compare.py trace --export DIR --out RESULT.json [--jobs NAME ...] [--set key=value ...]
      model B on the exported network, the engine's injected neurons, background off: the control-0 tests of the
      exported jobs, compared with the engine's per-step record (input currents over the first steps, then
      spikes per step, per group and per type)

structure_audit is also called by round6_export_engine.py on the pod. numpy only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

KINDS = ("EE_intra", "EE_inter", "EI_intra", "EI_inter", "IE_intra", "IE_inter")


def _stats(x) -> dict:
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return {"n": 0}
    return {"n": int(x.size), "mean": float(x.mean()), "min": float(x.min()), "max": float(x.max())}


def synapse_delays(bnd: np.ndarray, S: int) -> np.ndarray:
    """(N, S) delay of every synapse from the delay buckets (N, D + 1): synapses [bnd[r], bnd[r+1]) have delay r."""
    delay = np.zeros((bnd.shape[0], S), dtype=np.int8)
    cols = np.arange(S, dtype=np.int32)[None, :]
    for r in range(1, bnd.shape[1]):
        delay += (cols >= bnd[:, r:r + 1]).astype(np.int8)
    return delay


def structure_audit(post, isE, grp, bnd, w_eng, w_norm, group_cell, abcd=None, init_vu=None, model_flag=None,
                    lam: float | None = 0.4) -> dict:
    """
    Per neuron-type pair, within and between location groups: synapses per presynaptic neuron, weights (engine and
    normalized), delays (and their agreement with the rule round((D - 1) d / d_max)); in-degree of inhibitory
    neurons from excitatory ones by distance; E -> I synapses between groups at distance 1 against the count the
    rewire rule expects from the group sizes; neuron parameters by type.
    """
    N, S = post.shape
    G = group_cell.shape[0]
    grp = grp.astype(np.int64)
    valid = post >= 0
    pc = np.where(valid, post, 0).astype(np.int64)
    postE = isE[pc]
    preE = np.broadcast_to(isE[:, None], post.shape)
    same = grp[pc] == grp[:, None]
    masks = {
        "EE_intra": preE & postE & same, "EE_inter": preE & postE & ~same,
        "EI_intra": preE & ~postE & same, "EI_inter": preE & ~postE & ~same,
        "IE_intra": ~preE & postE & same, "IE_inter": ~preE & postE & ~same,
        "II": ~preE & ~postE,
    }
    gc = group_cell.astype(np.float64)
    dist_gg = np.linalg.norm(gc[:, None, :] - gc[None, :, :], axis=2)
    dmax = max(float(dist_gg.max()), 1e-9)
    D = bnd.shape[1] - 1
    delay = synapse_delays(bnd, S)
    d_syn = dist_gg[grp[:, None], grp[pc]].astype(np.float32)
    rule = np.rint((D - 1) * d_syn / dmax).astype(np.int8)
    out = {"N": int(N), "S": int(S), "G": int(G), "D": int(D),
           "neurons": {"exc": int(isE.sum()), "inh": int((~isE).sum())},
           "deleted_synapses": int((~valid).sum()),
           "group_sizes": {"exc": _stats(np.bincount(grp[isE], minlength=G)),
                           "inh": _stats(np.bincount(grp[~isE], minlength=G))},
           "per_pre_neuron": {}, "weights": {}, "delays": {}}
    for k, m in masks.items():
        m = m & valid
        rows = isE if k[0] == "E" else ~isE
        out["per_pre_neuron"][k] = _stats(m.sum(axis=1)[rows])
        if m.any():
            out["weights"][k] = {"engine": _stats(w_eng[m]), "normalized": _stats(w_norm[m])}
            out["delays"][k] = {"hist": np.bincount(delay[m], minlength=D).tolist(),
                                "rule_agreement": float((delay[m] == rule[m]).mean())}
    for t in ("EE", "EI", "IE"):
        m = (masks[f"{t}_intra"] | masks[f"{t}_inter"]) & valid
        out["per_pre_neuron"][f"{t}_all"] = _stats(m.sum(axis=1)[isE if t[0] == "E" else ~isE])
    # in-degree of inhibitory neurons from excitatory ones, by group distance (0: own group)
    m_ei = (masks["EI_intra"] | masks["EI_inter"]) & valid
    tgt, dd = pc[m_ei], d_syn[m_ei]
    indeg = {}
    for lab, sel in (("own_group", dd < 0.5), ("distance_1", np.abs(dd - 1.0) < 1e-3),
                     ("distance_le_2", dd <= 2.0 + 1e-3), ("all", np.ones(dd.shape, bool))):
        indeg[lab] = _stats(np.bincount(tgt[sel], minlength=N)[~isE])
    out["inh_in_degree_from_exc"] = indeg
    m_ie = (masks["IE_intra"] | masks["IE_inter"]) & valid
    out["exc_in_degree_from_inh"] = _stats(np.bincount(pc[m_ie], minlength=N)[isE])
    # E -> I synapses from group g to group h at distance 1, against the rewire rule's expectation
    pre_g = np.broadcast_to(grp[:, None], post.shape)[m_ei]
    cnt = np.bincount(pre_g * G + grp[tgt], minlength=G * G).reshape(G, G)
    near = np.abs(dist_gg - 1.0) < 1e-3
    blk = {"observed_mean": float(cnt[near].mean())}
    if lam:
        nE_g = np.bincount(grp[isE], minlength=G).astype(np.float64)
        nI_g = np.bincount(grp[~isE], minlength=G).astype(np.float64)
        ei_per_e = m_ei.sum(axis=1)[isE].mean()
        kern = np.exp(-dist_gg / float(lam)) * nI_g[None, :]
        prob = kern / kern.sum(axis=1, keepdims=True)
        exp = nE_g[:, None] * ei_per_e * prob
        blk["expected_by_rule_mean"] = float(exp[near].mean())
        blk["observed_over_expected"] = float(cnt[near].sum() / max(exp[near].sum(), 1e-9))
    out["ei_between_groups_distance_1"] = blk
    if abcd is not None:
        out["neuron_params"] = {t: {p: _stats(abcd[sel, j]) for j, p in enumerate("abcd")}
                                for t, sel in (("exc", isE), ("inh", ~isE))}
    if init_vu is not None:
        out["init_state"] = {t: {"v": _stats(init_vu[sel, 0]), "u": _stats(init_vu[sel, 1])}
                             for t, sel in (("exc", isE), ("inh", ~isE))}
    if model_flag is not None:
        u, c = np.unique(model_flag, return_counts=True)
        out["model_flag_counts"] = {str(int(a)): int(b) for a, b in zip(u, c)}
    return out


# ---------------------------------------------------------------------------------------------------------------
# model B side
# ---------------------------------------------------------------------------------------------------------------

def spec_for(meta: dict, export_dir: str | None = None, **over):
    """Model B spec matching an export: grid, size, delays and the exported job's parameters (s71 / s73 sessions
    share them; SpikeSpec.from_session reads the passing protocol's values)."""
    from admission_test import SESSION
    from spiking_group_model import SpikeSpec
    dim = int(meta["seg"][0])
    kw = dict(grid_dim=dim, neurons_per_group=meta["N"] / float(meta["G"]), n_delays=int(meta["D"]), syn_scale=1.0,
              neuron_scale=1.0, export_dir=export_dir)
    rewire = meta.get("engine", {}).get("rewire")
    if rewire:
        kw["lam"] = float(rewire["lam"])                 # the export's wiring (the session file has lambda 0.4)
    if dim == 9:
        kw["max_active_frac"] = 34 / 729.0
    kw.update(over)
    spec = SpikeSpec.from_session(SESSION, **kw)
    p = meta.get("params", {})
    checks = {"gain": p.get("gain"), "gain_ei": p.get("gain_ei"), "gain_ie": p.get("gain_ie"),
              "gain_ee_inter": p.get("gain_ee_inter"), "i_min": p.get("i_min"), "i_max": p.get("i_max"),
              "k_inject": p.get("k_inject"), "inject_current": p.get("inject_current"),
              "inject_steps": p.get("inject_steps"), "test_window": p.get("test_window"), "window": p.get("window")}
    diff = {k: (v, getattr(spec, k)) for k, v in checks.items() if v is not None and float(v) != float(getattr(spec, k))}
    if diff:
        raise ValueError(f"model B spec differs from the exported job's parameters: {diff}")
    return spec


def own_arrays(net) -> dict:
    """Model B's own network in the export's layout (engine weight = normalized x kind gain)."""
    return {"post": net.post, "isE": net.isE, "grp": net.grp, "bnd": net.bnd, "w_eng": net.wp0 * net.gm[net.kind],
            "w_norm": net.wp0, "group_cell": net.coords.astype(np.int64),
            "abcd": np.stack([net.neurons.a, net.neurons.b, net.neurons.c, net.neurons.d], axis=1),
            "init_vu": np.stack(net.init_state, axis=1), "model_flag": np.zeros(net.N, np.int32)}


def cmd_audit(a):
    from spiking_group_model import SpikingNetwork
    meta = json.loads(open(os.path.join(a.export, "meta.json")).read())
    lam = float(meta["engine"].get("rewire", {}).get("lam", 0.4))
    t0 = time.perf_counter()
    net = SpikingNetwork(spec_for(meta), seed=a.seed)
    x = own_arrays(net)
    own = structure_audit(x["post"], x["isE"], x["grp"], x["bnd"], x["w_eng"], x["w_norm"], x["group_cell"],
                          x["abcd"], x["init_vu"], x["model_flag"], lam=lam)
    res = {"export": a.export, "engine": meta["audit"], "model_b_own": own, "model_b_seed": a.seed,
           "seconds": time.perf_counter() - t0}
    _write(a.out, res)
    e, m = meta["audit"]["per_pre_neuron"], own["per_pre_neuron"]
    for k in KINDS + ("EE_all", "EI_all", "IE_all"):
        print(f"{k:10s} per presynaptic neuron: engine {e[k].get('mean', 0):8.1f}  model B {m[k].get('mean', 0):8.1f}")
    print("inh in-degree from exc, distance 1:", meta["audit"]["inh_in_degree_from_exc"]["distance_1"].get("mean"),
          own["inh_in_degree_from_exc"]["distance_1"].get("mean"))


# ---------------------------------------------------------------------------------------------------------------
# step 2: the A-alone test before learning, step by step
# ---------------------------------------------------------------------------------------------------------------

def activity_max(fired_steps, isE, grp, nE, window: int) -> np.ndarray:
    """Per-group maximum over the test of A_g (fraction of the group's excitatory neurons that fired in the last
    `window` steps; GroupActivity with activity_exc_only)."""
    G = len(nE)
    last = np.full(len(isE), -10 ** 9, dtype=np.int64)
    gmax = np.zeros(G)
    for k, f in enumerate(fired_steps):
        fe = f[isE[f]]
        last[fe] = k
        act = isE & (last > k - window)
        A = np.bincount(grp[act], minlength=G) / np.maximum(nE, 1)
        np.maximum(gmax, A, out=gmax)
    return gmax


def model_trace(net, inject_idx: np.ndarray, steps: int, inj_steps: int, k_input: int):
    """SpikingNetwork.run for a frozen test (run_test, mode 'perm'), recording fired ids per step and, for the
    first k_input steps, the unclamped summed synaptic input and v right after the step."""
    s = net.spec
    net.reset_dynamics()
    fired_steps, inp, vs = [], [], []
    orig = net.neurons.step

    def rec(i):
        f = orig(i)
        fired_steps.append(np.asarray(f, dtype=np.int64))
        return f

    net.neurons.step = rec
    net.capture_raw = True
    try:
        for i in range(steps):
            net.last_input_raw = np.zeros(net.N, dtype=np.float32)
            net.step(s.window, False, False, 0.0, False, False, False, inject_idx if i < inj_steps else None)
            if i < k_input:
                inp.append(net.last_input_raw.copy())
                vs.append(net.neurons.v.copy())
    finally:
        net.neurons.step = orig
        net.capture_raw = False
    return fired_steps, np.stack(inp) if inp else None, np.stack(vs) if vs else None


def compare_test(net, z, key: str, inject_idx, meta_test: dict, k_input: int) -> dict:
    s = net.spec
    offs = z[f"{key}_offsets"]
    fired_all = z[f"{key}_fired"].astype(np.int64)
    eng_f = [fired_all[offs[i]:offs[i + 1]] for i in range(len(offs) - 1)]
    steps = len(eng_f)
    mod_f, mod_in, mod_v = model_trace(net, inject_idx, steps, s.inject_steps, k_input)
    eng_in, eng_v = z[f"{key}_input"], z[f"{key}_v"]
    first_spike_diff = next((i for i in range(steps) if not np.array_equal(np.sort(eng_f[i]), np.sort(mod_f[i]))),
                            None)
    per_step = []
    for i in range(min(k_input, len(eng_in))):
        di = np.abs(eng_in[i].astype(np.float64) - mod_in[i])
        dv = np.abs(eng_v[i].astype(np.float64) - mod_v[i])
        scale = max(1.0, float(np.abs(eng_in[i]).max()))
        row = {"step": i, "input_max_abs_diff": float(di.max()), "input_rel": float(di.max() / scale),
               "v_max_abs_diff": float(dv.max()), "eng_input_sum": float(eng_in[i].sum()),
               "model_input_sum": float(mod_in[i].sum()),
               "eng_spikes": int(len(eng_f[i])), "model_spikes": int(len(mod_f[i]))}
        if di.max() > 1e-3 * scale:
            top = np.argsort(-di)[:10]
            row["worst"] = [{"n": int(n), "exc": bool(net.isE[n]), "group": int(net.grp[n]),
                             "engine": float(eng_in[i][n]), "model": float(mod_in[i][n])} for n in top]
        per_step.append(row)
    first_input_diff = next((r["step"] for r in per_step if r["input_rel"] > 1e-4), None)

    def totals(fs, src):
        allf = np.concatenate(fs) if fs else np.zeros(0, np.int64)
        e = net.isE[allf]
        ing = net.grp[allf] == src
        return {"total": int(len(allf)), "exc": int(e.sum()), "inh": int((~e).sum()),
                "exc_outside_src": int((e & ~ing).sum()), "inh_outside_src": int((~e & ~ing).sum())}

    src = int(meta_test["src"])
    tot_e, tot_m = totals(eng_f, src), totals(mod_f, src)
    ga_e = activity_max(eng_f, net.isE, net.grp, net.nE, s.window)
    ga_m = activity_max(mod_f, net.isE, net.grp, net.nE, s.window)
    act_e, act_m = set(np.nonzero(ga_e >= s.active)[0].tolist()), set(np.nonzero(ga_m >= s.active)[0].tolist())
    rel = abs(tot_m["total"] - tot_e["total"]) / max(tot_e["total"], 1)
    return {"steps": steps, "first_spike_diff_step": first_spike_diff, "first_input_diff_step": first_input_diff,
            "per_step": per_step, "engine": tot_e, "model": tot_m, "total_rel_diff": rel,
            "engine_reported_spikes": meta_test.get("spikes"), "groups_active_engine": sorted(act_e),
            "groups_active_model": sorted(act_m),
            "pass": bool(rel <= 0.05 and act_e == act_m
                         and (first_input_diff is None or (first_spike_diff is not None
                                                           and first_input_diff > first_spike_diff)))}


def cmd_trace(a):
    from round5_diag_spiking import parse_set
    from spiking_group_model import SpikingNetwork
    meta = json.loads(open(os.path.join(a.export, "meta.json")).read())
    t0 = time.perf_counter()
    net = SpikingNetwork(spec_for(meta, export_dir=a.export, **parse_set(a.set)), seed=int(meta["seed"]))
    build_s = time.perf_counter() - t0
    k_input = int(meta.get("input_steps", 12))
    res = {"export": a.export, "build_seconds": build_s, "settings": parse_set(a.set), "jobs": []}
    for job in meta["jobs"]:
        if a.jobs and job["job"] not in a.jobs:
            continue
        z = np.load(os.path.join(a.export, f"test_{job['job']}.npz"))
        e2m = net.engine_to_model                # engine group index -> model (lattice) index
        A, B = int(e2m[job["pair"]["A"]]), int(e2m[job["pair"]["B"]])
        out = {"job": job["job"], "pair": job["pair"], "pair_model": {"A": A, "B": B}}
        for key, src, inj in (("AB", A, z["inject_A"]), ("BA", B, z["inject_B"])):
            net.set_injection(src, inj)
            t = dict(job["tests"][key], src=src)
            out[key] = compare_test(net, z, key, net.inject_idx(src), t, k_input)
            r = out[key]
            print(f"{job['job']} {key}: spikes engine {r['engine']['total']} (inh outside {r['engine']['inh_outside_src']})"
                  f"  model {r['model']['total']} (inh outside {r['model']['inh_outside_src']});"
                  f" first input diff step {r['first_input_diff_step']}, first spike diff step {r['first_spike_diff_step']}",
                  flush=True)
        res["jobs"].append(out)
        _write(a.out, res)
    res["seconds"] = time.perf_counter() - t0
    _write(a.out, res)


def _single_job(args):
    meta, over, seed, pairs = args
    from round5_diag_spiking import parse_set
    from spiking_group_model import SpikingNetwork
    net = SpikingNetwork(spec_for(meta, **parse_set(over)), seed=seed)
    s = net.spec
    out = []
    for a, b in pairs:
        for src in (a, b):
            f, _, _ = model_trace(net, net.inject_idx(src), s.test_window, s.inject_steps, 0)
            allf = np.concatenate(f) if f else np.zeros(0, np.int64)
            e, ing = net.isE[allf], net.grp[allf] == src
            out.append({"seed": seed, "src": int(src), "total": int(len(allf)), "exc_outside_src": int((e & ~ing).sum()),
                        "inh_outside_src": int((~e & ~ing).sum())})
    return out


def cmd_single(a):
    """Step 3: model B's own networks (spec overrides --set), A-alone tests before learning at the engine's pair
    positions (relabelled to the model's lattice index), against the engine's tests of the same exports."""
    from concurrent.futures import ProcessPoolExecutor
    metas = [json.loads(open(os.path.join(d, "meta.json")).read()) for d in a.exports]
    dim = int(metas[0]["seg"][0])
    pairs = []
    for m in metas:
        for j in m["jobs"]:
            e = [j["pair"]["A"], j["pair"]["B"]]          # engine index z dim^2 + y dim + x -> model x dim^2 + y dim + z
            pairs.append(tuple(int((g % dim) * dim * dim + ((g // dim) % dim) * dim + g // (dim * dim)) for g in e))
    ref = []
    for d in a.exports:
        tr = json.loads(open(os.path.join(d, "trace.json")).read())
        for j in tr["jobs"]:
            for k in ("AB", "BA"):
                ref.append(j[k]["engine"])
    jobs = [(metas[0], a.set, sd, pairs) for sd in a.seeds]
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        res = [r for rs in ex.map(_single_job, jobs) for r in rs]

    def summ(rows):
        out = {}
        for k in ("total", "exc_outside_src", "inh_outside_src"):
            x = np.array([r[k] for r in rows], dtype=float)
            out[k] = {"median": float(np.median(x)), "q25": float(np.percentile(x, 25)), "q75": float(np.percentile(x, 75)),
                      "mean": float(x.mean())}
        return out

    s_eng, s_mod = summ(ref), summ(res)
    rel = abs(s_mod["total"]["median"] - s_eng["total"]["median"]) / max(s_eng["total"]["median"], 1)
    out = {"settings": a.set, "seeds": a.seeds, "exports": a.exports, "n_tests": len(res), "engine": s_eng,
           "model": s_mod, "median_total_rel_diff": rel, "tests": res, "seconds": time.perf_counter() - t0}
    _write(a.out, out)
    for k in ("total", "exc_outside_src", "inh_outside_src"):
        print(f"{k:16s} engine median {s_eng[k]['median']:7.1f} [{s_eng[k]['q25']:.0f}, {s_eng[k]['q75']:.0f}]   "
              f"model median {s_mod[k]['median']:7.1f} [{s_mod[k]['q25']:.0f}, {s_mod[k]['q75']:.0f}]")


def _write(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("audit")
    p.add_argument("--export", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=cmd_audit)
    p = sub.add_parser("trace")
    p.add_argument("--export", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--jobs", nargs="*", default=None)
    p.add_argument("--set", nargs="*", default=None)
    p.set_defaults(fn=cmd_trace)
    p = sub.add_parser("single")
    p.add_argument("--exports", nargs="+", required=True, help="export directories of one grid (pairs and reference)")
    p.add_argument("--out", required=True)
    p.add_argument("--seeds", type=int, nargs="+", default=[0, 1])
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--set", nargs="*", default=None)
    p.set_defaults(fn=cmd_single)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
