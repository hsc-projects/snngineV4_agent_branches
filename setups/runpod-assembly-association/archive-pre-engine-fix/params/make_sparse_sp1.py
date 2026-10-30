"""Writes params/sparse-sp1-substrate.json: Substeps 1 and 2 for S0 (lambda 0.4) and S1 (0.6, 1.0, 1.5)."""
import copy
import json
import os

here = os.path.dirname(os.path.abspath(__file__))
src = json.load(open(os.path.join(here, "session69a-stage2.json")))["jobs"][0]["params"]
base = copy.deepcopy(src)
for k in ("plasticity", "protocol", "c1", "c2", "learn_in_c2", "oracle", "pair_draw"):
    base.pop(k, None)
base.update({"assemblies": {"layout": "lattice", "spacing": 2}, "bridges": True,
             "protocol": {"pair_distance": 4.0}})

jobs = []
for lam in (0.4, 0.6, 1.0, 1.5):
    eng = {"n_neurons": 20000, "n_synapses": 2000, "seed": 0, "rewire": {"lam": lam, "seed": 0}}
    tag = f"lam{lam}"
    for typ, extra, kw in (("substep1", {}, {}),
                           ("single_synapse_threshold", {}, {}),
                           ("prop_survey", {}, {"n_pairs": 12}),
                           ("input_survey", {}, {"n_pairs": 12}),
                           ("hysteresis", {"hyst_sigma": 2.0}, {})):
        p = copy.deepcopy(base)
        p.update(extra)
        jobs.append({"name": f"sp1-{tag}-{typ}", "type": typ, "engine": eng, "params": p, "kwargs": kw})

out = {"session": "sp1-substrate", "engine": jobs[0]["engine"], "defaults": {"video": {"enabled": False}},
       "jobs": jobs}
with open(os.path.join(here, "sparse-sp1-substrate.json"), "w") as fh:
    json.dump(out, fh, indent=1)
print(len(jobs), "jobs")
