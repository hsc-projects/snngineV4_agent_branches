"""Writes params/sparse-sp2-substrate.json: Substep 2 for S2 to S5 at lambda 0.4 and 1.0 (no learning)."""
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
W_THR = 8.125          # measured single-synapse threshold (sp1), normalized inter-group E -> E weight

variants = {
    "S2-lamsup0.5": {"weights": {"inter_ee": {"kind": "powerlaw", "lam_sup": 0.5, "w_thr": W_THR, "mean": 0.05}}},
    "S2-lamsup1": {"weights": {"inter_ee": {"kind": "powerlaw", "lam_sup": 1.0, "w_thr": W_THR, "mean": 0.05}}},
    "S2-lamsup2": {"weights": {"inter_ee": {"kind": "powerlaw", "lam_sup": 2.0, "w_thr": W_THR, "mean": 0.05}}},
    "S3a-sig1": {"weights": {"inter_ee": {"kind": "lognormal", "sigma": 1.0, "mean": 0.05, "cap": W_THR}}},
    "S3a-sig0.51": {"weights": {"inter_ee": {"kind": "lognormal", "sigma": 0.51, "mean": 0.05, "cap": W_THR}}},
    "S3b-sig1": {"weights": {"inter_ee": {"kind": "lognormal", "sigma": 1.0, "mean": 0.045 * W_THR, "cap": W_THR}}},
    "S4": {"transmission": {"gain": 1.0, "c1_half": 0.05, "u_ref": 0.9},
           "c1": {"gain": 1.0, "k": 0.16, "decay": 0.0011}},
    "S5": {"silent": {"frac": 0.5, "v_half": -52.5, "v_width": 2.5}},
}
jobs = []
for lam in (0.4, 1.0):
    eng = {"n_neurons": 20000, "n_synapses": 2000, "seed": 0, "rewire": {"lam": lam, "seed": 0}}
    for vname, over in variants.items():
        for typ, kw, extra in (("prop_survey", {"n_pairs": 12}, {}), ("input_survey", {"n_pairs": 12}, {}),
                               ("hysteresis", {}, {"hyst_sigma": 2.0})):
            p = copy.deepcopy(base)
            for k, v in over.items():
                p[k] = dict(p.get(k, {}), **v) if isinstance(v, dict) and isinstance(p.get(k), dict) else v
            p.update(extra)
            jobs.append({"name": f"sp2-lam{lam}-{vname}-{typ}", "type": typ, "engine": eng, "params": p,
                         "kwargs": kw})
out = {"session": "sp2-substrate", "engine": jobs[0]["engine"], "defaults": {"video": {"enabled": False}},
       "jobs": jobs}
with open(os.path.join(here, "sparse-sp2-substrate.json"), "w") as fh:
    json.dump(out, fh, indent=1)
print(len(jobs), "jobs")
