#!/usr/bin/env python3
"""
Headless SNN Simulation Unified Composite Video Generator (snngine_v4)
======================================================================
Renders a synchronized 3-panel diagnostic video combining:
  1. Left Panel (50% width): 3D neural reservoir with orbital camera easing,
     membrane potential colormap, and brilliant white spike flashes.
  2. Top-Right Panel (50% width, 50% height): Firing scatter plot (spike raster)
     displaying action potentials over a rolling time window, color-coded by group.
  3. Bottom-Right Panel (50% width, 50% height): Multi-trace membrane potential
     waveforms (v(t)) for representative neurons (focal, recurrent, baseline).

Uses hardware-accelerated offscreen EGL OpenGL and encodes directly to H.264/H.265.
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

import imageio
import numpy as np
import torch
from vispy import scene
from vispy.scene import visuals

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

# Import simulation construction and color mapping from base generator
from generate_simulation_video import (
    build_simulation,
    compute_neuron_colors,
    resolve_unique_target,
    parse_resolution,
)

GROUP_COLORS = [
    [0.2, 0.8, 1.0, 0.9],   # Group 0: Cyan
    [0.3, 0.9, 0.4, 0.9],   # Group 1: Lime green
    [0.9, 0.5, 1.0, 0.9],   # Group 2: Lavender / purple
    [1.0, 0.6, 0.2, 0.9],   # Group 3: Amber / orange
]

TRACE_COLORS = [
    [1.0, 0.85, 0.2, 0.95],  # Monitored 0: Stimulated Focal (Gold)
    [1.0, 0.35, 0.2, 0.95],  # Monitored 1: Stimulated Focal (Coral)
    [0.2, 0.9, 0.9, 0.95],   # Monitored 2: Recurrent Excitatory (Cyan)
    [0.3, 0.95, 0.5, 0.95],  # Monitored 3: Recurrent Excitatory (Green)
    [0.4, 0.6, 1.0, 0.95],   # Monitored 4: Unstimulated Baseline (Sky Blue)
    [0.7, 0.4, 1.0, 0.95],   # Monitored 5: Unstimulated Baseline (Purple)
]


def render_composite_video(
    steps: int = 1200,
    stride: int = 2,
    fps: int = 30,
    resolution: tuple[int, int] = (1920, 1080),
    codec: str = "auto",
    stim_mode: str = "focal",
    stim_fraction: float = 0.20,
    stim_pt: float = 0.35,
    window_ms: int = 200,
    device_id: int = 0,
    output_dir: Path = Path(_SCRIPT_DIR) / "output",
) -> dict:
    """
    Execute headless simulation and render synchronized 3-panel composite video.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device(f"cuda:{device_id}" if torch.cuda.is_available() else "cpu")
    print(f"[*] Initializing simulation on {device}...")

    network, element, simulator, sim_instance, sim_backend, n_pos, stim_indices = build_simulation(
        device,
        stim_mode=stim_mode,
        stim_fraction=stim_fraction,
        stim_pt=stim_pt,
    )

    n_neurons = len(n_pos)
    n_groups = element.config.G
    neurons_per_group = n_neurons // n_groups

    # Select representative neurons for membrane potential multi-plot:
    # 2 focal stimulated, 2 recurrent excitatory, 2 quiescent baseline
    monitored_neurons = []
    # 2 focal
    if len(stim_indices) >= 2:
        monitored_neurons.extend([int(stim_indices[0]), int(stim_indices[1])])
    else:
        monitored_neurons.extend([0, 1])
    # 2 intermediate recurrent (from groups 1 & 2 not in stim_indices)
    unstimulated = [i for i in range(n_neurons) if i not in stim_indices]
    if len(unstimulated) >= 4:
        monitored_neurons.extend([unstimulated[0], unstimulated[len(unstimulated) // 4]])
        monitored_neurons.extend([unstimulated[len(unstimulated) // 2], unstimulated[-1]])
    else:
        monitored_neurons.extend([50, 100, 150, 180])
    
    monitored_neurons = monitored_neurons[:6]
    n_monitored = len(monitored_neurons)
    print(f"[*] Monitored neurons for voltage multi-plot: {monitored_neurons}")

    width, height = resolution
    res_tag = f"{height}p"
    now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_stem = f"simulation_composite_{res_tag}_{now_str}"
    target_mp4 = resolve_unique_target(output_dir, base_stem, ext=".mp4")
    print(f"[*] Target composite video file: {target_mp4}")

    # Set up offscreen VisPy SceneCanvas with 3-viewport Grid
    canvas = scene.SceneCanvas(
        keys=None,
        size=(width, height),
        show=False,
        bgcolor="#0c0e17",
    )
    grid = canvas.central_widget.add_grid()

    # Panel 1: Left Viewport (3D Neural Reservoir, spans 2 rows)
    view_3d = grid.add_view(row=0, col=0, row_span=2, col_span=1)
    view_3d.bgcolor = "#0e111d"
    view_3d.border_color = "#1e2438"

    # Panel 2: Top-Right Viewport (Spike Raster Plot)
    view_raster = grid.add_view(row=0, col=1, row_span=1, col_span=1)
    view_raster.bgcolor = "#0b0d18"
    view_raster.border_color = "#1e2438"

    # Panel 3: Bottom-Right Viewport (Membrane Potential Multi-Plot)
    view_voltage = grid.add_view(row=1, col=1, row_span=1, col_span=1)
    view_voltage.bgcolor = "#090a12"
    view_voltage.border_color = "#1e2438"

    # --- Setup Panel 1: 3D Reservoir Visuals ---
    center = n_pos.mean(axis=0)
    max_range = np.ptp(n_pos, axis=0).max()
    distance = max(max_range * 2.3, 10.0)

    view_3d.camera = scene.TurntableCamera(
        fov=45,
        elevation=25.0,
        azimuth=0.0,
        center=center,
        distance=distance,
    )
    scale_factor = height / 720.0
    marker_size = max(4.0, 7.5 * scale_factor)

    v_init = element.neuron_states.N_props.gpu_values[2, :].cpu().numpy()
    scatter_3d = visuals.Markers(parent=view_3d.scene)
    scatter_3d.set_data(
        pos=n_pos,
        face_color=compute_neuron_colors(v_init),
        edge_color=None,
        size=marker_size,
    )

    grid_min = n_pos.min(axis=0)
    grid_max = n_pos.max(axis=0)
    grid_size = grid_max - grid_min
    grid_box = visuals.Box(
        width=float(grid_size[0]),
        height=float(grid_size[1]),
        depth=float(grid_size[2]),
        color=(0.2, 0.4, 0.6, 0.12),
        edge_color=(0.3, 0.6, 0.9, 0.35),
        parent=view_3d.scene,
    )
    grid_box.transform = scene.transforms.STTransform(translate=center)

    # --- Setup Panel 2: Spike Raster Visuals ---
    window_steps = window_ms  # 1 ms per simulation step
    view_raster.camera = scene.PanZoomCamera(
        rect=(0, -5, window_steps, n_neurons + 10),
        aspect=None,
    )
    view_raster.camera.interactive = False

    # Group divider lines in raster view
    for g in range(1, n_groups):
        y_div = g * neurons_per_group
        div_line = visuals.Line(
            pos=np.array([[0, y_div], [window_steps, y_div]], dtype=np.float32),
            color=(0.3, 0.4, 0.6, 0.3),
            width=1.0,
            parent=view_raster.scene,
        )

    # Time cursor indicator line on the right edge
    cursor_raster = visuals.Line(
        pos=np.array([[window_steps, 0], [window_steps, n_neurons]], dtype=np.float32),
        color=(0.9, 0.3, 0.3, 0.6),
        width=1.5,
        parent=view_raster.scene,
    )

    raster_markers = visuals.Markers(parent=view_raster.scene)
    raster_markers.set_data(pos=np.empty((0, 2), dtype=np.float32), size=3.5)

    # --- Setup Panel 3: Voltage Waveforms Visuals ---
    v_spacing = 80.0  # mV spacing between stacked baseline traces
    y_total_height = n_monitored * v_spacing + 40.0
    view_voltage.camera = scene.PanZoomCamera(
        rect=(0, -85.0, window_steps, y_total_height),
        aspect=None,
    )
    view_voltage.camera.interactive = False

    voltage_lines = []
    x_plot_coords = np.linspace(0, window_steps, window_steps, dtype=np.float32)

    # Baseline reference lines for each monitored trace
    for m_idx in range(n_monitored):
        baseline_y = m_idx * v_spacing - 65.0
        ref_line = visuals.Line(
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

    cursor_voltage = visuals.Line(
        pos=np.array([[window_steps, -80.0], [window_steps, y_total_height]], dtype=np.float32),
        color=(0.9, 0.3, 0.3, 0.6),
        width=1.5,
        parent=view_voltage.scene,
    )

    # Rolling history buffers
    spike_history = deque()  # stores (step_time, neuron_id, group_id)
    v_rolling_buffers = [deque([ -65.0 ] * window_steps, maxlen=window_steps) for _ in range(n_monitored)]

    total_frames = steps // stride
    print(f"[*] Rendering {total_frames} composite frames ({steps} simulation steps @ stride {stride}, {fps} fps, resolution {width}x{height})...")

    # Codec selection
    selected_codec = codec
    if selected_codec == "auto":
        selected_codec = "libx265" if height >= 1440 else "libx264"

    try:
        writer = imageio.get_writer(
            str(target_mp4),
            fps=fps,
            codec=selected_codec,
            quality=8,
            pixelformat="yuv420p",
        )
    except Exception as e:
        if selected_codec != "libx264":
            print(f"[!] Codec {selected_codec} unavailable ({e}), falling back to libx264...")
            selected_codec = "libx264"
            writer = imageio.get_writer(
                str(target_mp4),
                fps=fps,
                codec=selected_codec,
                quality=8,
                pixelformat="yuv420p",
            )
        else:
            raise

    t0 = time.perf_counter()
    v_history = []
    total_spikes = 0
    curr_sim_step = 0

    for frame_idx in range(total_frames):
        stride_fired = np.zeros(n_neurons, dtype=bool)

        # Simulation micro-steps per frame
        for _ in range(stride):
            sim_backend.update(False, False)
            curr_sim_step += 1
            fired_step = (sim_instance.Fired.cpu().numpy() > 0)
            stride_fired |= fired_step

            # Record newly fired spikes into rolling history
            fired_idcs = np.where(fired_step)[0]
            for n_id in fired_idcs:
                group_id = int(n_id // neurons_per_group)
                spike_history.append((curr_sim_step, int(n_id), group_id))

            # Sample monitored voltages at each micro-step
            v_all = element.neuron_states.N_props.gpu_values[2, :].cpu().numpy()
            for m_idx, m_nid in enumerate(monitored_neurons):
                v_rolling_buffers[m_idx].append(float(v_all[m_nid]))

        if device.type == "cuda":
            torch.cuda.synchronize(device=device)

        v_current = element.neuron_states.N_props.gpu_values[2, :].cpu().numpy()
        v_history.append((float(v_current.min()), float(v_current.max())))
        total_spikes += int(stride_fired.sum())

        # 1. Update Panel 1 (3D Reservoir)
        fired_mask = stride_fired | (v_current >= -30.0)
        colors_3d = compute_neuron_colors(v_current, fired_mask=fired_mask)
        scatter_3d.set_data(pos=n_pos, face_color=colors_3d, size=marker_size)

        azimuth = (frame_idx / total_frames) * 360.0
        elevation = 25.0 + 8.0 * math.sin((frame_idx / total_frames) * 2.0 * math.pi)
        view_3d.camera.azimuth = azimuth
        view_3d.camera.elevation = elevation

        # 2. Update Panel 2 (Spike Raster Plot)
        # Purge spikes older than window_steps
        min_cutoff = curr_sim_step - window_steps
        while spike_history and spike_history[0][0] < min_cutoff:
            spike_history.popleft()

        if spike_history:
            sp_arr = list(spike_history)
            t_rel = np.array([sp[0] - min_cutoff for sp in sp_arr], dtype=np.float32)
            y_nid = np.array([sp[1] for sp in sp_arr], dtype=np.float32)
            raster_pos = np.column_stack([t_rel, y_nid])

            # Color points by neural group, or white flash for stimulated focal subset
            raster_colors = np.zeros((len(sp_arr), 4), dtype=np.float32)
            for s_idx, sp in enumerate(sp_arr):
                if sp[1] in stim_indices:
                    raster_colors[s_idx] = [1.0, 0.9, 0.3, 0.95]  # Gold for stimulated cluster
                else:
                    g_id = min(sp[2], n_groups - 1)
                    raster_colors[s_idx] = GROUP_COLORS[g_id]
            raster_markers.set_data(pos=raster_pos, face_color=raster_colors, size=3.5)
        else:
            raster_markers.set_data(pos=np.empty((0, 2), dtype=np.float32), size=0)

        # 3. Update Panel 3 (Voltage Waveforms)
        for m_idx in range(n_monitored):
            v_trace = np.array(v_rolling_buffers[m_idx], dtype=np.float32)
            y_trace = v_trace + (m_idx * v_spacing)
            voltage_lines[m_idx].set_data(pos=np.column_stack([x_plot_coords, y_trace]))

        # Render composite frame across all 3 viewports
        img = canvas.render()
        if img.shape[2] == 4:
            img = img[:, :, :3]
        writer.append_data(img)

        if (frame_idx + 1) % 25 == 0 or frame_idx == total_frames - 1:
            elapsed = time.perf_counter() - t0
            cur_fps = (frame_idx + 1) / elapsed
            print(f"    [Frame {frame_idx + 1:3d}/{total_frames}] v=[{v_current.min():.1f}, {v_current.max():.1f}] mV | spikes={total_spikes} | {cur_fps:.1f} fps")

    writer.close()
    canvas.close()
    total_time = time.perf_counter() - t0

    file_size = target_mp4.stat().st_size
    duration_sec = total_frames / fps
    print(f"\n[+] Composite video generated successfully:")
    print(f"    Path:       {target_mp4}")
    print(f"    Codec:      {selected_codec}")
    print(f"    Size:       {file_size / (1024 * 1024):.2f} MB ({file_size} bytes)")
    print(f"    Frames:     {total_frames} frames ({duration_sec:.1f}s @ {fps} fps)")
    print(f"    Resolution: {width}x{height} ({res_tag})")
    print(f"    Render:     {total_time:.2f}s ({total_frames / total_time:.1f} frames/sec)")
    print(f"    Spikes:     {total_spikes} spike events observed")

    metadata = {
        "timestamp": now_str,
        "filename": target_mp4.name,
        "path": str(target_mp4.resolve()),
        "composite": True,
        "panels": ["3d_reservoir", "spike_raster", "voltage_waveforms"],
        "resolution_tier": res_tag,
        "codec": selected_codec,
        "file_size_bytes": file_size,
        "total_steps": steps,
        "stride": stride,
        "total_frames": total_frames,
        "fps": fps,
        "duration_seconds": duration_sec,
        "render_time_seconds": total_time,
        "render_fps": round(total_frames / total_time, 2),
        "total_spikes": total_spikes,
        "stim_mode": stim_mode,
        "stim_fraction": stim_fraction,
        "stim_count": len(stim_indices),
        "stim_pt": stim_pt,
        "monitored_neurons": monitored_neurons,
        "window_ms": window_ms,
        "resolution": list(resolution),
        "device": str(device),
        "v_range_initial": v_history[0] if v_history else None,
        "v_range_final": v_history[-1] if v_history else None,
    }

    meta_path = target_mp4.with_suffix(".json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unified Composite SNN Simulation Video Generator")
    parser.add_argument("--steps", type=int, default=1200, help="Total simulation timesteps")
    parser.add_argument("--stride", type=int, default=2, help="Simulation steps per video frame")
    parser.add_argument("--fps", type=int, default=30, help="Video framerate")
    parser.add_argument("--resolution", default="1920x1080", help="Resolution: preset (1080p, 1440p, 4k) or WxH")
    parser.add_argument("--codec", default="auto", help="Video codec: auto, libx264, libx265")
    parser.add_argument("--stim-mode", choices=["focal", "group0", "all"], default="focal", help="Neuron activation pattern")
    parser.add_argument("--stim-fraction", type=float, default=0.20, help="Fraction of neurons to activate in distinct subset")
    parser.add_argument("--stim-pt", type=float, default=0.35, help="Thalamic stimulus probability for active subset")
    parser.add_argument("--window-ms", type=int, default=200, help="Telemetry scrolling window length in ms")
    parser.add_argument("--device-id", type=int, default=0, help="GPU device ID")
    parser.add_argument("--output-dir", type=Path, default=Path(_SCRIPT_DIR) / "output", help="Output directory")

    args = parser.parse_args()
    render_res = parse_resolution(args.resolution)

    meta = render_composite_video(
        steps=args.steps,
        stride=args.stride,
        fps=args.fps,
        resolution=render_res,
        codec=args.codec,
        stim_mode=args.stim_mode,
        stim_fraction=args.stim_fraction,
        stim_pt=args.stim_pt,
        window_ms=args.window_ms,
        device_id=args.device_id,
        output_dir=args.output_dir,
    )
    print(json.dumps(meta, indent=2))
