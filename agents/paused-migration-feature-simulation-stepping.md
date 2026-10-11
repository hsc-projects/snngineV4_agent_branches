# [PAUSED] Migration feature: simulation stepping (from SNNgine3D)

This work is paused/deactivated. It was originally embedded in SNNgine3D's
`AGENTS.md` as active task framing, which conflicted with the current
exploratory/mapping phase (see both repos' `AGENTS.md` → Workflow). Extracted
here for later reference, not for action now.

You are migrating the "simulation stepping" feature from a legacy GPU SNN
engine (SNNgine3D) into a new project. Read SNNgine3D's `AGENTS.md` first —
it defines the tensor layout, invariants, and the C++ constructor contract
(Data model / Inheritance sections).

The core loop is: allocate tensors → construct one `SnnSimulation` object
with ~45 raw pointers (see `snn_simulation.cuh` constructor) → call
`.update(b_stdp, verbose)` per timestep → optionally swap chemical buffers
→ record. Python never writes to state tensors after construction.

Key files to read (in order, paths relative to SNNgine3D repo root):

- `snngine3d/nn/utils/state_tensor.py`
- `snngine3d/nn/utils/torch_collections.py`
- `snngine3d/nn/spNN/neurons/states/neuron_flags.py`
- `snngine3d/nn/spNN/neurons/models/multi_model_state.py`
- `snngine3d/nn/spNN/neurons/states/grid_group_flags.py`
- `snngine3d/nn/spNN/neurons/neuron_representation.py`
- `snngine3d/nn/VspNN/v_neuron_representation.py`
- `snngine3d/nn/spNN/synapses/synapse_representation.py`
- `snngine3d/nn/spNN/simulation/simulation.py`
- `snngine3d/nn/VspNN/v_simulation.py`
- `snngine3d/nn/gpu_recorder.py`
- `snngine3d/nn/settings/simulation_settings.py`
- `snngine3d/nn/settings/network_settings.py`
- `snngine3d/configuration/deprecated/__init__.py`
- `snngine3d/configuration/deprecated/network/__init__.py`
- `snngine3d/configuration/deprecated/network/network_config.py`
- `snngine3d/nn/cuda_backend/src/structures/network_structures.h`
- `snngine3d/nn/cuda_backend/src/structures/network_structures.cpp`
- `snngine3d/nn/cuda_backend/src/simulation/snn_simulation.cuh`
- `snngine3d/nn/cuda_backend/src/simulation/snn_simulation.cu`

Read order for the implementing agent: `v_simulation.py` (the constructor +
update loop), `simulation.py` (tensor allocation), `neuron_representation.py`
(what N_flags/N_states/G2G_info contain), `synapse_representation.py`
(N_rep/N_delays/N_weights layout), `snn_simulation.cuh` (full struct +
constructor signature), `snn_simulation.cu` (kernel implementations).

Invariants that must be preserved: contiguous float32/int32, single CUDA
device, `last_Fired` init = −D, 15×N ring buffer for firing times/idcs, S×N
synapse layout, STDP gated by a bool flag, chemical swap is conditional.

## Execution loop findings (SNNgine3D reference vs. snngine_v4 status)

### SNNgine3D execution mechanics
- **Event loop timer**: Stepping was driven by a VisPy application timer (`Timer('auto', connect=self.update, start=False)` in `snngine3d/engine/engine.py`) running on the GUI thread.
- **Per-frame stepping**: Each timer tick (`engine.py:update` calling `v_simulation.py:update`):
  1. Ran an inner loop for `sim_updates_per_frame` (configurable, default: 1, 5, or 10):
     - Called `Simulation.update(B_STDP_ACTIVE, False)`.
     - If `Simulation.b_update_chemical_concentrations` was True, called `chemical_concentrations.c0.update()` to copy the diffused PyTorch tensor to the OpenGL 3D texture (`cpy_tnsr2tex` via `Memcpy3D`).
  2. Called `.update()` on plot scenes (`ui.SC_VOLTAGE_MULTIPLOTS`, `ui.SC_FIRING_SCATTERPLOT`).
- **Threading context**: Executed synchronously on the GUI event loop, keeping the OpenGL context (`scene.set_current()`) active without multi-threading.

### Current implementation status in snngine_v4
- **Backend wiring complete**: Tensor allocation, OpenGL VBO mapping, and backend constructor pointer passing (~45 raw pointers into `snn_simulation_gpu.SnnSimulation`) are already implemented in `Simulation._make_simulator_backend` (`snngine_v4/nn/sim/simulation.py`).
- **Stepping loop prototype**: `SNNgine.run_sim` (`snngine.py`) contains a basic stepping loop calling `sim.update(False, True)` and updating plot scenes.
- **Current gaps in snngine_v4**:
  - `run_sim` is a synchronous loop called only in commented-out manual debug code (`MainEngineWindow.test_func` in `main_window.py`). No GUI timer (`QTimer` or `vispy.app.Timer`) is currently wired in `EngineApp` or `MainEngineWindow`.
  - Chemical volume texture copying (`cpy_tnsr2tex`) is not invoked during `run_sim`.
  - Main scene redraw (`main_scene.update()`) is not invoked during `run_sim`.
