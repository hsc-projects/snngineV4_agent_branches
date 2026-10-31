"""
round6_regime_precheck.py

Round 6 (rate-model-task.md), before the admission test: model B's outcome classes (contained / ignition / none of
the first transfer in the joint rounds, no controls) at a given regime, to tell whether a spiking ground truth at
that regime can discriminate (mixed classes). Two sources of networks:

  own     model B's own networks (realizations), at the 24 pair positions of the s71 ground truth (as
          admission_spiking_group.py eval), full size, settings of session69a-stage2.json with --set overrides
  export  exported engine networks (round6_export_engine.py; for wirings model B does not sample, e.g. the engine's
          own), at the pairs of the exported jobs, each with its job's plasticity, fields and protocol (spec_for, stray
          limit 10 % of all groups); --set must reproduce the exported jobs' gains (spec_for checks)

  python round6_regime_precheck.py own --realizations 0,1 --set gain_ee_inter=2.4 --out R.json [--workers N]
  python round6_regime_precheck.py export --exports DIR [DIR ...] --set gain_ee_inter=1.2 --out R.json [--workers N]
  --c2 adds the short-circuit stage (association after C2; with --set c2_uniform=1.2, C2 held uniform where released);
  its rows then also hold the final tests' strays per direction (final).

numpy only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

CLASSES = ("contained", "ignition", "none")


def _c2_fields(r: dict) -> dict:
    """The short-circuit stage's outcome: rounds, runaway and the step of each C2 round's stop, the consolidated shares
    of w_fast on and off the route (with neuron positions), the rollback record, and per direction of the final tests
    success, bounded, runaway, strays."""
    f = r.get("final")
    return {"c2_rounds": r.get("c2_rounds"), "c2_runaway_round": r.get("c2_runaway_round"), "c2_stops": r.get("c2_stops"),
            "consolidated": r.get("consolidated"), "rollback": r.get("rollback"),
            "final": None if f is None else {d: {"success": bool(f[d]["success"]), "bounded": bool(f[d]["bounded"]),
                                                 "runaway": f[d]["runaway"] is not None,
                                                 "strays": int(f[d]["n_active_outside"])} for d in ("A_to_B", "B_to_A")}}


def _own_job(args):
    over, seed, i, pr, c2 = args
    from admission_spiking_group import make_spec
    from spiking_group_model import SpikingNetwork, run_pair_protocol
    t0 = time.perf_counter()
    net = SpikingNetwork(make_spec(syn_scale=1.0, **over), seed=seed)
    r = run_pair_protocol(net, pr[0], pr[1], c2_stage=c2, control0=False)
    return {"source": f"own-{seed}", "pair_index": i, "A": int(pr[0]), "B": int(pr[1]), "class": r["class"],
            "association": r.get("association"),
            "strays": r.get("strays"), "c1_rounds": r.get("c1_rounds"), "runaway_round": r.get("runaway_round"),
            **_c2_fields(r), "seconds": time.perf_counter() - t0}


def _export_job(args):
    d, over, i, pair, c2 = args
    import numpy as np
    from round6_compare import spec_for
    from spiking_group_model import SpikingNetwork, run_pair_protocol
    t0 = time.perf_counter()
    meta = json.loads(open(os.path.join(d, "meta.json")).read())
    net = SpikingNetwork(spec_for(meta, export_dir=d, job=i, **over), seed=int(meta["seed"]))
    e2m = net.engine_to_model
    A, B = int(e2m[pair["A"]]), int(e2m[pair["B"]])
    inj = meta["jobs"][i]["inject"]                      # the engine's injected neurons (exported networks keep its order)
    net.set_injection(A, np.asarray(inj[str(pair["A"])]))
    net.set_injection(B, np.asarray(inj[str(pair["B"])]))
    r = run_pair_protocol(net, A, B, c2_stage=c2, control0=False)
    return {"source": os.path.basename(d.rstrip("/")), "pair_index": i, "job": meta["jobs"][i]["job"],
            "pair_engine": pair, "A": A, "B": B, "class": r["class"], "association": r.get("association"), "strays": r.get("strays"), "c1_rounds": r.get("c1_rounds"),
            "runaway_round": r.get("runaway_round"), **_c2_fields(r), "seconds": time.perf_counter() - t0}


def main(argv=None):
    from round5_diag_spiking import parse_set
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["own", "export"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--set", nargs="*", default=None)
    ap.add_argument("--realizations", default="0,1")
    ap.add_argument("--exports", nargs="*", default=[])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--c2", action="store_true", help="add the short-circuit stage (association after C2)")
    a = ap.parse_args(argv)
    over = parse_set(a.set)
    if a.mode == "own":
        from admission_test import seed_pairs
        _, pairs = seed_pairs(None)
        jobs = [(over, int(s), i, pr, a.c2) for s in a.realizations.split(",") for i, pr in enumerate(pairs)]
        fn = _own_job
    else:
        jobs = []
        for d in a.exports:
            meta = json.loads(open(os.path.join(d, "meta.json")).read())
            jobs += [(d, over, i, j["pair"], a.c2) for i, j in enumerate(meta["jobs"])]
        fn = _export_job
    t0 = time.time()
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        rows = list(ex.map(fn, jobs))
    by_source = {}
    for r in rows:
        c = by_source.setdefault(r["source"], {k: 0 for k in CLASSES})
        c[r["class"]] += 1
    total = {k: sum(c[k] for c in by_source.values()) for k in CLASSES}
    assoc = sum(1 for r in rows if r.get("association")) if a.c2 else None
    out = {"mode": a.mode, "settings": over, "c2_stage": a.c2, "n_simulations": len(rows), "counts": total,
           "associations": assoc, "counts_by_source": by_source,
           "runaways": sum(1 for r in rows if r.get("runaway_round")), "seconds": time.time() - t0, "rows": rows}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    print(json.dumps({k: out[k] for k in ("mode", "settings", "c2_stage", "n_simulations", "counts", "associations",
                                         "counts_by_source", "runaways", "seconds")}))


if __name__ == "__main__":
    main()
