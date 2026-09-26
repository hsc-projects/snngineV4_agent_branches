# nn/

Simulation core of `snngine_v4`: spatially extended spiking neural network
models, neuron and synapse state data structures, synaptic connectivity
construction, simulation execution, CUDA/OpenGL interop plot streaming,
and pybind11/CUDA bindings. All 18 Python source files (~2,490 LOC), the
`cuda_backend/` CMake configuration, and `NDKNV/` reference note were read
for this write-up.

Per workflow guidelines, CUDA kernel internals are not opened; the CUDA
backend is treated as accelerated compute understood by its intent as
inferred from surrounding Python and configuration boundaries.

## Files and classes

### High-level orchestration

- **`spnn.py`**
  - `SpatialNetwork(EngineElement)` — root network element coordinating
    construction. Registers class maps for `FiniteGridConfig`,
    `NetworkReservoirConfig`, `NeuronStateModel`, and `SimulatorOptions`.
    Builds reservoirs, the finite grid, and simulator via `self.add_build()`.
    Triggers `elt.fill_tensors()` on each `NetworkReservoir`.
    Contains a dangling assignment `p = self.get_network_element(0).neuron_states.parent_element()`
    where `p` is never read — tagged `legacy-dead`.

- **`spnn_reservoir.py`**
  - `NetworkReservoir(EngineElement)` — spatial reservoir element
    representing a 3D block of $N$ neurons with $S$ synapses per neuron,
    discretized into $G$ location groups across $D$ delay steps.
    Declares `BUILDER_OBJECT_CLASS_MAP` for `SynapseModel` &rarr; `Synapses`,
    `SynapseCountTensors` &rarr; `SynCounts`, and `ChemicalConcentrationModel`
    &rarr; `ChemicalConcentrationVolume`.
    Orchestrates memory allocations for group-to-group metrics
    (`G_neuron_typed_ccount`, `L_Group_delay_counts`, `G2G_distance`,
    `G2G_delay_distance`, `G_rep`) and invokes CUDA construction routines
    (`snn_construction_gpu.fill_G_neuron_count_per_delay`).
    Provides `pos_vbo` (`GLBufferTensor`), exposing the zero-copy OpenGL
    buffer mapping for neuron positions. Tagged `config-driven` +
    `hand-written-edge`.

### Neuron and synapse representations

- **`neuron_states.py`**
  - `NeuronState(EngineElement)` — runtime container for neuron state.
    Holds `N_flags` (`TensorDataFrame` of types, groups, models, selection)
    and `N_props` (`TensorDataFrame` of dynamic variables and parameters).
    Calls `apply_preset()` to initialize Izhikevich parameters from the
    configured preset, and delegates to CUDA construction kernel
    `snn_construction_gpu.fill_N_flags_group_id_and_G_neuron_count_per_type`.
    Tagged `config-driven` + `cuda-adjacent`.

- **`synapses.py`**
  - `SynCounts(EngineElement)` — calculates cumulative expected synapse
    distributions across source types, sink types, and delays. Invokes
    `snn_construction_gpu.fill_G_exp_ccsyn_per_src_type_and_delay`.
    Contains extensive Python-side iterative target-distribution shaping
    (`output_correction`), validation routines (`validate_sink_counts`),
    and autapse masking (`potential_autapse_mask`). Tagged `cuda-adjacent`.
  - `Synapses(EngineElement)` — runtime container for synaptic connectivity
    tensors (`N_rep`, `N_delays`, `N_weights`, and pre-synaptic reverse
    lookup tables). Calls `counts.fill_tensors()`, then runs the full
    representation generation sequence via `RepBackend`
    (`snn_construction_gpu.SnnRepresentation`), followed by CUDA sorting,
    reindexing (`snn_construction_gpu.reindex_N_rep`), transpositions,
    and type connection weight initializations (`type_conns.apply_init_weights`).
    Tagged `hand-written-edge` + `cuda-adjacent`.

### Simulation and GPU plot interop (`sim/`)

- **`sim/simulator.py`**
  - `Simulator(EngineElement)` — manages runtime simulation instances
    mapped per network element (`self.simulations: Object2ObjectMap`).
    Constructs `CudaBackendPlotTensors` (`self.plots`) and `Simulation`
    instances. Holds cached accessors `voltage_plot` and `firings_scatter_plot`.
    Tagged `generic-machinery`.

- **`sim/simulation.py`**
  - `SimulationModel(EngineElementConfig)` — config model stub for simulation
    instances (commented-out array reset logic). Tagged `legacy-dead`.
  - `Simulation(EngineElement)` — primary simulation orchestrator. Allocates
    spike recording buffers (`Fired`, `last_Fired`, `Firing_times`,
    `Firing_idcs`, `Firing_counts`, `G_firing_count_hist`).
    In `_make_simulator_backend()`, acts as a major `hand-written-edge`:
    extracts raw device memory pointers (`.data_ptr()`) from neuron states,
    synapses, chemicals (`chemicals.C0`), and plot VBO buffers, passing them
    directly into the compiled C++/CUDA backend `snn_simulation_gpu.SnnSimulation`.

- **`sim/sim_parameters.py`**
  - `EngineMultiLinePlotConfig`, `EngineMultiScatterPlotConfig`: configuration
    mixins bridging visualization configs to `EngineElementConfig`.
  - `CudaBackendPlotConfig(EngineElementConfig)`: settings for three plot
    targets — `voltage_plot` (100 samples), `firings_scatter_plot` (100 samples),
    and `group_firings_plot` (200 samples).
  - `SimulatorOptions(EngineElementConfig)`: simulation time parameter `T = 1000`
    and child plot configuration. Tagged `config-driven`.

- **`sim/gpu_plots.py`**
  - `PlotElement(EngineElement)` — wraps GPU plotting buffers. Exposes
    `pos_vbo_gl` (`GLBufferTensor`) and `pos_vbo` (`torch.Tensor`) backed by
    VisPy OpenGL VBO allocations. Enables zero-copy simulation-to-plot
    rendering without host transfers.
  - `CudaBackendPlotTensors(EngineElement)` — container mapping plot configs
    to `PlotElement` instances. Tagged `hand-written-edge`.

### Configuration models (`config_models/`)

- **`config_models/spnn_config.py`**
  - `SpatialNetworkConfig(EngineElementConfig)` — top-level settings container:
    `device`, `grid: FiniteGridConfig`, `simulator: SimulatorOptions`,
    `elements: list[NetworkReservoirConfig | EngineElementConfig]`.
    Includes a debug field `bools: list[None | bool] | None = [None, True, False, True]`
    — tagged `legacy-dead`.

- **`config_models/reservoir/nn_reservoir_config.py`**
  - `PosGenerationMode(IntEnum)` (`CUSTOM=0`, `RND_UNIFORM=1`).
  - `NetworkReservoirConfig(EngineElementConfig3D)` — foundational reservoir
    specification: neuron count $N$ (default 200), synapse count $S$,
    delay count $D$, group count $G$.
    Implements delay calculation heuristic `_calc_delay_count()` ($N \to D \le 20$),
    synapse count heuristic `calc_synapse_count()` ($\sim \sqrt{N} + 50$, capped at $N/4$),
    grid segmentation generator `generate_segmentation()`, uniform random 3D position
    generator `generate_pos()`, and spatial sorting `sort_pos()`.
    Post-init validates and resets all child array dimensions (`reset_arrays()`).
    Tagged `config-driven`.

- **`config_models/reservoir/n_type_groups.py`**
  - `NeuronType(IntEnum)` (`INHIBITORY=1`, `EXCITATORY=2`).
  - `NTypeGroupGenerationMode`, `WeightGenerationMode`, `TypeConnGenerationMode`.
  - `NeuronTypeGroup`, `NTypeGroupList` — defines neuron type partitions
    (default 1:4 inhibitory-to-excitatory ratio) and partitions index ranges
    via `make_counts()`.
  - `NTypeGroupConnInit`, `NTypeGroupConn`, `NTypeGroupConnList` — defines
    directed synaptic projection blocks between type groups (e.g. Inh &rarr; Exc,
    Exc &rarr; Inh, Exc &rarr; Exc) with initial weights ($w_0$) and synapse
    allocation counts. Tagged `config-driven`.

- **`config_models/reservoir/lgroup_states.py`**
  - Schema definitions for location-group tabular data: `LGroupFlagsColumns`/`LGroupFlags`,
    `LGroupPropLabels`/`LGroupProps`, `LGNeuronCounts` (group neuron counts per
    type and delay), `LG2LGFlagLabels`/`LG2LGFlags`, and `LG2LGPropLabels`/`LG2LGProp`.
    Tagged `config-driven`.

- **`config_models/neurons/`**
  - `neuron_state.py` & `neuron_state_elements.py`: `NeuronStateModel`,
    `NeuronFlagsColumns`/`NeuronFlags`, `NPropLabels`/`NeuronProperties`.
    Explicitly structures the 2-variable Izhikevich parameterization:
    state variables $v$ (membrane potential), $u$ (recovery variable),
    parameters $a, b, c, d$, input currents $i, i_{prev}$, and $v_{prev}$.
  - `synapse_model.py`: `SynapseCountTensors`, `SynapseModel`, defining
    dataframes for delays, representation connections (`N_rep`), weights
    (`N_weights`), pre-synaptic reverse indices, and group connection probabilities.
  - `presets/preset_base.py` & `presets/izhikevich_presets.py`: `PresetsContainer`,
    `PresetParameter`, and `IzhikevichPresets`. Encodes 28 distinct electrophysiological
    firing regimes (Regular Spiking `RS`, Intrinsically Bursting `IB`, Chattering `CH`,
    Fast Spiking `FS`, Thalamo-Cortical `TC`, etc.) as documented by Eugene Izhikevich (2003/2004).
    `default_init()` applies randomized parameter spreads to inhibitory vs. excitatory
    populations. Tagged `config-driven`.

### CUDA backend bindings (`cuda_backend/`) and algorithmic sources (`NDKNV/`)

- **`cuda_backend/`**
  - `CMakeLists.txt` builds three shared pybind11 libraries:
    1. `snn_utils` (`utils_bindings.cu`, `network_structures.cpp`, `curand_states.cu`, `launch_parameters.cu`).
    2. `snn_construction_gpu` (`snn_construction_bindings.cu`, `snn_representation.cu`, `connector.cu`).
    3. `snn_simulation_gpu` (`snn_simulation_bindings.cu`, `snn_simulation.cu`).
  - Target prefix/suffix settings export `.so` (Linux) / `.pyd` (Windows) modules
    imported via `snngine_v4.nn.cuda_backend`. Tagged `cuda-adjacent`.

- **`NDKNV/`**
  - `README.md` documents algorithmic lineage: Nageswaran et al.,
    *"Efficient simulation of large-scale spiking Neural networks using cuda Graphics processors"*.

## Relationships within the subpackage

`SpatialNetworkConfig` aggregates `NetworkReservoirConfig`, which drives
the sizing of `NeuronStateModel`, `SynapseModel`, and location-group tables.
At runtime, `SpatialNetwork` instantiates `NetworkReservoir`, which constructs
child elements `NeuronState` and `Synapses`.

Construction flows strictly in phases:
1. Spatial positions and location-group bounds are computed (`NetworkReservoirConfig`).
2. Neuron flags and type partitions are loaded on GPU (`NeuronState`).
3. Group distance and delay distributions are computed (`NetworkReservoir`).
4. Synapse target distributions are solved and corrected (`SynCounts`).
5. Connectivity indices and weights are generated on GPU (`Synapses`).
6. `SpatialNetwork.configure_simulator()` binds runtime tensors and plot VBOs
   into `snn_simulation_gpu.SnnSimulation` (`Simulation`).

## Generic vs. particular

- **Generic**: `SpatialNetwork`, `NetworkReservoir`, `NeuronState`, `Synapses`,
  `Simulator`, and `Simulation` inherit `EngineElement`, participating in the
  recursive builder class-mapping pattern documented in `config-build-pattern.md`.
- **Particular**:
  - Hard-coded neuron model: dynamic state fields (`NPropLabels`) and presets
    are strictly structured around the 4-parameter Izhikevich model ($a, b, c, d, v, u$).
  - Hard-coded chemical coupling: `Simulation._make_simulator_backend()` explicitly
    binds `chemicals.C0`, assuming exactly one chemical concentration field.
  - CUDA / pybind11 memory interface: `Simulation` and `Synapses` manually extract
    `.data_ptr()` raw GPU pointers matching the exact argument signature of C++ kernels.

## Cross-links

- `agents/mapping/vertical-trace.md` — steps 3–6 of the traced execution path
  traverse `SpatialNetwork`, `NetworkReservoir`, and `Simulation._make_simulator_backend()`.
- `agents/mapping/chemistry.md` — `NetworkReservoir` instantiates `Chemicals`;
  `Simulation` passes `C0` diffusion buffers into CUDA simulation kernels.
- `agents/mapping/geometry.md` — `FiniteGrid` determines reservoir spatial bounds,
  group coordinates, and distance calculations.
- `agents/mapping/construction.md` — `SpatialNetwork` and `NetworkReservoir` are
  concrete consumers of the `EngineElement` tree and class mapping.
- `agents/feature-todos.md` — relates to the backlog item for adding an Integrate-and-Fire
  (IF/LIF) model alongside the Izhikevich model.

## Open questions

Indexed centrally in [`README.md` → Consolidated open questions](README.md#nn):

- [SOLVED] `SpatialNetwork.__init__` line 60 has an unused assignment `p = self.get_network_element(0).neuron_states.parent_element()`.
  Not confirmed whether this was a debug check or intended for a validation pass.
  - **Resolution**: Confirmed debug / smoke check. In `snngine_v4/nn/spnn.py:60`,
    `p = self.get_network_element(0).neuron_states.parent_element()` exercises the tree navigation
    path from child `NeuronStates` back to the enclosing `NetworkReservoir` via `node_tree`
    (`snngine_v4/construction/engine_element.py:234-243`). The returned instance is assigned to local
    variable `p` and never used. It verifies parent lookup integrity at construction time.
    See [`README.md#nn`](README.md#nn).
- [SOLVED] `SpatialNetworkConfig.bools` defaults to `[None, True, False, True]`. Not confirmed
  whether any external tool reads this or if it is purely a test artifact.
  - **Resolution**: Confirmed XML round-trip test fixture artifact. Introduced in commit `78bba4e7`
    (`snngine_v4/nn/config_models/spnn_config.py:29`), this field tests that `XMLConverter` and
    `XMLSettingsModel` correctly serialize and deserialize heterogeneous nullable boolean lists
    across `.snngine/template.xml:578-583`. It is never read by simulation, visualization, or GUI code.
    See [`README.md#nn`](README.md#nn).
- [SOLVED] In `Simulation._make_simulator_backend`, chemical bindings are hardcoded to
  `chemicals.C0`. If multiple chemicals (`C0`, `C1`) are configured in
  `DefaultChemicals`, `C1` is currently ignored by the simulation loop.
  - **Resolution**: Confirmed single-chemical architectural limit. The CUDA backend constructor
    (`snngine_v4/nn/cuda_backend/src/simulation/snn_simulation_bindings.cu:65,279`) and diffusion kernel
    (`snn_simulation.cu:205,278`) accept only one set of 3D diffusion pointers (`C_old`, `C_new`,
    `C_source`). Consequently, `Simulation._make_simulator_backend` (`snngine_v4/nn/sim/simulation.py:151-160`)
    exclusively binds `chemicals.C0`. Secondary chemical configs (such as `C1`) cannot be simulated
    without extending the CUDA kernel signature.
    See [`README.md#nn`](README.md#nn).
- [SOLVED] `SynCounts.fill_tensors` contains complex iterative target corrections
  (`output_correction`) and autapse checks in Python. It is not confirmed
  whether this logic was migrated from V2 host code or added as a post-hoc
  stability fix for specific network dimensions.
  - **Resolution**: Confirmed algorithmic discretization and autapse-avoidance logic migrated from
    NDKNV lineage (Nageswaran et al. 2009). Synaptic connectivity requires exact integer partition of
    synaptic capacity $S$ across delay steps $D$ and cell types. In `snngine_v4/nn/synapses.py:127-156`,
    `output_correction` iteratively redistributes rounding errors across adjacent delay rows and adjusts
    for autapse masking (`autapse_mask`), ensuring no slots are under- or over-allocated before GPU
    representation indexing (`assert len(self.N_rep[self.N_rep == -1]) == 0`).
    See [`README.md#nn`](README.md#nn).
