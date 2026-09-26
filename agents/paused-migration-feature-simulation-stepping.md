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
