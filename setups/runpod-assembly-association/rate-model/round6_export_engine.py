"""
round6_export_engine.py

Round 6, step 1 (rate-model-task.md): on a GPU pod, build the engine's network exactly as a spiking job did
(engine configuration and job parameters from params files), export what the engine simulates, record the
engine's A-alone tests before learning (control 0 of assoc_protocol.substep4_protocol, both directions) step by
step, and write the structure audit (round6_compare.structure_audit) of the exported network.

  python round6_export_engine.py --params P1.json [P2.json ...] --suffix E0 --out DIR [--tag g9-s0]
         [--input-steps 12] [--no-arrays]

All params files must share one engine configuration (one engine per process: building a second engine in
one process fails, see assoc_queue.py). Every job whose name ends with --suffix is replayed as far as its
control-0 tests. Output in DIR/<tag>/:
  meta.json            sizes, engine configuration, the first job's parameters, structure report, audit, per job:
                       pair, injected neurons of A and B, control-0 test results
  post.npy             (N, S) int32 postsynaptic neuron of synapse s of neuron n (N_rep transposed; -1 deleted)
  w_engine.npy         (N, S) float32 weight as written into the engine (gains included), before learning
  w_norm.npy           (N, S) float32 normalized weight (AssocRun.base_w)
  bnd.npy              (N, D + 1) int32 delay buckets (N_delays transposed): synapses [bnd[r], bnd[r+1]) have delay r
  abcd.npy             (N, 4) float32 Izhikevich a, b, c, d (N_states rows 3 to 6)
  init_vu.npy          (N, 2) float32 post-warm-up v, u (the state every reset returns to)
  types.npy, groups.npy, model_flag.npy   (N,) neuron type (1 inhibitory, 2 excitatory), location group, N_flags row 3
  group_cell.npy       (G, 3) grid cell of each location group
  test_<job>.npz       per direction (AB, BA): fired neuron ids per step (concatenated, with offsets), the
                       synaptic input current right after each of the first --input-steps steps (before clamp and
                       injection, as AssocRun.run reads it) and v at the same moments
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
for _p in (HERE, PARENT):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def merge(a, b):
    out = dict(a)
    for k, v in (b or {}).items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def engine_key(spec: dict, job: dict) -> str:
    return json.dumps(merge(spec["engine"], job.get("engine", {})), sort_keys=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", nargs="+", required=True)
    ap.add_argument("--suffix", default="E0", help="replay the jobs whose names end with this")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default=None, help="output subdirectory (default: g<dim>-s<seed>)")
    ap.add_argument("--input-steps", type=int, default=12)
    ap.add_argument("--no-arrays", action="store_true", help="audit and tests only, no network arrays")
    args = ap.parse_args(argv)

    import torch
    from assoc_engine import AssocEngine, ROW_I, ROW_U, ROW_V, FLAG_TYPE, FLAG_GROUP, TYPE_EXC
    from assoc_protocol import AssocRun, DEFAULTS
    from round6_compare import structure_audit

    jobs, key = [], None
    for path in args.params:
        spec = json.loads(open(path).read())
        defaults = merge(DEFAULTS, spec.get("defaults", {}))
        for job in spec["jobs"]:
            if not job["name"].endswith(args.suffix) or job["type"] != "substep4":
                continue
            k = engine_key(spec, job)
            if key is None:
                key = k
            elif k != key:
                raise SystemExit(f"{path}: job {job['name']} has another engine configuration")
            jobs.append((os.path.basename(path), job["name"], merge(defaults, job.get("params", {}))))
    if not jobs:
        raise SystemExit("no job selected")
    cfg = json.loads(key)
    device = torch.device("cuda:0")
    t0 = time.time()
    eng = AssocEngine(device, n_neurons=int(cfg["n_neurons"]),
                      reservoir_shape=tuple(float(x) for x in cfg.get("reservoir_shape", (1, 1, 1))),
                      seed=int(cfg.get("seed", 0)), engine_chem_dim=int(cfg.get("engine_chem_dim", 32)),
                      n_synapses=cfg.get("n_synapses"), rewire=cfg.get("rewire"), n_delays=cfg.get("n_delays"))
    build_s = time.time() - t0
    N, S, D, G = eng.N, eng.S, eng.D, eng.G
    tag = args.tag or f"g{eng.seg[0]}-s{eng.seed}"
    out = os.path.join(args.out, tag)
    os.makedirs(out, exist_ok=True)
    print(f"[*] engine N={N} S={S} D={D} G={G} seg={eng.seg} built in {build_s:.1f} s -> {out}", flush=True)

    # per-step recording: AssocRun.run calls eng.step(); the engine's own reset steps are not recorded
    rec = {"on": False, "fired": [], "inp": [], "v": []}
    orig_step = eng.step

    def step():
        sp = orig_step()
        if rec["on"]:
            rec["fired"].append(torch.nonzero(sp).view(-1).to(torch.int32).cpu().numpy())
            if len(rec["inp"]) < args.input_steps:
                rec["inp"].append(eng.states[ROW_I].detach().cpu().numpy().copy())
                rec["v"].append(eng.states[ROW_V].detach().cpu().numpy().copy())
        return sp

    eng.step = step

    meta = {"N": N, "S": S, "D": D, "G": G, "seg": list(eng.seg), "seed": eng.seed, "engine": cfg,
            "build_seconds": build_s, "structure_report": eng.structure_report(), "jobs": [],
            "params_files": sorted({j[0] for j in jobs}), "input_steps": args.input_steps}
    w_written = None
    for fname, name, params in jobs:
        params["deadline"] = None
        run = AssocRun(eng, params, rng_seed=eng.seed + 4)       # as substep4_protocol
        orig_run = run.run

        def run_rec(*a, **k):
            rec["on"] = True
            try:
                return orig_run(*a, **k)
            finally:
                rec["on"] = False

        run.run = run_rec
        pr = run.p["protocol"]
        for _ in range(int(params.get("pair_draw", 0))):
            run.pick_pair(pr["pair_distance"])
        a, b, c = (tuple(params["pair"]) if params.get("pair") else run.pick_pair(pr["pair_distance"]))
        if w_written is None:
            w_written = (eng.weights.detach().clone(), run.base_w.detach().clone())
            meta["params"] = {k: v for k, v in run.p.items() if k != "deadline"}
        else:
            same = bool(torch.equal(w_written[0], eng.weights)) and bool(torch.equal(w_written[1], run.base_w))
            if not same:
                raise SystemExit(f"job {name}: weights differ from the first job's (different gains or weights)")
        run.reset_all()
        entry = {"params_file": fname, "job": name, "pair": {"A": a, "B": b, "C": c},
                 "dist_AB_cells": run.group_dist(a, b), "tests": {}}
        arrays = {}
        for key_d, (src, dst) in (("AB", (a, b)), ("BA", (b, a))):
            rec["fired"], rec["inp"], rec["v"] = [], [], []
            res = run.test(src, dst, c, strict=True)
            run.baselines[(src, dst)] = run.last_group_max.clone()
            fired = rec["fired"]
            offs = np.cumsum([0] + [len(f) for f in fired]).astype(np.int64)
            arrays[f"{key_d}_fired"] = np.concatenate(fired) if fired else np.zeros(0, np.int32)
            arrays[f"{key_d}_offsets"] = offs
            arrays[f"{key_d}_input"] = np.stack(rec["inp"]).astype(np.float32)
            arrays[f"{key_d}_v"] = np.stack(rec["v"]).astype(np.float32)
            entry["tests"][key_d] = {k: v for k, v in res.items() if k != "active_outside"}
            entry["tests"][key_d]["active_outside"] = res.get("active_outside")
        inj = {int(g): run.inject_idx_cached(g).cpu().numpy().astype(np.int64) for g in (a, b)}
        entry["inject"] = {str(g): v.tolist() for g, v in inj.items()}
        arrays["inject_A"], arrays["inject_B"] = inj[a], inj[b]
        np.savez_compressed(os.path.join(out, f"test_{name}.npz"), **arrays)
        meta["jobs"].append(entry)
        print(f"[+] {name}: pair {a}-{b}, control-0 spikes AB {entry['tests']['AB']['spikes']} "
              f"BA {entry['tests']['BA']['spikes']}", flush=True)

    t1 = time.time()
    post = eng.n_rep.t().contiguous().cpu().numpy().astype(np.int32)
    w_eng = w_written[0].t().contiguous().cpu().numpy().astype(np.float32)
    w_norm = w_written[1].t().contiguous().cpu().numpy().astype(np.float32)
    bnd = eng.n_delays.t().contiguous().cpu().numpy().astype(np.int32)
    st = eng.init_states
    abcd = torch.stack([st[3], st[4], st[5], st[6]], dim=1).cpu().numpy().astype(np.float32)
    init_vu = torch.stack([st[ROW_V], st[ROW_U]], dim=1).cpu().numpy().astype(np.float32)
    types = eng.flags[FLAG_TYPE].cpu().numpy().astype(np.int8)
    groups = eng.flags[FLAG_GROUP].cpu().numpy().astype(np.int32)
    model_flag = eng.flags[3].cpu().numpy().astype(np.int32)
    group_cell = eng.group_cell.cpu().numpy().astype(np.int64)
    small = {"abcd": abcd, "init_vu": init_vu, "types": types, "groups": groups, "model_flag": model_flag,
             "group_cell": group_cell}
    for k, v in small.items():
        np.save(os.path.join(out, f"{k}.npy"), v)
    if not args.no_arrays:
        for k, v in (("post", post), ("w_engine", w_eng), ("w_norm", w_norm), ("bnd", bnd)):
            np.save(os.path.join(out, f"{k}.npy"), v)
    meta["export_seconds"] = time.time() - t1
    meta["type_exc"] = TYPE_EXC
    meta["audit"] = structure_audit(post, types == TYPE_EXC, groups, bnd, w_eng, w_norm, group_cell, abcd,
                                    init_vu, model_flag, lam=float((cfg.get("rewire") or {}).get("lam", 0.4)))
    with open(os.path.join(out, "meta.json"), "w") as f:
        json.dump(meta, f, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    print(f"[+] exported in {meta['export_seconds']:.1f} s; audit E->I per excitatory neuron: "
          f"{meta['audit']['per_pre_neuron']['EI_all']['mean']:.1f}", flush=True)
    print("EXPORT DONE")


if __name__ == "__main__":
    main()
