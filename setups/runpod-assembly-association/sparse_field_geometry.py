"""
Field-geometry check of sparse-assemblies-task.md, Substep 0 (ChemicalField only, no neurons).

Two static sources, A and B, release at a constant rate while they are injected (the joint rounds'
50 injection + 50 gap steps); the field diffuses and decays with assoc_fields.ChemicalField on the
task's voxel grid (vox_per_cell voxels per location-group cell along each axis). Release, diffusion
and decay are linear in the concentration, so every quantity below is reported relative to the
concentration at A and does not depend on the release rate.

Per grid, distance d and diffusion length L (cells), at the end of the injection in rounds
`--rounds` (the last one close to the periodic steady state):
  (i)   C in the route middle M against the off-route shell Sh (the regions of
        assoc_protocol.AssocRun.regions, radius `--sel-radius` cells);
  (ii)  the threshold theta_c at which the region {C >= theta} around A first contains B
        (6-connected), and whether that first connection lies on the segment A-B: it does when
        theta_c equals the minimum of C along the straight segment (the segment is then an optimal
        connection);
  (iii) the radius of the region around A just above theta_c (largest distance from A's centre and
        the radius of the sphere of equal volume), in cells.
Also the C2 marker check: C at 1 cell from A relative to C at A for C2's settings.

decay for a target length L (voxels) at diffusion constant k, from the exact lattice relation of the
update c <- (c + k lap c)(1 - decay):  cosh(1 / L) = 1 + decay / (2 k (1 - decay)).

Usage:  python sparse_field_geometry.py --out output/sp0-field-geometry/field_geometry.json
        [--grids 7 11] [--dists 4 6] [--lengths 1 1.5 2 3 4] [--rounds 1 5 10 30] [--k 0.16]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time

import torch
import torch.nn.functional as F

from assoc_fields import ChemicalField


def decay_for_length(L_vox: float, k: float) -> float:
    x = 2.0 * k * (math.cosh(1.0 / L_vox) - 1.0)
    return x / (1.0 + x)


def length_for_decay(k: float, decay: float) -> float:
    return 1.0 / math.acosh(1.0 + decay / (2.0 * k * (1.0 - decay)))


def voxel_centres(n_vox: int, v: int) -> torch.Tensor:
    ax = (torch.arange(n_vox).float() + 0.5) / v
    return torch.stack(torch.meshgrid(ax, ax, ax, indexing="ij"), dim=-1)      # (n, n, n, 3), cells


def seg_coords(x: torch.Tensor, pa: torch.Tensor, pb: torch.Tensor):
    ab = pb - pa
    t = ((x - pa) @ ab) / (ab @ ab)
    rho = torch.linalg.norm(x - (pa + t.unsqueeze(-1) * ab), dim=-1)
    d_end = torch.minimum(torch.linalg.norm(x - pa, dim=-1), torch.linalg.norm(x - pb, dim=-1))
    return t, rho, d_end


def component(mask: torch.Tensor, seed: tuple) -> torch.Tensor:
    """6-connected component of `mask` containing voxel `seed` (empty if the seed is outside)."""
    comp = torch.zeros_like(mask)
    if not bool(mask[seed]):
        return comp
    comp[seed] = True
    m = mask.float()[None, None]
    c = comp.float()[None, None]
    kern = torch.zeros(1, 1, 3, 3, 3)
    kern[0, 0, 1, 1, :] = 1
    kern[0, 0, 1, :, 1] = 1
    kern[0, 0, :, 1, 1] = 1
    while True:
        grown = (F.conv3d(c, kern, padding=1) > 0).float() * m
        if torch.equal(grown, c):
            return c[0, 0] > 0
        c = grown


def first_connection(c: torch.Tensor, va: tuple, vb: tuple, rel_tol: float = 1e-4):
    """Largest theta at which {c >= theta} connects voxel va to vb (bisection on theta)."""
    lo, hi = 0.0, float(min(c[va], c[vb]))
    while hi - lo > rel_tol * hi:
        mid = 0.5 * (lo + hi)
        if bool(component(c >= mid, va)[vb]):
            lo = mid
        else:
            hi = mid
    return lo


def run_case(g: int, d: int, L_cells: float, k: float, v: int, rounds: list[int], inject: int, gap: int,
             sel_radius: float) -> dict:
    n = g * v
    decay = decay_for_length(L_cells * v, k)
    f = ChemicalField((n, n, n), "cpu", k=k, decay=decay)
    mid_cell = g // 2
    ca = (mid_cell - d // 2, mid_cell, mid_cell)
    cb = (ca[0] + d, mid_cell, mid_cell)
    src = torch.zeros(n, n, n)
    for cell in (ca, cb):
        sl = tuple(slice(i * v, (i + 1) * v) for i in cell)
        src[sl] = 1.0 / v ** 3                      # one unit per step per group, spread over its voxels
    pa = torch.tensor(ca, dtype=torch.float32) + 0.5
    pb = torch.tensor(cb, dtype=torch.float32) + 0.5
    x = voxel_centres(n, v)
    t, rho, d_end = seg_coords(x, pa, pb)
    lo_s, hi_s = d / 4, math.sqrt((d / 2) ** 2 + sel_radius ** 2)
    M = (rho < sel_radius) & (t >= 0.25) & (t <= 0.75)
    Sh = (rho >= sel_radius) & (d_end >= lo_s) & (d_end <= hi_s)
    va = tuple(int(i * v + v // 2) for i in ca)
    vb = tuple(int(i * v + v // 2) for i in cb)
    on_seg = [tuple(int(q) for q in torch.floor((pa + s * (pb - pa)) * v).long().tolist())
              for s in torch.linspace(0, 1, 4 * d * v + 1).tolist()]
    out = {"grid": g, "d": d, "L_cells": L_cells, "k": k, "decay": decay,
           "L_vox_check": length_for_decay(k, decay), "settle_steps": round(1.0 / decay),
           "A_cell": list(ca), "B_cell": list(cb),
           "A_face_margin": int(min(min(i, g - 1 - i) for i in ca)), "n_M": int(M.sum()), "n_Sh": int(Sh.sum()),
           "snapshots": []}
    step = 0
    for r in range(1, max(rounds) + 1):
        for i in range(inject + gap):
            if i < inject:
                f.release(src, 1.0)
            f.diffuse()
            step += 1
            if i == inject - 1 and r in rounds:
                c = f.c
                cA = float(c[va])
                theta_c = first_connection(c, va, vb)
                seg_min = min(float(c[p]) for p in on_seg)
                above = component(c >= theta_c * (1 + 1e-3), va)
                dist_a = torch.linalg.norm(x - pa, dim=-1)
                connected = bool(above[vb])
                vol_cells = float(above.sum()) / v ** 3
                out["snapshots"].append({
                    "round": r, "step": step,
                    "C_M_over_Sh": float(c[M].mean() / c[Sh].mean()) if bool(Sh.any()) else None,
                    "C_M_over_A": float(c[M].mean()) / cA, "C_Sh_over_A": float(c[Sh].mean()) / cA,
                    "theta_c_over_A": theta_c / cA, "segment_min_over_A": seg_min / cA,
                    "first_connection_on_segment": bool(abs(theta_c - seg_min) <= 0.01 * theta_c),
                    "radius_A_max_cells": None if connected else float(dist_a[above].max()),
                    "radius_A_equiv_cells": None if connected else (3 * vol_cells / (4 * math.pi)) ** (1 / 3),
                    # gated readout (stop rule: other forms): fraction of M and of Sh voxels with
                    # C >= theta, for theta = factor x theta_c
                    "gate": {str(fac): {"M": float((c[M] >= fac * theta_c).float().mean()),
                                        "Sh": float((c[Sh] >= fac * theta_c).float().mean())}
                             for fac in (1.0, 1.1, 1.25, 1.5, 2.0, 3.0)},
                })
    return out


def marker_check(k: float, decay: float, v: int, g: int = 7, inject: int = 50) -> dict:
    """C at 1 and 2 cells from a single injected group relative to C at its centre (end of injection)."""
    n = g * v
    f = ChemicalField((n, n, n), "cpu", k=k, decay=decay)
    m = g // 2
    src = torch.zeros(n, n, n)
    src[m * v:(m + 1) * v, m * v:(m + 1) * v, m * v:(m + 1) * v] = 1.0 / v ** 3
    for _ in range(inject):
        f.release(src, 1.0)
        f.diffuse()
    c0 = float(f.c[m * v + v // 2, m * v + v // 2, m * v + v // 2])
    return {"k": k, "decay": decay, "L_vox": length_for_decay(k, decay),
            "L_cells": length_for_decay(k, decay) / v,
            "C_1cell_over_centre": float(f.c[(m + 1) * v + v // 2, m * v + v // 2, m * v + v // 2]) / c0,
            "C_2cells_over_centre": float(f.c[(m + 2) * v + v // 2, m * v + v // 2, m * v + v // 2]) / c0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--grids", type=int, nargs="+", default=[7, 11])
    ap.add_argument("--dists", type=int, nargs="+", default=[4, 6])
    ap.add_argument("--lengths", type=float, nargs="+", default=[1.0, 1.5, 2.0, 3.0, 4.0])
    ap.add_argument("--rounds", type=int, nargs="+", default=[1, 5, 10, 30])
    ap.add_argument("--k", type=float, default=0.16)
    ap.add_argument("--vox-per-cell", type=int, default=4)
    ap.add_argument("--inject", type=int, default=50)
    ap.add_argument("--gap", type=int, default=50)
    ap.add_argument("--sel-radius", type=float, default=1.0)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--only", type=int, default=None, help="run only case number i (for parallel workers)")
    a = ap.parse_args()
    torch.set_num_threads(a.threads)
    cases = [(g, d, L) for g in a.grids for d in a.dists for L in a.lengths if d < g]
    if a.only is not None:
        cases = [cases[a.only]]
    res = {"settings": vars(a), "cases": [], "c2_marker": None}
    t0 = time.time()
    for g, d, L in cases:
        res["cases"].append(run_case(g, d, L, a.k, a.vox_per_cell, a.rounds, a.inject, a.gap, a.sel_radius))
        print(f"grid {g} d {d} L {L}: {time.time() - t0:.0f} s", flush=True)
    if a.only is None or a.only == 0:
        res["c2_marker"] = marker_check(0.02, 0.01, a.vox_per_cell)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main()
