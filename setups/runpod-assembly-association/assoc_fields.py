"""
Engine-independent fields for the assembly association task
(setups/runpod-assembly-association/runpod-assembly-association-task.md).

- VoxelMap:        neuron positions -> voxel indices of the task's own chemical grid.
- ChemicalField:   C1 / C2 concentration fields (release, 7-point diffusion, decay).
- EnergyField:     optional local energy (shortcut 2): consumption, recovery, excitability.
- FuelField:       shortcut 2 as a third chemical C3 ("fuel"): fixed total supply, delivered where
                   recently used, consumed by spikes (global depletion, competitive allocation).
- GroupActivity:   A_g(t) = fraction of group g's neurons that fired within the last W steps.

All classes run on CPU or CUDA tensors alike; nothing here imports snngine_v4.
"""

from __future__ import annotations

import torch
import torch.nn.functional as F


class VoxelMap:
    """
    Maps neuron positions to voxels of a regular grid spanning the reservoir.

    Axis order of every field in this module is (x, y, z) of the neuron positions:
    voxel (i, j, k) covers [i, i+1) * shape_x / dims_x, and so on. This is the task's
    own grid, independent of the engine's C0 grid and its (height, width, depth) order.
    """

    def __init__(self, pos: torch.Tensor, reservoir_shape, dims):
        self.dims = tuple(int(d) for d in dims)
        shape = torch.as_tensor(reservoir_shape, dtype=torch.float32, device=pos.device)
        dims_t = torch.as_tensor(self.dims, dtype=torch.float32, device=pos.device)
        idx = torch.floor(pos.float() / shape * dims_t).long()
        idx = torch.minimum(torch.clamp(idx, min=0), (dims_t - 1).long())
        self.ijk = idx  # (N, 3)
        dx, dy, dz = self.dims
        self.lin = idx[:, 0] * (dy * dz) + idx[:, 1] * dz + idx[:, 2]  # (N,)
        self.n_voxels = dx * dy * dz

    def counts(self, mask: torch.Tensor) -> torch.Tensor:
        """Number of True entries of a per-neuron mask in each voxel, as a (dx, dy, dz) float field."""
        out = torch.zeros(self.n_voxels, dtype=torch.float32, device=self.lin.device)
        out.index_add_(0, self.lin, mask.float())
        return out.view(self.dims)

    def sample(self, field: torch.Tensor) -> torch.Tensor:
        """Per-neuron value of a (dx, dy, dz) field at each neuron's voxel."""
        return field.reshape(-1)[self.lin]


def laplacian_zero_flux(c: torch.Tensor) -> torch.Tensor:
    """
    7-point Laplacian (sum of the 6 neighbours minus 6 * centre) with zero-flux boundaries:
    an out-of-grid neighbour takes the centre voxel's value, as in the engine's
    update_chemical_concentrations_ kernel (snn_simulation.cu, halo cells at the grid edge).
    """
    p = F.pad(c[None, None], (1, 1, 1, 1, 1, 1), mode="replicate")[0, 0]
    s = (
        p[2:, 1:-1, 1:-1] + p[:-2, 1:-1, 1:-1]
        + p[1:-1, 2:, 1:-1] + p[1:-1, :-2, 1:-1]
        + p[1:-1, 1:-1, 2:] + p[1:-1, 1:-1, :-2]
    )
    return s - 6.0 * c


class ChemicalField:
    """
    One chemical (C1 or C2).

    Per diffusion substep:  c <- clamp((c + k * lap(c)) * (1 - decay) - depreciation, 0, c_max),
    then voxels with source > 0 are clamped to the source value. With decay = 0 this is the
    engine kernel's update rule (k_val, depreciation, cap 2000, clamped sources).
    Release adds `gain` per spike at the firing neuron's voxel (proportional to activity).
    """

    MAX_STABLE_K = 1.0 / 6.0

    def __init__(self, dims, device, k: float = 0.16, decay: float = 0.0,
                 depreciation: float = 0.0, c_max: float = 2000.0, substeps: int = 1):
        if not (0.0 <= k <= self.MAX_STABLE_K + 1e-9):
            raise ValueError(f"k={k} outside the stable range [0, 1/6]")
        self.dims = tuple(int(d) for d in dims)
        self.k = float(k)
        self.decay = float(decay)
        self.depreciation = float(depreciation)
        self.c_max = float(c_max)
        self.substeps = int(substeps)
        self.c = torch.zeros(self.dims, dtype=torch.float32, device=device)
        self.source = torch.zeros_like(self.c)

    def reset(self):
        self.c.zero_()
        self.source.zero_()

    def release(self, spike_counts: torch.Tensor, gain: float, saturation: float | None = None):
        """
        spike_counts: (dx, dy, dz) number of spikes per voxel in this step.
        saturation: if set, release is self-limiting, gain * (1 - c / saturation) per spike,
        so local release stops once the concentration reaches `saturation`.
        """
        if gain != 0.0:
            if saturation:
                s = float(saturation)
                inc = spike_counts * float(gain) * torch.clamp(1.0 - self.c / s, min=0.0)
                # release never pushes a voxel above `saturation` (diffusion may bring more in)
                self.c = torch.where(self.c < s, torch.minimum(self.c + inc, torch.tensor(s, device=self.c.device)),
                                     self.c)
            else:
                self.c.add_(spike_counts, alpha=float(gain))
            self.c.clamp_(max=self.c_max)

    def diffuse(self, substeps: int | None = None):
        n = self.substeps if substeps is None else int(substeps)
        src_mask = self.source > 0.0
        for _ in range(n):
            c = self.c + self.k * laplacian_zero_flux(self.c)
            if self.decay != 0.0:
                c = c * (1.0 - self.decay)
            if self.depreciation != 0.0:
                c = c - self.depreciation
            c.clamp_(0.0, self.c_max)
            if src_mask.any():
                c = torch.where(src_mask, self.source, c)
            self.c = c


class EnergyField:
    """
    Optional local energy (allowed shortcut 2).

    Per step:  e <- e - consume * spikes_per_voxel + recover * (baseline - e) + k * lap(e),
    clamped to [0, baseline]. Excitability of a neuron = (e / baseline) ** exponent at its
    voxel; the harness scales the neuron's synaptic input current by it (default idea in the task).
    """

    def __init__(self, dims, device, consume: float = 0.05, recover: float = 0.01,
                 k: float = 0.0, baseline: float = 1.0, exponent: float = 1.0):
        if not (0.0 <= k <= ChemicalField.MAX_STABLE_K + 1e-9):
            raise ValueError(f"k={k} outside the stable range [0, 1/6]")
        self.dims = tuple(int(d) for d in dims)
        self.consume = float(consume)
        self.recover = float(recover)
        self.k = float(k)
        self.baseline = float(baseline)
        self.exponent = float(exponent)
        self.e = torch.full(self.dims, self.baseline, dtype=torch.float32, device=device)

    def reset(self):
        self.e.fill_(self.baseline)

    def step(self, spike_counts: torch.Tensor):
        e = self.e - self.consume * spike_counts + self.recover * (self.baseline - self.e)
        if self.k != 0.0:
            e = e + self.k * laplacian_zero_flux(e)
        self.e = e.clamp_(0.0, self.baseline)

    def excitability(self, vmap: VoxelMap) -> torch.Tensor:
        f = vmap.sample(self.e) / self.baseline
        return f if self.exponent == 1.0 else f.pow(self.exponent)


class FuelField:
    """
    Energy as a third chemical, C3 "fuel" (shortcut 2, the user's variant, iteration 58): a fixed
    total supply per step, delivered where it was recently used, consumed by spikes.

    Per step, per voxel (c = C3 concentration, r = mean supply per voxel and step):
        trace <- trace * (1 - 1 / tau) + spikes          (recent use)
        share  = (trace + floor) ** beta / mean((trace + floor) ** beta)      (mean share 1)
        c     <- c + r * share - consume * spikes - decay * c + k * lap(c),   clamped at >= 0
    The total delivered is r * n_voxels every step whatever the activity, so activity spread over
    the whole reservoir lowers C3 everywhere (global depletion), while concentrated activity draws
    the supply towards itself (usage raises local availability). Without activity c settles at
    c_ref = r / decay. Excitability of a neuron = min(c / c_ref, cap) at its voxel.
    """

    def __init__(self, dims, device, supply: float = 0.01, decay: float = 0.01, consume: float = 1.0,
                 tau: float = 50.0, floor: float = 0.05, beta: float = 1.0, cap: float = 2.0, k: float = 0.0):
        if not (0.0 <= k <= ChemicalField.MAX_STABLE_K + 1e-9):
            raise ValueError(f"k={k} outside the stable range [0, 1/6]")
        if tau < 1.0 or floor <= 0.0 or supply <= 0.0 or decay <= 0.0:
            raise ValueError("need tau >= 1 and floor, supply, decay > 0")
        self.dims = tuple(int(d) for d in dims)
        self.supply, self.decay, self.consume = float(supply), float(decay), float(consume)
        self.tau, self.floor, self.beta = float(tau), float(floor), float(beta)
        self.cap, self.k = float(cap), float(k)
        self.c_ref = self.supply / self.decay
        self.trace = torch.zeros(self.dims, dtype=torch.float32, device=device)
        self.c = torch.full(self.dims, self.c_ref, dtype=torch.float32, device=device)

    def reset(self):
        self.trace.zero_()
        self.c.fill_(self.c_ref)

    def share(self) -> torch.Tensor:
        w = (self.trace + self.floor).pow(self.beta)
        return w / w.mean()

    def step(self, spike_counts: torch.Tensor):
        self.trace = self.trace * (1.0 - 1.0 / self.tau) + spike_counts
        c = self.c + self.supply * self.share() - self.consume * spike_counts - self.decay * self.c
        if self.k != 0.0:
            c = c + self.k * laplacian_zero_flux(c)
        self.c = c.clamp_(min=0.0)

    @property
    def e(self) -> torch.Tensor:
        """(dx, dy, dz) C3 relative to its resting level; telemetry reads it like EnergyField.e."""
        return self.c / self.c_ref

    def excitability(self, vmap: VoxelMap) -> torch.Tensor:
        return vmap.sample(self.e).clamp(max=self.cap)


class GroupActivity:
    """A_g(t): fraction of each location group's neurons that fired within the last `window` steps."""

    def __init__(self, groups: torch.Tensor, n_groups: int, window: int = 20,
                 member_mask: torch.Tensor | None = None):
        self.groups = groups.long()
        self.n_groups = int(n_groups)
        self.window = int(window)
        dev = self.groups.device
        self.member = (torch.ones_like(self.groups, dtype=torch.bool)
                       if member_mask is None else member_mask.bool())
        self.size = torch.zeros(self.n_groups, dtype=torch.float32, device=dev)
        self.size.index_add_(0, self.groups, self.member.float())
        self.last = torch.full(self.groups.shape, -10 ** 9, dtype=torch.long, device=dev)

    def reset(self):
        self.last.fill_(-10 ** 9)

    def update(self, spikes: torch.Tensor, t: int) -> torch.Tensor:
        self.last[spikes] = int(t)
        recent = ((int(t) - self.last) < self.window) & self.member
        a = torch.zeros(self.n_groups, dtype=torch.float32, device=self.groups.device)
        a.index_add_(0, self.groups, recent.float())
        return a / torch.clamp(self.size, min=1.0)
