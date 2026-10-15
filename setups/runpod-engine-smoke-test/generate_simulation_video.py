#!/usr/bin/env python3
"""
Headless SNNgine_v4 Simulation Video Generator.
Runs multi-step spatial neural network simulation on remote GPU,
renders 3D neural activity via hardware-accelerated offscreen EGL OpenGL,
and encodes frames into an H.264 MP4 container.

Filename format: simulation_YYYY-MM-DD_HH-MM-SS[(n)].mp4
"""

import argparse
from datetime import datetime
import json
import math
import os
from pathlib import Path
import sys
import time

# Ensure repository root and build directory are in sys.path
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
_BUILD_DIR = os.path.join(_REPO_ROOT, "snngine_v4", "nn", "cuda_backend", "build")

for p in [_REPO_ROOT, _BUILD_DIR]:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import torch

try:
    import vispy
    from vispy import scene
    from vispy.scene import visuals
    from vispy.color import Colormap
    VISPY_AVAILABLE = True
except ImportError:
    VISPY_AVAILABLE = False

try:
    import imageio
    IMAGEIO_AVAILABLE = True
except ImportError:
    IMAGEIO_AVAILABLE = False

from snngine_v4.config.template import (
    EngineConstructionConfig,
    SpatialNetworkConfig,
)
from snngine_v4.construction.nn_builder import NetworkBuilder
from snngine_v4.visualization.cuda.gl_interop.gl_buffer_types import (
    GLBufferTypes,
)
from snngine_v4.nn.config_models.reservoir.nn_reservoir_config import (
    NetworkReservoirConfig,
)
from snngine_v4.nn.spnn import SpatialNetwork
from snngine_v4.nn.spnn_reservoir import NetworkReservoir
from snngine_v4.utils.containers.mappings import Object2ObjectMap


def patch_array_interfaces():
    """Ensure numpydantic dynamically generated NDArray types match ArrayInterfaces inverse mapping."""
    from numpydantic import Shape
    from snngine_v4.utils.data_utils.validation.np_interface import TypedNumpyInterface
    from snngine_v4.utils.data_utils.validation.array_annotation import ArrayInterfaces
    from snngine_v4.nn.config_models.neurons.presets.izhikevich_presets import IzPreset

    ai = ArrayInterfaces()
    v = TypedNumpyInterface(dtype=np.float32, shape=Shape['4'])
    ai.dtype_interface_map[v] = IzPreset

    def make_type_patched(self_or_arg, *args, dtype):
        if hasattr(self_or_arg, "dtype_interface_map"):
            ai_instance = self_or_arg
            actual_args = args
        else:
            ai_instance = ai
            actual_args = (self_or_arg,) + args

        if len(actual_args) == 1:
            shape = Shape[f'{actual_args[0]}']
        elif len(actual_args) == 2:
            shape = Shape[f'{actual_args[0]}, {actual_args[1]}']
        elif len(actual_args) == 3:
            shape = Shape[f'{actual_args[0]}, {actual_args[1]}, {actual_args[2]}']
        else:
            raise NotImplementedError
        for interface in ai_instance.dtype_interface_map.inv.values():
            if getattr(interface, 'shape', None) == shape and getattr(interface, 'dtype', None) == dtype:
                return interface.array_type
        v_new = TypedNumpyInterface(dtype=dtype, shape=shape)
        ai_instance.dtype_interface_map[v_new] = v_new.array_type
        return v_new.array_type

    ArrayInterfaces.make_type = make_type_patched


def patch_runtime_tensors():
    """
    Enforce C-contiguity on GPU tensors created from Fortran-ordered pandas DataFrames,
    and prevent read-only destination ValueError during sync_to_cpu in NumPy 2.x environments.
    """
    from snngine_v4.utils.cuda_utils.tensor_dataframe import TensorSeries, TensorDataFrame
    from snngine_v4.utils.cuda_utils.tensor_dict import TensorDict
    from snngine_v4.utils.cuda_utils.cuda_functions import compare_devices

    orig_make_gpu_data = TensorSeries.make_gpu_data
    def make_gpu_data_contiguous(self, tensor, device):
        gpu_t = orig_make_gpu_data(self, tensor, device)
        if not gpu_t.is_contiguous():
            gpu_t = gpu_t.contiguous()
        return gpu_t
    TensorSeries.make_gpu_data = make_gpu_data_contiguous

    def sync_to_cpu_patched(self):
        for k, v in self.items():
            if compare_devices(v.device, 'cpu') is False:
                if isinstance(v, TensorDataFrame):
                    v.sync_to_df()
                elif isinstance(v, torch.Tensor):
                    dest = self.array2tensor.inv[v]
                    try:
                        if not dest.flags.writeable:
                            dest.setflags(write=True)
                        dest[:] = v.cpu().numpy()
                    except Exception:
                        pass
    TensorDict.sync_to_cpu = sync_to_cpu_patched


def resolve_unique_target(directory: Path, base_name: str, ext: str = ".mp4") -> Path:
    """Generate deterministic timestamped path with sequential (1), (2) collision handling."""
    directory.mkdir(parents=True, exist_ok=True)
    candidate = directory / f"{base_name}{ext}"
    if not candidate.exists():
        return candidate
    idx = 1
    while True:
        candidate = directory / f"{base_name} ({idx}){ext}"
        if not candidate.exists():
            return candidate
        idx += 1


def compute_neuron_colors(v_arr: np.ndarray, fired_mask: np.ndarray | None = None) -> np.ndarray:
    """
    Map membrane potentials v in [-75, 30] mV to RGBA colormap:
    - -70 mV (resting): Deep blue (0.1, 0.3, 0.8)
    - -55 mV (threshold): Yellow/Cyan transition (0.9, 0.8, 0.2)
    - >= 0 mV or fired: Bright white/magenta flash (1.0, 1.0, 1.0)
    """
    n = len(v_arr)
    colors = np.zeros((n, 4), dtype=np.float32)
    # Normalize v from [-75, 30] to [0.0, 1.0]
    norm_v = np.clip((v_arr + 75.0) / 105.0, 0.0, 1.0)

    # Color gradient: Blue -> Cyan -> Yellow -> Red/White
    colors[:, 0] = np.clip(norm_v * 1.5 - 0.2, 0.1, 1.0)        # R
    colors[:, 1] = np.clip(1.0 - np.abs(norm_v - 0.5) * 2, 0.2, 0.9) # G
    colors[:, 2] = np.clip(1.0 - norm_v * 1.2, 0.1, 0.9)        # B
    colors[:, 3] = 0.85                                          # Alpha

    # Spiking flash
    if fired_mask is not None:
        colors[fired_mask > 0] = [1.0, 1.0, 1.0, 1.0]
    return colors


def build_simulation(device: torch.device):
    """Construct SpatialNetwork and return (network, element, simulator, N_pos)."""
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

    # Mock GPU buffers for CUDA-GL interop contracts
    simulator = network.simulator
    volt_plot = simulator.voltage_plot
    firings_scatter_plot = simulator.firings_scatter_plot

    n_neurons = element.config.N
    v_n_plots, v_len = volt_plot.config.n_plots, volt_plot.config.len
    s_n_plots, s_len = firings_scatter_plot.config.n_plots, firings_scatter_plot.config.len

    pos_vbo_mock = torch.zeros((n_neurons * 4,), dtype=torch.float32, device=device)
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

    if hasattr(element, "chemicals"):
        for chem in [element.chemicals.C0, element.chemicals.C1]:
            chem_shape = chem.config.shape.shape_wdh
            chem_tensor = torch.zeros(chem_shape, dtype=torch.float32, device=device)
            cuda_gl_map[chem.config] = MockGLTensorDict(chem_tensor, GLBufferTypes.TEXTURE_3D.name)

    network.cuda_opengl_map = cuda_gl_map
    simulator.add_simulation(0)

    # Neuron 3D positions
    n_pos = element.N_pos.cpu().numpy()
    return network, element, simulator, n_pos


RESOLUTION_PRESETS = {
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
    "2k": (2560, 1440),
    "4k": (3840, 2160),
    "2160p": (3840, 2160),
}


def parse_resolution(res_str: str) -> tuple[int, int]:
    res_clean = res_str.strip().lower()
    if res_clean in RESOLUTION_PRESETS:
        return RESOLUTION_PRESETS[res_clean]
    for sep in ["x", ",", " "]:
        if sep in res_clean:
            parts = res_clean.split(sep)
            return (int(parts[0].strip()), int(parts[1].strip()))
    raise ValueError(f"Unrecognized resolution format: '{res_str}'. Expected preset (720p, 1080p, 1440p, 4k) or WxH.")


def render_and_encode_video(
    steps: int = 300,
    stride: int = 2,
    fps: int = 30,
    resolution: tuple[int, int] = (1280, 720),
    codec: str = "auto",
    device_id: int = 0,
    output_dir: Path = Path(_SCRIPT_DIR) / "output",
) -> dict:
    """
    Execute headless simulation, render 3D neural activity via offscreen EGL,
    and encode into timestamped MP4 container.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device(f"cuda:{device_id}" if torch.cuda.is_available() else "cpu")
    print(f"[*] Initializing simulation on {device}...")

    network, element, simulator, n_pos = build_simulation(device)

    # Resolve deterministic timestamped output path
    now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_stem = f"simulation_{now_str}"
    target_mp4 = resolve_unique_target(output_dir, base_stem, ext=".mp4")
    print(f"[*] Target video file: {target_mp4}")

    # Set up offscreen VisPy SceneCanvas
    width, height = resolution
    canvas = scene.SceneCanvas(
        keys=None,
        size=(width, height),
        show=False,
        bgcolor="#0f111a",
    )
    view = canvas.central_widget.add_view()
    
    # Calculate bounding box center and radius for camera framing
    center = n_pos.mean(axis=0)
    max_range = np.ptp(n_pos, axis=0).max()
    distance = max(max_range * 2.2, 10.0)

    view.camera = scene.TurntableCamera(
        fov=45,
        elevation=25.0,
        azimuth=0.0,
        center=center,
        distance=distance,
    )

    # Scale marker size proportionally with resolution height
    scale_factor = height / 720.0
    marker_size = max(4.0, 8.0 * scale_factor)

    # 3D Markers for neurons
    v_init = element.neuron_states.N_props.gpu_values[2, :].cpu().numpy()
    init_colors = compute_neuron_colors(v_init)
    scatter = visuals.Markers(parent=view.scene)
    scatter.set_data(
        pos=n_pos,
        face_color=init_colors,
        edge_color=None,
        size=marker_size,
    )

    # Bounding grid box
    grid_min = n_pos.min(axis=0)
    grid_max = n_pos.max(axis=0)
    grid_size = grid_max - grid_min
    grid_box = visuals.Box(
        width=float(grid_size[0]),
        height=float(grid_size[1]),
        depth=float(grid_size[2]),
        color=(0.2, 0.4, 0.6, 0.15),
        edge_color=(0.3, 0.6, 0.9, 0.4),
        parent=view.scene,
    )
    grid_box.transform = scene.transforms.STTransform(translate=center)

    total_frames = steps // stride
    print(f"[*] Rendering {total_frames} frames ({steps} simulation steps @ stride {stride}, {fps} fps, resolution {width}x{height})...")

    # Codec selection: default to libx265 for >= 1440p, libx264 for <= 1080p
    selected_codec = codec
    if selected_codec == "auto":
        selected_codec = "libx265" if height >= 1440 else "libx264"

    # Initialize video writer
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
    
    for frame_idx in range(total_frames):
        # Step simulation by stride
        for _ in range(stride):
            simulator.sim.update(b_stdp=False, verbose=False)

        # Retrieve membrane potential state
        v_current = element.neuron_states.N_props.gpu_values[2, :].cpu().numpy()
        v_history.append((float(v_current.min()), float(v_current.max())))

        # Dynamic colormap update
        colors = compute_neuron_colors(v_current)
        scatter.set_data(pos=n_pos, face_color=colors, size=marker_size)

        # Orbit camera around reservoir
        azimuth = (frame_idx / total_frames) * 360.0
        view.camera.azimuth = azimuth

        # Render offscreen frame buffer
        img = canvas.render()
        if img.shape[2] == 4:
            img = img[:, :, :3]
        writer.append_data(img)

        if (frame_idx + 1) % 25 == 0 or frame_idx == total_frames - 1:
            elapsed = time.perf_counter() - t0
            cur_fps = (frame_idx + 1) / elapsed
            print(f"    [Frame {frame_idx + 1:3d}/{total_frames}] v=[{v_current.min():.1f}, {v_current.max():.1f}] mV | {cur_fps:.1f} fps")

    writer.close()
    canvas.close()
    total_time = time.perf_counter() - t0

    file_size = target_mp4.stat().st_size
    duration_sec = total_frames / fps
    print(f"\n[+] Video generated successfully:")
    print(f"    Path:       {target_mp4}")
    print(f"    Codec:      {selected_codec}")
    print(f"    Size:       {file_size / (1024 * 1024):.2f} MB ({file_size} bytes)")
    print(f"    Frames:     {total_frames} frames ({duration_sec:.1f}s @ {fps} fps)")
    print(f"    Resolution: {width}x{height}")
    print(f"    Render:     {total_time:.2f}s ({total_frames / total_time:.1f} frames/sec)")

    metadata = {
        "timestamp": now_str,
        "filename": target_mp4.name,
        "path": str(target_mp4.resolve()),
        "codec": selected_codec,
        "file_size_bytes": file_size,
        "total_steps": steps,
        "stride": stride,
        "total_frames": total_frames,
        "fps": fps,
        "duration_seconds": duration_sec,
        "render_time_seconds": total_time,
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
    parser = argparse.ArgumentParser(description="Headless SNN Simulation Video Generator")
    parser.add_argument("--steps", type=int, default=300, help="Total simulation timesteps")
    parser.add_argument("--stride", type=int, default=2, help="Simulation steps per video frame")
    parser.add_argument("--fps", type=int, default=30, help="Video framerate")
    parser.add_argument("--resolution", default="1280x720", help="Resolution: preset (720p, 1080p, 1440p, 4k) or WxH")
    parser.add_argument("--codec", default="auto", help="Video codec: auto, libx264, libx265")
    parser.add_argument("--device-id", type=int, default=0, help="GPU device ID")
    parser.add_argument("--output-dir", type=Path, default=Path(_SCRIPT_DIR) / "output", help="Output directory")

    args = parser.parse_args()
    render_res = parse_resolution(args.resolution)

    meta = render_and_encode_video(
        steps=args.steps,
        stride=args.stride,
        fps=args.fps,
        resolution=render_res,
        codec=args.codec,
        device_id=args.device_id,
        output_dir=args.output_dir,
    )
    print(json.dumps(meta, indent=2))
