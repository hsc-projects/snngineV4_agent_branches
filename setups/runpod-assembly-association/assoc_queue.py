#!/usr/bin/env python3
"""
Queue runner for the assembly association task: one per pod session.

- Preflight (aborts at the first failure): module checks on CPU and GPU, imports, engine build,
  a few engine steps.
- Jobs from a parameter file, each with its own pass/fail line. Results are written
  incrementally (<session>/<job>.json, chemistry snapshots as .npz) with a done marker per
  job, so a rerun resumes. Per-job and per-session wall-clock limits.
- One summary.json at the end (GPU, timings, utilization, per-job pass/fail).

Parameter file:
{
  "session": "s1",
  "engine": {"n_neurons": 5000, "reservoir_shape": [1, 1, 1], "seed": 0, "engine_chem_dim": 32},
  "defaults": { ...AssocRun parameters... },
  "jobs": [{"name": "s0", "type": "substep0", "engine": {...}, "params": {...}}, ...]
}
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)


class GpuSampler(threading.Thread):
    def __init__(self, period=2.0):
        super().__init__(daemon=True)
        self.period = period
        self.util, self.mem = [], []
        self.stop_flag = False

    def run(self):
        while not self.stop_flag:
            try:
                out = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used",
                                      "--format=csv,noheader,nounits"], capture_output=True, text=True,
                                     timeout=10).stdout.strip().splitlines()[0]
                u, m = (float(x) for x in out.split(","))
                self.util.append(u)
                self.mem.append(m)
            except Exception:
                pass
            time.sleep(self.period)

    def summary(self):
        if not self.util:
            return {}
        return {"gpu_util_mean_pct": sum(self.util) / len(self.util), "gpu_util_max_pct": max(self.util),
                "gpu_mem_max_mb": max(self.mem), "samples": len(self.util)}


def to_jsonable(obj, arrays: dict, prefix=""):
    import numpy as np
    if isinstance(obj, dict):
        return {k: to_jsonable(v, arrays, f"{prefix}{k}.") for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v, arrays, f"{prefix}{i}.") for i, v in enumerate(obj)]
    if isinstance(obj, np.ndarray):
        if obj.size > 64:
            key = prefix.rstrip(".").replace(".", "_")
            arrays[key] = obj
            return f"<npz:{key} shape={list(obj.shape)}>"
        return obj.tolist()
    if isinstance(obj, (np.floating, np.integer, np.bool_)):
        return obj.item()
    return obj


def merge(a, b):
    from assoc_protocol import merge as m
    return m(a, b)


def run_module_checks(device: str) -> tuple[bool, str]:
    proc = subprocess.run([sys.executable, os.path.join(_SCRIPT_DIR, "test_assoc_modules.py"), "--device", device],
                          capture_output=True, text=True, timeout=600)
    return proc.returncode == 0, proc.stdout + proc.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", required=True)
    ap.add_argument("--output-dir", default="/workspace/output/assembly-association")
    ap.add_argument("--job-limit-min", type=float, default=45.0)
    ap.add_argument("--session-limit-min", type=float, default=45.0)
    ap.add_argument("--device", type=int, default=0)
    ap.add_argument("--setup-seconds", type=float, default=None)
    ap.add_argument("--only", nargs="*", default=None, help="run only these job names")
    ap.add_argument("--child", action="store_true",
                    help="internal: one engine configuration per process, no module checks")
    args = ap.parse_args()

    t_session = time.time()
    spec = json.loads(Path(args.params).read_text())
    session = spec.get("session", Path(args.params).stem)
    out_dir = Path(args.output_dir) / session
    out_dir.mkdir(parents=True, exist_ok=True)
    session_deadline = t_session + 60 * args.session_limit_min
    summary = {"session": session, "params_file": os.path.basename(args.params), "jobs": [],
               "setup_seconds": args.setup_seconds}
    summary_path = out_dir / ("summary.json" if not args.child else f"summary_child_{args.only[0]}.json")

    sampler = GpuSampler()
    sampler.start()

    # Building a second engine in one process fails (the sibling's array-interface patch
    # registers twice: ExtensionByDuplicateError), so every engine configuration runs in
    # its own child process.
    def engine_key(job):
        return json.dumps(merge(spec["engine"], job.get("engine", {})), sort_keys=True)

    jobs_sel = [j for j in spec["jobs"] if not args.only or j["name"] in args.only]
    groups: dict[str, list[str]] = {}
    for j in jobs_sel:
        groups.setdefault(engine_key(j), []).append(j["name"])
    if args.child:
        spec["engine"] = json.loads(next(iter(groups)))

    # ---------------------------------------------------------------- preflight
    pre = {}
    for dev in (() if args.child else ("cpu", "cuda")):
        ok, log = run_module_checks(dev)
        pre[f"module_checks_{dev}"] = ok
        (out_dir / f"module_checks_{dev}.log").write_text(log)
        print(log)
        print(("PASS" if ok else "FAIL") + f" preflight module checks on {dev}")
        if not ok:
            summary["preflight"] = pre
            (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
            sys.exit(2)

    if not args.child and len(groups) > 1:
        summary["preflight"] = pre
        summary["children"] = []
        for key, names in groups.items():
            left_min = (session_deadline - time.time()) / 60
            if left_min <= 0:
                summary["stopped_at"] = names[0]
                break
            cmd = [sys.executable, os.path.abspath(__file__), "--params", args.params,
                   "--output-dir", args.output_dir, "--job-limit-min", str(args.job_limit_min),
                   "--session-limit-min", str(left_min), "--device", str(args.device), "--child",
                   "--only", *names]
            print(f"[*] child process for engine {key}: {len(names)} jobs")
            rc = subprocess.run(cmd).returncode
            summary["children"].append({"engine": json.loads(key), "jobs": names, "returncode": rc})
            for n in names:
                f = out_dir / f"{n}.summary.json"
                if f.exists():
                    summary["jobs"].append(json.loads(f.read_text()))
            summary_path.write_text(json.dumps(summary, indent=2, default=str))
        sampler.stop_flag = True
        summary["gpu_sampling"] = sampler.summary()
        summary["session_seconds"] = time.time() - t_session
        summary_path.write_text(json.dumps(summary, indent=2, default=str))
        print(json.dumps({k: summary.get(k) for k in ("session_seconds", "gpu_sampling")}, indent=1))
        print("SESSION DONE")
        return

    import numpy as np
    import torch
    from assoc_engine import AssocEngine
    from assoc_protocol import JOBS, DEFAULTS, JobTimeout

    device = torch.device(f"cuda:{args.device}")
    summary["gpu"] = torch.cuda.get_device_name(device)
    summary["torch"] = torch.__version__

    engines: dict = {}

    def get_engine(cfg: dict):
        key = (int(cfg["n_neurons"]), tuple(float(x) for x in cfg.get("reservoir_shape", (1, 1, 1))),
               int(cfg.get("seed", 0)), int(cfg.get("engine_chem_dim", 32)), cfg.get("n_synapses"),
               json.dumps(cfg.get("rewire"), sort_keys=True))
        if key not in engines:
            for k in list(engines):
                del engines[k]
            torch.cuda.empty_cache()
            t0 = time.time()
            eng = AssocEngine(device, n_neurons=key[0], reservoir_shape=key[1], seed=key[2], engine_chem_dim=key[3],
                              n_synapses=key[4], rewire=cfg.get("rewire"))
            eng.build_seconds = time.time() - t0
            engines[key] = eng
            print(f"[*] engine built: N={eng.N} S={eng.S} D={eng.D} G={eng.G} seg={eng.seg} "
                  f"in {eng.build_seconds:.1f} s")
        return engines[key]

    try:
        eng = get_engine(spec["engine"])
        rep = eng.structure_report()
        t0 = time.time()
        for _ in range(20):
            eng.step()
        torch.cuda.synchronize()
        rep["steps_20_seconds"] = time.time() - t0
        w = eng.weights.clone()
        eng.write_weights(w * 0.5)
        ok_w = torch.allclose(eng.weights, w * 0.5)
        eng.write_weights(w)
        pre["engine"] = rep
        pre["engine_ok"] = bool(rep["weights_ptr_stable"] and ok_w and rep["n_rep_shape"] == [eng.S, eng.N])
        pre["engine_build_seconds"] = eng.build_seconds
    except Exception:
        pre["engine_ok"] = False
        pre["engine_error"] = traceback.format_exc()
        print(pre["engine_error"])
    print(("PASS" if pre["engine_ok"] else "FAIL") + " preflight engine build, shapes, weight write, 20 steps")
    summary["preflight"] = to_jsonable(pre, {})
    summary_path.write_text(json.dumps(summary, indent=2, default=str))
    if not pre["engine_ok"]:
        sys.exit(3)

    # ---------------------------------------------------------------- jobs
    defaults = merge(DEFAULTS, spec.get("defaults", {}))
    for job in spec["jobs"]:
        name = job["name"]
        if args.only and name not in args.only:
            continue
        done = out_dir / f"{name}.done"
        if done.exists():
            print(f"SKIP {name} (done marker present)")
            summary["jobs"].append(json.loads((out_dir / f"{name}.summary.json").read_text()))
            continue
        if time.time() > session_deadline:
            print(f"STOP session wall-clock limit reached before {name}")
            summary["stopped_at"] = name
            break
        t0 = time.time()
        params = merge(defaults, job.get("params", {}))
        params["deadline"] = min(session_deadline, t0 + 60 * args.job_limit_min)
        line = {"name": name, "type": job["type"]}
        try:
            eng = get_engine(merge(spec["engine"], job.get("engine", {})))
            torch.cuda.reset_peak_memory_stats(device)
            res = JOBS[job["type"]](eng, params, str(out_dir / name), **job.get("kwargs", {}))
            line["pass"] = bool(res.get("pass"))
            line["checks"] = res.get("checks")
        except JobTimeout as e:
            res = {"error": str(e)}
            line["pass"] = False
            line["error"] = "timeout"
        except Exception:
            res = {"error": traceback.format_exc()}
            line["pass"] = False
            line["error"] = res["error"].strip().splitlines()[-1]
            print(res["error"])
        line["seconds"] = time.time() - t0
        line["vram_peak_mb"] = torch.cuda.max_memory_allocated(device) / 2 ** 20
        line["engine"] = {"N": eng.N, "S": eng.S, "D": eng.D, "G": eng.G, "seed": eng.seed,
                          "build_seconds": getattr(eng, "build_seconds", None)}
        arrays = {}
        res = to_jsonable(res, arrays)
        res["job"] = job
        (out_dir / f"{name}.json").write_text(json.dumps(res, indent=1, default=str))
        if arrays:
            np.savez_compressed(out_dir / f"{name}.npz", **arrays)
        line = to_jsonable(line, {})
        (out_dir / f"{name}.summary.json").write_text(json.dumps(line, indent=1, default=str))
        if "error" not in line:
            done.write_text("ok\n")
        summary["jobs"].append(line)
        print(("PASS" if line["pass"] else "FAIL") + f" {name} ({job['type']}) in {line['seconds']:.1f} s"
              + (f"  error: {line.get('error')}" if line.get("error") else ""))
        summary_path.write_text(json.dumps(summary, indent=2, default=str))

    sampler.stop_flag = True
    summary["gpu_sampling"] = sampler.summary()
    summary["session_seconds"] = time.time() - t_session
    summary_path.write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps({k: summary[k] for k in ("gpu", "session_seconds", "gpu_sampling")}, indent=1))
    print("SESSION DONE")


if __name__ == "__main__":
    main()
