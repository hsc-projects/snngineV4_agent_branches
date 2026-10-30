"""
Build one engine network headlessly on the GPU and export what the tests check (one configuration per process:
the engine cannot be built twice in one process).

  python engine_export.py --n-neurons 2000 --n-synapses 200 [--n-delays D] [--seed 0] --out DIR

Writes DIR/network.npz (arrays below) and DIR/meta.json:
  post (N, S), bnd (N, D + 1), w (N, S)            synapse table, delay buckets, initial weights as built
  types, groups (N,), pos (N, 3), abcd (N, 4), v0, u0 (N,)   neurons and the post-warm-up state
  model_flag (N,)                                   N_flags row 3 (0: Izhikevich branch)
  g2g_delay (G, G), L (2 + 2 D, G)                  the engine's group-to-group delays and neuron counts by delay
  table_<src>_<snk> (D + 1, G)                      cumulative synapse counts per source group and delay, per type
                                                    connection, as the construction uses them (synapses.cc_syn_)
  probe_<k>_input (D + 1, N), probe_ids             delivery probe: neuron k fires once, all other weights zero;
                                                    synaptic input after each of D + 1 steps
  sim_fired, sim_offsets, sim_input, sim_inject     injected run: fired ids per step, synaptic input per step
The headless build uses the assembly harness's builder (setups/runpod-assembly-association/assoc_engine.py), the
only headless builder in the repository; its thalamic noise is switched off.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
HARNESS = os.path.join(REPO, "setups", "runpod-assembly-association")
for _p in (REPO, HARNESS):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-neurons", type=int, required=True)
    ap.add_argument("--n-synapses", type=int, required=True)
    ap.add_argument("--n-delays", type=int, default=None)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--reservoir-shape", type=float, nargs=3, default=(1.0, 1.0, 1.0))
    ap.add_argument("--probe-neurons", type=int, default=4, help="delivery probes (half inhibitory, half excitatory)")
    ap.add_argument("--sim-steps", type=int, default=100)
    ap.add_argument("--inject-current", type=float, default=20.0)
    ap.add_argument("--inject-steps", type=int, default=50)
    ap.add_argument("--inject-k", type=int, default=12)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    import torch
    from assoc_engine import AssocEngine, ROW_I, ROW_U, ROW_V, FLAG_TYPE, FLAG_GROUP

    t0 = time.time()
    eng = AssocEngine(torch.device("cuda:0"), n_neurons=a.n_neurons, seed=a.seed, n_synapses=a.n_synapses,
                      rewire=None, n_delays=a.n_delays, reservoir_shape=tuple(a.reservoir_shape))
    N, S, D, G = eng.N, eng.S, eng.D, eng.G
    el = eng.element
    cfg = el.config
    meta = {"N": N, "S": S, "D": D, "G": G, "seed": a.seed, "build_seconds": time.time() - t0,
            "shape": list(eng.reservoir_shape), "seg": list(eng.seg)}
    conns = []
    for c in cfg.type_conns.conns:
        conns.append({"src_type": int(c.src.ntype), "snk_type": int(c.snk.ntype), "n_synapses": int(c.n_synapses),
                      "w0": float(c.w0), "src_start": int(c.src.start_idx), "src_end": int(c.src.end_idx),
                      "syn_idx": int(c.syn_idx)})
    meta["conns"] = conns
    arr = {}
    arr["post"] = eng.n_rep.t().contiguous().cpu().numpy().astype(np.int32)
    arr["bnd"] = eng.n_delays.t().contiguous().cpu().numpy().astype(np.int32)
    w_built = eng.weights.clone()
    arr["w"] = w_built.t().contiguous().cpu().numpy().astype(np.float32)
    arr["types"] = eng.flags[FLAG_TYPE].cpu().numpy().astype(np.int64)
    arr["groups"] = eng.flags[FLAG_GROUP].cpu().numpy().astype(np.int64)
    arr["model_flag"] = eng.flags[3].cpu().numpy().astype(np.int64)
    arr["pos"] = eng.pos.cpu().numpy().astype(np.float64)
    st = eng.init_states
    arr["abcd"] = torch.stack([st[3], st[4], st[5], st[6]], dim=1).cpu().numpy().astype(np.float32)
    arr["v0"] = st[ROW_V].cpu().numpy().astype(np.float32)
    arr["u0"] = st[ROW_U].cpu().numpy().astype(np.float32)
    g2g = el.G2G_delay_distance
    g2g = g2g.gpu_values if hasattr(g2g, "gpu_values") else g2g
    arr["g2g_delay"] = g2g.reshape(G, G).cpu().numpy().astype(np.int64)
    L = el.L_Group_neuronCounts
    arr["L"] = (L.gpu_values if hasattr(L, "gpu_values") else L).cpu().numpy().astype(np.int64)
    counts = el.synapses.counts
    src_tab = counts.G_exp_ccsyn_per_src_type_and_delay.gpu_values.cpu().numpy().astype(np.int64)
    snk_tab = counts.G_exp_exc_ccsyn_per_snk_type_and_delay.gpu_values.cpu().numpy().astype(np.int64)
    # the tables each type connection is built from (synapses.py, cc_syn_)
    arr["table_1_2"] = src_tab[0:D + 1]           # inhibitory -> excitatory
    arr["table_2_1"] = snk_tab[0:D + 1]           # excitatory -> inhibitory
    arr["table_2_2"] = snk_tab[D + 1:2 * (D + 1)]  # excitatory -> excitatory

    # delivery probe: one neuron fires once (v above threshold at the start of a step), every other weight zero;
    # regular-spiking neurons only (reset c below -60): chattering ones fire a burst after one forced spike
    types = arr["types"]
    regular = eng.states[5].cpu().numpy() < -60.0
    rng = np.random.default_rng(a.seed + 11)
    k_half = max(1, a.probe_neurons // 2)
    probe_ids = np.concatenate([rng.choice(np.nonzero((types == 1) & regular)[0], k_half, replace=False),
                                rng.choice(np.nonzero((types == 2) & regular)[0], k_half, replace=False)])
    arr["probe_ids"] = probe_ids
    for j, n in enumerate(probe_ids):
        eng.reset_dynamics()
        eng.weights.zero_()
        eng.weights[:, int(n)] = w_built[:, int(n)]
        eng.states[ROW_V, int(n)] = 35.0
        rec = []
        for _ in range(D + 1):
            eng.step()
            rec.append(eng.states[ROW_I].cpu().numpy().copy())
        arr[f"probe_{j}_input"] = np.stack(rec).astype(np.float32)
    eng.weights.copy_(w_built)

    # injected run, the harness's stepping without clamp, fields or plasticity
    eng.reset_dynamics()
    g = int(np.argmax(np.bincount(arr["groups"][types == 2])))
    members = np.nonzero((arr["groups"] == g) & (types == 2))[0]
    inj = np.sort(rng.choice(members, min(a.inject_k, len(members)), replace=False))
    inj_t = torch.as_tensor(inj, device=eng.device)
    fired, inputs = [], []
    for t in range(a.sim_steps):
        sp = eng.step()
        fired.append(torch.nonzero(sp).view(-1).cpu().numpy().astype(np.int64))
        inputs.append(eng.states[ROW_I].cpu().numpy().copy())
        if t < a.inject_steps:
            eng.add_current(inj_t, a.inject_current)
    arr["sim_fired"] = np.concatenate(fired) if fired else np.zeros(0, np.int64)
    arr["sim_offsets"] = np.cumsum([0] + [len(f) for f in fired]).astype(np.int64)
    arr["sim_input"] = np.stack(inputs).astype(np.float32)
    arr["sim_inject"] = inj
    meta.update({"sim_steps": a.sim_steps, "inject_current": a.inject_current, "inject_steps": a.inject_steps,
                 "seconds": time.time() - t0})
    os.makedirs(a.out, exist_ok=True)
    np.savez(os.path.join(a.out, "network.npz"), **arr)
    with open(os.path.join(a.out, "meta.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print(f"EXPORT DONE N={N} S={S} D={D} G={G} in {meta['seconds']:.1f} s -> {a.out}")


if __name__ == "__main__":
    main()
