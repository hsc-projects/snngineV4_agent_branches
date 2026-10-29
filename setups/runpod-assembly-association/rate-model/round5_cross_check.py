"""
round5_cross_check.py

Round 5: does model A (population density) respond to a given set of learned weights as the spiking network does?
Both models are run on the SAME realization (neurons per group, synapse counts between groups) and the SAME group-level
learned weights, so that differences in the A-alone response are differences in the group dynamics, not in the
plasticity update or the sampled network.

  dumpB  --out F.npz [--seeds 0] [--pairs 0,1,3,6] [--rounds 1,2,3,5] [--set key=value ...]
         model B (full-scale reduced-spiking network): learns with joint rounds, and after the given rounds writes the
         group-level mean change of the effective weights (E -> E between groups, E -> I) and its own A-alone test
         (spikes per group, excitatory and inhibitory, and the maximum A_g per group).
  testA  --inp F.npz --out F.json [--set key=value ...]
         model A on the same realization with the same group-level weights: the same A-alone test.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

from spiking_group_model import (SpikeSpec, SpikingNetwork, run_round, KIND_EE, KIND_EI, KIND_EI_INTER, PLASTIC_LUT,
                                 W_LO, W_HI)
from rate_model import path_groups
from round5_diag_spiking import make_spec as make_spec_B, parse_set

HERE = os.path.dirname(os.path.abspath(__file__))


def group_counts(net: SpikingNetwork, chunk: int = 4000):
    """Synapse counts between groups by type: EE (inter-group plastic E -> E, diagonal 0), EI (all E -> I), IE (I -> E)."""
    G, S = net.G, net.S
    out = {k: np.zeros(G * G) for k in ("EE", "EI", "IE", "EE_all")}
    for lo in range(0, net.N, chunk):
        hi = min(lo + chunk, net.N)
        kd = net.kind[lo:hi]
        pre = np.broadcast_to(net.grp[lo:hi, None], kd.shape) * G
        key = pre + net.grp[net.post[lo:hi]]
        for name, mask in (("EE", kd == KIND_EE), ("EI", (kd == KIND_EI) | (kd == KIND_EI_INTER)), ("IE", kd == 3),
                           ("EE_all", (kd == KIND_EE) | (kd == 1))):
            out[name] += np.bincount(key[mask], minlength=G * G)
    res = {k: v.reshape(G, G) for k, v in out.items()}
    res["EE"] = res["EE_all"].copy()                      # A's counts["EE"] include the diagonal (intra-group, fixed)
    del res["EE_all"]
    return res


def aggregate_weights(net: SpikingNetwork, counts):
    """Mean change per synapse of the effective weight, by presynaptic group x postsynaptic group (E -> E between groups
    and E -> I), the quantity model A calls wf_ee and wf_ei."""
    G, S = net.G, net.S
    ids = net._touched_ids()
    out_ee, out_ei = np.zeros(G * G), np.zeros(G * G)
    if len(ids):
        w_eff = net.effective_normalized(ids)
        dw = w_eff - net.wp0.reshape(-1)[ids]
        kd = net.kind_f[ids]
        pre = net.grp[ids // S]
        post = net.grp[net.post_f[ids]]
        key = pre * G + post
        m = kd == KIND_EE
        out_ee = np.bincount(key[m], weights=dw[m], minlength=G * G)
        m = (kd == KIND_EI) | (kd == KIND_EI_INTER)
        out_ei = np.bincount(key[m], weights=dw[m], minlength=G * G)
    ee_n = counts["EE"] - np.diag(np.diag(counts["EE"]))
    wf_ee = out_ee.reshape(G, G) / np.maximum(ee_n, 1.0)
    wf_ei = out_ei.reshape(G, G) / np.maximum(counts["EI"], 1.0)
    return wf_ee, wf_ei


def b_test(net: SpikingNetwork, src: int):
    """A-alone test on the effective weights: spikes per group (E, I) and maximum A_g per group."""
    s = net.spec
    net.reset_dynamics()
    inj = net.inject_idx(src)
    eE, eI = np.zeros(net.G), np.zeros(net.G)
    gmax = np.zeros(net.G)
    tsE, tsI = np.zeros((s.test_window, net.G)), np.zeros((s.test_window, net.G))
    for i in range(s.test_window):
        A, nf = net.step(s.window, False, False, 1.0, False, False, False, inj if i < s.inject_steps else None)
        f = net.recent[0]
        if len(f):
            e = net.isE[f]
            tsE[i] = np.bincount(net.grp[f[e]], minlength=net.G)
            tsI[i] = np.bincount(net.grp[f[~e]], minlength=net.G)
        np.maximum(gmax, A, out=gmax)
    eE, eI = tsE.sum(axis=0), tsI.sum(axis=0)
    b_test.last_ts = (tsE, tsI)
    return eE, eI, gmax


def dump_b(a):
    over = parse_set(a.set)
    spec = make_spec_B(over)
    pairs_all = json.load(open(os.path.join(HERE, "s73_g9_d4_pairs.json")))
    seeds = [int(x) for x in a.seeds.split(",")]
    idx = [int(x) for x in a.pairs.split(",")]
    rounds = [int(x) for x in a.rounds.split(",")]
    out = {}
    for seed in seeds:
        net = SpikingNetwork(spec, seed=seed)
        counts = group_counts(net)
        for i in idx:
            pr = pairs_all[i]
            ia, ib = pr["A"], pr["B"]
            net.reset_all()
            key = f"s{seed}_p{i}"
            out[key + "_pair"] = np.array([ia, ib, pr["C"]])
            for r in range(1, max(rounds) + 1):
                run_round(net, [ia, ib], learn=True, consolidate=False, release1=True, release2=False)
                if r in rounds:
                    wf_ee, wf_ei = aggregate_weights(net, counts)
                    eE, eI, gmax = b_test(net, ia)
                    out[f"{key}_r{r}_wf_ee"], out[f"{key}_r{r}_wf_ei"] = wf_ee, wf_ei
                    out[f"{key}_r{r}_B_eE"], out[f"{key}_r{r}_B_eI"], out[f"{key}_r{r}_B_gmax"] = eE, eI, gmax
                    out[f"{key}_r{r}_B_tsE"], out[f"{key}_r{r}_B_tsI"] = b_test.last_ts[0].astype(np.int32), b_test.last_ts[1].astype(np.int32)
                    print(f"{key} round {r}: B A-alone spikes E {eE.sum():.0f} I {eI.sum():.0f} (own group {eE[ia]:.0f}/{eI[ia]:.0f}), "
                          f"groups >= 0.5 outside A: {(np.delete(gmax, ia) >= 0.5).sum()}", flush=True)
        out[f"s{seed}_nE"], out[f"s{seed}_nI"] = net.nE.astype(float), net.nI.astype(float)
        for k, v in counts.items():
            out[f"s{seed}_counts_{k}"] = v
    np.savez(a.out, **out)


def test_a(a):
    from popdensity_model import PopNetwork
    from round5_diag_popdensity import make_spec as make_spec_A
    over = parse_set(a.set)
    plast = float(over.pop("plast", 1.0))
    spec = make_spec_A(over, plast, 9)
    z = np.load(a.inp)
    rows = []
    for pk in sorted(k for k in z.files if k.endswith("_pair")):
        key = pk[:-len("_pair")]
        seed = int(key.split("_")[0][1:])
        ia, ib, ic = [int(x) for x in z[pk]]
        counts = {k: z[f"s{seed}_counts_{k}"] for k in ("EE", "EI", "IE")}
        net = PopNetwork(spec, seed=seed, counts=counts, sizes=(z[f"s{seed}_nE"], z[f"s{seed}_nI"]))
        for rk in sorted(k for k in z.files if k.startswith(key + "_r") and k.endswith("_wf_ee")):
            r = int(rk.split("_r")[1].split("_")[0])
            net.reset_all()
            net.wf_ee, net.wf_ei = z[f"{key}_r{r}_wf_ee"].copy(), z[f"{key}_r{r}_wf_ei"].copy()
            net.reset_dynamics()
            if a.diag and key.endswith("p0") and r == 3:
                gd = int(np.argsort(-z[f"{key}_r{r}_B_eE"])[1])       # busiest group other than A in B's test
                net.diag_group, net.diag_commits, net.diag_I, net.diag_E = gd, [], [], []
            else:
                net.diag_group = None
            w_ee, w_ei = net.weights("effective")
            inj = net.injection([ia])
            gmax = np.zeros(net.G)
            aE, aI = np.zeros((spec.test_window, net.G)), np.zeros((spec.test_window, net.G))
            for i in range(spec.test_window):
                e0, i0 = net.spk_E_total.copy(), net.spk_I_total.copy()
                net.step(inj=inj if i < spec.inject_steps else None, w_ee=w_ee, w_ei=w_ei, chem=False)
                aE[i], aI[i] = net.spk_E_total - e0, net.spk_I_total - i0
                np.maximum(gmax, net.activity(), out=gmax)
            eE, eI = net.spk_E_total.copy(), net.spk_I_total.copy()
            if net.diag_group is not None:
                I_t = np.array(net.diag_I)
                tot = sum(c[2] for c in net.diag_commits)
                after = 0
                multi = 0
                for (t0, L, n) in net.diag_commits:
                    # an I spike of the group registered between the commitment (step t0) and the excitatory spike (step t0 + L)
                    if I_t[t0:min(t0 + L, len(I_t))].sum() > 0 or (t0 + 1 < len(I_t) and I_t[t0 + 1:t0 + L].sum() > 0):
                        after += n
                    multi += n * (L > 1)
                print(f"  DIAG group {net.diag_group}: E commitments {tot}; with latency > 1 step: {multi}; committed before an I spike of the group and still fired: {after}", flush=True)
            if a.verbose and r == 3 and key.endswith("p0"):
                bE, bI = z[f"{key}_r{r}_B_tsE"], z[f"{key}_r{r}_B_tsI"]
                top = np.argsort(-(bE.sum(0) + aE.sum(0)))[:4]
                for g in top:
                    print(f"  group {g} (dist {np.linalg.norm(net.coords[g]-net.coords[ia]):.2f}) E per 5 steps  B {[int(bE[k:k+5, g].sum()) for k in range(0,60,5)]}")
                    print(f"                                  A {[int(aE[k:k+5, g].sum()) for k in range(0,60,5)]}")
                    print(f"                      I per 5 steps  B {[int(bI[k:k+5, g].sum()) for k in range(0,60,5)]}")
                    print(f"                                  A {[int(aI[k:k+5, g].sum()) for k in range(0,60,5)]}")
            bE, bI, bg = z[f"{key}_r{r}_B_eE"], z[f"{key}_r{r}_B_eI"], z[f"{key}_r{r}_B_gmax"]
            rows.append({"key": key, "round": r,
                         "A_spikes_E": float(eE.sum()), "A_spikes_I": float(eI.sum()), "B_spikes_E": float(bE.sum()), "B_spikes_I": float(bI.sum()),
                         "A_own_E": float(eE[ia]), "B_own_E": float(bE[ia]), "A_own_I": float(eI[ia]), "B_own_I": float(bI[ia]),
                         "A_out_E": float(eE.sum() - eE[ia]), "B_out_E": float(bE.sum() - bE[ia]),
                         "A_out_I": float(eI.sum() - eI[ia]), "B_out_I": float(bI.sum() - bI[ia]),
                         "A_groups_ge_0.5_outside": int((np.delete(gmax, ia) >= 0.5).sum()),
                         "B_groups_ge_0.5_outside": int((np.delete(bg, ia) >= 0.5).sum())})
            r_ = rows[-1]
            print(f"{key} r{r}: spikes E/I  A {r_['A_spikes_E']:.0f}/{r_['A_spikes_I']:.0f}  B {r_['B_spikes_E']:.0f}/{r_['B_spikes_I']:.0f}; "
                  f"out-of-group E A {r_['A_out_E']:.0f} B {r_['B_out_E']:.0f}; groups>=0.5 A {r_['A_groups_ge_0.5_outside']} B {r_['B_groups_ge_0.5_outside']}", flush=True)
    json.dump({"settings": {"overrides": over, "plast": plast}, "rows": rows}, open(a.out, "w"), indent=1)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["dumpB", "testA"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--inp")
    ap.add_argument("--seeds", default="0")
    ap.add_argument("--pairs", default="0,1,3,6")
    ap.add_argument("--rounds", default="1,2,3,5")
    ap.add_argument("--set", nargs="*", default=[])
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--diag", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.time()
    dump_b(a) if a.mode == "dumpB" else test_a(a)
    print("done", round(time.time() - t0), "s")


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    main()
