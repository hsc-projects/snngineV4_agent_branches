"""
round6_export_engine.py

Round 6, step 1 (rate-model-task.md): on a GPU pod, build the engine's network exactly as a spiking job did
(engine configuration and job parameters from params files), export what the engine simulates, record the
engine's A-alone tests before learning (control 0 of assoc_protocol.substep4_protocol, both directions) step by
step, and write the structure audit (round6_compare.structure_audit) of the exported network.

  python round6_export_engine.py --params P1.json [P2.json ...] --suffix E0 --out DIR [--tag g9-s0]
         [--input-steps 12] [--no-arrays] [--survey]

All params files must share one engine configuration (one engine per process: building a second engine in
one process fails, see assoc_queue.py). Every job whose name ends with --suffix is replayed as far as its
control-0 tests. With --survey (round 6 step 4, the sparse substrate), the selected jobs are prop_survey and
input_survey jobs (name ending with --suffix + "-prop_survey" or "-input_survey") instead: no test is run; per
job, the survey's pairs as it draws them, their path groups, bridges, off-route assemblies and injected neurons
go into meta.json, and survey_<job>.npz holds per pair the neuron masks of the regions M and Sh and the bin of
the input survey's profile (-1 outside), all from the engine's own geometry (assoc_protocol.AssocRun).
Output in DIR/<tag>/:
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


PROFILE_EDGES = [-0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]      # assoc_protocol.input_survey


def survey_entry(run, eng, fname: str, name: str, jtype: str, kwargs: dict, out: str, replay: bool = False) -> dict:
    """
    One survey job's pairs, drawn and prepared as assoc_protocol.prop_survey / input_survey do (all pairs first,
    then the injected neurons of A and B pair by pair, which is the order both surveys first ask for them), with
    the path groups, bridges and off-route assemblies of prop_survey and the neuron regions of both. With `replay`
    (a prop_survey job whose weights are the exported ones), the engine also runs the survey's joint, A and B
    conditions on this network and records per pair its spike count, M and Sh (step 2's check for the survey).
    """
    import torch
    p = run.p
    pairs = [run.pick_pair(p["protocol"]["pair_distance"]) for _ in range(int(kwargs.get("n_pairs", 8)))]
    cells = eng.pos / eng.cell_size
    r = float(p["sel_radius"])
    rows, m_mask, s_mask, prof = [], [], [], []
    for a, b, c in pairs:
        path = run.path_groups(a, b)
        bridges = [g for g in path if bool(run.is_asm[g])] if run.sparse else []
        off_asm = run.is_asm.clone()
        off_asm[[a, b] + bridges] = False
        inj = {str(g): run.inject_idx_cached(g).cpu().numpy().astype(np.int64).tolist() for g in (a, b)}
        nm, ns = run.regions(a, b)["neuron"]
        t, rho, _, _ = run.seg_coords(cells, a, b)
        code = torch.full((eng.N,), -1, dtype=torch.int8, device=eng.device)
        for i, (lo, hi) in enumerate(zip(PROFILE_EDGES[:-1], PROFILE_EDGES[1:])):
            code[(rho < r) & (t >= lo) & (t < hi)] = i
        rows.append({"A": a, "B": b, "C": c, "dist": run.group_dist(a, b), "path": path, "bridges": bridges,
                     "off_asm": torch.nonzero(off_asm).view(-1).tolist(), "inject": inj})
        m_mask.append(nm.cpu().numpy())
        s_mask.append(ns.cpu().numpy())
        prof.append(code.cpu().numpy())
    if replay:
        rnd = p["inject_steps"] + p["gap_steps"]
        exc = eng.exc.cpu().numpy()
        run.set_noise_phase(True)
        run.spike_acc = torch.zeros(eng.N, device=eng.device)
        for row, nm, ns in zip(rows, m_mask, s_mask):
            a, b, rep = row["A"], row["B"], {}
            for cond, inj in (("joint", (a, b)), ("A", (a,)), ("B", (b,))):
                run.reset_dynamics()
                run.spike_acc.zero_()
                _, _, n = run.run(rnd, inject=[run.inject_idx_cached(g) for g in inj], track=[a, b] + row["path"],
                                  chem=False, release1=False, header=f"replay {cond}")
                sa = run.spike_acc.cpu().numpy()
                rep[cond] = {"spikes": int(n), "M": float(sa[nm & exc].sum()) / max(1, int((nm & exc).sum())),
                             "Sh": float(sa[ns & exc].sum()) / max(1, int((ns & exc).sum())),
                             "runaway": run.stopped is not None}
            row["engine_replay"] = rep
        run.spike_acc = None
        run.set_noise_phase(False)
    np.savez_compressed(os.path.join(out, f"survey_{name}.npz"), M=np.stack(m_mask), Sh=np.stack(s_mask),
                        profile=np.stack(prof))
    return {"params_file": fname, "job": name, "type": jtype, "survey": True, "pairs": rows,
            "sel_radius": r, "profile_edges": PROFILE_EDGES}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", nargs="+", required=True)
    ap.add_argument("--suffix", default="E0", help="replay the jobs whose names end with this")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default=None, help="output subdirectory (default: g<dim>-s<seed>)")
    ap.add_argument("--input-steps", type=int, default=12)
    ap.add_argument("--no-arrays", action="store_true", help="audit and tests only, no network arrays")
    ap.add_argument("--survey", action="store_true", help="export prop_survey / input_survey jobs (sparse substrate)")
    ap.add_argument("--replay", action="store_true",
                    help="with --survey: the engine runs the first prop_survey job's conditions on the exported weights")
    args = ap.parse_args(argv)
    survey_types = ("prop_survey", "input_survey")

    import torch
    from assoc_engine import AssocEngine, ROW_I, ROW_U, ROW_V, FLAG_TYPE, FLAG_GROUP, TYPE_EXC
    from assoc_protocol import AssocRun, DEFAULTS
    from round6_compare import structure_audit

    jobs, key = [], None
    for path in args.params:
        spec = json.loads(open(path).read())
        defaults = merge(DEFAULTS, spec.get("defaults", {}))
        for job in spec["jobs"]:
            if args.survey:
                if job["type"] not in survey_types or job["name"] != f"{args.suffix}-{job['type']}":
                    continue
            elif not job["name"].endswith(args.suffix) or job["type"] != "substep4":
                continue
            k = engine_key(spec, job)
            if key is None:
                key = k
            elif k != key:
                raise SystemExit(f"{path}: job {job['name']} has another engine configuration")
            jobs.append((os.path.basename(path), job["name"], merge(defaults, job.get("params", {})),
                         job["type"], dict(job.get("kwargs", {}))))
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
    for fname, name, params, jtype, kwargs in jobs:
        params["deadline"] = None
        run = AssocRun(eng, params, rng_seed=eng.seed + 4)       # as substep4_protocol and the surveys
        if jtype in survey_types:
            w_now = (eng.weights.detach().clone(), run.base_w.detach().clone())
            if w_written is None:
                w_written = w_now
                meta["params"] = {k: v for k, v in run.p.items() if k != "deadline"}
                meta["is_asm"] = run.is_asm.cpu().numpy().astype(bool).tolist()
            else:
                # heavy-tailed initial weights are normalized per presynaptic neuron on the GPU (index_add_), so two
                # builds of them may differ in the last float32 bits; the first job's weights are exported
                dev = max(float((w_written[k] - w_now[k]).abs().max()) for k in (0, 1))
                meta.setdefault("weight_rebuild_max_abs_diff", {})[name] = dev
                if not (torch.allclose(w_written[0], w_now[0], rtol=1e-5, atol=1e-6)
                        and torch.allclose(w_written[1], w_now[1], rtol=1e-5, atol=1e-6)):
                    raise SystemExit(f"job {name}: weights differ from the first job's by up to {dev}")
            first = not meta["jobs"]
            meta["jobs"].append(survey_entry(run, eng, fname, name, jtype, kwargs, out,
                                             replay=args.replay and first and jtype == "prop_survey"))
            print(f"[+] {name}: {len(meta['jobs'][-1]['pairs'])} pairs", flush=True)
            continue
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
