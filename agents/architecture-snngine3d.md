# Architecture — SNNgine3D (old repo)

**Caveat:** this mapping (Architecture section below) was produced by an
Explore subagent during this session's initial `/init` pass, likely a
smaller/faster model than the one maintaining these docs. It may be less
accurate than newer content in `agents/`. The Data model and Inheritance
sections below predate this session entirely (pre-existing in the repo's
own `AGENTS.md`) and haven't been independently re-verified either.

## Architecture

- `cli.py` — Typer CLI, single `run` command, entry point.
- `engine/` — application/runtime layer (`engine.py`, `ui.py`, plus `base`, `devices`, `elements`, `experiment_window`, `interfaces`, `settings_tree`): the PyQt-driven app shell wiring simulation + rendering + UI together.
- `nn/` — the neural-network/simulation core:
  - `spNN/` — spiking NN representation (neurons/synapses/simulation), non-visualized.
  - `VspNN/` — Visualized spNN variants (e.g. `v_simulation.py`, `v_neuron_representation.py`), MRO-mixing `spNN` classes with graphics.
  - `cuda_backend/` — the pybind11/CUDA C++ extension (kernels, structures) — see Data model below.
  - `gpu_recorder.py`, `graph_structures/`, `grid/`, `plotting/`, `settings/`, `torch_models/`, `utils/` (`state_tensor.py`, `torch_collections.py` — base classes for the Inheritance section below).
- `graphics/` — Vispy/OpenGL rendering glue: `transformation`, `vispy_torch_interop` (bridges PyTorch tensors to Vispy GPU buffers), `vispy_torch_visuals`.
- `geometry/` — geometric primitives/math: `abstract`, `euclidian`, `grid`, `volume`.
- `configuration/` — settings/config models, including a `deprecated/` subpackage (old `NetworkConfig`-style config, still referenced by the default CLI arg `configuration.deprecated.DefaultEngineConfig`).
- `utils/` — general helpers (`array_utils`, `colors`, `enum_utils`, `typed_collections`, `xml_handler`, `tree_node`, `signals`, `auto_naming_dataclass`).

Relationship: `engine` is the top-level app (PyQt UI + Vispy render loop) that instantiates `nn.VspNN` objects, which combine `nn.spNN` simulation/data classes with `graphics` visualization mixins; the actual per-step numeric simulation runs in `nn/cuda_backend` (C++/CUDA), invoked via raw pointers from the PyTorch tensors allocated in `nn/spNN`. `geometry` and `configuration` support both layers.

## Data model

- **Neuron state (`N_states`):** 10×N float32 tensor. Rows: `pt`(0), `u`(1), `v`(2), `a`(3), `b`(4), `c`(5), `d`(6), `i`(7, input current, zeroed each step), `i_stored`(8), `v_prev`(9).
- **Neuron flags (`N_flags`):** 6-row int32 tensor — `b_sensory_input`(0), `type`(1: 1=INH, 2=EXC), `group`(2), `model`(3), `selected`(4), `selected_tmp`(5).
- **Synapses:** `N_rep` (S×N int32, post-synaptic index per pre-synaptic slot), `N_delays` (S×N int32), `N_weights` (S×N float32). S = max synapses per neuron.
- **Firing bookkeeping:** `Fired` (N, f32), `last_Fired` (N, i32, init −D), `Firing_times`/`Firing_idcs` (15×N ring buffers), `Firing_counts` (1×T*2, i32).
- **Group state:** `G_flags`, `G_props`, `G_group_delay_counts` (G×(D+1) i32 cumulative counts per delay).
- **STDP/group info:** `G_stdp_config0/1` (G×G i32), `G_avg_weight_inh/exc` (G×G f32), `G_syn_count_inh/exc` (G×G i32) — passed as raw pointers.
- **Chemicals:** `C_old`, `C_new`, `C_source` (grid W×H×D float32), `chem_k_val`, `chem_depreciation`.
- **WTA:** `L_winner_take_all_map` ((max_wta_size+1)×max_n_wta_layers, i32).

## Inheritance

    TorchCollection (FrozenPostInitCaller)
     └── Torch32BitCollection  (int32 / float32 defaults, izeros/fzeros, TensorDict, @loaded)
          ├── NeuronRepresentation
          │    └── VisualizedNeuronRepresentation  (+ TorchVisual32BitCollection via MRO)
          ├── SynapseRepresentation
          ├── NetworkSimulationGPU
          │    └── VisualizedNetworkSimulationGPU  (+ TorchVisual32BitCollection via MRO)
          └── GPURecorder  (TorchVisual32BitCollection)

    StateTensor  (row-indexed 2-D tensor, .rows, .data_ptr(), .cross_slice())
     ├── NeuronFlags        (6 rows: b_sensory_input, type, group, model, selected, selected_tmp)
     ├── MultiModelNeuronStateTensor  (10 rows: pt, u, v, a, b, c, d, i, i_stored, v_prev)
     └── G2GInfoArrays      (G_stdp_config0/1, G_delay_distance, G_rep, G_avg_weight_inh/exc, G_syn_count_inh/exc)

    NeuronStateTensors  (frozen dataclass: N_flags, N_states, G_props, G_flags)
     └── consumed by GPURecorder.record() and VisualizedNeuronRepresentation.state_tensors()
