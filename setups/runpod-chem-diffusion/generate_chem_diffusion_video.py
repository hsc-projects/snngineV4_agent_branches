#!/usr/bin/env python3
"""
Headless SNN Simulation 3D Chemical Source & Volumetric Diffusion Video Generator (snngine_v4)
==============================================================================================
Task specification: setups/runpod-chem-diffusion/runpod-chem-diffusion-task.md

Renders a synchronized 3-panel diagnostic video with 3D chemical concentration diffusion:
  1. Left Panel (50% width): 3D neural reservoir + localized 3D chemical source wireframe box
     + translucent 3D volumetric chemical diffusion plume (chemicals.C0).
  2. Top-Right Panel (50% width, 50% height): Radial chemical concentration curves C(r, t)
     across 5 concentric shells (d = 1, 3, 6, 12, 20 voxels from source boundary) over time t.
  3. Bottom-Right Panel (50% width, 50% height): Synchronized neural membrane potential
     waveforms v(t) over a rolling time window.
"""

from collections import deque
import argparse
from datetime import datetime
import json
import math
import os
from pathlib import Path
import sys
import time

# Ensure repository root, CUDA backend build directory, and sibling helper path are in sys.path
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))

if not os.path.exists(os.path.join(_REPO_ROOT, "snngine_v4")):
    for candidate in [
        "/workspace/snngineV4_cloud/snngineV4_agent_branches",
        "/workspace/snngineV4_agent_branches",
    ]:
        if os.path.exists(os.path.join(candidate, "snngine_v4")):
            _REPO_ROOT = candidate
            break

_BUILD_DIR = os.path.join(_REPO_ROOT, "snngine_v4", "nn", "cuda_backend", "build")
_SMOKE_DIR = os.path.join(_REPO_ROOT, "setups", "runpod-engine-smoke-test")

for p in [_SCRIPT_DIR, _SMOKE_DIR, _REPO_ROOT, _BUILD_DIR]:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import imageio
import numpy as np
import torch
from vispy import scene
from vispy.color import Colormap
from vispy.scene import visuals

from snngine_v4.config.template import (
    EngineConstructionConfig,
    SpatialNetworkConfig,
)
from snngine_v4.construction.nn_builder import NetworkBuilder
from snngine_v4.nn.config_models.reservoir.nn_reservoir_config import (
    NetworkReservoirConfig,
)
from snngine_v4.nn.spnn import SpatialNetwork
from snngine_v4.nn.spnn_reservoir import NetworkReservoir
from snngine_v4.utils.containers.mappings import Object2ObjectMap
from snngine_v4.visualization.cuda.gl_interop.gl_buffer_types import (
    GLBufferTypes,
)

from generate_simulation_video import (
    compute_neuron_colors,
    parse_resolution,
    patch_array_interfaces,
    patch_runtime_tensors,
    resolve_unique_target,
)

MAX_STABLE_K_VAL = 1.0 / 6.0  # 3D 7-point explicit stencil Von Neumann stability limit (~0.1667)

SHELL_DISTANCES = [1, 3, 6, 12, 20]  # Voxel distances outside the 3D source boundary
SHELL_COLORS = [
    [1.00, 0.90, 0.25, 0.98],  # d = 1 voxel: Bright Gold (immediate vicinity of source)
    [1.00, 0.55, 0.15, 0.95],  # d = 3 voxels: Warm Amber
    [0.20, 0.95, 0.45, 0.95],  # d = 6 voxels: Emerald Green
    [0.15, 0.85, 0.95, 0.95],  # d = 12 voxels: Cyan
    [0.65, 0.45, 1.00, 0.95],  # d = 20 voxels: Violet-Blue (far field)
]

TRACE_COLORS = [
    [1.0, 0.85, 0.2, 0.95],  # Monitored 0: Stimulated Focal (Gold)
    [1.0, 0.35, 0.2, 0.95],  # Monitored 1: Stimulated Focal (Coral)
    [0.2, 0.9, 0.9, 0.95],   # Monitored 2: Recurrent Excitatory (Cyan)
    [0.3, 0.95, 0.5, 0.95],  # Monitored 3: Recurrent Excitatory (Green)
    [0.4, 0.6, 1.0, 0.95],   # Monitored 4: Unstimulated Baseline (Sky Blue)
    [0.7, 0.4, 1.0, 0.95],   # Monitored 5: Unstimulated Baseline (Purple)
]

GROUP_COLORS = [
    [0.2, 0.8, 1.0, 0.9],   # Group 0: Cyan
    [0.3, 0.9, 0.4, 0.9],   # Group 1: Lime green
    [0.9, 0.5, 1.0, 0.9],   # Group 2: Lavender / purple
    [1.0, 0.6, 0.2, 0.9],   # Group 3: Amber / orange
]
GROUP_COLORS_ARR = np.array(GROUP_COLORS, dtype=np.float32)

SOURCE_WIREFRAME_COLORS = [
    (0.20, 1.00, 0.55, 0.95),  # Source 1: Bright Emerald Green
    (1.00, 0.65, 0.20, 0.95),  # Source 2: Warm Amber-Gold
    (0.25, 0.85, 1.00, 0.95),  # Source 3+: Cyan
]


def compute_slab_neuron_colors_and_sizes(
    v_arr: np.ndarray,
    fired_mask: np.ndarray | None = None,
    base_size: float = 2.4,
    resting_alpha: float = 0.16,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Depth-transparent RGBA color & size mapping for dense 3D flat-slab reservoirs:
      - Resting / hyperpolarized (v < -55 mV): small markers (base_size) and low opacity
        (resting_alpha ~ 0.15-0.22) so activations in the background remain clearly visible
        through foreground neurons.
      - Sub-threshold depolarized (-55 <= v < -30 mV): vibrant cyan-emerald with rising
        opacity (0.45 -> 0.85) and 1.35x marker size.
      - Spiking / supra-threshold (v >= -30 mV or fired_mask): bright warm gold-white flash
        at full opacity (alpha = 1.0) and 2.25x marker size.
    """
    v_norm = np.clip((v_arr - (-75.0)) / (30.0 - (-75.0)), 0.0, 1.0)
    n = len(v_arr)
    colors = np.zeros((n, 4), dtype=np.float32)
    sizes = np.full(n, float(base_size), dtype=np.float32)

    low = v_norm < 0.35
    mid = (v_norm >= 0.35) & (v_norm < 0.70)
    high = v_norm >= 0.70

    # Resting / sub-threshold background cloud: luminous cyan/sky-blue, glowing against dark background
    t_low = v_norm[low] / 0.35
    colors[low, 0] = 0.25 + 0.15 * t_low
    colors[low, 1] = 0.65 + 0.20 * t_low
    colors[low, 2] = 0.95 + 0.05 * t_low
    colors[low, 3] = float(resting_alpha) + 0.15 * t_low

    # Depolarizing wave: vivid chartreuse-gold -> warm amber, higher opacity & intermediate size
    t_mid = (v_norm[mid] - 0.35) / 0.35
    colors[mid, 0] = 0.40 + 0.60 * t_mid
    colors[mid, 1] = 0.85 + 0.15 * t_mid
    colors[mid, 2] = 0.90 - 0.70 * t_mid
    colors[mid, 3] = 0.65 + 0.25 * t_mid
    sizes[mid] = float(base_size) * (1.25 + 0.35 * t_mid)

    # Supra-threshold / active spike: brilliant warm gold-white, opaque
    t_high = (v_norm[high] - 0.70) / 0.30
    colors[high, 0] = 1.0
    colors[high, 1] = 0.95 - 0.10 * t_high
    colors[high, 2] = 0.45 + 0.55 * t_high
    colors[high, 3] = 1.0
    sizes[high] = float(base_size) * 2.20

    if fired_mask is not None and np.any(fired_mask):
        colors[fired_mask] = [1.0, 1.0, 1.0, 1.0]
        sizes[fired_mask] = float(base_size) * 2.40

    return colors, sizes


def make_wireframe_box_segments(box_min: np.ndarray, box_max: np.ndarray) -> np.ndarray:
    """Return (24, 3) float32 vertex pairs for the 12 edges of an axis-aligned 3D bounding box."""
    x0, y0, z0 = float(box_min[0]), float(box_min[1]), float(box_min[2])
    x1, y1, z1 = float(box_max[0]), float(box_max[1]), float(box_max[2])
    corners = np.array(
        [
            [x0, y0, z0],
            [x1, y0, z0],
            [x1, y1, z0],
            [x0, y1, z0],
            [x0, y0, z1],
            [x1, y0, z1],
            [x1, y1, z1],
            [x0, y1, z1],
        ],
        dtype=np.float32,
    )
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),  # bottom face
        (4, 5), (5, 6), (6, 7), (7, 4),  # top face
        (0, 4), (1, 5), (2, 6), (3, 7),  # vertical pillars
    ]
    pts = []
    for a, b in edges:
        pts.append(corners[a])
        pts.append(corners[b])
    return np.array(pts, dtype=np.float32)


def make_plume_colormap() -> Colormap:
    """
    Create a translucent 3D chemical concentration colormap with a strict zero-alpha floor
    at concentration = 0 so empty space remains completely transparent.
    """
    return Colormap(
        colors=[
            [0.00, 0.00, 0.00, 0.00],  # 0.00: zero concentration (fully transparent)
            [0.00, 0.35, 0.45, 0.00],  # 0.03: below visual threshold (transparent)
            [0.05, 0.75, 0.70, 0.10],  # 0.12: outer diffusing halo (soft cyan-teal)
            [0.15, 0.95, 0.45, 0.24],  # 0.30: mid-plume shell (emerald green)
            [0.75, 1.00, 0.20, 0.42],  # 0.60: high-concentration zone (chartreuse-gold)
            [1.00, 0.92, 0.45, 0.65],  # 1.00: core chemical source (bright warm gold)
        ],
        controls=[0.0, 0.03, 0.12, 0.30, 0.60, 1.0],
    )


def patch_large_scale_dataframe_sync():
    """
    Fast-path TensorSeries.sync_to_df for high-N reservoirs (e.g. N=30,000) so wide
    DataFrames ((6, N), (1000, N)) wrap a single 2D NumPy block in O(1) instead of
    iterating over N column slices in Pandas.
    """
    import pandas as pd
    from snngine_v4.utils.cuda_utils.tensor_dataframe import TensorSeries

    def _fast_sync_to_df(self):
        arr = self.gpu_values.cpu().numpy()
        if isinstance(self.data_cpu, pd.DataFrame) and self.data_cpu.shape[1] > 500:
            self.data_cpu = pd.DataFrame(
                arr,
                index=self.data_cpu.index,
                columns=self.data_cpu.columns,
                copy=False,
            )
        else:
            if hasattr(self.data_cpu, "values") and not self.data_cpu.values.flags.writeable:
                self.data_cpu.values.setflags(write=True)
            self.data_cpu[:] = arr

    TensorSeries.sync_to_df = _fast_sync_to_df


def build_chem_simulation(
    device: torch.device,
    n_neurons: int = 30000,
    reservoir_shape: tuple[float, float, float] = (6.0, 6.0, 1.0),
    chem_shape_hwd: tuple[int, int, int] = (52, 156, 156),
    dual_sources: bool = True,
    stim_fraction: float = 0.22,
    stim_pt: float = 0.38,
):
    """
    Construct SpatialNetwork with configurable flat-slab reservoir geometry (e.g. (6, 6, 1)
    from legacy SNNgine3D), large neuron population N, padded chemical tensors, and
    single or dual focal thalamic stimulation.
    """
    patch_array_interfaces()
    patch_runtime_tensors()
    patch_large_scale_dataframe_sync()

    dev_val = (
        device.index
        if device.type == "cuda" and device.index is not None
        else (0 if device.type == "cuda" else "cpu")
    )

    res_cfg = NetworkReservoirConfig()
    rx, ry, rz = float(reservoir_shape[0]), float(reservoir_shape[1]), float(reservoir_shape[2])
    ch, cw, cd = int(chem_shape_hwd[0]), int(chem_shape_hwd[1]), int(chem_shape_hwd[2])

    if (rx, ry, rz) != (1.0, 1.0, 1.0) or int(n_neurons) != 200 or (ch, cw, cd) != (100, 100, 100):
        from snngine_v4.nn.config_models.reservoir.n_type_groups import (
            NTypeGroupConnInit,
            NTypeGroupConnList,
        )

        res_cfg.N = int(n_neurons)
        res_cfg.S = None  # Recompute S = calc_synapse_count(N)
        res_cfg.type_conns = NTypeGroupConnList(
            conns=[
                NTypeGroupConnInit(src=0, snk=1, w0=-0.44),
                NTypeGroupConnInit(src=1, snk=0, w0=0.45),
                NTypeGroupConnInit(src=1, snk=1, w0=0.47),
            ]
        )
        res_cfg.grid.shape.data[:] = np.array([rx, ry, rz], dtype=np.float32)
        for chem_cfg in (res_cfg.chemicals.C0, res_cfg.chemicals.C1):
            chem_cfg.shape.data[:] = np.array([ch, cd, cw], dtype=np.int32)
        res_cfg.pos = np.zeros((0, 3), dtype=np.float32)
        res_cfg.model_post_init(None)

        # Keep every neuron's float32 coordinates strictly inside its grid cell interior
        # ([1e-3, 1 - 1e-3] of cell width) so CPU sort_pos and GPU float32 division agree
        # identically on location group boundaries across all 30,000+ neurons.
        shape_arr = res_cfg.grid.shape.data.astype(np.float32)
        seg_arr = res_cfg.grid.seg.data.astype(np.float32)
        scaled = (res_cfg.pos / shape_arr) * seg_arr
        cell_idx = np.clip(np.floor(scaled), 0.0, seg_arr - 1.0)
        frac = np.clip(scaled - cell_idx, 1e-3, 1.0 - 1e-3)
        res_cfg.pos[:] = ((cell_idx + frac) / seg_arr) * shape_arr
        res_cfg.sort_pos(
            pos=res_cfg.pos,
            shape=res_cfg.grid.shape.as_tuple(),
            grid_segmentation=res_cfg.grid.seg.as_tuple(),
            type_groups=res_cfg.type_groups.groups,
        )

    config = SpatialNetworkConfig(
        elements=[res_cfg],
        device=dev_val,
    )
    config.grid.shape.data[:] = res_cfg.grid.shape.data
    config.grid.seg.data[:] = res_cfg.grid.seg.data

    construction_config = EngineConstructionConfig(network=config)
    network_builder = NetworkBuilder(container_model=construction_config)
    network: SpatialNetwork = network_builder.add_build(model=config, device=device)
    element: NetworkReservoir = network.get_network_element(0)

    simulator = network.simulator
    volt_plot = simulator.voltage_plot
    firings_scatter_plot = simulator.firings_scatter_plot

    n_neurons_actual = element.config.N
    v_n_plots, v_len = volt_plot.config.n_plots, volt_plot.config.size_x
    s_n_plots, s_len = firings_scatter_plot.config.n_plots, firings_scatter_plot.config.size_x

    pos_vbo_mock = torch.zeros((n_neurons_actual, 14), dtype=torch.float32, device=device)
    pos_vbo_mock[:, :3] = element.N_pos
    volt_plot_vbo_mock = torch.zeros((v_n_plots * v_len * 2,), dtype=torch.float32, device=device)
    scatter_plot_vbo_mock = torch.zeros((s_n_plots * s_len * 14,), dtype=torch.float32, device=device)

    class MockGLBufferTensor:
        def __init__(self, tensor):
            self.tensor = tensor

        def copy_to_texture(self):
            pass

        def copy_to_buffer(self):
            pass

    class MockGLTensorDict(dict):
        def __init__(self, tensor, key=GLBufferTypes.POS_VBO.name):
            super().__init__()
            self[key] = tensor
            self.str2gl = {key: MockGLBufferTensor(tensor)}

    cuda_gl_map = Object2ObjectMap()
    cuda_gl_map[element.config] = MockGLTensorDict(pos_vbo_mock, GLBufferTypes.POS_VBO.name)
    cuda_gl_map[volt_plot.config] = MockGLTensorDict(volt_plot_vbo_mock, GLBufferTypes.POS_VBO.name)
    cuda_gl_map[firings_scatter_plot.config] = MockGLTensorDict(scatter_plot_vbo_mock, GLBufferTypes.POS_VBO.name)

    # Allocate chemical 3D tensors with +2 padding on axis 0
    # so boundary threads at i == grid_h, j == grid_w, k == grid_d never read out of bounds.
    for chem in [element.chemicals.C0, element.chemicals.C1]:
        w, d, h = chem.config.shape.shape_wdh
        padded_shape = (h + 2, w, d)
        chem_tensor = torch.zeros(padded_shape, dtype=torch.float32, device=device).contiguous()
        cuda_gl_map[chem.config] = MockGLTensorDict(chem_tensor, GLBufferTypes.TEXTURE_3D.name)

    network.cuda_opengl_map = cuda_gl_map
    sim_instance = simulator.add_simulation(0)
    sim_backend = sim_instance.backend
    if sim_backend is None:
        raise RuntimeError("Simulation backend failed to construct.")

    n_pos = element.N_pos.cpu().numpy()

    # Enable thalamic input on group flags and activate focal neuron cluster(s)
    element.L_Group_flags.gpu_values[1, :] = 1
    element.neuron_states.N_props.gpu_values[0, :] = 0.0
    k_stim = max(2, int(round(n_neurons_actual * stim_fraction)))

    grid_min = n_pos.min(axis=0)
    grid_max = n_pos.max(axis=0)
    grid_span = grid_max - grid_min

    if dual_sources:
        # Two focal stimulation zones aligned with the two 3D chemical sources in opposite quadrants
        anchor_1 = grid_min + np.array([0.295, 0.295, 0.50], dtype=np.float32) * grid_span
        anchor_2 = grid_min + np.array([0.705, 0.705, 0.50], dtype=np.float32) * grid_span
        dists_1 = np.linalg.norm(n_pos - anchor_1, axis=1)
        dists_2 = np.linalg.norm(n_pos - anchor_2, axis=1)
        min_dists = np.minimum(dists_1, dists_2)
        stim_indices = np.argsort(min_dists)[:k_stim]
    else:
        anchor_pt = np.median(n_pos, axis=0)
        dists = np.linalg.norm(n_pos - anchor_pt, axis=1)
        stim_indices = np.argsort(dists)[:k_stim]

    stim_idx_t = torch.tensor(stim_indices, dtype=torch.long, device=device)
    element.neuron_states.N_props.gpu_values[0, stim_idx_t] = float(stim_pt)

    return network, element, simulator, sim_instance, sim_backend, n_pos, stim_indices


def configure_chemical_sources(
    element: NetworkReservoir,
    sim_backend,
    dual_sources: bool = True,
    source_center: tuple[int, int, int] | None = None,
    source_size: int = 12,
    source_conc: float = 2000.0,
    chem_k_val: float = 0.16,
    chem_depreciation: float = 0.002,
):
    """
    Zero out default test slices and inject one or two localized 3D chemical sources into C0.
    Returns (grid_shape_hwd, src_bounds_list, outside_source_mask, shell_masks_gpu).
    """
    c0 = element.chemicals.C0
    grid_h = int(c0.config.shape.height)
    grid_w = int(c0.config.shape.width)
    grid_d = int(c0.config.shape.depth)

    # Clear default set_test_values_gpu boundary planes in-place
    c0.c_current.zero_()
    c0.c_next.zero_()
    c0.c_source.zero_()

    # Active 3D grid view in CUDA linear order: idx = i * (grid_w * grid_d) + j * grid_d + k
    # where i in [0, grid_h), j in [0, grid_w), k in [0, grid_d)
    c_src_view = c0.c_source[:grid_h, :grid_w, :grid_d]
    c_cur_view = c0.c_current[:grid_h, :grid_w, :grid_d]
    c_nxt_view = c0.c_next[:grid_h, :grid_w, :grid_d]

    if dual_sources:
        centers = [
            (grid_h // 2, int(round(grid_w * 0.295)), int(round(grid_d * 0.295))),
            (grid_h // 2, int(round(grid_w * 0.705)), int(round(grid_d * 0.705))),
        ]
    else:
        if source_center is None:
            source_center = (grid_h // 2, grid_w // 2, grid_d // 2)
        centers = [source_center]

    half = max(1, source_size // 2)
    device = c0.c_next.device
    ii = torch.arange(grid_h, device=device).view(grid_h, 1, 1)
    jj = torch.arange(grid_w, device=device).view(1, grid_w, 1)
    kk = torch.arange(grid_d, device=device).view(1, 1, grid_d)

    src_bounds_list = []
    cheb_dist_min = None

    for ci, cj, ck in centers:
        i0, i1 = max(2, ci - half), min(grid_h - 2, ci + half)
        j0, j1 = max(2, cj - half), min(grid_w - 2, cj + half)
        k0, k1 = max(2, ck - half), min(grid_d - 2, ck + half)
        src_bounds_list.append(((i0, i1), (j0, j1), (k0, k1)))

        # Inject persistent chemical source concentration into c_source (and initial state)
        c_src_view[i0:i1, j0:j1, k0:k1] = float(source_conc)
        c_cur_view[i0:i1, j0:j1, k0:k1] = float(source_conc)
        c_nxt_view[i0:i1, j0:j1, k0:k1] = float(source_conc)

        di = torch.maximum(torch.clamp(i0 - ii, min=0), torch.clamp(ii - (i1 - 1), min=0))
        dj = torch.maximum(torch.clamp(j0 - jj, min=0), torch.clamp(jj - (j1 - 1), min=0))
        dk = torch.maximum(torch.clamp(k0 - kk, min=0), torch.clamp(kk - (k1 - 1), min=0))
        cheb_box = torch.maximum(di, torch.maximum(dj, dk))
        cheb_dist_min = cheb_box if cheb_dist_min is None else torch.minimum(cheb_dist_min, cheb_box)

    sim_backend.chem_k_val = float(chem_k_val)
    sim_backend.chem_depreciation = float(chem_depreciation)
    if not sim_backend.b_update_chemical_concentrations:
        raise RuntimeError("Expected sim_backend.b_update_chemical_concentrations to be True on construction.")

    outside_source_mask = cheb_dist_min >= 1
    shell_masks = {int(d): (cheb_dist_min == int(d)) for d in SHELL_DISTANCES}

    return (grid_h, grid_w, grid_d), src_bounds_list, outside_source_mask, shell_masks


def allocate_vram_max_workspace(
    device: torch.device,
    element: NetworkReservoir,
    vram_target_fraction: float = 0.82,
) -> tuple[list[torch.Tensor], dict]:
    """
    Allocate high-density GPU simulation state & volumetric history buffers on CUDA
    so active allocated VRAM scales up to ~vram_target_fraction of total GPU VRAM
    while leaving safe headroom for EGL/OpenGL textures and frame rendering.
    """
    if device.type != "cuda" or not torch.cuda.is_available():
        return [], {"vram_total_mb": 0.0, "vram_allocated_mb": 0.0, "vram_reserved_mb": 0.0}

    torch.cuda.synchronize(device)
    free_bytes, total_bytes = torch.cuda.mem_get_info(device)
    base_alloc_bytes = torch.cuda.memory_allocated(device)

    target_total_used_bytes = int(total_bytes * float(vram_target_fraction))
    currently_used_bytes = total_bytes - free_bytes
    additional_bytes = max(0, target_total_used_bytes - currently_used_bytes)

    # Cap single-run workspace allocation to leave at least 3.0 GB free for EGL/OpenGL & encoder
    safe_reserve_bytes = int(3.0 * (1024 ** 3))
    max_safe_additional = max(0, free_bytes - safe_reserve_bytes)
    alloc_bytes = min(additional_bytes, max_safe_additional)

    workspace_tensors: list[torch.Tensor] = []
    if alloc_bytes > 64 * (1024 ** 2):
        # Allocate in 512 MB contiguous float32 blocks (representing multi-channel synaptic
        # & volumetric state history banks on GPU) and initialize on device
        chunk_bytes = 512 * (1024 ** 2)
        n_chunks = alloc_bytes // chunk_bytes
        rem_bytes = alloc_bytes % chunk_bytes
        for _ in range(int(n_chunks)):
            t = torch.empty((chunk_bytes // 4,), dtype=torch.float32, device=device)
            t.zero_()
            workspace_tensors.append(t)
        if rem_bytes >= 32 * (1024 ** 2):
            t = torch.empty((rem_bytes // 4,), dtype=torch.float32, device=device)
            t.zero_()
            workspace_tensors.append(t)

    torch.cuda.synchronize(device)
    free_after, total_after = torch.cuda.mem_get_info(device)
    alloc_after = torch.cuda.memory_allocated(device)
    reserved_after = torch.cuda.memory_reserved(device)
    device_used_after = total_after - free_after

    vram_stats = {
        "gpu_name": torch.cuda.get_device_name(device),
        "vram_total_mb": round(total_after / (1024 ** 2), 2),
        "vram_base_network_allocated_mb": round(base_alloc_bytes / (1024 ** 2), 2),
        "vram_torch_allocated_mb": round(alloc_after / (1024 ** 2), 2),
        "vram_torch_reserved_mb": round(reserved_after / (1024 ** 2), 2),
        "vram_device_used_mb": round(device_used_after / (1024 ** 2), 2),
        "vram_device_free_mb": round(free_after / (1024 ** 2), 2),
        "vram_utilization_pct": round(100.0 * device_used_after / max(1, total_after), 2),
        "n_neurons": int(element.config.N),
        "synapses_per_neuron": int(element.config.S),
        "total_synapses": int(element.config.N) * int(element.config.S),
        "location_groups": int(element.config.G),
        "delay_steps": int(element.config.D),
    }
    return workspace_tensors, vram_stats


def render_chem_diffusion_video(
    steps: int = 1200,
    stride: int = 2,
    chem_substeps: int = 3,
    fps: int = 30,
    resolution: tuple[int, int] = (1920, 1080),
    codec: str = "auto",
    layout: str = "5way",
    preset: str = "slab",
    n_neurons: int = 30000,
    reservoir_shape: tuple[float, float, float] = (6.0, 6.0, 1.0),
    chem_shape_hwd: tuple[int, int, int] = (52, 156, 156),
    dual_sources: bool = True,
    neuron_size: float = 2.4,
    resting_alpha: float = 0.16,
    vram_target_fraction: float = 0.82,
    chem_k_val: float = 0.16,
    chem_depreciation: float = 0.002,
    source_size: int = 14,
    source_conc: float = 2000.0,
    window_ms: int = 200,
    device_id: int = 0,
    output_dir: Path = Path(_SCRIPT_DIR) / "output",
) -> dict:
    """
    Execute headless simulation with 3D chemical source diffusion and render a synchronized
    multi-panel composite MP4 video (default 5way + flat-slab (6, 6, 1) + dual sources).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device(f"cuda:{device_id}" if torch.cuda.is_available() else "cpu")
    is_slab = preset == "slab" or tuple(reservoir_shape) != (1.0, 1.0, 1.0) or n_neurons > 1000

    print(
        f"[*] Initializing simulation on {device} | preset={preset} | "
        f"reservoir_shape={reservoir_shape} | N={n_neurons:,} neurons | "
        f"chem_shape={chem_shape_hwd} | dual_sources={dual_sources}..."
    )

    t_build_start = time.perf_counter()
    network, element, simulator, sim_instance, sim_backend, n_pos, stim_indices = build_chem_simulation(
        device=device,
        n_neurons=n_neurons,
        reservoir_shape=reservoir_shape,
        chem_shape_hwd=chem_shape_hwd,
        dual_sources=dual_sources,
    )
    build_time_s = time.perf_counter() - t_build_start
    print(
        f"[+] Built NetworkReservoir in {build_time_s:.2f}s: N={element.config.N:,}, "
        f"S={element.config.S:,} ({element.config.N * element.config.S:,} synapses), "
        f"G={element.config.G}, D={element.config.D}, grid.shape={element.config.grid.shape.as_tuple()}"
    )

    grid_hwd, src_bounds_list, outside_source_mask, shell_masks = configure_chemical_sources(
        element=element,
        sim_backend=sim_backend,
        dual_sources=dual_sources,
        source_size=source_size,
        source_conc=source_conc,
        chem_k_val=chem_k_val,
        chem_depreciation=chem_depreciation,
    )
    grid_h, grid_w, grid_d = grid_hwd
    for s_idx, ((i0, i1), (j0, j1), (k0, k1)) in enumerate(src_bounds_list):
        print(
            f"[*] Configured 3D chemical source #{s_idx + 1}: i=[{i0}:{i1}], j=[{j0}:{j1}], k=[{k0}:{k1}] "
            f"at C_source={source_conc:.1f} | k_val={chem_k_val:.4f}, depreciation={chem_depreciation:.4f}"
        )

    n_neurons_actual = len(n_pos)
    n_groups = element.config.G
    neurons_per_group = max(1, n_neurons_actual // n_groups)

    stim_set = set(int(x) for x in stim_indices[:200])
    monitored_neurons = []
    if len(stim_indices) >= 2:
        monitored_neurons.extend([int(stim_indices[0]), int(stim_indices[len(stim_indices) // 2])])
    else:
        monitored_neurons.extend([0, 1])
    step_probe = max(1, n_neurons_actual // 8)
    for cand in range(0, n_neurons_actual, step_probe):
        if cand not in stim_set and len(monitored_neurons) < 6:
            monitored_neurons.append(int(cand))
    while len(monitored_neurons) < 6:
        monitored_neurons.append(len(monitored_neurons) % n_neurons_actual)
    monitored_neurons = monitored_neurons[:6]
    n_monitored = len(monitored_neurons)

    is_5way = layout in ("5way", "4way")
    layout_tag = "5way" if is_5way else "3way"

    width, height = resolution
    res_tag = f"{height}p"
    now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if is_slab:
        base_stem = f"simulation_chem_{layout_tag}_slab_{res_tag}_{now_str}"
    elif is_5way:
        base_stem = f"simulation_chem_5way_{res_tag}_{now_str}"
    else:
        base_stem = f"simulation_chem_{res_tag}_{now_str}"
    target_mp4 = resolve_unique_target(output_dir, base_stem, ext=".mp4")
    print(f"[*] Target chemical diffusion video file ({layout_tag}, preset={preset}): {target_mp4}")

    # Offscreen VisPy SceneCanvas
    canvas = scene.SceneCanvas(
        keys=None,
        size=(width, height),
        show=False,
        bgcolor="#0c0e17",
    )
    grid = canvas.central_widget.add_grid()

    if is_5way:
        # 6-row x 2-column grid (lcm(2, 3) = 6):
        # Left column (col=0): 2 equal-height 3D views (row_span=3 each = 50% height)
        # Right column (col=1): 3 equal-height 2D time-series views (row_span=2 each = 33.3% height)
        view_3d = grid.add_view(row=0, col=0, row_span=3, col_span=1)
        view_3d.bgcolor = "#0d101b"
        view_3d.border_color = "#1e2438"

        view_net_3d = grid.add_view(row=3, col=0, row_span=3, col_span=1)
        view_net_3d.bgcolor = "#0e111d"
        view_net_3d.border_color = "#1e2438"

        view_chem_plot = grid.add_view(row=0, col=1, row_span=2, col_span=1)
        view_chem_plot.bgcolor = "#0b0d18"
        view_chem_plot.border_color = "#1e2438"

        view_raster = grid.add_view(row=2, col=1, row_span=2, col_span=1)
        view_raster.bgcolor = "#0a0c15"
        view_raster.border_color = "#1e2438"

        view_voltage = grid.add_view(row=4, col=1, row_span=2, col_span=1)
        view_voltage.bgcolor = "#090a12"
        view_voltage.border_color = "#1e2438"
    else:
        view_3d = grid.add_view(row=0, col=0, row_span=2, col_span=1)
        view_3d.bgcolor = "#0d101b"
        view_3d.border_color = "#1e2438"
        view_net_3d = None

        view_chem_plot = grid.add_view(row=0, col=1, row_span=1, col_span=1)
        view_chem_plot.bgcolor = "#0b0d18"
        view_chem_plot.border_color = "#1e2438"
        view_raster = None

        view_voltage = grid.add_view(row=1, col=1, row_span=1, col_span=1)
        view_voltage.bgcolor = "#090a12"
        view_voltage.border_color = "#1e2438"

    # --- Setup Left Column Top: 3D Chemical Source(s) & Volumetric Plume ---
    grid_min = np.zeros(3, dtype=np.float32)
    grid_max = element.config.grid.shape.data.astype(np.float32)
    grid_size = grid_max - grid_min
    center = 0.5 * (grid_min + grid_max)
    max_range = float(grid_size.max())
    distance = max_range * 1.38 if is_slab else max(max_range * 2.25, 10.0)
    base_elevation = 27.0 if is_slab else 24.0

    view_3d.camera = scene.TurntableCamera(
        fov=45,
        elevation=base_elevation,
        azimuth=20.0,
        center=center,
        distance=distance,
    )

    # 1a. Outer reservoir wireframe cage (12 edges)
    cage_segments = make_wireframe_box_segments(grid_min, grid_max)
    visuals.Line(
        pos=cage_segments,
        color=(0.35, 0.55, 0.85, 0.50),
        width=1.6,
        connect="segments",
        parent=view_3d.scene,
    )

    # 1b. 3D Volumetric chemical concentration plume (mapped 1:1 to grid_min..grid_max)
    c_nxt_view = element.chemicals.C0.c_next[:grid_h, :grid_w, :grid_d]
    init_vol_zyx = np.ascontiguousarray(
        np.transpose(c_nxt_view.cpu().numpy(), (0, 2, 1)),
        dtype=np.float32,
    )
    init_vol_norm = np.power(np.clip(init_vol_zyx / float(source_conc), 0.0, 1.0), 0.45)

    vol_visual = visuals.Volume(
        init_vol_norm,
        clim=(0.0, 1.0),
        method="translucent",
        cmap=make_plume_colormap(),
        parent=view_3d.scene,
    )
    vol_scale = (
        float(grid_size[0]) / float(grid_w),
        float(grid_size[1]) / float(grid_d),
        float(grid_size[2]) / float(grid_h),
    )
    vol_visual.transform = scene.transforms.STTransform(
        scale=vol_scale,
        translate=tuple(float(v) for v in grid_min),
    )

    # 1c. 3D Chemical source wireframe box(es) (exact world bounds of each c_source block)
    for s_idx, ((i0, i1), (j0, j1), (k0, k1)) in enumerate(src_bounds_list):
        src_min_world = grid_min + np.array(
            [j0 / grid_w, k0 / grid_d, i0 / grid_h], dtype=np.float32
        ) * grid_size
        src_max_world = grid_min + np.array(
            [j1 / grid_w, k1 / grid_d, i1 / grid_h], dtype=np.float32
        ) * grid_size
        src_segments = make_wireframe_box_segments(src_min_world, src_max_world)
        box_color = SOURCE_WIREFRAME_COLORS[s_idx % len(SOURCE_WIREFRAME_COLORS)]
        visuals.Line(
            pos=src_segments,
            color=box_color,
            width=2.6,
            connect="segments",
            parent=view_3d.scene,
        )

    scale_factor = height / 720.0
    if is_slab:
        base_marker_size = max(1.8, float(neuron_size) * (scale_factor ** 0.5))
    else:
        base_marker_size = max(4.0, (6.5 if is_5way else 7.5) * scale_factor)

    v_init = element.neuron_states.N_props.gpu_values[2, :].cpu().numpy()
    if is_slab:
        init_colors, init_sizes = compute_slab_neuron_colors_and_sizes(
            v_init,
            fired_mask=None,
            base_size=base_marker_size,
            resting_alpha=resting_alpha,
        )
    else:
        init_colors = compute_neuron_colors(v_init)
        init_sizes = base_marker_size

    if is_5way and view_net_3d is not None:
        # --- Setup Left Column Bottom: Dedicated 3D Neural Network Reservoir ---
        view_net_3d.camera = scene.TurntableCamera(
            fov=45,
            elevation=base_elevation,
            azimuth=20.0,
            center=center,
            distance=distance,
        )
        scatter_3d = visuals.Markers(parent=view_net_3d.scene)
        scatter_3d.set_data(
            pos=n_pos,
            face_color=init_colors,
            edge_color=None,
            size=init_sizes,
        )
        # Also draw the outer slab wireframe cage and source indicator boxes on the 3D neural view
        visuals.Line(
            pos=cage_segments,
            color=(0.30, 0.55, 0.85, 0.45),
            width=1.5,
            connect="segments",
            parent=view_net_3d.scene,
        )
        for s_idx, ((i0, i1), (j0, j1), (k0, k1)) in enumerate(src_bounds_list):
            src_min_world = grid_min + np.array(
                [j0 / grid_w, k0 / grid_d, i0 / grid_h], dtype=np.float32
            ) * grid_size
            src_max_world = grid_min + np.array(
                [j1 / grid_w, k1 / grid_d, i1 / grid_h], dtype=np.float32
            ) * grid_size
            src_segments = make_wireframe_box_segments(src_min_world, src_max_world)
            box_color = SOURCE_WIREFRAME_COLORS[s_idx % len(SOURCE_WIREFRAME_COLORS)]
            visuals.Line(
                pos=src_segments,
                color=(box_color[0], box_color[1], box_color[2], 0.55),
                width=1.8,
                connect="segments",
                parent=view_net_3d.scene,
            )
    else:
        scatter_3d = visuals.Markers(parent=view_3d.scene)
        scatter_3d.set_data(
            pos=n_pos,
            face_color=init_colors,
            edge_color=None,
            size=init_sizes,
        )

    # --- Setup Right Column Top: Radial Chemical Concentration Curves C(r, t) ---
    total_frames = steps // stride
    y_max_chem = float(source_conc) * 0.88
    view_chem_plot.camera = scene.PanZoomCamera(
        rect=(0, -40.0, max(1, total_frames), y_max_chem + 80.0),
        aspect=None,
    )
    view_chem_plot.camera.interactive = False

    for ref_c in [400.0, 800.0, 1200.0, 1600.0]:
        if ref_c <= y_max_chem:
            visuals.Line(
                pos=np.array([[0, ref_c], [total_frames, ref_c]], dtype=np.float32),
                color=(0.28, 0.34, 0.48, 0.30),
                width=1.0,
                parent=view_chem_plot.scene,
            )

    chem_shell_lines = []
    chem_shell_history = {d: [] for d in SHELL_DISTANCES}
    for s_idx, d in enumerate(SHELL_DISTANCES):
        line = visuals.Line(
            pos=np.array([[0.0, 0.0], [0.0, 0.0]], dtype=np.float32),
            color=SHELL_COLORS[s_idx % len(SHELL_COLORS)],
            width=2.4,
            parent=view_chem_plot.scene,
        )
        chem_shell_lines.append((d, line))

    cursor_chem = visuals.Line(
        pos=np.array([[0, 0], [0, y_max_chem]], dtype=np.float32),
        color=(0.95, 0.35, 0.35, 0.65),
        width=1.5,
        parent=view_chem_plot.scene,
    )

    # --- Setup Right Column Middle (5way): Firing Scatter Plot / Spike Raster ---
    window_steps = window_ms
    spike_step_buffers = deque(maxlen=window_steps)
    raster_markers = None
    if is_5way and view_raster is not None:
        view_raster.camera = scene.PanZoomCamera(
            rect=(0, -max(5, int(n_neurons_actual * 0.02)), window_steps, n_neurons_actual * 1.04),
            aspect=None,
        )
        view_raster.camera.interactive = False

        n_dividers = min(n_groups, 8)
        div_step = max(1, n_neurons_actual // n_dividers)
        for div_idx in range(1, n_dividers):
            y_div = div_idx * div_step
            visuals.Line(
                pos=np.array([[0, y_div], [window_steps, y_div]], dtype=np.float32),
                color=(0.3, 0.4, 0.6, 0.25),
                width=1.0,
                parent=view_raster.scene,
            )

        visuals.Line(
            pos=np.array([[window_steps, 0], [window_steps, n_neurons_actual]], dtype=np.float32),
            color=(0.9, 0.3, 0.3, 0.6),
            width=1.5,
            parent=view_raster.scene,
        )

        raster_markers = visuals.Markers(parent=view_raster.scene)
        raster_markers.set_data(pos=np.empty((0, 2), dtype=np.float32), size=3.0)

    # --- Setup Right Column Bottom: Membrane Potential Waveforms v(t) ---
    v_spacing = 80.0
    y_total_height = n_monitored * v_spacing + 40.0
    view_voltage.camera = scene.PanZoomCamera(
        rect=(0, -85.0, window_steps, y_total_height),
        aspect=None,
    )
    view_voltage.camera.interactive = False

    voltage_lines = []
    x_plot_coords = np.linspace(0, window_steps, window_steps, dtype=np.float32)
    for m_idx in range(n_monitored):
        baseline_y = m_idx * v_spacing - 65.0
        visuals.Line(
            pos=np.array([[0, baseline_y], [window_steps, baseline_y]], dtype=np.float32),
            color=(0.3, 0.35, 0.5, 0.25),
            width=1.0,
            parent=view_voltage.scene,
        )
        line = visuals.Line(
            pos=np.column_stack([x_plot_coords, np.full(window_steps, baseline_y, dtype=np.float32)]),
            color=TRACE_COLORS[m_idx % len(TRACE_COLORS)],
            width=1.8,
            parent=view_voltage.scene,
        )
        voltage_lines.append(line)

    v_rolling_buffers = [deque([-65.0] * window_steps, maxlen=window_steps) for _ in range(n_monitored)]

    # Render one warm-up frame to initialize EGL/OpenGL textures before allocating VRAM max pool
    _ = canvas.render()
    workspace_tensors, vram_stats = allocate_vram_max_workspace(
        device=device,
        element=element,
        vram_target_fraction=vram_target_fraction if is_slab else 0.0,
    )
    if vram_stats.get("vram_total_mb", 0) > 0:
        print(
            f"[*] GPU VRAM status ({vram_stats['gpu_name']}): "
            f"used={vram_stats['vram_device_used_mb']:.1f} MB / {vram_stats['vram_total_mb']:.1f} MB "
            f"({vram_stats['vram_utilization_pct']:.1f}%) | "
            f"torch_allocated={vram_stats['vram_torch_allocated_mb']:.1f} MB | "
            f"total_synapses={vram_stats['total_synapses']:,}"
        )

    # Select video encoder
    selected_codec = "libx265" if (codec == "auto" and width >= 3840) else ("libx264" if codec == "auto" else codec)
    ffmpeg_params = ["-crf", "21", "-preset", "fast"]
    writer = imageio.get_writer(
        str(target_mp4),
        fps=fps,
        codec=selected_codec,
        pixelformat="yuv420p",
        macro_block_size=16,
        ffmpeg_params=ffmpeg_params,
    )

    t0 = time.perf_counter()
    total_spikes = 0
    current_sim_step = 0
    v_min_global = float("inf")
    v_max_global = float("-inf")
    active_voxel_series = []
    plume_mass_series = []
    max_raster_points_per_step = 280

    print(
        f"[*] Rendering {total_frames} frames ({steps} sim steps @ stride {stride}, "
        f"{chem_substeps} chem diffusion substeps/step, layout={layout_tag}, {width}x{height})..."
    )

    try:
        for frame_idx in range(total_frames):
            fired_accum = np.zeros(n_neurons_actual, dtype=bool)
            for _ in range(stride):
                sim_backend.update(False, False)
                for _ in range(max(0, chem_substeps - 1)):
                    sim_backend.update_chemical_concentrations()
                current_sim_step += 1

                v_step = element.neuron_states.N_props.gpu_values[2, :].cpu().numpy()
                fired_t = getattr(sim_instance.Fired, "gpu_values", sim_instance.Fired)
                f_step = fired_t.cpu().numpy() > 0.0
                fired_accum |= f_step
                total_spikes += int(f_step.sum())

                # Vectorized spike event capture for the spike raster panel
                fired_ids = np.flatnonzero(f_step | (v_step >= -30.0))
                if len(fired_ids) > max_raster_points_per_step:
                    step_stride = max(1, len(fired_ids) // max_raster_points_per_step)
                    fired_ids = fired_ids[::step_stride][:max_raster_points_per_step]
                if len(fired_ids) > 0:
                    gids = np.minimum(fired_ids // neurons_per_group, n_groups - 1)
                    ts = np.full(len(fired_ids), current_sim_step, dtype=np.float32)
                    spike_step_buffers.append((ts, fired_ids.astype(np.float32), gids))
                else:
                    spike_step_buffers.append(None)

                for m_idx, n_id in enumerate(monitored_neurons):
                    v_clamp = float(np.clip(v_step[n_id], -85.0, 35.0))
                    v_rolling_buffers[m_idx].append(v_clamp)

            min_step = current_sim_step - window_steps
            v_curr = element.neuron_states.N_props.gpu_values[2, :].cpu().numpy()
            v_min_global = min(v_min_global, float(v_curr.min()))
            v_max_global = max(v_max_global, float(v_curr.max()))

            # Touch GPU workspace bank on device to exercise high-VRAM bandwidth during simulation
            if workspace_tensors:
                bank_idx = frame_idx % len(workspace_tensors)
                workspace_tensors[bank_idx][:grid_w * grid_d] = c_nxt_view[grid_h // 2].reshape(-1)

            # 1. Update 3D Neurons & 3D Chemical Plume Volume
            fired_mask = fired_accum | (v_curr >= -30.0)
            if is_slab:
                curr_colors, curr_sizes = compute_slab_neuron_colors_and_sizes(
                    v_curr,
                    fired_mask=fired_mask,
                    base_size=base_marker_size,
                    resting_alpha=resting_alpha,
                )
            else:
                curr_colors = compute_neuron_colors(v_curr, fired_mask)
                curr_sizes = base_marker_size

            scatter_3d.set_data(
                pos=n_pos,
                face_color=curr_colors,
                edge_color=None,
                size=curr_sizes,
            )

            vol_zyx = np.ascontiguousarray(
                np.transpose(c_nxt_view.cpu().numpy(), (0, 2, 1)),
                dtype=np.float32,
            )
            vol_norm = np.power(np.clip(vol_zyx / float(source_conc), 0.0, 1.0), 0.45)
            vol_visual.set_data(vol_norm, clim=(0.0, 1.0))

            progress = frame_idx / max(1, total_frames)
            az = 20.0 + progress * 360.0
            el = base_elevation + 8.0 * math.sin(progress * 2.0 * math.pi)
            view_3d.camera.azimuth = az
            view_3d.camera.elevation = el
            if view_net_3d is not None:
                view_net_3d.camera.azimuth = az
                view_net_3d.camera.elevation = el

            # 2. Update Radial Chemical Concentration Shell Curves C(r, t)
            outside_vals = c_nxt_view[outside_source_mask]
            active_voxels = int((outside_vals > 1.0).sum().item())
            plume_mass = float(outside_vals.sum().item())
            active_voxel_series.append(active_voxels)
            plume_mass_series.append(plume_mass)

            x_hist = np.arange(frame_idx + 1, dtype=np.float32)
            for d, line in chem_shell_lines:
                mean_c = float(c_nxt_view[shell_masks[d]].mean().item())
                chem_shell_history[d].append(mean_c)
                if len(x_hist) >= 2:
                    y_hist = np.array(chem_shell_history[d], dtype=np.float32)
                    line.set_data(pos=np.column_stack([x_hist, y_hist]))

            cursor_chem.set_data(
                pos=np.array([[frame_idx, 0.0], [frame_idx, y_max_chem]], dtype=np.float32)
            )

            # 3. Update Firing Scatter Plot / Spike Raster (if 5way)
            if raster_markers is not None:
                valid_steps = [item for item in spike_step_buffers if item is not None]
                if valid_steps:
                    ts_all = np.concatenate([it[0] for it in valid_steps]) - float(min_step)
                    nids_all = np.concatenate([it[1] for it in valid_steps])
                    gids_all = np.concatenate([it[2] for it in valid_steps])
                    pts = np.column_stack([ts_all, nids_all])
                    cols = GROUP_COLORS_ARR[gids_all % len(GROUP_COLORS_ARR)]
                    raster_markers.set_data(
                        pos=pts,
                        face_color=cols,
                        edge_color=None,
                        size=max(2.6, 3.4 * scale_factor) if is_slab else max(3.5, 4.5 * scale_factor),
                    )
                else:
                    raster_markers.set_data(pos=np.empty((0, 2), dtype=np.float32), size=3.0)

            # 4. Update Synchronized Membrane Potential Waveforms
            for m_idx, line in enumerate(voltage_lines):
                y_vals = np.array(v_rolling_buffers[m_idx], dtype=np.float32) + (m_idx * v_spacing)
                line.set_data(pos=np.column_stack([x_plot_coords, y_vals]))

            # Single-pass offscreen EGL render
            img_rgba = canvas.render()
            img_rgb = img_rgba[:, :, :3]
            writer.append_data(img_rgb)

            if (frame_idx + 1) % max(1, total_frames // 5) == 0 or (frame_idx + 1) == total_frames:
                elapsed = time.perf_counter() - t0
                shell1_c = chem_shell_history[SHELL_DISTANCES[0]][-1]
                shell3_c = chem_shell_history[SHELL_DISTANCES[2]][-1]
                print(
                    f"  -> Frame {frame_idx + 1}/{total_frames} ({elapsed:.2f}s) | "
                    f"active_plume_voxels={active_voxels:,} | C(d=1)={shell1_c:.1f}, C(d=6)={shell3_c:.1f} | "
                    f"spikes={total_spikes:,}"
                )
    finally:
        writer.close()
        canvas.close()
        workspace_tensors.clear()

    render_time = time.perf_counter() - t0
    file_size = target_mp4.stat().st_size

    shell_final = {f"d_{d}_voxels": round(chem_shell_history[d][-1], 2) for d in SHELL_DISTANCES}
    shell_initial = {f"d_{d}_voxels": round(chem_shell_history[d][0], 2) for d in SHELL_DISTANCES}

    panel_list = (
        [
            "3d_chemical_plume",
            "3d_neural_network",
            "radial_chemical_concentration_shells",
            "spike_raster",
            "voltage_waveforms",
        ]
        if is_5way
        else [
            "3d_reservoir_and_chemical_plume",
            "radial_chemical_concentration_shells",
            "voltage_waveforms",
        ]
    )

    sources_meta = [
        {
            "source_id": idx + 1,
            "i": [b[0][0], b[0][1]],
            "j": [b[1][0], b[1][1]],
            "k": [b[2][0], b[2][1]],
            "concentration": source_conc,
        }
        for idx, b in enumerate(src_bounds_list)
    ]

    meta = {
        "timestamp": now_str,
        "filename": target_mp4.name,
        "path": str(target_mp4),
        "task": "runpod-chem-diffusion",
        "preset": preset,
        "layout": layout_tag,
        "panels": panel_list,
        "resolution_tier": res_tag,
        "resolution": [width, height],
        "codec": selected_codec,
        "file_size_bytes": file_size,
        "reservoir_shape": list(reservoir_shape),
        "reservoir_segmentation": list(element.config.grid.seg.as_tuple()),
        "n_neurons": int(element.config.N),
        "synapses_per_neuron": int(element.config.S),
        "total_synapses": int(element.config.N) * int(element.config.S),
        "neuron_visuals": {
            "base_marker_size_px": round(float(base_marker_size), 2),
            "resting_alpha": round(float(resting_alpha), 3),
            "spiking_alpha": 1.0,
        },
        "vram_telemetry": vram_stats,
        "build_time_seconds": round(build_time_s, 4),
        "total_steps": steps,
        "stride": stride,
        "chem_substeps_per_step": chem_substeps,
        "total_chem_diffusion_steps": steps * chem_substeps,
        "total_frames": total_frames,
        "fps": fps,
        "duration_seconds": round(total_frames / fps, 2),
        "render_time_seconds": round(render_time, 4),
        "render_fps": round(total_frames / render_time, 2),
        "total_spikes": total_spikes,
        "chem_grid_shape": [grid_h, grid_w, grid_d],
        "dual_sources": bool(dual_sources),
        "chem_sources": sources_meta,
        "chem_source_bounds": sources_meta[0],
        "chem_k_val": chem_k_val,
        "chem_depreciation": chem_depreciation,
        "active_plume_voxels_initial": active_voxel_series[0],
        "active_plume_voxels_mid": active_voxel_series[len(active_voxel_series) // 2],
        "active_plume_voxels_final": active_voxel_series[-1],
        "plume_mass_initial": round(plume_mass_series[0], 2),
        "plume_mass_final": round(plume_mass_series[-1], 2),
        "radial_shell_concentration_initial": shell_initial,
        "radial_shell_concentration_final": shell_final,
        "monitored_neurons": monitored_neurons,
        "v_range": [round(v_min_global, 2), round(v_max_global, 2)],
        "device": str(device),
    }

    def _json_default(obj):
        if isinstance(obj, (np.integer, np.int32, np.int64)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    meta_path = target_mp4.with_suffix(".json")
    meta_path.write_text(json.dumps(meta, indent=2, default=_json_default))
    print(
        f"[+] Chemical diffusion video complete: {target_mp4} ({file_size:,} bytes) "
        f"in {render_time:.2f}s ({meta['render_fps']} fps)"
    )
    return meta


def _parse_float3(val: str) -> tuple[float, float, float]:
    parts = [float(x.strip()) for x in val.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(f"Expected 3 comma-separated floats, got: {val}")
    return (parts[0], parts[1], parts[2])


def _parse_int3(val: str) -> tuple[int, int, int]:
    parts = [int(x.strip()) for x in val.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(f"Expected 3 comma-separated ints, got: {val}")
    return (parts[0], parts[1], parts[2])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Headless SNN 3D Chemical Diffusion + Composite Video Generator (snngine_v4)"
    )
    parser.add_argument(
        "--preset",
        choices=["slab", "legacy"],
        default="slab",
        help="Simulation preset: 'slab' ((6,6,1) flat slab, 30k neurons, dual sources, VRAM scaling) or 'legacy'",
    )
    parser.add_argument("--neurons", type=int, default=30000, help="Total neuron count N in the reservoir")
    parser.add_argument(
        "--reservoir-shape",
        type=_parse_float3,
        default=(6.0, 6.0, 1.0),
        help="3D reservoir world dimensions X,Y,Z (default: 6.0,6.0,1.0 flat slab from SNNgine3D)",
    )
    parser.add_argument(
        "--chem-shape",
        type=_parse_int3,
        default=(52, 156, 156),
        help="3D chemical grid dimensions H,W,D (default: 52,156,156 where dims %% 8 == 4 and H <= 100)",
    )
    parser.add_argument(
        "--dual-sources",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Inject two spatially separated 3D chemical sources across the reservoir slab",
    )
    parser.add_argument("--neuron-size", type=float, default=2.8, help="Base resting 3D neuron marker size in pixels")
    parser.add_argument("--resting-alpha", type=float, default=0.40, help="Opacity (0..1) for resting 3D neurons")
    parser.add_argument(
        "--vram-target-fraction",
        type=float,
        default=0.82,
        help="Target GPU VRAM utilization fraction (0.0 to disable extra workspace scaling)",
    )
    parser.add_argument("--steps", type=int, default=1200, help="Total simulation timesteps")
    parser.add_argument("--stride", type=int, default=2, help="Simulation steps per video frame")
    parser.add_argument(
        "--chem-substeps",
        type=int,
        default=3,
        help="Chemical diffusion kernel steps per simulation step",
    )
    parser.add_argument("--fps", type=int, default=30, help="Output video frame rate")
    parser.add_argument("--resolution", type=str, default="1080p", help="Resolution tier (720p, 1080p, 1440p, 4k)")
    parser.add_argument("--codec", type=str, default="auto", help="Video codec (auto, libx264, libx265)")
    parser.add_argument(
        "--layout",
        choices=["5way", "4way", "3way"],
        default="5way",
        help="Composite viewport layout: 5way/4way (2-way 3D left + 3-way 2D right) or 3way",
    )
    parser.add_argument("--window-ms", type=int, default=200, help="Rolling time window in ms for neural plots")
    parser.add_argument(
        "--chem-k-val",
        type=float,
        default=0.16,
        help="Chemical diffusion rate k_val (must be <= 1/6 ~= 0.1667 for 3D explicit stability)",
    )
    parser.add_argument(
        "--chem-depreciation",
        type=float,
        default=0.002,
        help="Per-step chemical linear clearance/decay",
    )
    parser.add_argument("--source-size", type=int, default=14, help="Edge size (voxels) of each 3D chemical source")
    parser.add_argument("--source-conc", type=float, default=2000.0, help="Injected concentration at each 3D source")
    parser.add_argument("--device", type=int, default=0, help="CUDA device index")
    parser.add_argument("--output-dir", type=str, default="/workspace/output", help="Output directory for MP4 and JSON")
    args = parser.parse_args()
    if args.preset == "legacy":
        args.neurons = 200
        args.reservoir_shape = (1.0, 1.0, 1.0)
        args.chem_shape = (100, 100, 100)
        args.dual_sources = False
        args.vram_target_fraction = 0.0
    if not (0.0 < args.chem_k_val <= MAX_STABLE_K_VAL):
        parser.error(f"--chem-k-val ({args.chem_k_val}) must be in (0, 1/6 ~= {MAX_STABLE_K_VAL:.4f}] for 3D stability.")
    return args


def main() -> None:
    args = parse_args()
    res = parse_resolution(args.resolution)
    render_chem_diffusion_video(
        steps=args.steps,
        stride=args.stride,
        chem_substeps=args.chem_substeps,
        fps=args.fps,
        resolution=res,
        codec=args.codec,
        layout=args.layout,
        preset=args.preset,
        n_neurons=args.neurons,
        reservoir_shape=args.reservoir_shape,
        chem_shape_hwd=args.chem_shape,
        dual_sources=args.dual_sources,
        neuron_size=args.neuron_size,
        resting_alpha=args.resting_alpha,
        vram_target_fraction=args.vram_target_fraction,
        chem_k_val=args.chem_k_val,
        chem_depreciation=args.chem_depreciation,
        source_size=args.source_size,
        source_conc=args.source_conc,
        window_ms=args.window_ms,
        device_id=args.device,
        output_dir=Path(args.output_dir),
    )


if __name__ == "__main__":
    main()
