"""
Headless network builder for the assembly association task, with the synapse count S as a
parameter. Adapted from build_chem_simulation() in
setups/runpod-chem-diffusion/generate_chem_diffusion_video.py (that file stays unmodified;
its patches and helpers are imported), minus the focal thalamic stimulation.

The engine derives S from N (calc_synapse_count); here S can be set explicitly, identical
for every pair (a global parameter of the task).
"""

from __future__ import annotations

import numpy as np
import torch

from generate_chem_diffusion_video import patch_large_scale_dataframe_sync
from generate_simulation_video import patch_array_interfaces, patch_runtime_tensors

from snngine_v4.config.template import EngineConstructionConfig, SpatialNetworkConfig
from snngine_v4.construction.nn_builder import NetworkBuilder
from snngine_v4.nn.config_models.reservoir.n_type_groups import NTypeGroupConnInit, NTypeGroupConnList
from snngine_v4.nn.config_models.reservoir.nn_reservoir_config import NetworkReservoirConfig
from snngine_v4.utils.containers.mappings import Object2ObjectMap
from snngine_v4.visualization.cuda.gl_interop.gl_buffer_types import GLBufferTypes


class _MockGLBufferTensor:
    def __init__(self, tensor):
        self.tensor = tensor

    def copy_to_texture(self):
        pass

    def copy_to_buffer(self):
        pass


class _MockGLTensorDict(dict):
    def __init__(self, tensor, key=GLBufferTypes.POS_VBO.name):
        super().__init__()
        self[key] = tensor
        self.str2gl = {key: _MockGLBufferTensor(tensor)}


def build_network(device: torch.device, n_neurons: int, n_synapses: int | None = None,
                  reservoir_shape=(1.0, 1.0, 1.0), chem_shape_hwd=(32, 32, 32),
                  spike_buffer_factor: int = 40, n_delays: int | None = None):
    """
    Returns (network, element, simulator, sim_instance, sim_backend).

    n_delays (iteration 61): the delay count D instead of the engine's log-N rule; the engine derives
    the grid from D (int(D / sqrt(3)) cells per axis of a cubic reservoir), so this sets a larger grid
    at a given group size (D 16: 9 x 9 x 9, D 20: 11 x 11 x 11). None: the engine's rule.
    """
    if n_delays is None:
        return _build_network(device, n_neurons, n_synapses, reservoir_shape, chem_shape_hwd,
                              spike_buffer_factor)
    if not 2 <= int(n_delays) <= 20:
        raise ValueError(f"n_delays {n_delays} outside the engine's range 2 to 20")
    original = NetworkReservoirConfig.__dict__["_calc_delay_count"]
    NetworkReservoirConfig._calc_delay_count = staticmethod(lambda n_neurons, **_: int(n_delays))
    try:
        return _build_network(device, n_neurons, n_synapses, reservoir_shape, chem_shape_hwd,
                              spike_buffer_factor)
    finally:
        NetworkReservoirConfig._calc_delay_count = original


def _build_network(device, n_neurons, n_synapses, reservoir_shape, chem_shape_hwd, spike_buffer_factor):
    patch_array_interfaces()
    patch_runtime_tensors()
    patch_large_scale_dataframe_sync()

    dev_val = (device.index if device.type == "cuda" and device.index is not None
               else (0 if device.type == "cuda" else "cpu"))

    res_cfg = NetworkReservoirConfig()
    rx, ry, rz = (float(x) for x in reservoir_shape)
    ch, cw, cd = (int(x) for x in chem_shape_hwd)
    res_cfg.N = int(n_neurons)
    res_cfg.S = None if n_synapses is None else int(n_synapses)
    res_cfg.type_conns = NTypeGroupConnList(conns=[
        NTypeGroupConnInit(src=0, snk=1, w0=-0.44),
        NTypeGroupConnInit(src=1, snk=0, w0=0.45),
        NTypeGroupConnInit(src=1, snk=1, w0=0.47),
    ])
    res_cfg.grid.shape.data[:] = np.array([rx, ry, rz], dtype=np.float32)
    for chem_cfg in (res_cfg.chemicals.C0, res_cfg.chemicals.C1):
        chem_cfg.shape.data[:] = np.array([ch, cd, cw], dtype=np.int32)
    res_cfg.pos = np.zeros((0, 3), dtype=np.float32)
    res_cfg.model_post_init(None)
    if n_synapses is not None and int(res_cfg.S) != int(n_synapses):
        raise RuntimeError(f"requested S={n_synapses}, config has S={res_cfg.S}")

    # keep every neuron strictly inside its grid cell, so CPU sort_pos and GPU float32
    # division agree on location-group boundaries (as in the sibling builder)
    shape_arr = res_cfg.grid.shape.data.astype(np.float32)
    seg_arr = res_cfg.grid.seg.data.astype(np.float32)
    scaled = (res_cfg.pos / shape_arr) * seg_arr
    cell_idx = np.clip(np.floor(scaled), 0.0, seg_arr - 1.0)
    frac = np.clip(scaled - cell_idx, 1e-3, 1.0 - 1e-3)
    res_cfg.pos[:] = ((cell_idx + frac) / seg_arr) * shape_arr
    res_cfg.sort_pos(pos=res_cfg.pos, shape=res_cfg.grid.shape.as_tuple(),
                     grid_segmentation=res_cfg.grid.seg.as_tuple(), type_groups=res_cfg.type_groups.groups)

    config = SpatialNetworkConfig(elements=[res_cfg], device=dev_val)
    config.grid.shape.data[:] = res_cfg.grid.shape.data
    config.grid.seg.data[:] = res_cfg.grid.seg.data

    network = NetworkBuilder(container_model=EngineConstructionConfig(network=config)).add_build(
        model=config, device=device)
    element = network.get_network_element(0)
    simulator = network.simulator
    volt_plot = simulator.voltage_plot
    scatter = simulator.firings_scatter_plot

    n = element.config.N
    pos_vbo = torch.zeros((n, 14), dtype=torch.float32, device=device)
    pos_vbo[:, :3] = element.N_pos
    volt_vbo = torch.zeros((volt_plot.config.n_plots * volt_plot.config.size_x * 2,),
                           dtype=torch.float32, device=device)
    scatter_vbo = torch.zeros((scatter.config.n_plots * scatter.config.size_x * 14,),
                              dtype=torch.float32, device=device)
    gl_map = Object2ObjectMap()
    gl_map[element.config] = _MockGLTensorDict(pos_vbo)
    gl_map[volt_plot.config] = _MockGLTensorDict(volt_vbo)
    gl_map[scatter.config] = _MockGLTensorDict(scatter_vbo)
    # +2 padding on axis 0: the chemistry kernel's boundary threads read one slice past the grid
    for chem in (element.chemicals.C0, element.chemicals.C1):
        w, d, h = chem.config.shape.shape_wdh
        gl_map[chem.config] = _MockGLTensorDict(
            torch.zeros((h + 2, w, d), dtype=torch.float32, device=device).contiguous(),
            GLBufferTypes.TEXTURE_3D.name)
    network.cuda_opengl_map = gl_map

    # Spike ring buffer: the kernel rewinds its write pointer after 13 * N spikes
    # (snn_simulation.cu, reset_firing_times_ptr_threshold) while spikes of the last D steps are
    # still being read; with the default 15 * N buffer, near-global bursts at D = 13 (N = 20,000)
    # overran it (cudaErrorIllegalAddress). Simulation takes the size as a default argument only.
    from snngine_v4.nn.sim.simulation import Simulation
    Simulation.__init__.__defaults__ = (int(spike_buffer_factor),)

    sim_instance = simulator.add_simulation(0)
    if sim_instance.backend is None:
        raise RuntimeError("Simulation backend failed to construct.")
    return network, element, simulator, sim_instance, sim_instance.backend
