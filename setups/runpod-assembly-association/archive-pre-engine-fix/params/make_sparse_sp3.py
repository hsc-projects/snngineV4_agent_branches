"""Writes params/sparse-sp3-inhibition.json: Substep 2 for S6 (inter-group inhibition) on S0, S2 and S3b."""
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
W_THR = 8.125
weights = {
    "S0": None,
    "S2": {"kind": "powerlaw", "lam_sup": 1.0, "w_thr": W_THR, "mean": 0.05},
    "S3b": {"kind": "lognormal", "sigma": 1.0, "mean": 0.045 * W_THR, "cap": W_THR},
}
inhib = {"ei0.5": (0.5, 1.0), "ei0.2": (0.2, 1.0), "ei0.05": (0.05, 1.0),
         "ie0.5": (1.0, 0.5), "ie0.2": (1.0, 0.2), "ie0.05": (1.0, 0.05), "both0.2": (0.2, 0.2)}
jobs = []
for lam in (0.4, 1.0):
    eng = {"n_neurons": 20000, "n_synapses": 2000, "seed": 0, "rewire": {"lam": lam, "seed": 0}}
    for sname, wspec in weights.items():
        for iname, (gei, gie) in inhib.items():
            if sname == "S3b" and iname not in ("ei0.2", "ei0.05", "both0.2"):
                continue
            for typ, kw, extra in (("prop_survey", {"n_pairs": 12}, {}), ("input_survey", {"n_pairs": 12}, {}),
                                   ("hysteresis", {}, {"hyst_sigma": 2.0})):
                p = copy.deepcopy(base)
                p["weights"] = dict(p["weights"], inter_ee=wspec)
                p.update({"gain_ei_inter": gei, "gain_ie_inter": gie}, **extra)
                jobs.append({"name": f"sp3-lam{lam}-{sname}-{iname}-{typ}", "type": typ, "engine": eng,
                             "params": p, "kwargs": kw})
out = {"session": "sp3-inhibition", "engine": jobs[0]["engine"], "defaults": {"video": {"enabled": False}},
       "jobs": jobs}
with open(os.path.join(here, "sparse-sp3-inhibition.json"), "w") as fh:
    json.dump(out, fh, indent=1)
print(len(jobs), "jobs")
