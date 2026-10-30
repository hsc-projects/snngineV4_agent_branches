"""
Probes of the engine's other CUDA paths on one built network (GPU, one configuration per process), saved for
test_engine_probes.py. Order matters: the destructive probes (synapse removal) come last.

  python engine_probes.py --n-neurons 2000 --n-synapses 200 [--chem-dim 30] [--seed 0] --out DIR

DIR/probes.npz and DIR/probes.json:
  presynaptic indices   rep_pre_synaptic, _idcs, _counts as built, then after RepBackend.actualize_N_rep_pre_synaptic
  stdp                  forced pre/post spike pairs on one E -> E synapse with STDP on (backend.update(True, ...)),
                        the synapse's weight before and after: causal, anti-causal, causal with the pair's STDP
                        configuration 0; the engine's STDP parameters
  ring buffer           a fraction of all neurons forced to fire every step for many steps (several rewinds of the
                        spike buffer); fired ids and synaptic input per step
  chemistry             the engine's concentration update (update_chemical_concentrations) from a random field
                        without sources (1 and 10 steps, twice from the same state) and with a point source;
                        grid size, k_val, depreciation
  inputs                N_states row 8 (the step's total input) with thalamic input on (set_noise) and with sensory
                        input on (N_flags row 0, group flags/properties), all weights zero
  removal               nullify_all_weights_to_group, then remove_synapses_to_group on one group
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

ROW_INPUT_TOTAL = 8          # update_N_state_ writes the step's total input here (N_states[n + 8 N] = i)
NO_STDP_STEPS = 20           # SnnSimulation.no_stdp_time_threshold (snn_simulation.cuh): no STDP while t <= 20


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-neurons", type=int, required=True)
    ap.add_argument("--n-synapses", type=int, required=True)
    ap.add_argument("--n-delays", type=int, default=None)
    ap.add_argument("--chem-dim", type=int, default=32)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--ring-fraction", type=float, default=0.9)
    ap.add_argument("--ring-steps", type=int, default=60)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    import torch
    from assoc_engine import AssocEngine, ROW_I, ROW_V, FLAG_TYPE, FLAG_GROUP

    t0 = time.time()
    eng = AssocEngine(torch.device("cuda:0"), n_neurons=a.n_neurons, seed=a.seed, n_synapses=a.n_synapses,
                      rewire=None, n_delays=a.n_delays, engine_chem_dim=a.chem_dim)
    N, S, D, G = eng.N, eng.S, eng.D, eng.G
    el, sim = eng.element, eng.backend
    syn = el.synapses
    out, meta = {}, {"N": N, "S": S, "D": D, "G": G, "seed": a.seed}
    rng = np.random.default_rng(a.seed + 5)
    types = eng.flags[FLAG_TYPE].cpu().numpy().astype(np.int64)
    groups = eng.flags[FLAG_GROUP].cpu().numpy().astype(np.int64)
    out["types"], out["groups"] = types, groups
    out["post"] = eng.n_rep.t().contiguous().cpu().numpy().astype(np.int64)
    out["bnd"] = eng.n_delays.t().contiguous().cpu().numpy().astype(np.int64)
    w_built = eng.weights.clone()
    out["w"] = w_built.t().contiguous().cpu().numpy().astype(np.float32)

    def gpu(x):
        return x.gpu_values if hasattr(x, "gpu_values") else x

    def pre_arrays(prefix):
        out[f"{prefix}_pre"] = gpu(syn.rep_pre_synaptic).reshape(-1).cpu().numpy().astype(np.int64)
        out[f"{prefix}_pre_idcs"] = gpu(syn.rep_pre_synaptic_idcs).reshape(-1).cpu().numpy().astype(np.int64)
        out[f"{prefix}_pre_counts"] = gpu(syn.rep_pre_synaptic_counts).reshape(-1).cpu().numpy().astype(np.int64)

    # ---- presynaptic indices: as built, then rebuilt by the engine's own kernel
    pre_arrays("built")
    syn.RepBackend.actualize_N_rep_pre_synaptic()
    torch.cuda.synchronize()
    pre_arrays("actualized")

    # ---- STDP on single synapses A -> B with delay >= 1
    post, bnd = out["post"], out["bnd"]
    stdp_params = ("phi_r", "phi_p", "a_r_p", "a_p_m", "a_r_m", "a_p_p", "max_w_exc", "min_w_exc", "max_w_inh",
                   "min_w_inh")

    # regular-spiking neurons only (reset c below -60): neurons with c near -50 and small d chatter, i.e. fire a
    # burst after a single forced spike, and every extra spike adds an STDP update
    c_reset = eng.states[5].cpu().numpy()
    regular = c_reset < -60.0

    def pick_synapse(src_type, snk_type):
        for A_ in rng.permutation(np.nonzero((types == src_type) & regular)[0]):
            for s in range(int(bnd[A_, 1]), S):
                B_ = int(post[A_, s])
                if types[B_] == snk_type and regular[B_] and B_ != A_ and (post[A_] == B_).sum() == 1:
                    return int(A_), B_, s, int(np.searchsorted(bnd[A_], s, side="right") - 1)
        raise RuntimeError(f"no single synapse {src_type} -> {snk_type} with delay >= 1")

    cfg0 = el.G2G_stdp_config0

    def pairing(A_, B_, s_, first, second, gap, config_value):
        """`first` fires, `gap` steps later `second` fires; STDP on; returns the A_ -> B_ weight before and after
        (all other neurons' outgoing weights zero)."""
        # the engine applies STDP only from simulation time t > no_stdp_time_threshold (20, snn_simulation.cuh):
        # make the quiet reset long enough that the whole pairing lies beyond it
        eng.reset_dynamics(quiet_steps=max(D + 2, NO_STDP_STEPS + 2 - int(sim.t)))
        assert int(sim.t) > NO_STDP_STEPS, "pairing would start before the engine enables STDP"
        eng.weights.zero_()
        eng.weights[:, A_] = w_built[:, A_]
        gpu(cfg0)[:] = int(config_value)
        sim.set_stdp_config(0, True)
        w0 = float(eng.weights[s_, A_])
        n_a = n_b = 0                              # spikes of A_ and B_ during the pairing (each should be 1)
        for k in range(gap + 2 * D + 2):
            if k == 0:
                eng.states[ROW_V, first] = 35.0
            if k == gap:
                eng.states[ROW_V, second] = 35.0
            sim.update(True, False)
            eng.t += 1
            n_a += int(eng.fired[A_] != 0)
            n_b += int(eng.fired[B_] != 0)
        return w0, float(eng.weights[s_, A_]), n_a, n_b

    A, B, s_ab, d_ab = pick_synapse(2, 2)
    meta["stdp"] = {"A": A, "B": B, "slot": s_ab, "delay": d_ab,
                    "params": {k: float(getattr(sim, k)) for k in stdp_params}}
    meta["stdp"]["causal"] = pairing(A, B, s_ab, A, B, d_ab + 1, 1)          # pre then post, after arrival
    meta["stdp"]["anticausal"] = pairing(A, B, s_ab, B, A, 1, 1)             # post then pre
    meta["stdp"]["causal_config0"] = pairing(A, B, s_ab, A, B, d_ab + 1, 0)  # no STDP configured for the pair
    # inhibitory -> excitatory, with the excitatory upper bound changed so that the bound of the weight's own type
    # (|min_w_inh|) and the excitatory one differ
    Ai, Bi, s_i, d_i = pick_synapse(1, 2)
    old_max = sim.max_w_exc
    sim.max_w_exc = 0.8
    meta["stdp_inh"] = {"A": Ai, "B": Bi, "slot": s_i, "delay": d_i,
                        "params": {k: float(getattr(sim, k)) for k in stdp_params},
                        "causal": pairing(Ai, Bi, s_i, Ai, Bi, d_i + 1, 1)}
    sim.max_w_exc = old_max
    gpu(cfg0)[:] = 0
    eng.weights.copy_(w_built)

    # ---- chemistry: C_old = c_current, C_new = c_next, C_source = c_source (Simulation), layout (h [+ padding], w, d)
    c0 = el.chemicals.C0
    shp = c0.config.shape
    w_, h_, d_ = int(shp.width), int(shp.height), int(shp.depth)
    meta["chem"] = {"w": w_, "h": h_, "d": d_, "k_val": float(sim.chem_k_val),
                    "depreciation": float(sim.chem_depreciation), "tensor_shape": list(c0.c_current.shape)}
    field0 = torch.as_tensor(rng.uniform(0.0, 100.0, size=(h_, w_, d_)).astype(np.float32), device=eng.device)
    eng.weights.zero_()

    def chem_run(steps, source=None):
        for t_ in (c0.c_current, c0.c_next):
            t_.zero_()
            t_[:h_] = field0
        c0.c_source.zero_()
        if source is not None:
            c0.c_source[source] = 500.0
        for _ in range(steps):
            eng.step()
        torch.cuda.synchronize()
        return c0.c_current[:h_].cpu().numpy().copy(), c0.c_next[:h_].cpu().numpy().copy()

    out["chem_field0"] = field0.cpu().numpy()
    out["chem_1_current"], out["chem_1_next"] = chem_run(1)
    out["chem_10_current"], _ = chem_run(10)
    out["chem_10_current_repeat"], _ = chem_run(10)
    src = (h_ // 2, w_ // 2, d_ // 2)
    meta["chem"]["source"] = list(src)
    out["chem_src_current"], _ = chem_run(10, source=src)
    for t_ in (c0.c_current, c0.c_next, c0.c_source):
        t_.zero_()

    # ---- inputs: N_states row 8 holds the step's total input; weights zero, so it is the external input only
    eng.set_noise(pt=1.0, exc_current=15.0, inh_current=25.0)
    eng.reset_dynamics()
    eng.weights.zero_()
    eng.step()
    out["input_thalamic_pt1"] = eng.states[ROW_INPUT_TOTAL].cpu().numpy().copy()
    eng.set_noise(pt=0.3, exc_current=15.0, inh_current=25.0)
    eng.reset_dynamics()
    eng.weights.zero_()
    eng.step()
    out["input_thalamic_pt03"] = eng.states[ROW_INPUT_TOTAL].cpu().numpy().copy()
    eng.set_noise(pt=0.0)
    meta["thalamic"] = {"exc_current": 15.0, "inh_current": 25.0}
    # sensory input: neurons flagged in N_flags row 0 receive current1 (group input type 1) or current0 (type 0)
    gflags, gprops = gpu(el.L_Group_flags), gpu(el.L_Group_properties)
    nflags = eng.flags
    sens = np.sort(rng.choice(N, max(1, N // 20), replace=False))
    sens_t = torch.as_tensor(sens, device=eng.device)
    g_type1 = int(groups[sens[0]])
    gflags[0, :] = 0                       # sensory_input_type 0 everywhere ...
    gflags[0, g_type1] = 1                 # ... and 1 in one group
    gprops[2, :] = 65.0                    # sensory_input_current0
    gprops[3, :] = 25.0                    # sensory_input_current1
    nflags[0, sens_t] = 1
    eng.reset_dynamics()
    eng.weights.zero_()
    eng.step()
    out["input_sensory"] = eng.states[ROW_INPUT_TOTAL].cpu().numpy().copy()
    out["sensory_ids"] = sens
    meta["sensory"] = {"group_type1": g_type1, "current0": 65.0, "current1": 25.0}
    nflags[0, sens_t] = 0
    eng.weights.copy_(w_built)

    # save what was recorded so far: an engine error in the removal steps (e.g. an illegal memory access, which ends
    # the CUDA context) then loses only the removal results
    def save():
        meta["seconds"] = time.time() - t0
        os.makedirs(a.out, exist_ok=True)
        np.savez(os.path.join(a.out, "probes.npz"), **out)
        with open(os.path.join(a.out, "probes.json"), "w") as f:
            json.dump(meta, f, indent=1)

    save()

    # ---- ring buffer under near-total activity: a fraction of the neurons forced to fire every step (after the
    # save: on an engine with the spike-buffer error this can end in an illegal memory access)
    eng.reset_dynamics()
    k_fire = int(a.ring_fraction * N)
    fired, inputs = [], []
    for k in range(a.ring_steps):
        ids = torch.as_tensor(np.sort(rng.choice(N, k_fire, replace=False)), device=eng.device)
        eng.states[ROW_V, ids] = 35.0
        sp = eng.step()
        fired.append(torch.nonzero(sp).view(-1).cpu().numpy().astype(np.int64))
        inputs.append(eng.states[ROW_I].cpu().numpy().copy())
    out["ring_fired"] = np.concatenate(fired)
    out["ring_offsets"] = np.cumsum([0] + [len(f) for f in fired]).astype(np.int64)
    out["ring_input"] = np.stack(inputs).astype(np.float32)
    eng.reset_dynamics()
    save()

    # ---- removal (last: changes N_rep)
    g_rm = int(np.bincount(groups).argmax())
    meta["removal"] = {"group": g_rm}
    syn.RepBackend.nullify_all_weights_to_group(group=g_rm)
    torch.cuda.synchronize()
    out["nullified_w"] = eng.weights.t().contiguous().cpu().numpy().astype(np.float32)
    pre_arrays("before_removal")
    syn.RepBackend.remove_synapses_to_group(group=g_rm)
    torch.cuda.synchronize()
    out["removed_post"] = eng.n_rep.t().contiguous().cpu().numpy().astype(np.int64)
    pre_arrays("after_removal")
    # with deleted synapses present: a second removal, zeroing weights and rebuilding the presynaptic index must
    # skip them (no out-of-range reads) and change nothing else
    syn.RepBackend.remove_synapses_to_group(group=g_rm)
    syn.RepBackend.nullify_all_weights_to_group(group=g_rm)
    torch.cuda.synchronize()
    out["removed_twice_post"] = eng.n_rep.t().contiguous().cpu().numpy().astype(np.int64)
    out["nullified_after_removal_w"] = eng.weights.t().contiguous().cpu().numpy().astype(np.float32)
    syn.RepBackend.actualize_N_rep_pre_synaptic()
    torch.cuda.synchronize()
    pre_arrays("rebuilt_after_removal")

    save()
    print(f"PROBES DONE N={N} S={S} D={D} G={G} in {meta['seconds']:.1f} s -> {a.out}")


if __name__ == "__main__":
    main()
