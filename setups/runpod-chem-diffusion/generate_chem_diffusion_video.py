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


def build_chem_simulation(
    device: torch.device,
    stim_fraction: float = 0.20,
    stim_pt: float = 0.35,
):
    """
    Construct SpatialNetwork with padded chemical tensors (to guard against i <= grid_h
    boundary reads in snn_simulation.cu:221) and focal thalamic stimulation.
    """
    patch_array_interfaces()
    patch_runtime_tensors()

    dev_val = device.index if device.type == "cuda" and device.index is not None else (0 if device.type == "cuda" else "cpu")
    config = SpatialNetworkConfig(
        elements=[NetworkReservoirConfig()],
        device=dev_val,
    )
    construction_config = EngineConstructionConfig(network=config)
    network_builder = NetworkBuilder(container_model=construction_config)
    network: SpatialNetwork = network_builder.add_build(model=config, device=device)
    element: NetworkReservoir = network.get_network_element(0)

    simulator = network.simulator
    volt_plot = simulator.voltage_plot
    firings_scatter_plot = simulator.firings_scatter_plot

    n_neurons = element.config.N
    v_n_plots, v_len = volt_plot.config.n_plots, volt_plot.config.size_x
    s_n_plots, s_len = firings_scatter_plot.config.n_plots, firings_scatter_plot.config.size_x

    pos_vbo_mock = torch.zeros((n_neurons, 14), dtype=torch.float32, device=device)
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

    # Allocate chemical 3D tensors with +2 padding on axis 0 (102 x 100 x 100 = 1,020,000 floats)
    # so boundary threads at i == grid_h, j == grid_w, k == grid_d (idx <= 1,010,100) never read out of bounds.
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

    # Enable thalamic input on group flags and activate focal neuron cluster near the center
    element.L_Group_flags.gpu_values[1, :] = 1
    element.neuron_states.N_props.gpu_values[0, :] = 0.0
    k_stim = max(1, int(round(n_neurons * stim_fraction)))
    anchor_pt = np.median(n_pos, axis=0)
    dists = np.linalg.norm(n_pos - anchor_pt, axis=1)
    stim_indices = np.argsort(dists)[:k_stim]
    stim_idx_t = torch.tensor(stim_indices, dtype=torch.long, device=device)
    element.neuron_states.N_props.gpu_values[0, stim_idx_t] = float(stim_pt)

    return network, element, simulator, sim_instance, sim_backend, n_pos, stim_indices


def configure_chemical_source(
    element: NetworkReservoir,
    sim_backend,
    source_center: tuple[int, int, int] = (50, 50, 50),
    source_size: int = 12,
    source_conc: float = 2000.0,
    chem_k_val: float = 0.16,
    chem_depreciation: float = 0.005,
):
    """
    Zero out default test slices and inject a localized 3D cubic chemical source into C0.
    Returns (grid_shape_hwd, src_bounds_hwd, shell_masks_gpu).
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

    ci, cj, ck = source_center
    half = max(1, source_size // 2)
    i0, i1 = max(2, ci - half), min(grid_h - 2, ci + half)
    j0, j1 = max(2, cj - half), min(grid_w - 2, cj + half)
    k0, k1 = max(2, ck - half), min(grid_d - 2, ck + half)

    # Inject persistent chemical source concentration into c_source (and initial state)
    c_src_view[i0:i1, j0:j1, k0:k1] = float(source_conc)
    c_cur_view[i0:i1, j0:j1, k0:k1] = float(source_conc)
    c_nxt_view[i0:i1, j0:j1, k0:k1] = float(source_conc)

    # Configure backend diffusion parameters (leave b_update_chemical_concentrations True as initialized)
    sim_backend.chem_k_val = float(chem_k_val)
    sim_backend.chem_depreciation = float(chem_depreciation)
    if not sim_backend.b_update_chemical_concentrations:
        raise RuntimeError("Expected sim_backend.b_update_chemical_concentrations to be True on construction.")

    # Precompute concentric Chebyshev distance shell masks outside the source box [i0:i1, j0:j1, k0:k1]
    device = c0.c_next.device
    ii = torch.arange(grid_h, device=device).view(grid_h, 1, 1)
    jj = torch.arange(grid_w, device=device).view(1, grid_w, 1)
    kk = torch.arange(grid_d, device=device).view(1, 1, grid_d)

    di = torch.maximum(torch.clamp(i0 - ii, min=0), torch.clamp(ii - (i1 - 1), min=0))
    dj = torch.maximum(torch.clamp(j0 - jj, min=0), torch.clamp(jj - (j1 - 1), min=0))
    dk = torch.maximum(torch.clamp(k0 - kk, min=0), torch.clamp(kk - (k1 - 1), min=0))
    cheb_dist = torch.maximum(di, torch.maximum(dj, dk))

    outside_source_mask = cheb_dist >= 1
    shell_masks = {int(d): (cheb_dist == int(d)) for d in SHELL_DISTANCES}

    return (grid_h, grid_w, grid_d), ((i0, i1), (j0, j1), (k0, k1)), outside_source_mask, shell_masks


def render_chem_diffusion_video(
    steps: int = 1200,
    stride: int = 2,
    chem_substeps: int = 2,
    fps: int = 30,
    resolution: tuple[int, int] = (1920, 1080),
    codec: str = "auto",
    layout: str = "5way",
    chem_k_val: float = 0.16,
    chem_depreciation: float = 0.002,
    source_size: int = 12,
    source_conc: float = 2000.0,
    window_ms: int = 200,
    device_id: int = 0,
    output_dir: Path = Path(_SCRIPT_DIR) / "output",
) -> dict:
    """
    Execute headless simulation with 3D chemical source diffusion and render a synchronized
    multi-panel composite MP4 video (default 5way: 2-way 3D left column + 3-way 2D right column).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device(f"cuda:{device_id}" if torch.cuda.is_available() else "cpu")
    print(f"[*] Initializing simulation + 3D chemical diffusion on {device}...")

    network, element, simulator, sim_instance, sim_backend, n_pos, stim_indices = build_chem_simulation(
        device=device,
    )

    grid_hwd, src_bounds, outside_source_mask, shell_masks = configure_chemical_source(
        element=element,
        sim_backend=sim_backend,
        source_center=(50, 50, 50),
        source_size=source_size,
        source_conc=source_conc,
        chem_k_val=chem_k_val,
        chem_depreciation=chem_depreciation,
    )
    grid_h, grid_w, grid_d = grid_hwd
    (i0, i1), (j0, j1), (k0, k1) = src_bounds
    print(
        f"[*] Configured 3D chemical source cube: i=[{i0}:{i1}], j=[{j0}:{j1}], k=[{k0}:{k1}] "
        f"at C_source={source_conc:.1f} | k_val={chem_k_val:.4f}, depreciation={chem_depreciation:.4f}"
    )

    n_neurons = len(n_pos)
    n_groups = element.config.G
    neurons_per_group = n_neurons // n_groups

    monitored_neurons = []
    if len(stim_indices) >= 2:
        monitored_neurons.extend([int(stim_indices[0]), int(stim_indices[1])])
    else:
        monitored_neurons.extend([0, 1])
    unstimulated = [idx for idx in range(n_neurons) if idx not in stim_indices]
    if len(unstimulated) >= 4:
        monitored_neurons.extend([unstimulated[0], unstimulated[len(unstimulated) // 4]])
        monitored_neurons.extend([unstimulated[len(unstimulated) // 2], unstimulated[-1]])
    else:
        monitored_neurons.extend([50, 100, 150, 180])
    monitored_neurons = monitored_neurons[:6]
    n_monitored = len(monitored_neurons)

    is_5way = layout in ("5way", "4way")
    layout_tag = "5way" if is_5way else "3way"

    width, height = resolution
    res_tag = f"{height}p"
    now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_stem = (
        f"simulation_chem_5way_{res_tag}_{now_str}"
        if is_5way
        else f"simulation_chem_{res_tag}_{now_str}"
    )
    target_mp4 = resolve_unique_target(output_dir, base_stem, ext=".mp4")
    print(f"[*] Target chemical diffusion video file ({layout_tag}): {target_mp4}")

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

    # --- Setup Left Column Top: 3D Chemical Source & Volumetric Plume ---
    grid_min = n_pos.min(axis=0)
    grid_max = n_pos.max(axis=0)
    grid_size = grid_max - grid_min
    center = 0.5 * (grid_min + grid_max)
    max_range = float(grid_size.max())
    distance = max(max_range * 2.25, 10.0)

    view_3d.camera = scene.TurntableCamera(
        fov=45,
        elevation=24.0,
        azimuth=15.0,
        center=center,
        distance=distance,
    )

    # 1a. Outer reservoir wireframe cage (12 edges)
    cage_segments = make_wireframe_box_segments(grid_min, grid_max)
    visuals.Line(
        pos=cage_segments,
        color=(0.35, 0.55, 0.85, 0.45),
        width=1.5,
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

    # 1c. 3D Chemical source wireframe box (exact world bounds of the c_source block)
    src_min_world = grid_min + np.array(
        [j0 / grid_w, k0 / grid_d, i0 / grid_h], dtype=np.float32
    ) * grid_size
    src_max_world = grid_min + np.array(
        [j1 / grid_w, k1 / grid_d, i1 / grid_h], dtype=np.float32
    ) * grid_size
    src_segments = make_wireframe_box_segments(src_min_world, src_max_world)
    visuals.Line(
        pos=src_segments,
        color=(0.25, 1.0, 0.55, 0.95),
        width=2.5,
        connect="segments",
        parent=view_3d.scene,
    )

    scale_factor = height / 720.0
    marker_size = max(4.0, (6.5 if is_5way else 7.5) * scale_factor)
    v_init = element.neuron_states.N_props.gpu_values[2, :].cpu().numpy()

    if is_5way and view_net_3d is not None:
        # --- Setup Left Column Bottom: Dedicated 3D Neural Network Reservoir (from runpod-engine-smoke-test) ---
        view_net_3d.camera = scene.TurntableCamera(
            fov=45,
            elevation=24.0,
            azimuth=15.0,
            center=center,
            distance=distance,
        )
        scatter_3d = visuals.Markers(parent=view_net_3d.scene)
        scatter_3d.set_data(
            pos=n_pos,
            face_color=compute_neuron_colors(v_init),
            edge_color=None,
            size=marker_size,
        )
        net_grid_box = visuals.Box(
            width=float(grid_size[0]),
            height=float(grid_size[1]),
            depth=float(grid_size[2]),
            color=(0.2, 0.4, 0.6, 0.15),
            edge_color=(0.3, 0.6, 0.9, 0.4),
            parent=view_net_3d.scene,
        )
        net_grid_box.transform = scene.transforms.STTransform(translate=center)
    else:
        scatter_3d = visuals.Markers(parent=view_3d.scene)
        scatter_3d.set_data(
            pos=n_pos,
            face_color=compute_neuron_colors(v_init),
            edge_color=None,
            size=marker_size,
        )

    # --- Setup Right Column Top: Radial Chemical Concentration Curves C(r, t) ---
    total_frames = steps // stride
    y_max_chem = float(source_conc) * 0.88  # Scale Y axis to cover shell d=1 (~1700) cleanly
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

    # --- Setup Right Column Middle (5way): Firing Scatter Plot / Spike Raster (from runpod-engine-smoke-test) ---
    window_steps = window_ms
    spike_history = deque()  # stores (step_time, neuron_id, group_id)
    raster_markers = None
    if is_5way and view_raster is not None:
        view_raster.camera = scene.PanZoomCamera(
            rect=(0, -5, window_steps, n_neurons + 10),
            aspect=None,
        )
        view_raster.camera.interactive = False

        for g in range(1, n_groups):
            y_div = g * neurons_per_group
            visuals.Line(
                pos=np.array([[0, y_div], [window_steps, y_div]], dtype=np.float32),
                color=(0.3, 0.4, 0.6, 0.3),
                width=1.0,
                parent=view_raster.scene,
            )

        visuals.Line(
            pos=np.array([[window_steps, 0], [window_steps, n_neurons]], dtype=np.float32),
            color=(0.9, 0.3, 0.3, 0.6),
            width=1.5,
            parent=view_raster.scene,
        )

        raster_markers = visuals.Markers(parent=view_raster.scene)
        raster_markers.set_data(pos=np.empty((0, 2), dtype=np.float32), size=3.5)

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

    print(
        f"[*] Rendering {total_frames} frames ({steps} sim steps @ stride {stride}, "
        f"{chem_substeps} chem diffusion substeps/step, layout={layout_tag}, {width}x{height})..."
    )

    try:
        for frame_idx in range(total_frames):
            fired_accum = np.zeros(n_neurons, dtype=bool)
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

                # Record spike events for the spike raster panel
                fired_ids = np.where(f_step | (v_step >= -30.0))[0]
                for nid in fired_ids:
                    gid = min(int(nid) // max(1, neurons_per_group), n_groups - 1)
                    spike_history.append((current_sim_step, int(nid), gid))

                for m_idx, n_id in enumerate(monitored_neurons):
                    v_clamp = float(np.clip(v_step[n_id], -85.0, 35.0))
                    v_rolling_buffers[m_idx].append(v_clamp)

            # Prune spike history outside rolling time window
            min_step = current_sim_step - window_steps
            while spike_history and spike_history[0][0] < min_step:
                spike_history.popleft()

            v_curr = element.neuron_states.N_props.gpu_values[2, :].cpu().numpy()
            v_min_global = min(v_min_global, float(v_curr.min()))
            v_max_global = max(v_max_global, float(v_curr.max()))

            # 1. Update 3D Neurons & 3D Chemical Plume Volume
            fired_mask = fired_accum | (v_curr >= -30.0)
            scatter_3d.set_data(
                pos=n_pos,
                face_color=compute_neuron_colors(v_curr, fired_mask),
                edge_color=None,
                size=marker_size,
            )

            vol_zyx = np.ascontiguousarray(
                np.transpose(c_nxt_view.cpu().numpy(), (0, 2, 1)),
                dtype=np.float32,
            )
            vol_norm = np.power(np.clip(vol_zyx / float(source_conc), 0.0, 1.0), 0.45)
            vol_visual.set_data(vol_norm, clim=(0.0, 1.0))

            progress = frame_idx / max(1, total_frames)
            az = 15.0 + progress * 360.0
            el = 24.0 + 8.0 * math.sin(progress * 2.0 * math.pi)
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
                if spike_history:
                    pts = np.array(
                        [[t - min_step, nid] for (t, nid, _) in spike_history],
                        dtype=np.float32,
                    )
                    cols = np.array(
                        [GROUP_COLORS[gid % len(GROUP_COLORS)] for (_, _, gid) in spike_history],
                        dtype=np.float32,
                    )
                    raster_markers.set_data(
                        pos=pts,
                        face_color=cols,
                        edge_color=None,
                        size=max(3.5, 4.5 * scale_factor),
                    )
                else:
                    raster_markers.set_data(pos=np.empty((0, 2), dtype=np.float32), size=3.5)

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
                    f"active_plume_voxels={active_voxels} | C(d=1)={shell1_c:.1f}, C(d=6)={shell3_c:.1f} | "
                    f"spikes={total_spikes}"
                )
    finally:
        writer.close()
        canvas.close()

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

    meta = {
        "timestamp": now_str,
        "filename": target_mp4.name,
        "path": str(target_mp4),
        "task": "runpod-chem-diffusion",
        "layout": layout_tag,
        "panels": panel_list,
        "resolution_tier": res_tag,
        "resolution": [width, height],
        "codec": selected_codec,
        "file_size_bytes": file_size,
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
        "chem_source_bounds": {
            "i": [i0, i1],
            "j": [j0, j1],
            "k": [k0, k1],
            "concentration": source_conc,
        },
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

    meta_path = target_mp4.with_suffix(".json")
    meta_path.write_text(json.dumps(meta, indent=2))
    print(
        f"[+] Chemical diffusion video complete: {target_mp4} ({file_size:,} bytes) "
        f"in {render_time:.2f}s ({meta['render_fps']} fps)"
    )
    return meta


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Headless SNN 3D Chemical Diffusion + Composite Video Generator (snngine_v4)"
    )
    parser.add_argument("--steps", type=int, default=1200, help="Total simulation timesteps")
    parser.add_argument("--stride", type=int, default=2, help="Simulation steps per video frame")
    parser.add_argument(
        "--chem-substeps",
        type=int,
        default=2,
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
    parser.add_argument("--source-size", type=int, default=12, help="Edge size (voxels) of the 3D cubic chemical source")
    parser.add_argument("--source-conc", type=float, default=2000.0, help="Injected concentration at the 3D source")
    parser.add_argument("--device", type=int, default=0, help="CUDA device index")
    parser.add_argument("--output-dir", type=str, default="/workspace/output", help="Output directory for MP4 and JSON")
    args = parser.parse_args()
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
