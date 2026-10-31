"""
Chemical-gated plasticity on the engine's fixed synapses (Substep 3 of
setups/runpod-assembly-association/runpod-assembly-association-task.md).

Layout follows the engine (snn_simulation.cu, update_current_): synapse s of presynaptic
neuron n sits at linear index n + N * s, i.e. tensors of shape (S, N); N_rep[s, n] is the
postsynaptic neuron (-1 = deleted); synapse s of n has delay d where
N_delays[d, n] <= s < N_delays[d + 1, n].

Timing windows, soft-bounded form and bounds are those of the engine's STDP:
- potentiation ("upstream" rule): when post fires at t, every synapse whose pre fired in
  [t - 2D, t] is potentiated;
- depression ("downstream" rule): when a pre spike arrives at t (pre fired at t - d), and
  post fired in [t - 2d, t - d), the synapse is depressed;
- dw *= |w| * (bound - |w|), result clipped to [0.05, 1] (excitatory pre) or [-1, -0.05]
  (`weight_dep` "upper" instead: potentiation times (bound - |w|), depression times |w|).

The engine's per-group-pair sign (G_stdp_config) is replaced by a chemical gate on the
postsynaptic neuron's local concentration:
- learning phase: gated changes go into w_fast, which decays (non-permanent part);
- consolidation: where C1 and C2 are both above threshold, w_fast moves into w_perm,
  which does not decay (permanent part).
The engine sees w_perm + w_fast (clipped), written into N_weights by the harness.

`rule` selects what drives the C1-gated changes: "stdp" (above), "pre_c1" (a neuron firing
inside a high-C1 region potentiates its outgoing synapses, no postsynaptic spike required;
user decision after tuning iteration 13), or "both". Sparse task, Substep 3:
- "pre_c1_signed" (L3): as "pre_c1", with a sign set by the presynaptic rate (an exponential trace
  over `rate_tau` steps): negative below `rate_thr` spikes per step, positive above, up to 1 at twice it;
- "btsp" (L1, L2): a gate event in a neuron (`btsp["gate"]` "plateau": random, `plateau_rate` per step;
  "c1": its C1 rising through theta1) opens a window of `window` steps, `before` of them before the event;
  only synapses onto that neuron whose presynaptic neuron fired in the window change, no postsynaptic
  spike needed. `form` "binary" (Wu & Maass 2025): each flips with probability 0.5, a weak one (below the
  middle of its bounds) to the upper bound, a strong one to the lower, at most one event per neuron while
  `once`; "continuous" (Milstein et al. 2021): it moves by `rate` toward bound * Ip / (Ip + Id), the
  overlaps of a potentiation and a depression trace of the presynaptic spikes (time constants before / 3
  and twice that) with a gate trace decaying from the event (time constant (window - before) / 3).
  The changes go into w_fast like the other rules'.
`track_increase` (L5): keep each step's positive learned change of w_fast, summed per postsynaptic neuron,
in `increase_post` (the harness releases C1 from it).
"""

from __future__ import annotations

import math

import torch


def delays_from_N_delays(n_delays: torch.Tensor, S: int) -> torch.Tensor:
    """(D + 1, N) bucket boundaries -> (S, N) per-synapse delay in steps."""
    n_rows, N = n_delays.shape
    s = torch.arange(S, device=n_delays.device).view(S, 1)
    d = torch.zeros((S, N), dtype=torch.long, device=n_delays.device)
    for r in range(1, n_rows):
        d += (s >= n_delays[r].view(1, N).long()).long()
    return torch.clamp(d, max=n_rows - 2)


def gate(c: torch.Tensor, threshold: float, softness: float) -> torch.Tensor:
    """0 below threshold, 1 above threshold + softness, linear in between (hard step if softness == 0)."""
    if softness <= 0.0:
        return (c >= threshold).float()
    return torch.clamp((c - threshold) / softness, 0.0, 1.0)


class GatedPlasticity:

    def __init__(self, n_rep: torch.Tensor, syn_delay: torch.Tensor, pre_exc: torch.Tensor,
                 w_init: torch.Tensor, D: int,
                 a_plus: float = 0.05, a_minus: float = 0.05,
                 tau_fast: float = 2000.0, kappa: float = 0.01,
                 theta1: float = 1.0, theta2: float = 1.0,
                 soft1: float = 0.0, soft2: float = 0.0,
                 plastic_exc_only: bool = True,
                 w_exc=(0.05, 1.0), w_inh=(-1.0, -0.05),
                 fixed: torch.Tensor | None = None,
                 rule: str = "stdp", a_pre: float = 0.05, pre_post_gate: bool = True,
                 consolidate_ee_only: bool = False, weight_dep: str = "mult",
                 norm_factor: float | None = None,
                 rate_thr: float | None = None, rate_tau: float = 100.0,
                 btsp: dict | None = None, track_increase: bool = False):
        self.S, self.N = n_rep.shape
        self.D = int(D)
        self.dev = n_rep.device
        self.valid = n_rep >= 0
        self.post = torch.clamp(n_rep.long(), min=0)            # (S, N)
        self.delay = syn_delay.long()                            # (S, N)
        self.pre_exc = pre_exc.bool()                            # (N,)
        exc_cols = self.pre_exc.view(1, self.N).expand(self.S, self.N)
        self.plastic = self.valid & (exc_cols if plastic_exc_only else torch.ones_like(self.valid))
        # fixed synapses (e.g. intra-group weights boosted above the bound, shortcut 1) are
        # neither plastic nor clipped to the bounds
        self.fixed = torch.zeros_like(self.valid) if fixed is None else fixed.bool() & self.valid
        self.plastic &= ~self.fixed
        self.lo = torch.where(exc_cols, torch.tensor(w_exc[0], device=self.dev),
                              torch.tensor(w_inh[0], device=self.dev))
        self.hi = torch.where(exc_cols, torch.tensor(w_exc[1], device=self.dev),
                              torch.tensor(w_inh[1], device=self.dev))
        self.bound = torch.where(exc_cols, torch.tensor(abs(w_exc[1]), device=self.dev),
                                 torch.tensor(abs(w_inh[0]), device=self.dev))
        self.a_plus, self.a_minus = float(a_plus), float(a_minus)
        self.fast_decay = math.exp(-1.0 / float(tau_fast)) if tau_fast > 0 else 0.0
        self.kappa = float(kappa)
        self.theta1, self.theta2 = float(theta1), float(theta2)
        self.soft1, self.soft2 = float(soft1), float(soft2)
        if rule not in ("stdp", "pre_c1", "both", "pre_c1_signed", "btsp"):
            raise ValueError(f"unknown rule {rule}")
        self.rule = rule
        if rule == "pre_c1_signed" and not rate_thr:
            raise ValueError("rule pre_c1_signed needs rate_thr")
        self.rate_thr = None if rate_thr is None else float(rate_thr)
        self.rate_decay = math.exp(-1.0 / float(rate_tau))
        self.rate = torch.zeros(self.N, device=self.dev)        # presynaptic rate trace (L3)
        self.btsp = None
        if rule == "btsp":
            b = {"gate": "plateau", "form": "binary", "window": 200, "before": 133, "plateau_rate": 1e-4,
                 "once": True, "rate": 0.5, "seed": 0}
            b.update(btsp or {})
            if b["gate"] not in ("plateau", "c1") or b["form"] not in ("binary", "continuous"):
                raise ValueError(f"unknown btsp gate or form {b}")
            self.btsp = b
            self.ev_eval = torch.full((self.N,), -1, dtype=torch.long, device=self.dev)   # evaluation step
            self.ev_time = torch.full((self.N,), -1, dtype=torch.long, device=self.dev)   # event step
            self.ev_done = torch.zeros(self.N, dtype=torch.bool, device=self.dev)
            self.c1_prev = torch.zeros(self.N, device=self.dev)
            self.gen = torch.Generator(device=self.dev).manual_seed(int(b["seed"]))
            after = int(b["window"]) - int(b["before"])
            self.dec_p = math.exp(-3.0 / float(b["before"]))
            self.dec_d = math.exp(-1.5 / float(b["before"]))
            self.dec_g = math.exp(-3.0 / float(max(after, 1)))
            self.xp = torch.zeros(self.N, device=self.dev)
            self.xd = torch.zeros(self.N, device=self.dev)
            self.gtr = torch.zeros(self.N, device=self.dev)
            self.t_last = -1
            if b["form"] == "continuous":
                self.Ip = torch.zeros(self.S, self.N, device=self.dev)
                self.Id = torch.zeros(self.S, self.N, device=self.dev)
        self.track_increase = bool(track_increase)
        self.increase_post = torch.zeros(self.N, device=self.dev)
        self.a_pre = float(a_pre)
        self.pre_post_gate = bool(pre_post_gate)
        # consolidate only synapses onto excitatory neurons (excitatory-to-inhibitory changes stay
        # in w_fast and decay; iteration 36)
        self.consolidate_mask = (self.pre_exc[self.post] if consolidate_ee_only
                                 else torch.ones_like(self.valid))
        # weight dependence: "mult" (engine STDP: every change times |w| (bound - |w|)) or "upper"
        # (potentiation times (bound - |w|), depression times |w|: no stall at the lower bound;
        # iteration 43)
        if weight_dep not in ("mult", "upper"):
            raise ValueError(f"unknown weight dependence {weight_dep}")
        self.weight_dep = weight_dep

        # learning-rate scale on every learned change (a_plus, a_minus, a_pre); the protocol's
        # rollback rule lowers it after a round that ignited (iteration 60)
        self.rate_scale = 1.0

        self.w_perm = w_init.float().clone()
        self.w_fast = torch.zeros_like(self.w_perm)
        # synaptic normalization (iteration 48): each neuron's summed plastic input weight is kept
        # at or below norm_factor times its initial sum (heterosynaptic scaling of w_fast)
        self.norm_factor = None if not norm_factor else float(norm_factor)
        if self.norm_factor:
            self.norm_target = self._input_sums(self.w_perm) * self.norm_factor
        self.H = 2 * self.D + 2
        self.hist = torch.zeros((self.H, self.N), dtype=torch.bool, device=self.dev)
        self.last = torch.full((self.N,), -10 ** 6, dtype=torch.long, device=self.dev)
        self.n_idx = torch.arange(self.N, device=self.dev).view(1, self.N).expand(self.S, self.N)

    # --- state ---------------------------------------------------------------------------

    def reset_spike_state(self):
        if self.btsp is not None:
            # a window does not span a reset (a round is shorter than the window): pending events are
            # evaluated now, on the part of their window that ran (before the spike times are cleared);
            # `ev_done` and `c1_prev` persist
            self._btsp_apply(self.ev_eval >= 0, None, self.t_last)
        self.hist.zero_()
        self.last.fill_(-10 ** 6)
        self.rate.zero_()
        if self.btsp is not None:
            self.ev_eval.fill_(-1)
            for x in (self.xp, self.xd, self.gtr):
                x.zero_()
            if self.btsp["form"] == "continuous":
                self.Ip.zero_()
                self.Id.zero_()

    def effective(self) -> torch.Tensor:
        w = torch.clamp(self.w_perm + self.w_fast, self.lo, self.hi)
        return torch.where(self.valid & ~self.fixed, w, self.w_perm)

    # --- per step ------------------------------------------------------------------------

    def observe(self, spikes: torch.Tensor, t: int):
        """Record this step's spikes (call once per step, after timing_dw for that step)."""
        self.hist[int(t) % self.H] = spikes
        self.last[spikes] = int(t)

    def timing_dw(self, spikes: torch.Tensor, t: int) -> torch.Tensor:
        """Ungated, soft-bounded STDP change for this step's spikes (spikes not yet observed)."""
        t = int(t)
        last = self.last.clone()
        last[spikes] = t
        # potentiation: post fires now, pre fired within [t - 2D, t]
        post_now = spikes[self.post]
        dt_pre = t - last.view(1, self.N)
        ltp = post_now & (dt_pre >= 0) & (dt_pre <= 2 * self.D)
        # depression: pre spike (fired at t - d) arrives now; post fired in [t - 2d, t - d)
        t_fire = t - self.delay
        hist = self.hist.clone()
        hist[t % self.H] = spikes
        arrived = hist[torch.remainder(t_fire, self.H), self.n_idx] & (self.delay > 0)
        last_post = self.last[self.post]  # post's last spike strictly before t
        ltd = arrived & (last_post < t_fire) & (last_post >= t_fire - self.delay)
        w = self.effective().abs()
        if self.weight_dep == "upper":
            dw = self.a_plus * ltp.float() * (self.bound - w) - self.a_minus * ltd.float() * w
        else:
            dw = (self.a_plus * ltp.float() - self.a_minus * ltd.float()) * w * (self.bound - w)
        # sign: excitatory weights grow with dw, inhibitory weights grow in magnitude
        dw = torch.where(self.lo < 0, -dw, dw)
        return torch.where(self.plastic, dw, torch.zeros_like(dw))

    def pre_c1_dw(self, spikes: torch.Tensor, g1n: torch.Tensor) -> torch.Tensor:
        """
        Presynaptic, C1-gated potentiation (no postsynaptic spike required): when a neuron
        fires inside a high-C1 region, its outgoing plastic synapses are potentiated, scaled by
        the C1 gate at the presynaptic neuron and (pre_post_gate) at the postsynaptic one, so
        that synapses connecting high-C1 locations are strengthened (a chemical trail).
        Soft-bounded like the STDP rule.
        """
        g_pre = (spikes.float() * g1n).view(1, self.N)
        g = g_pre * g1n[self.post] if self.pre_post_gate else g_pre.expand(self.S, self.N)
        w = self.effective().abs()
        dw = self.a_pre * g * (self.bound - w) * (1.0 if self.weight_dep == "upper" else w)
        dw = torch.where(self.lo < 0, -dw, dw)
        return torch.where(self.plastic, dw, torch.zeros_like(dw))

    def pre_c1_signed_dw(self, spikes: torch.Tensor, g1n: torch.Tensor) -> torch.Tensor:
        """
        L3: as pre_c1_dw, times f(presynaptic rate) = clamp(rate / rate_thr - 1, -1, 1): depression
        (times |w|) below the rate threshold, potentiation (times bound - |w|) above it; with
        weight_dep "mult" both also times the other factor, as in the STDP rule.
        """
        f = torch.clamp(self.rate / self.rate_thr - 1.0, -1.0, 1.0)
        g_pre = (spikes.float() * g1n * f).view(1, self.N)
        g = g_pre * g1n[self.post] if self.pre_post_gate else g_pre.expand(self.S, self.N)
        w = self.effective().abs()
        if self.weight_dep == "upper":
            dw = self.a_pre * (torch.clamp(g, min=0.0) * (self.bound - w) + torch.clamp(g, max=0.0) * w)
        else:
            dw = self.a_pre * g * w * (self.bound - w)
        dw = torch.where(self.lo < 0, -dw, dw)
        return torch.where(self.plastic, dw, torch.zeros_like(dw))

    def btsp_step(self, spikes: torch.Tensor, t: int, c1_post: torch.Tensor):
        """L1 / L2: traces, gate events and, at the end of each event's window, the weight change."""
        b, t = self.btsp, int(t)
        sf = spikes.float()
        self.xp.mul_(self.dec_p).add_(sf)
        self.xd.mul_(self.dec_d).add_(sf)
        free = (self.ev_eval < 0) & ~(self.ev_done if b["once"] else torch.zeros_like(self.ev_done))
        if b["gate"] == "plateau":
            new = free & (torch.rand(self.N, generator=self.gen, device=self.dev) < float(b["plateau_rate"]))
        else:
            new = free & (self.c1_prev < self.theta1) & (c1_post >= self.theta1)
        self.c1_prev = c1_post.clone()
        after = int(b["window"]) - int(b["before"])
        self.ev_eval = torch.where(new, torch.full_like(self.ev_eval, t + after), self.ev_eval)
        self.ev_time = torch.where(new, torch.full_like(self.ev_time, t), self.ev_time)
        self.ev_done |= new
        self.gtr = torch.where(new, torch.ones_like(self.gtr), self.gtr)
        if b["form"] == "continuous":
            g = self.gtr[self.post]
            self.Ip.add_(g * self.xp.view(1, self.N))
            self.Id.add_(g * self.xd.view(1, self.N))
        self.gtr.mul_(self.dec_g)
        self.t_last = t
        self._btsp_apply(self.ev_eval == t, spikes, t)

    def _btsp_apply(self, due: torch.Tensor, spikes: torch.Tensor | None, t: int):
        """Weight change of the events in `due` (N,), whose windows end at step t (or are cut there)."""
        b = self.btsp
        if not bool(due.any()):
            return
        syn = due[self.post] & self.plastic
        w = torch.clamp(self.w_perm + self.w_fast, self.lo, self.hi)
        if b["form"] == "binary":
            last = self.last.clone()
            if spikes is not None:
                last[spikes] = t
            start = self.ev_time[self.post] - int(b["before"])          # (S, N): the window's first step
            active = syn & (last.view(1, self.N) >= start)
            flip = active & (torch.rand(w.shape, generator=self.gen, device=self.dev) < 0.5 * self.rate_scale)
            strong = w.abs() >= 0.5 * (self.lo.abs() + self.hi.abs())
            target = torch.where(strong, self.lo, self.hi)
            new_w = torch.where(flip, target, w)
        else:
            tot = self.Ip + self.Id
            ok = syn & (tot > 1e-9)
            target = self.bound * self.Ip / torch.clamp(tot, min=1e-9)
            new_w = torch.where(ok, w + float(b["rate"]) * self.rate_scale * (target - w), w)
            self.Ip = torch.where(syn, torch.zeros_like(self.Ip), self.Ip)
            self.Id = torch.where(syn, torch.zeros_like(self.Id), self.Id)
        self.w_fast = self.w_fast + torch.where(syn, torch.clamp(new_w, self.lo, self.hi) - w, torch.zeros_like(w))
        self.ev_eval = torch.where(due, torch.full_like(self.ev_eval, -1), self.ev_eval)

    def _input_sums(self, w: torch.Tensor) -> torch.Tensor:
        """(N,) summed |w| of the plastic synapses onto each neuron."""
        v = torch.where(self.plastic, w.abs(), torch.zeros_like(w))
        return torch.zeros(self.N, device=self.dev).index_add_(0, self.post.reshape(-1), v.reshape(-1))

    def normalize(self):
        """Scale each neuron's plastic input weights down to its target sum (changes w_fast only)."""
        eff = torch.clamp(self.w_perm + self.w_fast, self.lo, self.hi)
        f = torch.clamp(self.norm_target / torch.clamp(self._input_sums(eff), min=1e-9), max=1.0)
        self.w_fast = torch.where(self.plastic, eff * f[self.post] - self.w_perm, self.w_fast)

    def ltp_events(self, spikes: torch.Tensor, t: int) -> torch.Tensor:
        """(S, N) plastic synapses whose post fires now and whose pre fired within [t - 2D, t]."""
        t = int(t)
        last = self.last.clone()
        last[spikes] = t
        dt_pre = t - last.view(1, self.N)
        return spikes[self.post] & (dt_pre >= 0) & (dt_pre <= 2 * self.D) & self.plastic

    def capture(self, eligible: torch.Tensor, kappa: float = 1.0):
        """Move kappa of the positive w_fast of eligible synapses into w_perm (iteration 48)."""
        moved = float(kappa) * eligible.float() * torch.clamp(self.w_fast, min=0.0)
        self.w_perm = torch.where(self.fixed, self.w_perm, torch.clamp(self.w_perm + moved, self.lo, self.hi))
        self.w_fast = self.w_fast - moved

    def step(self, spikes: torch.Tensor, t: int, c1_post: torch.Tensor | None,
             c2_post: torch.Tensor | None, learn: bool, consolidate: bool):
        """
        c1_post / c2_post: per-neuron concentrations (N,) at each neuron's voxel.
        learn:        apply C1-gated changes to w_fast.
        consolidate:  move w_fast into w_perm where C1 and C2 gates are both on.
        w_fast decays every step unless both flags are False (frozen test phase).
        """
        if learn:
            before = self.w_fast.clone() if self.track_increase else None
            self.rate.mul_(self.rate_decay).add_(spikes.float(), alpha=1.0 - self.rate_decay)
            g1n = gate(c1_post, self.theta1, self.soft1)                 # (N,) per neuron
            if self.rule in ("stdp", "both"):
                self.w_fast.add_(g1n[self.post] * self.timing_dw(spikes, t), alpha=self.rate_scale)
            if self.rule in ("pre_c1", "both"):
                self.w_fast.add_(self.pre_c1_dw(spikes, g1n), alpha=self.rate_scale)
            if self.rule == "pre_c1_signed":
                self.w_fast.add_(self.pre_c1_signed_dw(spikes, g1n), alpha=self.rate_scale)
            if self.rule == "btsp":
                self.btsp_step(spikes, t, c1_post)
            if self.norm_factor:
                self.normalize()
            if before is not None:
                inc = torch.clamp(self.w_fast - before, min=0.0)
                self.increase_post = torch.zeros(self.N, device=self.dev).index_add_(
                    0, self.post.reshape(-1), torch.where(self.plastic, inc, torch.zeros_like(inc)).reshape(-1))
        elif self.track_increase:
            self.increase_post.zero_()
        if learn or consolidate:
            if consolidate:
                g12 = (gate(c1_post, self.theta1, self.soft1)
                       * gate(c2_post, self.theta2, self.soft2))[self.post] * self.consolidate_mask
                moved = self.kappa * g12 * self.w_fast
                self.w_perm.add_(moved)
                self.w_fast.sub_(moved)
                self.w_perm = torch.where(self.fixed, self.w_perm, torch.clamp(self.w_perm, self.lo, self.hi))
            self.w_fast.mul_(self.fast_decay)
        self.observe(spikes, t)
