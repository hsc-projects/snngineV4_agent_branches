"""
Substeps 0 to 4 of setups/runpod-assembly-association/runpod-assembly-association-task.md
as job functions on an AssocEngine. Each returns a JSON-serializable result with its own
pass/fail entries; the queue runner (assoc_queue.py) calls them from parameter files.
"""

from __future__ import annotations

import copy
import math
import time

import numpy as np
import torch

from assoc_fields import ChemicalField, EnergyField, FuelField, GroupActivity, VoxelMap
from assoc_plasticity import GatedPlasticity, gate

DEFAULTS = {
    "window": 20, "active": 0.5, "inactive": 0.1,
    "k_inject": 3, "inject_current": 20.0, "inject_steps": 50, "gap_steps": 50, "test_window": 100,
    "weights": {"w_ee": None, "w_ei": None, "w_ie": None, "w_intra_ee": 1.0, "w_intra_ei": None},
    "vox_per_cell": 4,
    # which location groups are assemblies (assembly_layout); "all": every group (Substeps 1 to 7)
    "assemblies": {"layout": "all"},
    "c1": {"gain": 1.0, "k": 0.16, "decay": 0.002, "substeps": 1, "saturation": None},
    "c2": {"gain": 1.0, "k": 0.16, "decay": 0.01, "substeps": 1, "saturation": None},
    # A_g over excitatory neurons only, as the engine's G_firing_count_hist (user decision, iteration 18)
    "activity_exc_only": True,
    "c1_release_in_c2": True,
    # False: the C2 stage only consolidates the w_fast learned in the C1 rounds (no new learning)
    "learn_in_c2": True,
    "plasticity": {"a_plus": 0.05, "a_minus": 0.05, "tau_fast": 2000.0, "kappa": 0.01,
                   "theta1": 5.0, "theta2": 5.0, "soft1": 5.0, "soft2": 5.0},
    # in_c1 / in_c2 / in_test (iteration 47): energy per phase (default: `enabled`); shortcut 2 is
    # meant for the hardening under C2
    # mode "fuel" (iteration 58): C3 fuel (assoc_fields.FuelField) with supply, decay, consume, tau,
    # floor, beta, cap, k instead of the local energy; consume and k not given fall back to the
    # defaults below (0.05, 0.0), the others to FuelField's
    "energy": {"enabled": False, "consume": 0.05, "recover": 0.01, "k": 0.0, "exponent": 1.0},
    # sparse layouts (iteration 47, user decision): assemblies on the route between A and B are
    # bridges and count as path (may be active); C and off-route assemblies must stay inactive
    "bridges": False,
    "noise": {"pt": 0.0, "exc_current": 15.0, "inh_current": 25.0},
    "gain": 1.0,  # global synaptic current gain g: engine current per spike = g * w
    "gain_ei": 1.0,  # extra gain on excitatory-to-inhibitory synapses (times gain)
    "gain_ie": 1.0,  # extra gain on inhibitory-to-excitatory synapses (times gain)
    "gain_ee_inter": 1.0,  # extra gain on excitatory-to-excitatory synapses between groups (times gain)
    "inter_norm": False,  # normalize those gains by the target's in-degree (AssocEngine.set_gains, iteration 45)
    "train_noise": None,  # e.g. {"pt": 0.01}: background input during training rounds only
    # fluctuating background current in every phase (iteration 46), e.g. {"mu_e": 2.5, "sigma_e": 6,
    # "mu_i": 2.5, "sigma_i": 6, "warmup": 100}: each step every neuron gets mu + sigma * N(0, 1);
    # after each reset the network runs `warmup` steps without injection to reach its stationary state;
    # "targets": "ordinary" (iteration 52) gives it only to neurons outside assemblies (default "all")
    "bg": None,
    "i_min": None,  # lower clamp on the summed input current (numerical safeguard), e.g. -60
    "i_max": None,  # upper clamp on the summed input current (numerical safeguard), e.g. 100
    # stop a phase in the step in which more than this fraction of all neurons fires: the engine
    # rewinds its spike pointer at 13 * N spikes (snn_simulation.cu:414), which total runaway
    # over a D = 13 window reaches (iteration 23). None: off
    "runaway_frac": None,
    # accept_uncontained (iteration 47): a C1-phase transfer that spreads beyond the path still
    # ends the C1 phase and goes on to the C2 stage (instead of stopping without consolidation);
    # the final strict test still has to satisfy the criterion.
    # criterion (iteration 53, user decision): "bounded" = no runaway and at most max_active_frac of
    # all groups active (A_g >= active) outside A, B and the path, C counted like any other group;
    # "contained" = the earlier agent's check (C and every group outside A, B and the path <= inactive).
    # control_modes (iteration 54): any of "no_chemistry", "gating_off" (control 1) and "separate" (A and
    # B trained in alternating rounds); inject_mode "joint" (protocol) or "alternate" (used by "separate")
    "protocol": {"pair_distance": 2.0, "max_c1_rounds": 20, "c2_rounds": 5, "max_extra_c2_rounds": 10,
                 "c2_after_max_rounds": True, "strict_test": True, "controls": True,
                 "accept_uncontained": False, "criterion": "bounded", "max_active_frac": 0.1,
                 "control_modes": ["no_chemistry", "gating_off"], "inject_mode": "joint"},
    "video": {"enabled": False, "frame_stride": 2, "fps": 30},
    "deadline": None,
    # diagnostic (iteration 43), e.g. {"radius": 1.0}: C1 and C2 held fixed, gates fully open within
    # `radius` cells of segment A-B and closed elsewhere (pair-specific, never a protocol result)
    "oracle": None,
    "sel_radius": 1.0,  # radius of the path region in the selectivity telemetry (regions)
}


def _mean(x: torch.Tensor):
    return float(x.float().mean()) if x.numel() else None


def _ratio(m, s):
    return m / s if (m is not None and s is not None and s > 0) else None


def merge(base: dict, over: dict | None) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge(out[k], v)
        else:
            out[k] = v
    return out


class JobTimeout(RuntimeError):
    pass


def assembly_layout(group_cell: torch.Tensor, spec: dict | None) -> torch.Tensor | None:
    """
    Which location groups are assemblies (task Substep 8). spec["layout"]:
    "all" (None returned): every group, as in Substeps 1 to 7;
    "lattice": groups whose cell coordinates are all = offset (mod spacing); spacing 2 leaves one
    non-assembly cell between neighbouring assemblies along every axis and diagonal;
    "random": up to `count` groups in random order, each at Chebyshev distance > min_gap from
    every chosen one (min_gap 1: at least one non-assembly cell in between), seeded by `seed`.
    """
    spec = spec or {}
    layout = spec.get("layout", "all")
    if layout == "all":
        return None
    cells = group_cell.long()
    if layout == "lattice":
        sp, off = int(spec.get("spacing", 2)), int(spec.get("offset", 0))
        return ((cells - off) % sp == 0).all(dim=1)
    if layout == "random":
        rng = np.random.default_rng(int(spec.get("seed", 0)))
        gap, count = int(spec.get("min_gap", 1)), int(spec["count"])
        mask = torch.zeros(cells.shape[0], dtype=torch.bool, device=cells.device)
        for g in rng.permutation(cells.shape[0]).tolist():
            if int(mask.sum()) >= count:
                break
            if mask.any() and ((cells[mask] - cells[g]).abs().max(dim=1).values <= gap).any():
                continue
            mask[g] = True
        return mask
    raise ValueError(f"unknown assembly layout {layout!r}")


class AssocRun:
    """Fields, activity, plasticity and stimulation on top of one AssocEngine."""

    def __init__(self, eng, params: dict, rng_seed: int = 0):
        self.eng = eng
        self.p = merge(DEFAULTS, params)
        self.rng = np.random.default_rng(rng_seed)
        eng.set_noise(**self.p["noise"])
        dev = eng.device
        amask = assembly_layout(eng.group_cell, self.p["assemblies"])
        eng.set_assemblies(amask)   # before the gains and weights, which depend on it
        self.sparse = amask is not None
        self.asm = list(range(eng.G)) if amask is None else torch.nonzero(amask).view(-1).tolist()
        self.is_asm = torch.ones(eng.G, dtype=torch.bool, device=dev) if amask is None else amask
        eng.set_gains(self.p["gain"], self.p["gain_ei"], self.p["gain_ie"], self.p["gain_ee_inter"],
                      self.p["inter_norm"])
        v = int(self.p["vox_per_cell"])
        self.dims = tuple(s * v for s in eng.seg)
        self.vmap = VoxelMap(eng.pos, eng.reservoir_shape, self.dims)
        c1, c2 = self.p["c1"], self.p["c2"]
        self.C1 = ChemicalField(self.dims, dev, k=c1["k"], decay=c1["decay"], substeps=c1["substeps"])
        self.C2 = ChemicalField(self.dims, dev, k=c2["k"], decay=c2["decay"], substeps=c2["substeps"])
        e = self.p["energy"]
        if e.get("mode", "local") == "fuel":     # iteration 58: C3 fuel (FuelField)
            self.E = FuelField(self.dims, dev, **{k: e[k] for k in ("supply", "decay", "consume", "tau",
                                                                   "floor", "beta", "cap", "k") if k in e})
        else:
            self.E = EnergyField(self.dims, dev, consume=e["consume"], recover=e["recover"], k=e["k"],
                                 exponent=e["exponent"])
        self.act = GroupActivity(eng.groups, eng.G, window=self.p["window"],
                                 member_mask=eng.exc if self.p["activity_exc_only"] else None)
        self.base_w = eng.typed_weights(**self.p["weights"])
        if not hasattr(eng, "_delay_cache"):
            eng._delay_cache = eng.synapse_delays()
        self.delays = eng._delay_cache
        self.P = self.new_plasticity()
        eng.write_weights(self.base_w)
        self.video = None
        self.steps_run = 0
        self.t_loop = 0.0
        self.stopped = None      # runaway stop of the last run() call (see run)
        self.runaway_events = []
        self.last_group_max = None
        self.baselines = {}      # (src, dst) -> (G,) group maxima of the control-0 test
        bg = self.p.get("bg")
        self.bg = None           # (mu, sigma) per neuron, (N,) each
        if bg:
            exc = eng.exc
            self.bg = (torch.where(exc, float(bg["mu_e"]), float(bg["mu_i"])).to(dev),
                       torch.where(exc, float(bg["sigma_e"]), float(bg["sigma_i"])).to(dev))
            targets = bg.get("targets", "all")
            if targets == "ordinary":
                ordinary = (~eng.assembly_of_neuron()).float().to(dev)
                self.bg = (self.bg[0] * ordinary, self.bg[1] * ordinary)
            elif targets != "all":
                raise ValueError(f"unknown bg targets {targets!r}")
            self.bg_gen = torch.Generator(device=dev).manual_seed(int(rng_seed) + 7919)
        self.oracle = None       # (a, b) while C1 / C2 are held fixed along A-B (set_oracle)
        self.spike_acc = None    # optional (N,) spike counter, incremented by run()
        self.input_acc = None    # optional (N,) sum of the synaptic input per step, filled by run()
        self.elig = None         # optional (S, N) bool: synapses that transmitted (pre then post) in run()
        self._regions = {}       # (a, b) -> selectivity region masks (regions)

    def new_plasticity(self, **over) -> GatedPlasticity:
        pp = dict(self.p["plasticity"])
        pp.update(over)
        wi = self.p["weights"].get("w_intra_ee")
        normed = self.p["weights"].get("w_intra_ee_total") is not None
        fixed = self.eng.intra_ee_mask() if (normed or (wi is not None and wi > 1.0)) else None
        P = GatedPlasticity(self.eng.n_rep, self.delays, self.eng.exc, self.base_w, self.eng.D,
                            fixed=fixed, **pp)
        if getattr(self, "frozen_pair", None) is not None:
            P.plastic &= ~self.direct_mask(*self.frozen_pair)
        return P

    def direct_mask(self, a: int, b: int) -> torch.Tensor:
        """(S, N): valid synapses from a neuron of group a onto one of group b, or from b onto a."""
        g = self.eng.groups
        pre = g.view(1, -1).expand_as(self.eng.n_rep)
        post = g[torch.clamp(self.eng.n_rep.long(), min=0)]
        return (self.eng.n_rep >= 0) & (((pre == a) & (post == b)) | ((pre == b) & (post == a)))

    def direct_stats(self, a: int, b: int) -> dict:
        """Direct A <-> B synapses (telemetry, iteration 37): counts and summed initial weight."""
        g, exc = self.eng.groups, self.eng.exc
        out = {}
        for key, (s, t) in (("A_to_B", (a, b)), ("B_to_A", (b, a))):
            m = self.direct_mask(s, t) & (g.view(1, -1).expand_as(self.eng.n_rep) == s)
            pre_exc = exc.view(1, -1).expand_as(m)
            out[key] = {"n": int(m.sum()), "n_exc": int((m & pre_exc).sum()),
                        "w_exc_sum": float(self.base_w[m & pre_exc].sum())}
        return out

    # ------------------------------------------------------------ selection

    def group_dist(self, g0: int, g1: int) -> float:
        d = (self.eng.group_cell[g0] - self.eng.group_cell[g1]).float()
        return float(torch.linalg.norm(d))

    def pick_pair(self, distance: float):
        """A, B at (nearly) `distance` cells and C far from both, all three assemblies."""
        pool = torch.as_tensor(self.asm, device=self.eng.device)
        cells = self.eng.group_cell.float()[pool]
        for _ in range(100):
            ia = int(self.rng.integers(len(pool)))
            d = torch.linalg.norm(cells - cells[ia], dim=1)
            err = (d - float(distance)).abs()
            err[ia] = float("inf")
            cand = torch.nonzero(err <= err.min() + 1e-6).view(-1).tolist()
            if cand:
                ib = int(self.rng.choice(cand))
                dab = torch.minimum(d, torch.linalg.norm(cells - cells[ib], dim=1))
                order = torch.argsort(dab, descending=True).tolist()
                ic = int(self.rng.choice(order[:max(1, min(5, len(pool) // 10))]))
                return int(pool[ia]), int(pool[ib]), int(pool[ic])
        raise RuntimeError("no pair found")

    def inject_idx(self, g: int) -> torch.Tensor:
        members = torch.nonzero((self.eng.groups == g) & self.eng.exc).view(-1).cpu().numpy()
        k = min(int(self.p["k_inject"]), len(members))
        return torch.as_tensor(np.sort(self.rng.choice(members, size=k, replace=False)),
                               device=self.eng.device)

    # ------------------------------------------------------------ state

    def reset_all(self):
        self.C1.reset()
        self.C2.reset()
        if self.oracle is not None:
            self.apply_oracle()
        self.E.reset()
        self.P = self.new_plasticity()
        self.eng.write_weights(self.base_w)
        self.reset_dynamics()

    def reset_dynamics(self):
        self.eng.reset_dynamics()
        self.act.reset()
        self.P.reset_spike_state()
        self.E.reset()
        if self.bg is not None and int(self.p["bg"].get("warmup", 0)) > 0:
            video, self.video = self.video, None      # no frames of the warm-up
            self.run(int(self.p["bg"]["warmup"]), chem=False, header="background warm-up")
            self.steps_run -= int(self.p["bg"]["warmup"])
            self.video = video

    # ------------------------------------------------------------ stepping

    def run(self, steps: int, inject=(), inject_steps: int | None = None, learn=False, consolidate=False,
            release1=False, release2=False, chem=True, energy=None, track=(), header="", write_weights=None,
            on_inject_end=None):
        """
        Step the engine `steps` times. `inject`: list of index tensors, stimulated for the first
        `inject_steps` steps. Returns per-step activity of the tracked groups (T, len(track)),
        the per-step maximum over all other groups (T,), and the spike count.
        `on_inject_end`: optional callable, called without arguments after the last injection step
        (telemetry, e.g. gate_profile).
        With `runaway_frac` set, the phase stops in the first step in which more than that
        fraction of all neurons fires: `self.stopped` then describes it (else None), the event is
        appended to `self.runaway_events`, and the returned arrays end at that step.
        """
        eng, p = self.eng, self.p
        energy = p["energy"]["enabled"] if energy is None else energy
        inj_n = p["inject_steps"] if inject_steps is None else inject_steps
        track_t = torch.as_tensor(list(track), dtype=torch.long, device=eng.device)
        others = torch.ones(eng.G, dtype=torch.bool, device=eng.device)
        if len(track):
            others[track_t] = False
        a_track = torch.zeros((steps, len(track)), device=eng.device)
        a_other = torch.zeros(steps, device=eng.device)
        g_max = torch.zeros(eng.G, device=eng.device)
        n_spikes = torch.zeros((), device=eng.device)
        plastic = learn or consolidate
        need_counts = release1 or release2 or energy
        vid = self.video if (self.video is not None and p["video"]["enabled"]) else None
        stride = int(p["video"]["frame_stride"])
        deadline = p.get("deadline")
        frac = p.get("runaway_frac")
        limit = None if frac is None else float(frac) * eng.N
        clamp = p.get("i_min") is not None or p.get("i_max") is not None
        self.stopped = None
        n_run = steps
        t0 = time.perf_counter()
        eng.diag_phase = header.replace(",", ";")
        for i in range(steps):
            if deadline is not None and (i % 200 == 0) and time.time() > deadline:
                raise JobTimeout(f"deadline reached in phase '{header}'")
            spikes = eng.step()
            a = self.act.update(spikes, eng.t)
            n_now = spikes.sum()
            n_spikes += n_now
            if self.spike_acc is not None:
                self.spike_acc += spikes.float()
            if self.input_acc is not None:   # synaptic input only: read before injection / background
                self.input_acc += eng.input_current()
            if len(track):
                a_track[i] = a[track_t]
            a_other[i] = torch.where(others, a, torch.zeros_like(a)).max()
            torch.maximum(g_max, a, out=g_max)
            if limit is not None and float(n_now) > limit:
                self.stopped = {"phase": header, "step": i, "engine_t": int(eng.t), "spikes": int(n_now),
                                "fraction": float(n_now) / eng.N}
                self.runaway_events.append(self.stopped)
                n_run = i + 1
                break
            counts = self.vmap.counts(spikes) if need_counts else None
            if chem:
                if release1:
                    self.C1.release(counts, p["c1"]["gain"], p["c1"].get("saturation"))
                if release2:
                    self.C2.release(counts, p["c2"]["gain"], p["c2"].get("saturation"))
                self.C1.diffuse()
                self.C2.diffuse()
            if plastic:
                self.P.step(spikes, eng.t, self.vmap.sample(self.C1.c), self.vmap.sample(self.C2.c),
                            learn=learn, consolidate=consolidate)
                eng.write_weights(self.P.effective() if write_weights is None else write_weights(self.P))
            elif self.elig is not None:      # frozen phase (test): only record which synapses transmit
                self.elig |= self.P.ltp_events(spikes, eng.t)
                self.P.observe(spikes, eng.t)
            if energy:
                self.E.step(counts)
                eng.scale_current(self.E.excitability(self.vmap))
            if self.bg is not None:
                mu, sigma = self.bg
                eng.add_current_vector(mu + sigma * torch.randn(mu.shape, generator=self.bg_gen, device=mu.device))
            if clamp:
                eng.clamp_current(p.get("i_min"), p.get("i_max"))
            if i < inj_n:
                for idx in inject:
                    eng.add_current(idx, p["inject_current"])
            if on_inject_end is not None and i == inj_n - 1:
                on_inject_end()
            if vid is not None and i % stride == 0:
                vid.add(a.cpu().numpy(), self.C1.c.cpu().numpy(), self.C2.c.cpu().numpy(),
                        f"{header}  step {i}/{steps}  t={eng.t}")
        torch.cuda.synchronize() if eng.device.type == "cuda" else None
        self.t_loop += time.perf_counter() - t0
        self.steps_run += n_run
        self.last_group_max = g_max  # (G,) maximum A_g of every group over this call
        return a_track[:n_run].cpu().numpy(), a_other[:n_run].cpu().numpy(), int(n_spikes.item())

    def test(self, src: int, dst: int, c: int | None, strict: bool, energy=None, header="test",
             exclude=()):
        """Inject into src alone, everything frozen; B must reach A_B >= active within test_window."""
        p = self.p
        training = getattr(self, "training", False)
        self.set_noise_phase(False)
        w = self.P.w_perm if strict else self.P.effective()
        saved = self.eng.read_weights()
        self.eng.write_weights(torch.where(self.P.valid & ~self.P.fixed, torch.clamp(w, self.P.lo, self.P.hi), w))
        self.reset_dynamics()
        energy = self.phase_energy("test") if energy is None else energy
        track = [src, dst] + ([c] if c is not None else []) + [g for g in exclude if g not in (src, dst, c)]
        at, ao, ns = self.run(p["test_window"], inject=[self.inject_idx_cached(src)], track=track,
                              chem=False, energy=energy, header=header)
        self.eng.write_weights(saved)
        self.set_noise_phase(training)
        res = {
            "src_max": float(at[:, 0].max()), "dst_max": float(at[:, 1].max()),
            "c_max": float(at[:, 2].max()) if c is not None else None,
            "others_max": float(ao.max()), "spikes": ns,
            "dst_first_active_step": int(np.argmax(at[:, 1] >= p["active"])) if at[:, 1].max() >= p["active"] else None,
            "runaway": self.stopped,
        }
        res["success"] = res["dst_max"] >= p["active"]
        # contained: C and every group outside A, B and `exclude` (the path) stay inactive
        res["contained"] = (self.stopped is None and (res["c_max"] is None or res["c_max"] <= p["inactive"])
                            and res["others_max"] <= p["inactive"])
        # bounded (iteration 53): groups active outside src, dst and `exclude` (the path), C included
        outside = torch.ones(self.eng.G, dtype=torch.bool, device=self.eng.device)
        outside[torch.as_tensor([src, dst] + [g for g in exclude if g not in (src, dst)],
                                dtype=torch.long, device=self.eng.device)] = False
        gmax = self.last_group_max
        active_out = torch.nonzero(outside & (gmax >= p["active"])).view(-1)
        res["n_active_outside"] = int(active_out.numel())
        res["active_outside"] = active_out.tolist()
        res["n_above_inactive_outside"] = int((outside & (gmax > p["inactive"])).sum())
        res["bounded"] = (self.stopped is None and
                          res["n_active_outside"] <= int(float(p["protocol"]["max_active_frac"]) * self.eng.G))
        # telemetry only: rise of every other group above its own level in the same test before
        # training (control 0), so that an assembly's untrained spill is not counted as spread
        base = self.baselines.get((src, dst))
        if base is not None:
            outside = torch.ones(self.eng.G, dtype=torch.bool, device=self.eng.device)
            outside[torch.as_tensor(track, device=self.eng.device)] = False
            exc = float((self.last_group_max - base)[outside].max()) if outside.any() else 0.0
            res["others_excess_over_control0"] = exc
            res["contained_rel_control0"] = (self.stopped is None and exc <= p["inactive"]
                                             and (res["c_max"] is None or res["c_max"] <= p["inactive"]))
        return res

    def phase_energy(self, phase: str) -> bool:
        """Energy on in this phase ("c1", "c2" or "test"): energy.in_<phase>, default energy.enabled."""
        e = self.p["energy"]
        return bool(e.get(f"in_{phase}", e["enabled"]))

    def set_noise_phase(self, training: bool):
        """Background input: `train_noise` during training rounds (if set), `noise` otherwise (tests)."""
        self.training = bool(training)
        cfg = dict(self.p["noise"])
        if training and self.p.get("train_noise"):
            cfg.update(self.p["train_noise"])
        self.eng.set_noise(**cfg)

    def path_groups(self, a: int, b: int, radius: float = 1.0) -> list[int]:
        """
        Groups (other than A and B) whose cell centre lies within `radius` cells of segment A-B.
        With sparse assemblies only non-assembly cells count as path: another assembly that
        becomes active is a spurious association, not part of the path (agent's choice).
        """
        cells = self.eng.group_cell.float()
        pa, pb = cells[a], cells[b]
        ab = pb - pa
        t = torch.clamp(((cells - pa) @ ab) / torch.clamp(ab @ ab, min=1e-9), 0.0, 1.0)
        d = torch.linalg.norm(cells - (pa + t.view(-1, 1) * ab), dim=1)
        near = d <= radius + 1e-6
        if self.sparse and not self.p["bridges"]:
            near &= ~self.is_asm
        return [int(g) for g in torch.nonzero(near).view(-1).tolist() if g not in (a, b)]

    def inject_idx_cached(self, g: int) -> torch.Tensor:
        if not hasattr(self, "_inj_cache"):
            self._inj_cache = {}
        if g not in self._inj_cache:
            self._inj_cache[g] = self.inject_idx(g)
        return self._inj_cache[g]

    # ------------------------------------------------------------ telemetry

    def weight_change_stats(self, w_ref: torch.Tensor, w_new: torch.Tensor, a: int, b: int, eps=1e-6) -> dict:
        eng = self.eng
        dw = w_new - w_ref
        mask = (dw.abs() > eps) & self.P.valid
        s_idx, n_idx = torch.nonzero(mask, as_tuple=True)
        out = {"n_changed": int(mask.sum()), "sum_dw": float(dw[mask].sum()) if mask.any() else 0.0}
        if s_idx.numel() == 0:
            return out
        post = self.P.post[s_idx, n_idx]
        mid = 0.5 * (eng.pos[n_idx] + eng.pos[post]) / eng.cell_size
        pa = (eng.group_cell[a].float() + 0.5)
        pb = (eng.group_cell[b].float() + 0.5)
        ab = pb - pa
        t_raw = ((mid - pa) @ ab) / torch.clamp(ab @ ab, min=1e-9)
        tt = torch.clamp(t_raw, 0.0, 1.0)
        dist = torch.linalg.norm(mid - (pa + tt.view(-1, 1) * ab), dim=1)
        vals = dw[s_idx, n_idx]
        bins = torch.clamp((dist / 0.5).long(), max=19)
        cnt = torch.zeros(20, device=eng.device).index_add_(0, bins, torch.ones_like(vals))
        sw = torch.zeros(20, device=eng.device).index_add_(0, bins, vals)
        out["by_distance_from_AB_half_cells"] = {"count": cnt.cpu().tolist(), "sum_dw": sw.cpu().tolist()}
        # on the line (synapse midpoint within one cell of segment A-B) or off it, split by the
        # target's type and by position along A-B (iteration 36)
        on = dist < 1.0
        post_exc = eng.exc[post]
        pos = torch.bucketize(t_raw, torch.tensor([0.0, 1 / 3, 2 / 3, 1.0], device=eng.device), right=True)
        names = ("behind_A", "near_A", "middle", "near_B", "beyond_B")
        split = {}
        for band, bmask in (("on_line", on), ("off_line", ~on)):
            split[band] = {
                "post_exc": float(vals[bmask & post_exc].sum()), "post_inh": float(vals[bmask & ~post_exc].sum()),
                "n_post_exc": int((bmask & post_exc).sum()), "n_post_inh": int((bmask & ~post_exc).sum()),
                "along": {nm: float(vals[bmask & (pos == k)].sum()) for k, nm in enumerate(names)}}
        out["split"] = split
        return out

    def gate_profile(self, a: int, b: int, path: list[int]) -> dict:
        """
        Mean C1 gate, C2 gate and their product at the neurons of A and B, of the path groups and
        of all other groups, at this moment (telemetry; call at the end of an injection).
        """
        eng, P = self.eng, self.P
        g1 = gate(self.vmap.sample(self.C1.c), P.theta1, P.soft1)
        g2 = gate(self.vmap.sample(self.C2.c), P.theta2, P.soft2)
        cat = torch.full((eng.G,), 2, dtype=torch.long, device=eng.device)
        if path:
            cat[torch.as_tensor(path, device=eng.device)] = 1
        cat[a] = 0
        cat[b] = 0
        ncat = cat[eng.groups]
        out = {}
        for k, nm in enumerate(("AB", "path", "other")):
            m = ncat == k
            if not m.any():
                continue
            g12 = g1[m] * g2[m]
            out[nm] = {"g1": float(g1[m].mean()), "g2": float(g2[m].mean()), "g12": float(g12.mean()),
                       "frac_g12_open": float((g12 > 0).float().mean()), "n": int(m.sum())}
        return out

    def chem_profile(self, a: int, b: int) -> dict:
        """C1 / C2 at the A and B voxels' groups and along the A-B line (11 samples)."""
        eng = self.eng
        v = int(self.p["vox_per_cell"])
        pa = eng.group_cell[a].float() * v + v / 2
        pb = eng.group_cell[b].float() * v + v / 2
        prof = {}
        for name, f in (("C1", self.C1), ("C2", self.C2)):
            vals = []
            for s in np.linspace(0, 1, 11):
                q = torch.clamp((pa + float(s) * (pb - pa)).long(), min=0)
                q = torch.minimum(q, torch.tensor(self.dims, device=eng.device) - 1)
                vals.append(float(f.c[q[0], q[1], q[2]]))
            prof[name] = {"along_AB": vals, "max": float(f.c.max()), "mean": float(f.c.mean())}
        return prof

    # ------------------------------------------------------------ geometry relative to A-B

    def seg_coords(self, x: torch.Tensor, a: int, b: int):
        """
        For points x (..., 3) in cell units: t along A-B (0 at A, 1 at B, unclamped), distance to
        the infinite line A-B, to the segment A-B, and to the nearer of A and B (cell centres).
        """
        pa = self.eng.group_cell[a].float() + 0.5
        pb = self.eng.group_cell[b].float() + 0.5
        ab = pb - pa
        t = ((x - pa) @ ab) / torch.clamp(ab @ ab, min=1e-9)
        rho = torch.linalg.norm(x - (pa + t.unsqueeze(-1) * ab), dim=-1)
        d_seg = torch.linalg.norm(x - (pa + torch.clamp(t, 0.0, 1.0).unsqueeze(-1) * ab), dim=-1)
        d_end = torch.minimum(torch.linalg.norm(x - pa, dim=-1), torch.linalg.norm(x - pb, dim=-1))
        return t, rho, d_seg, d_end

    def voxel_centres(self) -> torch.Tensor:
        """(dx, dy, dz, 3) voxel centres of the chemical grid in cell units."""
        v = float(self.p["vox_per_cell"])
        axes = [(torch.arange(n, device=self.eng.device).float() + 0.5) / v for n in self.dims]
        return torch.stack(torch.meshgrid(*axes, indexing="ij"), dim=-1)

    # ------------------------------------------------------------ oracle chemistry (diagnostic)

    def set_oracle(self, a: int, b: int):
        """
        Diagnostic, pair-specific (iteration 43): C1 and C2 are held at a level that opens their
        gates fully in the voxels within `oracle.radius` cells of segment A-B, and at zero
        elsewhere; no release, diffusion or decay. Shows whether the plasticity rule and the network
        regime form a contained association when the chemistry marks the path perfectly.
        """
        self.oracle = (a, b)
        self.p["c1"]["gain"] = 0.0
        self.p["c2"]["gain"] = 0.0
        self.apply_oracle()

    def apply_oracle(self):
        a, b = self.oracle
        _, _, d_seg, _ = self.seg_coords(self.voxel_centres(), a, b)
        tube = d_seg <= float(self.p["oracle"].get("radius", 1.0)) + 1e-6
        pp = self.p["plasticity"]
        for f, th, so in ((self.C1, pp["theta1"], pp["soft1"]), (self.C2, pp["theta2"], pp["soft2"])):
            f.k, f.decay, f.depreciation = 0.0, 0.0, 0.0
            f.source = torch.where(tube, torch.full_like(f.c, float(th) + float(so) + 1.0), torch.zeros_like(f.c))
            f.c = f.source.clone()

    # ------------------------------------------------------------ path selectivity (telemetry)

    def regions(self, a: int, b: int) -> dict:
        """
        Two regions for the path selectivity (iteration 43), radius r = `sel_radius` cells:
        M (middle): within r of line A-B, 0.25 <= t <= 0.75;
        Sh (shell): farther than r from line A-B, but as far from the nearer of A and B as M is
        (d / 4 to sqrt((d / 2)^2 + r^2)), i.e. off the path at the same distance from the assemblies.
        Masks (M, Sh) for neurons (N,), synapses by their midpoint (S, N) and voxels; cached per pair.
        """
        if (a, b) in self._regions:
            return self._regions[(a, b)]
        eng = self.eng
        r = float(self.p["sel_radius"])
        d = self.group_dist(a, b)
        lo, hi = d / 4, math.sqrt((d / 2) ** 2 + r ** 2)

        def cat(x):
            t, rho, _, d_end = self.seg_coords(x, a, b)
            return ((rho < r) & (t >= 0.25) & (t <= 0.75),
                    (rho >= r) & (d_end >= lo) & (d_end <= hi))

        cells = eng.pos / eng.cell_size
        post = torch.clamp(eng.n_rep.long(), min=0)
        sm = torch.zeros(post.shape, dtype=torch.bool, device=eng.device)
        ss = torch.zeros_like(sm)
        for s0 in range(0, post.shape[0], 128):
            sm[s0:s0 + 128], ss[s0:s0 + 128] = cat(0.5 * (cells.unsqueeze(0) + cells[post[s0:s0 + 128]]))
        valid = eng.n_rep >= 0
        self._regions[(a, b)] = {"neuron": cat(cells), "synapse": (sm & valid, ss & valid),
                                 "voxel": cat(self.voxel_centres())}
        return self._regions[(a, b)]

    def selectivity(self, a: int, b: int) -> dict:
        """
        M against Sh (regions) at this moment: spikes per excitatory neuron counted in spike_acc,
        mean C1 / C2 in the voxels, mean C1 gate at the neurons, mean w_fast per plastic synapse
        by target type; `ratio` = M / Sh (None where Sh is empty or zero).
        """
        R, eng, P = self.regions(a, b), self.eng, self.P
        g1 = gate(self.vmap.sample(self.C1.c), P.theta1, P.soft1)
        post_exc = eng.exc[P.post]
        out = {}
        for k, name in enumerate(("M", "Sh")):
            n_m, v_m, s_m = R["neuron"][k], R["voxel"][k], R["synapse"][k] & P.plastic
            ne = n_m & eng.exc
            out[name] = {
                "n_exc": int(ne.sum()), "n_syn": int(s_m.sum()),
                "spikes_per_exc": (float(self.spike_acc[ne].sum()) / max(1, int(ne.sum()))
                                   if self.spike_acc is not None else None),
                "C1": _mean(self.C1.c[v_m]), "C2": _mean(self.C2.c[v_m]), "E": _mean(self.E.e[v_m]),
                "g1": _mean(g1[n_m]),
                "w_fast_ee": _mean(P.w_fast[s_m & post_exc]), "w_fast_ei": _mean(P.w_fast[s_m & ~post_exc])}
        out["ratio"] = {q: _ratio(out["M"][q], out["Sh"][q])
                        for q in ("spikes_per_exc", "C1", "C2", "E", "g1", "w_fast_ee", "w_fast_ei")}
        return out

    def weight_selectivity(self, a: int, b: int, dw: torch.Tensor) -> dict:
        """Mean weight change per plastic synapse in M and Sh by target type, and M / Sh."""
        R, P = self.regions(a, b), self.P
        post_exc = self.eng.exc[P.post]
        out = {}
        for k, name in enumerate(("M", "Sh")):
            s_m = R["synapse"][k] & P.plastic
            out[name] = {"n_ee": int((s_m & post_exc).sum()), "n_ei": int((s_m & ~post_exc).sum()),
                         "dw_ee": _mean(dw[s_m & post_exc]), "dw_ei": _mean(dw[s_m & ~post_exc])}
        out["ratio"] = {q: _ratio(out["M"][q], out["Sh"][q]) for q in ("dw_ee", "dw_ei")}
        return out


# ======================================================================== substeps

def _video(run: AssocRun, marks: dict):
    from assoc_video import AssocVideo
    cell = {k: tuple(int(x) for x in run.eng.group_cell[g].tolist()) for k, g in marks.items()}
    v = AssocVideo(run.eng.seg, cell, c_scale=max(run.p["plasticity"]["theta1"] * 3, 1.0))
    v.set_group_coords(run.eng.group_cell.cpu().numpy())
    return v


def substep0_harness(eng, params: dict, out_prefix: str) -> dict:
    """Quiet baseline, Python-side injection, weight writes between steps, structure, voxel mapping."""
    run = AssocRun(eng, params, rng_seed=eng.seed)
    p = run.p
    res = {"structure": eng.structure_report(), "checks": {}}
    st = res["structure"]
    res["checks"]["structure"] = bool(
        st["n_rep_shape"] == [eng.S, eng.N] and st["weights_shape"] == [eng.S, eng.N]
        and st["n_delays_shape"] == [eng.D + 1, eng.N] and st["n_delays_row0_zero"]
        and st["n_delays_last_row_is_S"] and st["n_delays_monotone"]
        and st["weights_ptr_stable"] and st["states_ptr_stable"]
        and st["thalamic_flags_on"] == 0 and st["pt_nonzero"] == 0)
    dly = run.delays
    res["delay_histogram"] = torch.bincount(dly.view(-1), minlength=eng.D).cpu().tolist()

    # quiet baseline
    run.reset_all()
    _, ao, ns = run.run(500, header="baseline")
    res["baseline"] = {"max_A_g": float(ao.max()), "spikes": ns}
    res["checks"]["baseline_quiet"] = bool(ao.max() <= p["inactive"])

    # python-side injection with all weights zero: only injected neurons fire
    g = int(run.rng.integers(eng.G))
    idx = run.inject_idx(g)
    zero_w = torch.zeros_like(run.base_w)
    eng.write_weights(zero_w)
    run.reset_dynamics()
    eng.write_weights(zero_w)
    inj_spikes = torch.zeros(eng.N, device=eng.device)
    for i in range(p["inject_steps"]):
        s = eng.step()
        inj_spikes += s.float()
        eng.add_current(idx, p["inject_current"])
    others = inj_spikes.clone()
    others[idx] = 0
    res["python_injection"] = {"group": g, "injected": idx.tolist(), "spikes_injected": inj_spikes[idx].tolist(),
                               "spikes_other": int(others.sum())}
    res["checks"]["python_injection"] = bool(inj_spikes[idx].min() > 0 and others.sum() == 0)

    # weights written from Python between steps are what update_current_ delivers: the synaptic
    # current pending in row 7 for non-injected neurons doubles when the weights are doubled
    # (only synapses leaving the injected neurons are kept, so the injected spike trains are
    # identical in both runs and the pending current comes from them alone)
    post = torch.clamp(eng.n_rep.long(), min=0)
    is_inj = torch.zeros(eng.N, dtype=torch.bool, device=eng.device)
    is_inj[idx] = True
    keep = is_inj.view(1, -1) & ~is_inj[post]
    w1 = torch.where(keep, run.base_w, torch.zeros_like(run.base_w))
    pending = []
    for scale in (1.0, 2.0):
        eng.write_weights(w1 * scale)
        run.reset_dynamics()
        acc = torch.zeros((), device=eng.device)
        for i in range(p["inject_steps"]):
            eng.step()
            row = eng.states[7].clone()
            row[idx] = 0
            acc += row.abs().sum()
            eng.add_current(idx, p["inject_current"])
        pending.append(float(acc))
    ratio = pending[1] / max(pending[0], 1e-9)
    res["weights_used"] = {"pending_current_w": pending[0], "pending_current_2w": pending[1], "ratio": ratio}
    res["checks"]["weights_written_between_steps"] = bool(pending[0] > 0 and abs(ratio - 2.0) < 1e-3)
    eng.write_weights(run.base_w)
    res["checks"]["weights_read_back"] = bool(torch.allclose(eng.read_weights(), run.base_w))

    # voxel mapping: every neuron's voxel lies inside its group's cell block
    v = int(p["vox_per_cell"])
    cell_of_voxel = torch.div(run.vmap.ijk, v, rounding_mode="floor")
    gc = eng.group_cell[eng.groups]
    res["voxel_mapping"] = {
        "dims_xyz": list(run.dims), "voxels_per_cell": v,
        "rule": "voxel = floor(pos / reservoir_shape * dims) per axis (x, y, z); own grid, not the engine C0 grid",
        "neurons_in_own_group_cell": float((cell_of_voxel == gc).all(dim=1).float().mean()),
    }
    res["checks"]["voxel_mapping"] = res["voxel_mapping"]["neurons_in_own_group_cell"] > 0.999

    # telemetry + video: a short stimulated run with C1 release
    run.reset_all()
    a, b, c = run.pick_pair(p["protocol"]["pair_distance"])
    run.video = _video(run, {"A": a, "B": b, "C": c})
    p["video"]["enabled"] = True
    at, ao, ns = run.run(p["inject_steps"] + p["gap_steps"], inject=[run.inject_idx_cached(a), run.inject_idx_cached(b)],
                         release1=True, track=[a, b, c], header="harness demo: inject A+B, C1 release")
    p["video"]["enabled"] = False
    n_frames = run.video.write(out_prefix + "_harness.mp4", fps=p["video"]["fps"])
    run.video = None
    res["demo"] = {"pair": [a, b, c], "A_max": float(at[:, 0].max()), "B_max": float(at[:, 1].max()),
                   "C_max": float(at[:, 2].max()), "others_max": float(ao.max()), "frames": n_frames,
                   "chem": run.chem_profile(a, b)}
    res["checks"]["video_written"] = n_frames > 0
    res["timing"] = {"steps": run.steps_run, "loop_s": run.t_loop,
                     "steps_per_s": run.steps_run / max(run.t_loop, 1e-9)}
    res["pass"] = all(res["checks"].values())
    return res


def substep1_activation(eng, params: dict, out_prefix: str, n_groups: int = 5) -> dict:
    run = AssocRun(eng, params, rng_seed=eng.seed + 1)
    p = run.p
    pool = np.asarray(run.asm)
    groups = pool[run.rng.choice(len(pool), size=min(n_groups, len(pool)), replace=False)].tolist()
    st = eng.structure_report()
    # unstimulated activity with the same settings (background noise, weights)
    run.reset_all()
    _, ao_base, ns_base = run.run(300, chem=False, header="Substep 1 baseline")
    base = {"others_max": float(ao_base.max()), "spikes": ns_base,
            "rate_hz": ns_base / eng.N / 0.3}
    intra = eng.intra_ee_mask()
    rows = []
    for j, g in enumerate(groups):
        run.reset_all()
        if j == 0 and params.get("video", {}).get("enabled"):
            run.video = _video(run, {"A": g})
        at, ao, ns = run.run(p["inject_steps"] + p["gap_steps"], inject=[run.inject_idx_cached(g)], track=[g],
                             chem=False, header=f"Substep 1: inject group {g}")
        if run.video is not None:
            run.video.write(out_prefix + "_activation.mp4", fps=p["video"]["fps"])
            run.video = None
        a_max = float(at[:, 0].max())
        a_end = float(at[-1, 0])  # end of the gap, or the step a runaway stop ended the run
        runaway = run.stopped
        inj = run.inject_idx_cached(g)
        in_g = intra[:, eng.groups == g]
        rows.append({"group": int(g), "A_max": a_max, "A_at_end_of_gap": a_end, "others_max": float(ao.max()),
                     "spikes": ns, "runaway": runaway,
                     "pass": runaway is None and a_max >= p["active"] and float(ao.max()) <= p["inactive"],
                     "size": int(eng.group_size[g]), "exc_size": int(eng.group_exc_size[g]),
                     "intra_ee_from_injected": int(intra[:, inj].sum()),
                     "intra_ee_per_exc_neuron": float(in_g.sum()) / max(1, int(eng.group_exc_size[g]))})
    counts = {"n_groups": len(rows), "n_pass": sum(r["pass"] for r in rows),
              "n_under_recruited": sum(r["A_max"] < p["active"] for r in rows),
              "n_spill": sum(r["others_max"] > p["inactive"] for r in rows),
              "n_runaway": sum(r["runaway"] is not None for r in rows),
              "spilling_groups": [r["group"] for r in rows if r["others_max"] > p["inactive"]],
              "under_recruited_groups": [r["group"] for r in rows if r["A_max"] < p["active"]]}
    return {"groups": rows, "pass": all(r["pass"] for r in rows) and base["others_max"] <= p["inactive"],
            "counts": counts, "baseline": base, "noise": eng.noise, "k_inject": p["k_inject"], "gain": eng.gain,
            "network": {k: st[k] for k in ("N", "S", "requested_S", "D", "G", "group_size_mean",
                                           "intra_group_ee_synapses_per_exc_neuron")},
            "timing": {"steps": run.steps_run, "loop_s": run.t_loop}}


def substep2_chemistry(eng, params: dict, out_prefix: str) -> dict:
    run = AssocRun(eng, params, rng_seed=eng.seed + 2)
    p = run.p
    res = {"checks": {}}

    # (a) release proportional to activity: scale the stimulus (k injected neurons)
    g = int(run.rng.integers(eng.G))
    rel = []
    for k in (1, 2, 4):
        run.reset_all()
        run.C1.decay = 0.0
        p["k_inject"] = k
        idx = run.inject_idx(g)
        _, _, ns = run.run(p["inject_steps"], inject=[idx], release1=True, chem=True, header="release")
        rel.append({"k": k, "spikes": ns, "C1_total": float(run.C1.c.sum())})
    p["k_inject"] = merge(DEFAULTS, params)["k_inject"]
    run.C1.decay = p["c1"]["decay"]
    ratios = [r["C1_total"] / max(r["spikes"], 1) for r in rel]
    res["release"] = {"runs": rel, "C1_per_spike": ratios, "gain": p["c1"]["gain"]}
    res["checks"]["release_proportional"] = all(abs(x - p["c1"]["gain"]) <= 1e-3 * p["c1"]["gain"] for x in ratios) \
        and rel[-1]["spikes"] > rel[0]["spikes"]

    # (b) diffusion matches the engine's C0 kernel on one identical clamped source
    run.reset_dynamics()     # steps the engine; done before the sources are set
    c0 = eng.element.chemicals.C0
    h, w, d = int(c0.config.shape.height), int(c0.config.shape.width), int(c0.config.shape.depth)
    for t in (c0.c_current, c0.c_next, c0.c_source):
        t.zero_()
    eng.backend.chem_k_val = 0.16
    eng.backend.chem_depreciation = 0.0
    mine = ChemicalField((h, w, d), eng.device, k=0.16, decay=0.0, depreciation=0.0)
    ci, cj, ck = h // 2, w // 2, d // 2
    view = lambda t: t.view(-1)[: h * w * d].view(h, w, d)
    for t in (view(c0.c_source), view(c0.c_current), view(c0.c_next)):
        t[ci - 1:ci + 1, cj - 1:cj + 1, ck - 1:ck + 1] = 2000.0
    mine.source[ci - 1:ci + 1, cj - 1:cj + 1, ck - 1:ck + 1] = 2000.0
    mine.c.copy_(mine.source)
    n_cmp = 60
    for _ in range(n_cmp):
        eng.step()           # one engine diffusion update per engine step
        mine.diffuse(1)
    eng_c = view(c0.c_current).clone()
    err = (eng_c - mine.c).abs()
    res["kernel_comparison"] = {"grid_hwd": [h, w, d], "steps": n_cmp, "max_abs_err": float(err.max()),
                                "max_value": float(mine.c.max()),
                                "rel_err": float(err.max() / max(float(mine.c.max()), 1e-9)),
                                "mass_engine": float(eng_c.sum()), "mass_mine": float(mine.c.sum()),
                                "outside_source_max_engine": float(eng_c[ci + 3, cj, ck]),
                                "outside_source_max_mine": float(mine.c[ci + 3, cj, ck])}
    res["checks"]["diffusion_matches_kernel"] = res["kernel_comparison"]["rel_err"] < 1e-3
    for t in (c0.c_current, c0.c_next, c0.c_source):
        t.zero_()

    # (c) plume around an active assembly that fades afterwards
    run.reset_all()
    a, b, c = run.pick_pair(p["protocol"]["pair_distance"])
    v = int(p["vox_per_cell"])
    pa = (eng.group_cell[a] * v + v // 2).tolist()
    far = (eng.group_cell[c] * v + v // 2).tolist()
    trace = []
    idx = run.inject_idx_cached(a)
    for phase, n, inj in (("on", p["inject_steps"], True), ("off", 300, False)):
        for chunk in range(n // 10):
            run.run(10, inject=[idx] if inj else [], inject_steps=10, release1=True, header="plume")
            trace.append({"phase": phase, "C1_at_A": float(run.C1.c[pa[0], pa[1], pa[2]]),
                          "C1_far": float(run.C1.c[far[0], far[1], far[2]]),
                          "C1_total": float(run.C1.c.sum())})
    peak = max(x["C1_at_A"] for x in trace)
    end = trace[-1]["C1_at_A"]
    res["plume"] = {"group": a, "far_group": c, "trace": trace, "peak_at_A": peak, "end_at_A": end}
    res["checks"]["plume_forms_and_fades"] = bool(peak > 0 and peak > 5 * max(x["C1_far"] for x in trace)
                                                  and end < 0.5 * peak)

    # (d) energy (optional shortcut): suppresses nearby activity outside the active assembly
    if p["energy"]["enabled"] or params.get("test_energy", True):
        g = a
        near = [int(x) for x in torch.nonzero(
            torch.linalg.norm((eng.group_cell - eng.group_cell[g]).float(), dim=1) == 1.0).view(-1).tolist()]
        out = {}
        for on in (False, True):
            run.reset_all()
            at, ao, ns = run.run(p["inject_steps"] * 2, inject=[run.inject_idx_cached(g)],
                                 inject_steps=p["inject_steps"] * 2, track=[g] + near, chem=False, energy=on,
                                 header="energy")
            out["on" if on else "off"] = {"A_mean": float(at[:, 0].mean()),
                                          "near_mean": float(at[:, 1:].mean()) if near else 0.0, "spikes": ns}
        e_min = float(run.E.e.min())
        run.run(300, chem=False, energy=True, header="energy recovery")
        out["e_min_after_drive"] = e_min
        out["e_min_after_300_quiet_steps"] = float(run.E.e.min())
        res["energy"] = out
        res["checks_energy"] = {
            "suppresses_nearby": out["on"]["near_mean"] < out["off"]["near_mean"] or out["off"]["near_mean"] == 0.0,
            "recovers": out["e_min_after_300_quiet_steps"] > e_min,
        }
    res["pass"] = all(res["checks"].values())
    return res


def substep3_plasticity(eng, params: dict, out_prefix: str) -> dict:
    """Gated plasticity on the real synapse tensors, driven by synthetic clamped spikes and chemistry."""
    run = AssocRun(eng, params, rng_seed=eng.seed + 3)
    P = run.P
    dev = eng.device
    gen = torch.Generator(device=dev).manual_seed(eng.seed + 3)
    x = eng.pos[:, 0] / eng.reservoir_shape[0]
    th1, th2 = P.theta1 + P.soft1 + 1.0, P.theta2 + P.soft2 + 1.0
    c1 = torch.where(x < 0.5, torch.tensor(th1, device=dev), torch.tensor(0.0, device=dev))
    c2 = torch.where(x < 0.25, torch.tensor(th2, device=dev), torch.tensor(0.0, device=dev))
    w0 = P.w_perm.clone()
    rate = 0.05
    for t in range(1, 401):
        spikes = torch.rand(eng.N, generator=gen, device=dev) < rate
        P.step(spikes, t, c1, c2, learn=True, consolidate=False)
    post_x = x[P.post]
    changed_fast = (P.w_fast != 0) & P.valid
    res = {"checks": {}}
    res["checks"]["fast_changes_only_where_C1_gate_on"] = bool(changed_fast.any()) and not bool(
        (changed_fast & (post_x >= 0.5)).any())
    res["checks"]["perm_unchanged_without_consolidation"] = bool(torch.equal(P.w_perm, w0))
    fast_before = P.w_fast.clone()
    for t in range(401, 451):
        P.step(torch.zeros(eng.N, dtype=torch.bool, device=dev), t, c1, c2, learn=False, consolidate=True)
    dperm = (P.w_perm - w0).abs() > 0
    res["checks"]["perm_changes_only_where_C1_and_C2_on"] = bool(dperm.any()) and not bool((dperm & (post_x >= 0.25)).any())
    perm = P.w_perm.clone()
    # decay of the remaining fast part: no gate, learning on, no spikes
    zero = torch.zeros(eng.N, device=dev)
    ref = P.w_fast.clone()
    n_dec = 500
    for t in range(451, 451 + n_dec):
        P.step(torch.zeros(eng.N, dtype=torch.bool, device=dev), t, zero, zero, learn=True, consolidate=False)
    expected = ref * (P.fast_decay ** n_dec)
    res["checks"]["fast_decays_as_specified"] = bool(torch.allclose(P.w_fast, expected, rtol=1e-3, atol=1e-7))
    res["checks"]["perm_persists"] = bool(torch.equal(P.w_perm, perm))
    w = P.effective()
    res["checks"]["bounds"] = bool(((w >= P.lo - 1e-6) & (w <= P.hi + 1e-6)).all())
    res["stats"] = {"n_fast_changed": int(changed_fast.sum()), "n_perm_changed": int(dperm.sum()),
                    "mean_abs_fast_before_consolidation": float(fast_before.abs().mean()),
                    "fast_decay_per_step": P.fast_decay}
    res["pass"] = all(res["checks"].values())
    return res


def control_key(mode: str) -> str:
    """Result key of a control run: control 1 (chemistry or gating disabled) or the joint-activation control."""
    return f"control1_{mode}" if mode in ("no_chemistry", "gating_off") else f"control_{mode}"


def round_inject(pr: dict, r: int, ia, ib) -> list:
    """
    Neurons injected in training round r (0-based): A and B together ("joint", the protocol), or
    (inject_mode "alternate", the joint-activation control of iteration 54) A alone in even rounds and
    B alone in odd rounds, so that A and B are never active together.
    """
    mode = pr.get("inject_mode", "joint")
    if mode == "joint":
        return [ia, ib]
    if mode == "alternate":
        return [ia] if r % 2 == 0 else [ib]
    raise ValueError(f"unknown inject_mode {mode!r}")


def criterion_key(pr: dict) -> str:
    """Name of the test field that decides a transfer (protocol.criterion, iteration 53)."""
    crit = pr.get("criterion", "bounded")
    if crit not in ("bounded", "contained"):
        raise ValueError(f"unknown criterion {crit!r}")
    return crit


def substep4_protocol(eng, params: dict, out_prefix: str) -> dict:
    if params.get("diag_log"):
        eng.start_diag(out_prefix + "_steps.csv")
    run = AssocRun(eng, params, rng_seed=eng.seed + 4)
    p = run.p
    pr = p["protocol"]
    for _ in range(int(params.get("pair_draw", 0))):  # pair_draw = k: the (k + 1)-th random pair
        run.pick_pair(pr["pair_distance"])
    a, b, c = (tuple(params["pair"]) if params.get("pair") else run.pick_pair(pr["pair_distance"]))
    res = {"pair": {"A": a, "B": b, "C": c, "dist_AB_cells": run.group_dist(a, b),
                    "dist_C_cells": min(run.group_dist(a, c), run.group_dist(b, c)),
                    "direct": run.direct_stats(a, b)}}
    if pr.get("freeze_direct_AB"):  # diagnostic (iteration 37): direct A <-> B synapses not plastic
        run.frozen_pair = (a, b)
    if p.get("oracle"):  # diagnostic (iteration 43): the chemistry controls do not apply to fixed chemistry
        run.set_oracle(a, b)
        pr["controls"] = False
        res["oracle"] = p["oracle"]
    run.reset_all()
    res["control0_before"] = {}
    for key, (src, dst) in (("A_to_B", (a, b)), ("B_to_A", (b, a))):
        res["control0_before"][key] = run.test(src, dst, c, strict=True)
        run.baselines[(src, dst)] = run.last_group_max.clone()
    main = protocol_body(run, a, b, c, video=p["video"]["enabled"], out_prefix=out_prefix)
    res["main"] = main
    rounds = main["c1_rounds"]
    modes = list(pr.get("control_modes", ("no_chemistry", "gating_off")))
    if pr["controls"]:
        for mode in modes:
            res[control_key(mode)] = control_run(eng, params, a, b, c, rounds, mode=mode, inj=run._inj_cache,
                                                 baselines=run.baselines)
        if any(run.phase_energy(ph) for ph in ("c1", "c2", "test")):
            res["control3_energy_off_test"] = main.get("final_energy_off")
    fin = main["final"]
    ok_assoc = fin["A_to_B"]["success"] or fin["B_to_A"]["success"]
    best = fin["A_to_B"] if fin["A_to_B"]["success"] else fin["B_to_A"]
    old = {
        "control2_C_inactive": best["c_max"] is not None and best["c_max"] <= p["inactive"],
        # no spread beyond A, B and the path in the successful test (runaway check)
        "association_contained": bool(best.get("contained", False)),
    }
    key = criterion_key(pr)
    checks = {"control0_no_association_before": not (res["control0_before"]["A_to_B"]["success"]
                                                      or res["control0_before"]["B_to_A"]["success"])}
    if key == "bounded":
        # iteration 53 (user decision): a direction passes if B is active and the test is bounded;
        # C and containment are telemetry only
        checks["association"] = any(fin[d]["success"] and fin[d]["bounded"] for d in ("A_to_B", "B_to_A"))
        res["telemetry_checks"] = dict(old, association_any=ok_assoc)
    else:
        checks.update(old, association=ok_assoc)
    if pr["controls"]:
        # control 1 fails only on an association that meets the criterion; a network-wide ignition
        # (B active because everything is) counts as no association (user decision, iteration 30)
        for k in map(control_key, modes):
            r = res[k]["final"]
            checks[k] = not any(r[d]["success"] and r[d][key] for d in ("A_to_B", "B_to_A"))
    res["checks"] = checks
    res["pass"] = all(checks.values())
    res["timing"] = {"steps": run.steps_run, "loop_s": run.t_loop,
                     "steps_per_s": run.steps_run / max(run.t_loop, 1e-9)}
    return res


def protocol_body(run: AssocRun, a: int, b: int, c: int, video=False, out_prefix=None, label="main") -> dict:
    p, pr = run.p, run.p["protocol"]
    eng = run.eng
    if video:
        run.video = _video(run, {"A": a, "B": b, "C": c})
    run.reset_all()
    ia, ib = run.inject_idx_cached(a), run.inject_idx_cached(b)
    rnd_len = p["inject_steps"] + p["gap_steps"]
    rounds, log = 0, []
    w0 = run.base_w.clone()
    c1_ok = False
    runaway_round = None
    path = run.path_groups(a, b)
    run.set_noise_phase(True)
    snap = {}
    run.spike_acc = torch.zeros(eng.N, device=eng.device)

    def gates_at_inject_end():
        snap["gates"] = run.gate_profile(a, b, path)
        snap["sel"] = run.selectivity(a, b)      # spikes counted over this round's injection
        snap["chem"] = run.chem_profile(a, b)

    while rounds < pr["max_c1_rounds"]:
        run.reset_dynamics()
        snap.clear()
        run.spike_acc.zero_()
        at, ao, ns = run.run(rnd_len, inject=round_inject(pr, rounds, ia, ib), learn=True, release1=True,
                             track=[a, b, c] + path,
                             header=f"{label} C1 round {rounds + 1}", on_inject_end=gates_at_inject_end,
                             energy=run.phase_energy("c1"))
        rounds += 1
        if run.stopped is not None:  # the training round itself ran away: stop before consolidation
            log.append({"round": rounds, "runaway": run.stopped, "spikes": ns,
                        "w_fast_abs_mean": float(run.P.w_fast.abs().mean()), "chem": run.chem_profile(a, b)})
            runaway_round = rounds
            break
        cap = pr.get("capture")
        if cap:
            run.elig = torch.zeros_like(run.P.valid)
        t_ab = run.test(a, b, c, strict=False, header=f"{label} C1 test {rounds}", exclude=path)
        if cap:
            # capture (iteration 48, user decision): B active under A alone releases C2, taken as reaching
            # every synapse (fast, broad C2); synapses that transmitted in this test are made permanent
            elig, run.elig = run.elig, None
            entry_cap = {"captured": False, "n_eligible": int(elig.sum())}
            if t_ab["success"]:
                run.P.capture(elig, float(cap.get("kappa", 1.0)))
                strict = run.test(a, b, c, strict=True, header=f"{label} capture strict test {rounds}", exclude=path)
                entry_cap.update(captured=True, strict=strict)
                if strict["success"]:
                    c1_ok = True
            pm = at[:, 3:].max(axis=0) if path else np.zeros(1)
            log.append({"round": rounds, "A_max": float(at[:, 0].max()), "B_max": float(at[:, 1].max()),
                        "others_max": float(ao.max()), "spikes": ns, "path_max": float(pm.max()),
                        "test_A_to_B": t_ab, "capture": entry_cap, "w_fast_abs_mean": float(run.P.w_fast.abs().mean()),
                        "sel_inject_end": snap.get("sel"), "gates_inject_end": snap.get("gates")})
            if c1_ok:
                break
            continue
        pm = at[:, 3:].max(axis=0) if path else np.zeros(1)
        log.append({"round": rounds, "A_max": float(at[:, 0].max()), "B_max": float(at[:, 1].max()),
                    "C_max": float(at[:, 2].max()), "others_max": float(ao.max()), "spikes": ns,
                    "path_groups": path, "path_max": float(pm.max()), "path_mean_of_max": float(pm.mean()),
                    "test_A_to_B": t_ab, "w_fast_abs_mean": float(run.P.w_fast.abs().mean()),
                    "chem": run.chem_profile(a, b), "gates_inject_end": snap.get("gates"),
                    "sel_inject_end": snap.get("sel"), "chem_inject_end": snap.get("chem")})
        if not t_ab[criterion_key(pr)] and t_ab["success"] and not pr.get("accept_uncontained"):
            runaway_round = rounds  # transfer only as part of activity spreading beyond the path
            break
        if t_ab["success"]:
            c1_ok = True
            break
    out = {"c1_rounds": rounds, "c1_test_passed": c1_ok, "c1_log": log, "path_groups": path,
           "runaway_round": runaway_round,
           "w_fast_after_c1": run.weight_change_stats(torch.zeros_like(w0), run.P.w_fast, a, b),
           "sel_w_fast_after_c1": run.weight_selectivity(a, b, run.P.w_fast)}
    c2_log = []
    final = None
    if runaway_round is None and (c1_ok or pr["c2_after_max_rounds"]):
        n_c2 = 0
        limit = pr["c2_rounds"] + pr["max_extra_c2_rounds"]
        while n_c2 < limit:
            run.reset_dynamics()
            snap.clear()
            run.spike_acc.zero_()
            at, ao, ns = run.run(rnd_len, inject=round_inject(pr, n_c2, ia, ib), learn=p["learn_in_c2"],
                                 consolidate=True, release1=p["c1_release_in_c2"], release2=True, track=[a, b, c],
                                 header=f"{label} C2 round {n_c2 + 1}", on_inject_end=gates_at_inject_end,
                                 energy=run.phase_energy("c2"))
            n_c2 += 1
            entry = {"round": n_c2, "A_max": float(at[:, 0].max()), "B_max": float(at[:, 1].max()),
                     "others_max": float(ao.max()), "spikes": ns, "chem": run.chem_profile(a, b),
                     "gates_inject_end": snap.get("gates"), "sel_inject_end": snap.get("sel"),
                     "runaway": run.stopped}
            if run.stopped is not None:  # stop consolidating; the final tests below still run
                c2_log.append(entry)
                out["c2_runaway_round"] = n_c2
                break
            if n_c2 >= pr["c2_rounds"]:
                final = {"A_to_B": run.test(a, b, c, strict=pr["strict_test"], header=f"{label} final A->B", exclude=path),
                         "B_to_A": run.test(b, a, c, strict=pr["strict_test"], header=f"{label} final B->A", exclude=path)}
                entry["final"] = final
                c2_log.append(entry)
                if final["A_to_B"]["success"] or final["B_to_A"]["success"]:
                    break
            else:
                c2_log.append(entry)
        out["c2_rounds"] = n_c2
    run.set_noise_phase(False)
    if final is None:
        final = {"A_to_B": run.test(a, b, c, strict=pr["strict_test"], exclude=path),
                 "B_to_A": run.test(b, a, c, strict=pr["strict_test"], exclude=path)}
    out["c2_log"] = c2_log
    out["final"] = final
    out["runaway_events"] = run.runaway_events
    out["w_perm_change"] = run.weight_change_stats(w0, run.P.w_perm, a, b)
    out["sel_w_perm_change"] = run.weight_selectivity(a, b, run.P.w_perm - w0)
    run.spike_acc = None
    if any(run.phase_energy(ph) for ph in ("c1", "c2", "test")):
        out["final_energy_off"] = {"A_to_B": run.test(a, b, c, strict=pr["strict_test"], energy=False),
                                   "B_to_A": run.test(b, a, c, strict=pr["strict_test"], energy=False)}
    if run.video is not None:
        out["video_frames"] = run.video.write(f"{out_prefix}_{label}.mp4", fps=p["video"]["fps"])
        run.video = None
    out["chem_snapshot"] = {"C1": run.C1.c.cpu().numpy(), "C2": run.C2.c.cpu().numpy()}
    return out


def control_run(eng, params, a, b, c, rounds, mode: str, inj: dict, baselines=None) -> dict:
    """
    Same pair, same injected neurons, same number of rounds; chemistry or gating disabled.
    With protocol.capture (iteration 53), the control runs the same capture loop (protocol_body)
    for at most `rounds` C1 rounds: w_perm changes only by capture there, so the fixed-round body,
    which never captures, could not show an association and the control could not fail.
    """
    over = merge(params, {"protocol": {"controls": False}, "video": {"enabled": False}})
    capture = bool(over["protocol"].get("capture"))
    if capture:
        over["protocol"]["max_c1_rounds"] = max(1, int(rounds))
    run = AssocRun(eng, over, rng_seed=eng.seed + 4)
    run._inj_cache = dict(inj)
    run.baselines = dict(baselines or {})
    if run.p["protocol"].get("freeze_direct_AB"):
        run.frozen_pair = (a, b)
    if mode == "no_chemistry":
        run.p["c1"]["gain"] = 0.0
        run.p["c2"]["gain"] = 0.0
    elif mode == "gating_off":
        run.P = run.new_plasticity(theta1=-1.0, theta2=-1.0, soft1=0.0, soft2=0.0)
        run.p["plasticity"].update({"theta1": -1.0, "theta2": -1.0, "soft1": 0.0, "soft2": 0.0})
    elif mode == "separate":
        # joint-activation control (iteration 54): A and B in alternating rounds, never together
        run.p["protocol"]["inject_mode"] = "alternate"
    else:
        raise ValueError(f"unknown control mode {mode!r}")
    if capture:
        body = protocol_body(run, a, b, c, label=f"control {mode}")
        return {"mode": mode, "body": "capture", "rounds": body["c1_rounds"], "final": body["final"],
                "c1_test_passed": body["c1_test_passed"], "w_perm_change": body["w_perm_change"],
                "stopped_in": None if body["runaway_round"] is None else f"C1 {body['runaway_round']}",
                "runaway_events": body["runaway_events"]}
    body = protocol_body_fixed_rounds(run, a, b, c, rounds=max(1, rounds), label=f"control {mode}")
    return {"mode": mode, "body": "fixed_rounds", "rounds": body["c1_rounds"], "final": body["final"],
            "w_perm_change": body["w_perm_change"], "stopped_in": body["stopped_in"],
            "runaway_events": body["runaway_events"]}


def protocol_body_fixed_rounds(run: AssocRun, a, b, c, rounds: int, label: str) -> dict:
    pr = run.p["protocol"]
    run.reset_all()
    ia, ib = run.inject_idx_cached(a), run.inject_idx_cached(b)
    rnd_len = run.p["inject_steps"] + run.p["gap_steps"]
    w0 = run.base_w.clone()
    run.set_noise_phase(True)
    stopped_in = None
    for r in range(rounds):
        run.reset_dynamics()
        run.run(rnd_len, inject=round_inject(pr, r, ia, ib), learn=True, release1=True, header=f"{label} C1 {r + 1}",
                energy=run.phase_energy("c1"))
        if run.stopped is not None:
            stopped_in = f"C1 {r + 1}"
            break
    for r in range(pr["c2_rounds"] if stopped_in is None else 0):
        run.reset_dynamics()
        run.run(rnd_len, inject=round_inject(pr, r, ia, ib), learn=run.p["learn_in_c2"], consolidate=True,
                release1=run.p["c1_release_in_c2"],
                release2=True, header=f"{label} C2 {r + 1}", energy=run.phase_energy("c2"))
        if run.stopped is not None:
            stopped_in = f"C2 {r + 1}"
            break
    run.set_noise_phase(False)
    path = run.path_groups(a, b)
    final = {"A_to_B": run.test(a, b, c, strict=pr["strict_test"], exclude=path),
             "B_to_A": run.test(b, a, c, strict=pr["strict_test"], exclude=path)}
    return {"c1_rounds": rounds, "final": final, "w_perm_change": run.weight_change_stats(w0, run.P.w_perm, a, b),
            "stopped_in": stopped_in, "runaway_events": run.runaway_events}


def diag_saturated_path(eng, params: dict, out_prefix: str, radius: float = 1.0, n_pairs: int = 1) -> dict:
    """
    Upper bound for learning (diagnostic, not part of the protocol): every plastic synapse
    whose pre and post both lie in A, B or the path groups (within `radius` cells of
    segment A-B) is set to the upper weight bound; then A alone and B alone are tested.
    If B stays inactive, no plasticity within the bounds can create the association.
    n_pairs > 1: that many random pairs at `pair_distance` (the first is the n_pairs = 1 pair);
    the result lists each pair and the fraction passing.
    """
    run = AssocRun(eng, params, rng_seed=eng.seed + 4)
    pr = run.p["protocol"]
    if n_pairs <= 1:
        a, b, c = (tuple(params["pair"]) if params.get("pair") else run.pick_pair(pr["pair_distance"]))
        return _diag_pair(run, a, b, c, radius)
    rows = [_diag_pair(run, *run.pick_pair(pr["pair_distance"]), radius) for _ in range(int(n_pairs))]
    keys = rows[0]["checks"].keys()
    return {"pairs": rows, "n_pairs": len(rows),
            "fraction_pass": sum(r["pass"] for r in rows) / len(rows),
            "fraction_by_check": {k: sum(r["checks"][k] for r in rows) / len(rows) for k in keys},
            "pass": all(r["pass"] for r in rows)}


def _diag_pair(run: AssocRun, a: int, b: int, c: int, radius: float) -> dict:
    eng = run.eng
    path = run.path_groups(a, b, radius)
    run.reset_all()
    before = {"A_to_B": run.test(a, b, c, strict=True), "B_to_A": run.test(b, a, c, strict=True)}
    member = torch.zeros(eng.G, dtype=torch.bool, device=eng.device)
    member[[a, b] + path] = True
    in_region = member[eng.groups]
    mask = run.P.plastic & in_region.view(1, -1) & in_region[run.P.post]
    run.P.w_perm = torch.where(mask, run.P.hi, run.P.w_perm)
    after = {"A_to_B": run.test(a, b, c, strict=True), "B_to_A": run.test(b, a, c, strict=True)}
    inactive = run.p["inactive"]
    checks = {
        "no_transfer_untrained": not (before["A_to_B"]["success"] or before["B_to_A"]["success"]),
        "untrained_C_inactive": max(before[k]["c_max"] for k in before) <= inactive,
        "transfer_at_max_weights": after["A_to_B"]["success"] or after["B_to_A"]["success"],
        "saturated_C_inactive": max(after[k]["c_max"] for k in after) <= inactive,
    }
    return {"pair": [a, b, c], "path_groups": path, "n_saturated": int(mask.sum()),
            "before": before, "after": after, "checks": checks, "pass": all(checks.values())}


def prop_survey(eng, params: dict, out_prefix: str, n_pairs: int = 8) -> dict:
    """
    Propagation without learning (iteration 45): for random pairs at `pair_distance` (the same
    pairs as `pair_draw` 0, 1, ... in substep4), one round (inject_steps + gap_steps) each of joint
    A + B injection, A alone and B alone; chemistry and plasticity off, training background input
    on. Per condition: spikes per excitatory neuron in M and Sh (regions), maximum A_g of A, B,
    the path groups and all other groups, runaway. Does the path fire under joint injection, more
    than off the path (selectivity) and more than both single injections together (convergence)?
    With sparse assemblies and `bridges` (iteration 51), also the maximum A_g of the bridges (the
    assemblies among the path groups) per condition: does a bridge ignite under input from A and
    B together but not from one alone? `off_asm_max` (iteration 52): maximum A_g of the assemblies
    off the route, which, unlike others_max, ignores ordinary groups firing on background input.
    """
    run = AssocRun(eng, params, rng_seed=eng.seed + 4)
    p = run.p
    rnd = p["inject_steps"] + p["gap_steps"]
    pairs = [run.pick_pair(p["protocol"]["pair_distance"]) for _ in range(int(n_pairs))]
    run.set_noise_phase(True)
    run.spike_acc = torch.zeros(eng.N, device=eng.device)
    rows = []
    for a, b, c in pairs:
        path = run.path_groups(a, b)
        bridges = [g for g in path if bool(run.is_asm[g])] if run.sparse else []
        row = {"pair": [a, b, c], "dist": run.group_dist(a, b), "n_path": len(path), "bridges": bridges}
        off_asm = run.is_asm.clone()          # assemblies off the route (iteration 52)
        off_asm[[a, b] + bridges] = False
        out = (eng.groups != a) & (eng.groups != b)
        out_e, out_i = out & eng.exc, out & ~eng.exc
        # "none": no injection, the background-input baseline to subtract (iteration 45)
        for cond, inj in (("joint", (a, b)), ("A", (a,)), ("B", (b,)), ("none", ())):
            run.reset_dynamics()
            run.spike_acc.zero_()
            at, ao, ns = run.run(rnd, inject=[run.inject_idx_cached(g) for g in inj], track=[a, b] + path,
                                 chem=False, header=f"survey {cond}")
            sel = run.selectivity(a, b)
            pm = at[:, 2:].max(axis=0) if path else np.zeros(1)
            row[cond] = {"M": sel["M"]["spikes_per_exc"], "Sh": sel["Sh"]["spikes_per_exc"],
                         "A_max": float(at[:, 0].max()), "B_max": float(at[:, 1].max()),
                         "path_max": float(pm.max()), "path_mean_of_max": float(pm.mean()),
                         "others_max": float(ao.max()), "spikes": ns, "runaway": run.stopped is not None,
                         "bridge_max": float(run.last_group_max[bridges].max()) if bridges else None,
                         "off_asm_max": float(run.last_group_max[off_asm].max()) if bool(off_asm.any()) else None,
                         # spikes per neuron outside A and B, excitatory and inhibitory (iteration 45)
                         "exc_out": _mean(run.spike_acc[out_e]), "inh_out": _mean(run.spike_acc[out_i])}
        j, sa, sb = row["joint"], row["A"], row["B"]
        row["convergence"] = _ratio(j["M"], (sa["M"] or 0.0) + (sb["M"] or 0.0))
        row["selectivity"] = _ratio(j["M"], j["Sh"])
        rows.append(row)
    run.spike_acc = None
    run.set_noise_phase(False)

    def med(xs):
        xs = [x for x in xs if x is not None]
        return float(np.median(xs)) if xs else None

    summary = {
        "M_joint": med([r["joint"]["M"] for r in rows]),
        "M_A_plus_B": med([(r["A"]["M"] or 0.0) + (r["B"]["M"] or 0.0) for r in rows]),
        "Sh_joint": med([r["joint"]["Sh"] for r in rows]),
        "path_mean_of_max_joint": med([r["joint"]["path_mean_of_max"] for r in rows]),
        "others_max_joint": med([r["joint"]["others_max"] for r in rows]),
        "others_max_single": med([max(r["A"]["others_max"], r["B"]["others_max"]) for r in rows]),
        "assembly_max_single": med([min(r["A"]["A_max"], r["B"]["B_max"]) for r in rows]),
        "runaway_pairs": sum(any(r[k]["runaway"] for k in ("joint", "A", "B")) for r in rows),
        "exc_out_joint": med([r["joint"]["exc_out"] for r in rows]),
        "inh_out_joint": med([r["joint"]["inh_out"] for r in rows]),
        "convergence": med([r["convergence"] for r in rows]),
        "selectivity": med([r["selectivity"] for r in rows]),
    }
    return {"pairs": rows, "summary": summary, "n_pairs": len(rows), "pass": True}


def input_survey(eng, params: dict, out_prefix: str, n_pairs: int = 8) -> dict:
    """
    Two-sided synaptic input without learning (iteration 47; is a coincidence-gated release viable?).
    For random pairs at `pair_distance`: injection into A alone, B alone and both, `inject_steps`
    steps each; per neuron the mean synaptic input per step (net, before injection and background)
    and the spikes. Per region (excitatory neurons outside A and B: M, Sh, and bins of t along the
    line within `sel_radius`): mean input under A, B and joint, the coincidence signal
    min(I_A+, I_B+) (positive parts), joint - A - B (interaction), and the fraction of neurons whose
    coincidence signal exceeds 0.5, 1, 2 and 4. A coincidence-gated rule needs that signal clearly
    higher in M than in Sh and behind A or B.
    """
    run = AssocRun(eng, params, rng_seed=eng.seed + 4)
    p = run.p
    n_steps = int(p["inject_steps"])
    pairs = [run.pick_pair(p["protocol"]["pair_distance"]) for _ in range(int(n_pairs))]
    run.set_noise_phase(True)
    run.spike_acc = torch.zeros(eng.N, device=eng.device)
    run.input_acc = torch.zeros(eng.N, device=eng.device)
    cells = eng.pos / eng.cell_size
    r = float(p["sel_radius"])
    edges = [-0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]
    valid = eng.n_rep >= 0
    post_all = torch.clamp(eng.n_rep.long(), min=0)
    rows = []
    for a, b, c in pairs:
        I, S = {}, {}
        for cond, inj in (("A", (a,)), ("B", (b,)), ("joint", (a, b))):
            run.reset_dynamics()
            run.spike_acc.zero_()
            run.input_acc.zero_()
            run.run(n_steps, inject=[run.inject_idx_cached(g) for g in inj], chem=False, header=f"input {cond}")
            I[cond] = run.input_acc / n_steps
            S[cond] = run.spike_acc.clone()
            # excitatory and inhibitory input separately (iteration 48): spikes x synaptic current, summed
            # per target over the window (delays ignored), per step
            for kind, pre in (("E", eng.exc), ("Inh", ~eng.exc)):
                contrib = torch.where(valid & pre.view(1, -1), eng.weights * S[cond].view(1, -1),
                                      torch.zeros_like(eng.weights))
                I[f"{kind}_{cond}"] = torch.zeros(eng.N, device=eng.device).index_add_(
                    0, post_all.reshape(-1), contrib.reshape(-1)) / n_steps
        out_e = (eng.groups != a) & (eng.groups != b) & eng.exc
        t, rho, _, _ = run.seg_coords(cells, a, b)
        nm, ns = run.regions(a, b)["neuron"]
        pos_a, pos_b = torch.clamp(I["A"], min=0.0), torch.clamp(I["B"], min=0.0)
        coinc = torch.minimum(pos_a, pos_b)
        coinc_e = torch.minimum(I["E_A"], I["E_B"])   # excitation arriving from both sides

        def stats(mask):
            m = mask & out_e
            if not bool(m.any()):
                return {"n": 0}
            return {"n": int(m.sum()), "I_A": _mean(I["A"][m]), "I_B": _mean(I["B"][m]), "I_joint": _mean(I["joint"][m]),
                    "coinc": _mean(coinc[m]), "interaction": _mean((I["joint"] - I["A"] - I["B"])[m]),
                    "E_A": _mean(I["E_A"][m]), "E_B": _mean(I["E_B"][m]), "E_joint": _mean(I["E_joint"][m]),
                    "Inh_A": _mean(I["Inh_A"][m]), "Inh_joint": _mean(I["Inh_joint"][m]),
                    "coinc_E": _mean(coinc_e[m]),
                    "spikes_joint": _mean(S["joint"][m]), "spikes_A": _mean(S["A"][m]), "spikes_B": _mean(S["B"][m]),
                    "frac_coinc_over": {str(th): _mean((coinc[m] > th).float()) for th in (0.5, 1.0, 2.0, 4.0)}}

        row = {"pair": [a, b, c], "dist": run.group_dist(a, b), "M": stats(nm), "Sh": stats(ns),
               "profile": [dict(t=[lo, hi], **stats((rho < r) & (t >= lo) & (t < hi)))
                           for lo, hi in zip(edges[:-1], edges[1:])]}
        row["coinc_ratio_M_Sh"] = _ratio(row["M"].get("coinc"), row["Sh"].get("coinc"))
        rows.append(row)
    run.spike_acc = None
    run.input_acc = None
    run.set_noise_phase(False)

    def med(xs):
        xs = [x for x in xs if x is not None]
        return float(np.median(xs)) if xs else None

    summary = {k: {q: med([rw[k].get(q) for rw in rows]) for q in ("I_A", "I_B", "I_joint", "coinc", "interaction",
                                                                      "spikes_joint", "E_A", "E_B", "E_joint", "Inh_A",
                                                                      "Inh_joint", "coinc_E")} for k in ("M", "Sh")}
    summary["coinc_E_ratio_M_Sh"] = med([_ratio(rw["M"].get("coinc_E"), rw["Sh"].get("coinc_E")) for rw in rows])
    summary["profile_coinc_E"] = [med([rw["profile"][i].get("coinc_E") for rw in rows]) for i in range(len(edges) - 1)]
    summary["profile_E_A"] = [med([rw["profile"][i].get("E_A") for rw in rows]) for i in range(len(edges) - 1)]
    summary["profile_Inh_A"] = [med([rw["profile"][i].get("Inh_A") for rw in rows]) for i in range(len(edges) - 1)]
    summary["coinc_ratio_M_Sh"] = med([rw["coinc_ratio_M_Sh"] for rw in rows])
    summary["profile_coinc"] = [med([rw["profile"][i].get("coinc") for rw in rows]) for i in range(len(edges) - 1)]
    summary["profile_I_A"] = [med([rw["profile"][i].get("I_A") for rw in rows]) for i in range(len(edges) - 1)]
    return {"pairs": rows, "summary": summary, "n_pairs": len(rows), "pass": True}


def conn_survey(eng, params: dict, out_prefix: str) -> dict:
    """
    Connectivity of the built network, no simulation (iteration 39): excitatory-to-excitatory
    synapses between every ordered pair of location groups, summarized by the Euclidean distance
    between the groups' cells (rounded to whole cells). A multi-hop path needs many synapses
    between neighbouring groups; "not (or only weakly) directly connected" needs few between
    distant ones.
    """
    G, dev = eng.G, eng.device
    post = torch.clamp(eng.n_rep.long(), min=0)
    pre_g = eng.groups.view(1, -1).expand_as(post)
    m = (eng.n_rep >= 0) & eng.exc.view(1, -1) & eng.exc[post]
    idx = (pre_g[m] * G + eng.groups[post][m]).view(-1)
    cnt = torch.bincount(idx, minlength=G * G).view(G, G).float()
    n_exc = torch.bincount(eng.groups[eng.exc], minlength=G).float()
    cells = eng.group_cell.float()
    dist = torch.cdist(cells, cells).round().long()
    by_d = {}
    for d in range(int(dist.max()) + 1):
        sel = dist == d
        if d > 0:
            sel &= ~torch.eye(G, dtype=torch.bool, device=dev)
        v = cnt[sel]
        if v.numel() == 0:
            continue
        per_post = (cnt / n_exc.clamp(min=1).view(1, -1))[sel]   # synapses per target neuron
        by_d[str(d)] = {"pairs": int(v.numel()), "median": float(v.median()), "mean": float(v.mean()),
                        "max": float(v.max()), "frac_zero": float((v == 0).float().mean()),
                        "mean_per_target_neuron": float(per_post.mean())}
    res = {"N": int(eng.N), "S": int(eng.n_rep.shape[0]), "D": int(eng.D), "G": int(G),
           "rewire": getattr(eng, "rewire_stats", None),
           "seg": list(eng.seg), "exc_per_group": {"min": float(n_exc.min()), "mean": float(n_exc.mean())},
           "ee_synapses_by_cell_distance": by_d,
           "build_seconds": float(getattr(eng, "build_seconds", 0.0)), "pass": True}
    return res


JOBS = {
    "conn_survey": conn_survey,
    "diag_saturated_path": diag_saturated_path,
    "prop_survey": prop_survey,
    "input_survey": input_survey,
    "substep0": substep0_harness,
    "substep1": substep1_activation,
    "substep2": substep2_chemistry,
    "substep3": substep3_plasticity,
    "substep4": substep4_protocol,
}
