"""
Headless snngine_v4 network for the assembly association task, built through the sibling
chemical diffusion script (setups/runpod-chem-diffusion/generate_chem_diffusion_video.py,
imported, not modified), plus the per-step hooks the protocol needs.

Engine facts used here (snngine_v4/nn/cuda_backend/src/simulation/snn_simulation.cu):
- update() runs update_N_state_ (reads N_states row 7 = input current, then zeroes it),
  then update_current_ (adds the synaptic currents for the next step into row 7).
  Current added to row 7 from Python between two update() calls is therefore read by the
  next update_N_state_ (verified on the pod in Substep 0, check `python_injection`).
- Izhikevich integration uses two 0.5 half-steps per update(): one step = 1 ms.
- Fired[n] = t (float) when neuron n fired in the step with engine time t, else 0.
- Synapse s of neuron n: index n + N * s, tensors of shape (S, N).
"""

from __future__ import annotations

import os
import sys

import numpy as np
import torch

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
if not os.path.exists(os.path.join(_REPO_ROOT, "snngine_v4")):
    for _c in ("/workspace/snngineV4_cloud/snngineV4_agent_branches", "/workspace/snngineV4_agent_branches"):
        if os.path.exists(os.path.join(_c, "snngine_v4")):
            _REPO_ROOT = _c
            break
_CHEM_DIR = os.path.join(_REPO_ROOT, "setups", "runpod-chem-diffusion")
for _p in (_SCRIPT_DIR, _CHEM_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

ROW_PT, ROW_U, ROW_V, ROW_I = 0, 1, 2, 7
FLAG_TYPE, FLAG_GROUP = 1, 2
TYPE_INH, TYPE_EXC = 1, 2


class AssocEngine:
    """Owns the engine objects and exposes tensors and per-step hooks."""

    def __init__(self, device: torch.device, n_neurons: int, reservoir_shape=(1.0, 1.0, 1.0),
                 engine_chem_dim: int = 32, seed: int = 0, warmup_steps: int = 5,
                 n_synapses: int | None = None, rewire: dict | None = None):
        np.random.seed(seed)
        torch.manual_seed(seed)
        from assoc_build import build_network

        self.device = device
        self.seed = int(seed)
        self.requested_S = n_synapses
        cd = int(engine_chem_dim)
        (self.network, self.element, self.simulator, self.sim_instance, self.backend) = build_network(
            device, n_neurons=int(n_neurons), n_synapses=n_synapses,
            reservoir_shape=tuple(float(x) for x in reservoir_shape), chem_shape_hwd=(cd, cd, cd))
        el = self.element
        cfg = el.config
        self.N, self.S, self.D, self.G = int(cfg.N), int(cfg.S), int(cfg.D), int(cfg.G)
        self.reservoir_shape = tuple(float(x) for x in cfg.grid.shape.data)
        self.seg = tuple(int(x) for x in cfg.grid.seg.data)

        # thalamic noise off: quiet baseline (task: keep off or set deliberately)
        el.L_Group_flags.gpu_values[1, :] = 0
        el.neuron_states.N_props.gpu_values[ROW_PT, :] = 0.0
        # engine STDP stays off (update(False, ...)); engine C0 is only used by the diffusion comparison
        c0 = el.chemicals.C0
        for t in (c0.c_current, c0.c_next, c0.c_source):
            t.zero_()

        self.states = el.neuron_states.N_props.gpu_values          # (rows, N) float32
        self.flags = el.neuron_states.N_flags.gpu_values            # (rows, N) int32
        syn = el.synapses
        self.n_rep = syn.N_rep.gpu_values                           # (S, N) int32
        self.weights = syn.N_weights.gpu_values                     # (S, N) float32
        self.n_delays = syn.N_delays.gpu_values                     # (D + 1, N) int32
        self.fired = getattr(self.sim_instance.Fired, "gpu_values", self.sim_instance.Fired)
        self.pos = el.N_pos.float()                                 # (N, 3)
        self.types = self.flags[FLAG_TYPE].long()
        self.groups = self.flags[FLAG_GROUP].long()
        self.exc = self.types == TYPE_EXC

        self._ptr_weights = syn.N_weights.data_ptr()
        self._ptr_states = el.neuron_states.N_props.data_ptr()
        self.t = 0
        for _ in range(int(warmup_steps)):  # engine t = 0 cannot be told apart from "no spike"
            self.step()
        self.init_states = self.states.clone()
        self.built_weights = self.weights.clone()

        g_idx = self.groups
        cnt = torch.zeros(self.G, device=device).index_add_(0, g_idx, torch.ones(self.N, device=device))
        cen = torch.zeros((self.G, 3), device=device).index_add_(0, g_idx, self.pos)
        self.group_size = cnt
        self.group_exc_size = torch.zeros(self.G, device=device).index_add_(0, g_idx, self.exc.float())
        self.group_centroid = cen / torch.clamp(cnt, min=1).view(-1, 1)
        cell = torch.tensor(self.reservoir_shape, device=device) / torch.tensor(self.seg, device=device).float()
        self.cell_size = cell
        self.group_cell = torch.floor(self.group_centroid / cell).long()  # (G, 3) grid coordinates
        self.rewire_spec = rewire
        if rewire:
            self.rewire_by_distance(**rewire)
            self.built_weights = self.weights.clone()

    # ---------------------------------------------------------------- connectivity

    def rewire_by_distance(self, lam: float, seed: int = 0, autapse_tries: int = 20):
        """
        Distance-dependent connectivity (tuning-log iteration 39). The engine's own rule is
        practically flat in space (iteration 39 survey), so after construction every synapse gets a
        new target: group drawn with probability proportional to (neurons of the target's type in
        the group) * exp(-d / lam), d = distance between the cell centres in cells, neuron uniform
        within the group. The target's type (excitatory / inhibitory) is kept, so inhibitory neurons
        still project only to excitatory ones and the per-type synapse counts stay as built; no
        autapses. The delay of a synapse follows the engine's rule round((D - 1) * d / d_max)
        (spnn_reservoir.py), and each neuron's synapses are re-sorted into the delay buckets of
        N_delays, which the simulation kernel reads (update_current_). N_rep, N_weights and N_delays
        are written in place; the pre-synaptic reverse indices are only used by the engine's STDP,
        which stays off.
        """
        dev, G, N, S, D = self.device, self.G, self.N, self.S, self.D
        gen = torch.Generator(device=dev)
        gen.manual_seed(int(seed))
        cells = self.group_cell.float()
        dist = torch.cdist(cells, cells)
        kern = torch.exp(-dist / float(lam))
        valid = self.n_rep >= 0
        post_old = torch.clamp(self.n_rep.long(), min=0)
        tgt_exc = self.exc[post_old]
        pre_n = torch.arange(N, device=dev).view(1, -1).expand(S, N)
        pre_g = self.groups[pre_n]
        new_post = post_old.clone()
        for is_exc in (True, False):
            members = torch.nonzero(self.exc == is_exc).view(-1)
            order = torch.argsort(self.groups[members], stable=True)
            members = members[order]
            counts = torch.bincount(self.groups[members], minlength=G)
            starts = torch.cumsum(counts, 0) - counts
            prob = kern.double() * counts.double().view(1, -1)
            prob = prob / prob.sum(dim=1, keepdim=True).clamp(min=1e-300)
            cdf = torch.cumsum(prob, dim=1)
            cdf[:, -1] = 1.0
            flat = (cdf + torch.arange(G, device=dev, dtype=cdf.dtype).view(-1, 1)).reshape(-1)

            def draw(gp):
                u = torch.rand(gp.shape, generator=gen, device=dev, dtype=torch.float64) * (1.0 - 1e-12)
                k = torch.searchsorted(flat, gp.to(flat.dtype) + u, right=True)
                g_new = torch.clamp(k - gp * G, 0, G - 1)
                u2 = torch.rand(gp.shape, generator=gen, device=dev)
                j = starts[g_new] + torch.minimum((u2 * counts[g_new]).long(), counts[g_new] - 1)
                return members[j]

            sel = valid & (tgt_exc == is_exc)
            new_post[sel] = draw(pre_g[sel])
            for _ in range(int(autapse_tries)):
                auto = sel & (new_post == pre_n)
                if not bool(auto.any()):
                    break
                new_post[auto] = draw(pre_g[auto])
        auto = valid & (new_post == pre_n)
        if bool(auto.any()):
            raise RuntimeError(f"{int(auto.sum())} autapses left after rewiring")
        delay = torch.round((D - 1) * dist[pre_g, self.groups[new_post]] / dist.max().clamp(min=1e-9)).long()
        delay = torch.where(valid, delay, torch.full_like(delay, D - 1))
        delay_s, perm = torch.sort(delay, dim=0, stable=True)
        rep = torch.where(valid, new_post, torch.full_like(new_post, -1)).gather(0, perm)
        w = self.weights.gather(0, perm)
        n_del = torch.stack([(delay_s < r).sum(dim=0) for r in range(D + 1)])
        self.n_rep.copy_(rep.to(self.n_rep.dtype))
        self.weights.copy_(w)
        self.n_delays.copy_(n_del.to(self.n_delays.dtype))
        self.rewire_stats = {"lam": float(lam), "seed": int(seed),
                             "mean_delay": float(delay_s[valid.gather(0, perm)].float().mean())}

    # ---------------------------------------------------------------- per step

    diag_file = None   # open text file: per-step crash diagnostics (see start_diag)
    diag_phase = ""

    def start_diag(self, path: str):
        """Log one line before and one after every update(), flushed, so the record survives a crash."""
        self.diag_file = open(path, "w", buffering=1)
        self.diag_file.write("kind,step,engine_t,phase,n_spikes,w_finite,w_min,w_max,"
                             "v_nan,v_min,v_max,u_min,u_max,i_min,i_max\n")

    def _diag_pre(self):
        w, s = self.weights, self.states
        v, u, i = s[ROW_V], s[ROW_U], s[ROW_I]
        vals = torch.stack([torch.isfinite(w).all().float(), w.min(), w.max(), torch.isnan(v).sum().float(),
                            v.min(), v.max(), u.min(), u.max(), i.min(), i.max()]).tolist()
        self.diag_file.write("pre,%d,%d,%s,," % (self.t, self.backend.t, self.diag_phase)
                             + ",".join("%.6g" % x for x in vals) + "\n")
        self.diag_file.flush()

    def step(self) -> torch.Tensor:
        if self.diag_file is not None:
            self._diag_pre()
        self.backend.update(False, False)
        self.t += 1
        spikes = self.fired != 0
        if self.diag_file is not None:
            self.diag_file.write("post,%d,%d,%s,%d\n" % (self.t, self.backend.t, self.diag_phase, int(spikes.sum())))
            self.diag_file.flush()
        return spikes

    def set_noise(self, pt: float = 0.0, exc_current: float = 15.0, inh_current: float = 25.0):
        """
        Background (thalamic) input, set deliberately and identically for every neuron: each step
        a neuron receives, with probability pt, a current uniform in [0, exc_current] (excitatory)
        or [0, inh_current] (inhibitory) (update_N_state_ in snn_simulation.cu). pt = 0: off.
        """
        el = self.element
        el.L_Group_flags.gpu_values[1, :] = 1 if pt > 0 else 0
        el.L_Group_properties.gpu_values[0, :] = float(inh_current)
        el.L_Group_properties.gpu_values[1, :] = float(exc_current)
        self.states[ROW_PT, :] = float(pt)
        self.init_states[ROW_PT, :] = float(pt)
        self.noise = {"pt": float(pt), "exc_current": float(exc_current), "inh_current": float(inh_current)}

    def add_current(self, idx: torch.Tensor, current: float):
        self.states[ROW_I, idx] += float(current)

    def input_current(self) -> torch.Tensor:
        """(N,) summed synaptic input pending for the next step (read right after step())."""
        return self.states[ROW_I]

    def add_current_vector(self, current: torch.Tensor):
        """(N,) current added to every neuron's input for the next step."""
        self.states[ROW_I] += current

    def scale_current(self, factor: torch.Tensor):
        self.states[ROW_I] *= factor

    def clamp_current(self, i_min: float | None = None, i_max: float | None = None):
        """
        Numerical safeguard: the kernel integrates v in two 0.5 ms half-steps, and a large
        negative input drives v so far down in the first half-step that the quadratic term
        overshoots past threshold in the second one (e.g. v = -65, I = -500: v -> -316 -> +717,
        a spurious spike). Clamping the summed input from below avoids this artefact.
        From above (i_max): under total runaway the summed input reached about 7,800 and v about
        60,000 (iteration 23); at I = 100 a resting neuron still fires in one step
        (v = -65 -> -16.5 -> +74), so the clamp only cuts the numerical explosion.
        """
        self.states[ROW_I].clamp_(min=None if i_min is None else float(i_min),
                                  max=None if i_max is None else float(i_max))

    gain = 1.0  # global synaptic current gain: the engine receives gain * w
    gain_map = None  # optional (S, N) per-synapse gain (gain by neuron-type pair), overrides gain

    def set_gains(self, gain: float = 1.0, gain_ei: float = 1.0, gain_ie: float = 1.0, gain_ee_inter: float = 1.0,
                  inter_norm: bool = False):
        """
        Synaptic current gains by neuron-type pair, identical for every pair of groups:
        excitatory-to-excitatory gain, excitatory-to-inhibitory gain * gain_ei,
        inhibitory-to-excitatory gain * gain_ie; excitatory-to-excitatory synapses outside
        assemblies (between different location groups, or within a non-assembly group)
        additionally * gain_ee_inter (with a correspondingly lower initial w_ee, a learned path
        can carry more current without more untrained spread).
        inter_norm (iteration 45): those synapses additionally * mean in-degree / in-degree of their
        target (in-degree: the target's number of such synapses), so every excitatory neuron's
        summed gain over its inter-group excitatory inputs is the same (synaptic scaling).
        """
        self.gain = float(gain)
        if gain_ei == 1.0 and gain_ie == 1.0 and gain_ee_inter == 1.0 and not inter_norm:
            self.gain_map = None
            return
        post = torch.clamp(self.n_rep.long(), min=0)
        pre_exc = self.exc.view(1, -1).expand_as(post)
        post_exc = self.exc[post]
        m = torch.full(post.shape, float(gain), device=self.device)
        m[pre_exc & ~post_exc] *= float(gain_ei)
        m[~pre_exc & post_exc] *= float(gain_ie)
        if gain_ee_inter != 1.0 or inter_norm:
            intra_asm = (self.groups[post] == self.groups.view(1, -1)) & self.assembly_of_neuron().view(1, -1)
            inter = pre_exc & post_exc & ~intra_asm
            m[inter] *= float(gain_ee_inter)
            if inter_norm:
                inter &= self.n_rep >= 0
                indeg = torch.zeros(self.N, device=self.device).index_add_(0, post[inter], torch.ones_like(m[inter]))
                mean = indeg[indeg > 0].mean()
                m[inter] *= mean / indeg[post[inter]]
        self.gain_map = m

    def write_weights(self, w: torch.Tensor):
        """w: normalized weights (plasticity bounds [0.05, 1] / [-1, -0.05]); N_weights = gain * w."""
        if self.gain_map is not None:
            torch.mul(w, self.gain_map, out=self.weights)
        elif self.gain == 1.0:
            self.weights.copy_(w)
        else:
            torch.mul(w, self.gain, out=self.weights)

    def read_weights(self) -> torch.Tensor:
        """Normalized weights currently in N_weights."""
        return self.weights / (self.gain_map if self.gain_map is not None else self.gain)

    # ---------------------------------------------------------------- state

    def reset_dynamics(self, quiet_steps: int | None = None):
        """Back to the post-warmup neuron state, with spikes still in flight flushed out."""
        w_saved = self.weights.clone()
        self.weights.zero_()
        self.states.copy_(self.init_states)
        for _ in range(int(quiet_steps if quiet_steps is not None else self.D + 2)):
            self.step()
        self.weights.copy_(w_saved)
        self.states.copy_(self.init_states)
        self.states[ROW_I].zero_()

    def typed_weights(self, w_ee=None, w_ei=None, w_ie=None, w_intra_ee=None, w_intra_ei=None,
                      w_intra_ee_total=None, w_intra_ee_cap=None):
        """
        Global weights by neuron type (identical for every pair), plus the allowed intra-group
        boost (shortcut 1) for synapses whose pre and post sit in the same location group.
        None keeps the engine's built value.
        w_intra_ee_total (replaces w_intra_ee): every excitatory neuron's incoming intra-group
        excitatory weights are w_intra_ee_total / (its number of such synapses), so its summed
        intra-group input when its whole group fires is the same for every neuron, whatever the
        group's internal density; w_intra_ee_cap bounds the single weight.
        """
        w = self.built_weights.clone()
        post = torch.clamp(self.n_rep.long(), min=0)
        pre_exc = self.exc.view(1, -1).expand_as(post)
        post_exc = self.exc[post]
        # shortcut 1 applies only within assemblies (see set_assemblies)
        same = (self.groups[post] == self.groups.view(1, -1)) & self.assembly_of_neuron().view(1, -1)
        valid = self.n_rep >= 0
        for val, mask in ((w_ee, pre_exc & post_exc), (w_ei, pre_exc & ~post_exc),
                          (w_ie, ~pre_exc & post_exc)):
            if val is not None:
                w[mask & valid] = float(val)
        if w_intra_ee_total is not None:
            m = pre_exc & post_exc & same & valid
            indeg = torch.zeros(self.N, device=w.device).index_add_(0, post[m], torch.ones_like(w[m]))
            vals = float(w_intra_ee_total) / indeg[post[m]]
            w[m] = vals if w_intra_ee_cap is None else torch.clamp(vals, max=float(w_intra_ee_cap))
        elif w_intra_ee is not None:
            w[pre_exc & post_exc & same & valid] = float(w_intra_ee)
        if w_intra_ei is not None:
            w[pre_exc & ~post_exc & same & valid] = float(w_intra_ei)
        return w

    def intra_ee_mask(self) -> torch.Tensor:
        """(S, N): excitatory-to-excitatory synapses within one assembly (location group)."""
        post = torch.clamp(self.n_rep.long(), min=0)
        same = (self.groups[post] == self.groups.view(1, -1)) & self.assembly_of_neuron().view(1, -1)
        return same & self.exc.view(1, -1) & self.exc[post] & (self.n_rep >= 0)

    assembly = None  # (G,) bool: location groups that are assemblies; None: every group

    def set_assemblies(self, mask: torch.Tensor | None):
        self.assembly = None if mask is None else mask.to(self.groups.device).bool()

    def assembly_of_neuron(self) -> torch.Tensor:
        """(N,) bool: the neuron belongs to an assembly."""
        if self.assembly is None:
            return torch.ones(self.groups.shape[0], dtype=torch.bool, device=self.groups.device)
        return self.assembly[self.groups]

    def synapse_delays(self) -> torch.Tensor:
        from assoc_plasticity import delays_from_N_delays
        return delays_from_N_delays(self.n_delays, self.S)

    # ---------------------------------------------------------------- checks

    def structure_report(self) -> dict:
        nd = self.n_delays
        post = torch.clamp(self.n_rep.long(), min=0)
        same = (self.groups[post] == self.groups.view(1, -1)) & (self.n_rep >= 0)
        intra_ee = same & self.exc.view(1, -1) & self.exc[post]
        return {
            "N": self.N, "S": self.S, "D": self.D, "G": self.G,
            "seg": self.seg, "reservoir_shape": self.reservoir_shape,
            "n_rep_shape": list(self.n_rep.shape), "weights_shape": list(self.weights.shape),
            "n_delays_shape": list(nd.shape),
            "n_delays_row0_zero": bool((nd[0] == 0).all()),
            "n_delays_last_row_is_S": bool((nd[-1] == self.S).all()),
            "n_delays_monotone": bool((nd[1:] >= nd[:-1]).all()),
            "deleted_synapses": int((self.n_rep < 0).sum()),
            "types": {int(k): int(v) for k, v in zip(*torch.unique(self.types, return_counts=True))},
            "group_size_min": int(self.group_size.min()), "group_size_mean": float(self.group_size.mean()),
            "group_exc_size_min": int(self.group_exc_size.min()),
            "intra_group_ee_synapses_per_exc_neuron": float(intra_ee.sum()) / max(1, int(self.exc.sum())),
            "weight_values": sorted({round(float(x), 4) for x in torch.unique(self.built_weights)})[:12],
            "weights_ptr_stable": self.weights.data_ptr() == self._ptr_weights,
            "states_ptr_stable": self.states.data_ptr() == self._ptr_states,
            "requested_S": self.requested_S,
            "thalamic_flags_on": int(self.element.L_Group_flags.gpu_values[1].sum()),
            "pt_nonzero": int((self.states[ROW_PT] != 0).sum()),
            "step_ms": 1.0,
        }
