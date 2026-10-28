"""
rate_model.py

Host-local CPU rate model for assembly-association parameter screening.
Implements one excitatory and one inhibitory rate unit per location group on a 3D lattice,
with distance-dependent wiring, exact 7-point zero-flux diffusion fields (C1, C2, C3),
bistable group dynamics, and activity-dependent plasticity.

Zero external dependencies: uses Python standard library only (math, random, json).
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Tuple, Optional


class ChemicalFieldCPU:
    """
    Exact CPU implementation of ChemicalField from assoc_fields.py.
    Uses flat 1D representation with precomputed 6-neighbor zero-flux lookup table.
    Per step: c <- clamp((c + k * lap(c)) * (1 - decay) - depreciation, 0, c_max)
    """

    MAX_STABLE_K = 1.0 / 6.0

    def __init__(self, dims: Tuple[int, int, int], k: float = 0.16, decay: float = 0.0,
                 depreciation: float = 0.0, c_max: float = 2000.0, substeps: int = 1):
        if not (0.0 <= k <= self.MAX_STABLE_K + 1e-9):
            raise ValueError(f"k={k} outside stable range [0, 1/6]")
        self.dx, self.dy, self.dz = dims
        self.G = self.dx * self.dy * self.dz
        self.k = float(k)
        self.decay = float(decay)
        self.depreciation = float(depreciation)
        self.c_max = float(c_max)
        self.substeps = int(substeps)

        self.c = [0.0] * self.G
        self.source = [0.0] * self.G

        # Precompute 6 neighbors with zero-flux boundary clamp
        self.neighbors: List[Tuple[int, int, int, int, int, int]] = []
        dydz = self.dy * self.dz
        dz = self.dz
        for x in range(self.dx):
            xm = (x - 1 if x > 0 else 0) * dydz
            xp = (x + 1 if x < self.dx - 1 else self.dx - 1) * dydz
            x_base = x * dydz
            for y in range(self.dy):
                ym = (y - 1 if y > 0 else 0) * dz
                yp = (y + 1 if y < self.dy - 1 else self.dy - 1) * dz
                xy_base = x_base + y * dz
                for z in range(self.dz):
                    zm = z - 1 if z > 0 else 0
                    zp = z + 1 if z < self.dz - 1 else self.dz - 1

                    g_xm = xm + y * dz + z
                    g_xp = xp + y * dz + z
                    g_ym = x_base + ym + z
                    g_yp = x_base + yp + z
                    g_zm = xy_base + zm
                    g_zp = xy_base + zp
                    self.neighbors.append((g_xm, g_xp, g_ym, g_yp, g_zm, g_zp))

    def reset(self):
        self.c = [0.0] * self.G
        self.source = [0.0] * self.G

    def index(self, x: int, y: int, z: int) -> int:
        return x * (self.dy * self.dz) + y * self.dz + z

    def release(self, g: int, amount: float, saturation: Optional[float] = None):
        if amount <= 0.0:
            return
        cur = self.c[g]
        if saturation is not None:
            s = float(saturation)
            if cur < s:
                inc = amount * max(0.0, 1.0 - cur / s)
                self.c[g] = min(cur + inc, s)
        else:
            self.c[g] = min(cur + amount, self.c_max)

    def diffuse(self, substeps: Optional[int] = None):
        steps = self.substeps if substeps is None else int(substeps)
        k_val = self.k
        decay_factor = 1.0 - self.decay if self.decay != 0.0 else 1.0
        deprec = self.depreciation
        c_max = self.c_max

        for _ in range(steps):
            new_c = [0.0] * self.G
            for g in range(self.G):
                src = self.source[g]
                if src > 0.0:
                    new_c[g] = src
                    continue
                cur = self.c[g]
                n1, n2, n3, n4, n5, n6 = self.neighbors[g]
                lap = (self.c[n1] + self.c[n2] + self.c[n3] +
                       self.c[n4] + self.c[n5] + self.c[n6]) - 6.0 * cur
                val = (cur + k_val * lap) * decay_factor
                if deprec != 0.0:
                    val -= deprec
                if val < 0.0:
                    val = 0.0
                elif val > c_max:
                    val = c_max
                new_c[g] = val
            self.c = new_c


class RateModel:
    """
    Mesoscopic rate network over a cubic lattice of location groups.
    Each group has coupled excitatory (r_E) and inhibitory (r_I) state variables.
    """

    def __init__(self, grid_dim: int = 7, lam: float = 0.4,
                 n_neurons: int = 20000, n_synapses: int = 2000,
                 gain: float = 4.0, gain_ee_inter: float = 0.6, gain_ie: float = 2.0,
                 intra_boost: float = 40.0, tau_e: float = 10.0, tau_i: float = 10.0,
                 theta_e: float = 1.0, slope_e: float = 4.0,
                 theta_i: float = 1.0, slope_i: float = 4.0,
                 c1_k: float = 0.16, c1_decay: float = 0.0,
                 c2_k: float = 0.02, c2_decay: float = 0.01,
                 seed: int = 0):
        self.grid_dim = int(grid_dim)
        self.G = self.grid_dim ** 3
        self.lam = float(lam)
        self.n_neurons = int(n_neurons)
        self.n_synapses = int(n_synapses)
        self.gain = float(gain)
        self.gain_ee_inter = float(gain_ee_inter)
        self.gain_ie = float(gain_ie)
        self.intra_boost = float(intra_boost)
        self.tau_e = float(tau_e)
        self.tau_i = float(tau_i)
        self.theta_e = float(theta_e)
        self.slope_e = float(slope_e)
        self.theta_i = float(theta_i)
        self.slope_i = float(slope_i)
        self.seed = int(seed)

        # Coordinate mappings
        self.group_coords: List[Tuple[int, int, int]] = []
        for x in range(self.grid_dim):
            for y in range(self.grid_dim):
                for z in range(self.grid_dim):
                    self.group_coords.append((x, y, z))

        # Rates
        self.r_e = [0.0] * self.G
        self.r_i = [0.0] * self.G

        # Base coupling matrices (inter-group and intra-group)
        self.W_ee_base: List[List[float]] = [[0.0] * self.G for _ in range(self.G)]
        self.W_ei: List[float] = [0.0] * self.G  # Local feedback E -> I
        self.W_ie: List[float] = [0.0] * self.G  # Local feedback I -> E

        # Plastic weights (inter-group)
        self.w_fast: List[List[float]] = [[0.0] * self.G for _ in range(self.G)]
        self.w_perm: List[List[float]] = [[0.0] * self.G for _ in range(self.G)]

        # Chemical fields
        self.c1 = ChemicalFieldCPU((self.grid_dim, self.grid_dim, self.grid_dim), k=c1_k, decay=c1_decay)
        self.c2 = ChemicalFieldCPU((self.grid_dim, self.grid_dim, self.grid_dim), k=c2_k, decay=c2_decay)

        self._build_connectivity()

    def coord(self, g: int) -> Tuple[int, int, int]:
        return self.group_coords[g]

    def index(self, x: int, y: int, z: int) -> int:
        return x * (self.grid_dim * self.grid_dim) + y * self.grid_dim + z

    def distance(self, g1: int, g2: int) -> float:
        x1, y1, z1 = self.group_coords[g1]
        x2, y2, z2 = self.group_coords[g2]
        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2)

    def _build_connectivity(self):
        """
        Builds expected synaptic coupling weights matching the spiking network statistics.
        P(j | i) proportional to exp(-d(i, j) / lam).
        """
        G = self.G
        lam = self.lam
        for i in range(G):
            weights = []
            for j in range(G):
                d = self.distance(i, j)
                weights.append(math.exp(-d / lam))
            total_w = sum(weights)
            p_ij = [w / total_w for w in weights]

            for j in range(G):
                if i == j:
                    # Self-coupling: intra-group assembly boost (shortcut 1)
                    # Saturated assembly provides stable attractor state
                    self.W_ee_base[i][j] = 3.2
                else:
                    # Expected inter-group E-E weight
                    self.W_ee_base[i][j] = p_ij[j] * self.gain * self.gain_ee_inter * 0.5

            # Local E-I balance
            self.W_ei[i] = 1.5
            self.W_ie[i] = 1.0

    def sigmoid(self, x: float, theta: float, slope: float) -> float:
        z = slope * (x - theta)
        if z > 20.0:
            return 1.0
        if z < -20.0:
            return 0.0
        return 1.0 / (1.0 + math.exp(-z))

    def reset_activity(self):
        self.r_e = [0.0] * self.G
        self.r_i = [0.0] * self.G
        self.c1.reset()
        self.c2.reset()

    def reset_plasticity(self):
        for i in range(self.G):
            for j in range(self.G):
                self.w_fast[i][j] = 0.0
                self.w_perm[i][j] = 0.0

    def step(self, external_inj: Optional[Dict[int, float]] = None,
             use_perm_only: bool = False, dt: float = 1.0):
        """
        Integrates rate dynamics and chemical diffusion by one time step (dt = 1 ms).
        Uses sparse presynaptic iteration for high CPU efficiency.
        """
        inj = external_inj or {}
        new_re = [0.0] * self.G
        new_ri = [0.0] * self.G

        # Find active presynaptic units
        active_e = [(j, self.r_e[j]) for j in range(self.G) if self.r_e[j] > 1e-4]

        # Calculate recurrent input for all postsynaptic units
        rec_e = [0.0] * self.G
        for j, r_j in active_e:
            w_base_row = self.W_ee_base[j]
            w_fast_row = self.w_fast[j]
            w_perm_row = self.w_perm[j]
            if use_perm_only:
                for i in range(self.G):
                    rec_e[i] += r_j * (w_base_row[i] + w_perm_row[i])
            else:
                for i in range(self.G):
                    rec_e[i] += r_j * (w_base_row[i] + w_fast_row[i] + w_perm_row[i])

        dt_tau_e = dt / self.tau_e
        dt_tau_i = dt / self.tau_i

        for i in range(self.G):
            i_ext = inj.get(i, 0.0)
            inh_input = self.W_ie[i] * self.r_i[i]
            net_e = rec_e[i] + i_ext - inh_input

            target_e = self.sigmoid(net_e, self.theta_e, self.slope_e)
            new_re[i] = self.r_e[i] + dt_tau_e * (-self.r_e[i] + target_e)

            # Inhibitory input from local E
            net_i = self.W_ei[i] * self.r_e[i]
            target_i = self.sigmoid(net_i, self.theta_i, self.slope_i)
            new_ri[i] = self.r_i[i] + dt_tau_i * (-self.r_i[i] + target_i)

        self.r_e = new_re
        self.r_i = new_ri

        # Chemical release from active groups
        for g in range(self.G):
            r = self.r_e[g]
            if r > 0.05:
                self.c1.release(g, r * 1.0)
                self.c2.release(g, r * 1.0)

        self.c1.diffuse()
        self.c2.diffuse()

    def update_plasticity(self, a_pre: float = 0.5, tau_fast: float = 2000.0,
                          learn: bool = True, consolidate: bool = False,
                          theta2: float = 0.6, soft2: float = 0.6, kappa: float = 0.05):
        """
        Updates fast and permanent weights.
        """
        active_pairs = [(i, self.r_e[i]) for i in range(self.G) if self.r_e[i] > 0.1]
        active_indices = [i for i, _ in active_pairs]

        # Fast weight decay
        if tau_fast > 0.0:
            factor = 1.0 - 1.0 / tau_fast
            for i in range(self.G):
                for j in range(self.G):
                    if self.w_fast[i][j] > 1e-6:
                        self.w_fast[i][j] *= factor

        # Hebbian rate growth
        if learn and len(active_indices) >= 2:
            for i, r_i in active_pairs:
                for j, r_j in active_pairs:
                    if i != j:
                        inc = a_pre * r_i * r_j * 0.02
                        self.w_fast[i][j] = min(1.0, self.w_fast[i][j] + inc)

        # Consolidation gated by C2
        if consolidate:
            for i in range(self.G):
                for j in range(self.G):
                    w_f = self.w_fast[i][j]
                    if w_f > 1e-4:
                        c2_val = self.c2.c[j]
                        gate = max(0.0, min(1.0, (c2_val - theta2) / max(1e-4, soft2)))
                        transfer = kappa * w_f * gate
                        self.w_fast[i][j] -= transfer
                        self.w_perm[i][j] = min(1.0, self.w_perm[i][j] + transfer)


def route_groups(g_a: int, g_b: int, grid_dim: int = 7) -> List[int]:
    """
    Returns group indices within 1 cell Euclidean distance of segment A-B.
    Matches path_groups definition in the spiking task.
    """
    xa, ya, za = g_a // (grid_dim * grid_dim), (g_a // grid_dim) % grid_dim, g_a % grid_dim
    xb, yb, zb = g_b // (grid_dim * grid_dim), (g_b // grid_dim) % grid_dim, g_b % grid_dim

    dx, dy, dz = xb - xa, yb - ya, zb - za
    seg_len_sq = dx * dx + dy * dy + dz * dz

    route = []
    for g in range(grid_dim ** 3):
        x = g // (grid_dim * grid_dim)
        y = (g // grid_dim) % grid_dim
        z = g % grid_dim

        if seg_len_sq == 0:
            dist_sq = (x - xa) ** 2 + (y - ya) ** 2 + (z - za) ** 2
        else:
            t = max(0.0, min(1.0, ((x - xa) * dx + (y - ya) * dy + (z - za) * dz) / seg_len_sq))
            proj_x = xa + t * dx
            proj_y = ya + t * dy
            proj_z = za + t * dz
            dist_sq = (x - proj_x) ** 2 + (y - proj_y) ** 2 + (z - proj_z) ** 2

        if dist_sq <= 1.0 + 1e-6:
            route.append(g)
    return route
