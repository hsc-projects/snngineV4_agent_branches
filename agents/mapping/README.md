# agents/mapping/ index

Per-topic write-ups produced by the horizontal mapping pass (one file per
`snngine_v4/` subpackage, plus the earlier vertical trace and the
config/build architecture note). Suggested reading order:

1. **`vertical-trace.md`** — one concrete construction/wiring path through
   the whole engine, entry point to CUDA/OpenGL interop; also contains the
   `N_pos` zero-copy CUDA↔VisPy case study. Not full coverage of the
   codebase, one path only.
2. **`config-build-pattern.md`** — the config→template→build architecture:
   the generic Pydantic builder machinery, and the three confirmed
   hand-written edges where it meets a fixed external API (CUDA/pybind11,
   VisPy visual construction, field-ownership between base and visual
   configs).
3. **`chemistry.md`** — the `chemistry/` subpackage: volumetric "chemical"
   diffusion fields, their config/build split, and the 3D-texture
   CUDA/OpenGL interop boundary (contrasted with the zero-copy path in
   `vertical-trace.md`).
4. **`geometry.md`** — the `geometry/` subpackage: spatial parameter
   vocabulary, the finite-grid config/build split, and its VisPy-rendering
   workaround; also notes some found dead code and internal
   inconsistencies (direction-ordering mismatch, an unimported-`torch`
   branch) not yet confirmed as bugs.
5. **`construction.md`** — the `construction/` subpackage: the
   `EngineElement`/`NetworkBuilder` generic builder machinery,
   per-class-grounded against `config-build-pattern.md`'s conceptual
   description; notes a class-level shared-mutable-state pattern and two
   separate ownership-enforcement mechanisms as open questions.
6. **`config.md`** — the `config/` subpackage (plus the root-level
   `snngine_config.py`): engine-level pydantic settings (`app`, `devices`,
   `scenes`, `template`/`built`) assembled into `EngineConfig`; notes a
   likely incomplete field rename and an unconfirmed-intentional default
   network topology as open questions.
7. **`nn.md`** — the `nn/` subpackage: simulation core, spiking neural
   network topology, neuron state representations, synaptic connectivity
   matrices, simulation loop, CUDA backend interop, and live VisPy GPU
   plotting; notes hardcoded single-chemical coupling and Python-side
   synaptic distribution adjustments as open questions.
8. **`visualization.md`** — the `visualization/` subpackage: VisPy-based
   scene canvas management, visual construction machinery, custom OpenGL
   geometry and volume shaders, live GPU plotting schemas, and the
   zero-copy CUDA/OpenGL interop bridge (along with the 3D texture copy
   fallback).
9. **`utils.md`** — the `utils/` subpackage: cross-cutting foundation
   providing the generic object builder engine, type-enforced containers,
   dual-backed CPU/GPU tensor dataframes, Pydantic settings base models
   with XML/HDF5 serialization, and array validation interfaces.
10. **`gui.md`** — the `gui/` subpackage: PySide6 application shell,
    pyqtgraph parameter tree docking framework, reactive connector layer
    (`CudaVispyConnector`, `VispyConnector`, `TensorConnector`), custom
    interactive parameter widgets, and Behringer X-Touch Mini hardware
    MIDI controller integration.

All planned subpackages in the horizontal mapping pass are now written.

`architecture-snngine_v4.md` is being migrated into this directory
subpackage by subpackage (each migrated bullet is replaced there with a
pointer to its new file here); see that file's own remaining content for
what hasn't been migrated yet.

## Consolidated open questions

Open questions, suspected bugs, unconfirmed defaults, and migration relics
identified across the horizontal mapping pass.

### Resolution protocol and instructions
- **Status labels**:
  - `[OPEN]`: The item is identified but remains unresolved or
    unverified.
  - `[SOLVED]`: The question has been answered, verified against the
    codebase, or resolved with technical findings.
- **Answering guidelines**:
  - Detailed answers, technical findings, and verifiable source citations
    are documented directly in the respective subpackage mapping file
    (`agents/mapping/<subpackage>.md` under `## Open questions`).
  - This central index tracks the status (`[OPEN]` vs. `[SOLVED]`) and
    provides a concise summary linking to the full resolution in the
    subfile.
  - Every answer must cite exact code sources (verifiable file paths, line
    ranges, and symbols).
  - Upon resolving an item, update its status label from `[OPEN]` to
    `[SOLVED]` in both the subfile and this central index.
  - Maintain bidirectional cross-references between this central index
    and each subpackage document.

### [`chemistry/`](chemistry.md#open-questions)
- [SOLVED] **Slot mismatch between config and runtime**
  ([`chemistry.md`](chemistry.md#open-questions)): `Chemicals`
  (`snngine_v4/chemistry/chem_volume.py:100-102`) declares only
  `C0: ChemicalConcentrationVolume`, whereas its configuration
  counterpart `DefaultChemicals`
  (`snngine_v4/chemistry/chem_models.py:27-31`) declares both `C0` and
  `C1`.
  - **Resolution** (detailed in
    [`chemistry.md#open-questions`](chemistry.md#open-questions)): `C1` is
    an unplumbed configuration leftover. Both the visual builder
    (`snngine.py:159-172`) and the CUDA simulation backend
    (`simulation.py:151-160`) only accept `C0`. `Chemicals` accurately
    reflects this single-chemical limit.
- [SOLVED] **Unread model field**
  ([`chemistry.md`](chemistry.md#open-questions)): `depreciation`
  (`ChemicalConcentrationModel` in
  `snngine_v4/chemistry/chem_models.py:18`) is defined with default
  `0.0`, but has no reader within `chemistry/` (it is passed as a scalar
  into the CUDA backend from `Simulation`).
  - **Resolution** (detailed in
    [`chemistry.md#open-questions`](chemistry.md#open-questions)):
    `depreciation` is consumed by the CUDA backend via
    `Simulation._make_simulator_backend` (`nn/sim/simulation.py:159`). In
    the CUDA diffusion kernel (`snn_simulation.cu:205,278`), it represents
    the per-timestep linear clearance/decay rate of chemical
    concentration. It is live in simulation and XML presets
    (`template.xml:560`).
- [SOLVED] **Synthetic test dataset enabled by default**
  ([`chemistry.md`](chemistry.md#open-questions)): `b_test_init` defaults
  to `True` on `ChemicalConcentrationModel`
  (`snngine_v4/chemistry/chem_models.py:20`), causing
  `ChemicalConcentrationVolume.__init__`
  (`snngine_v4/chemistry/chem_volume.py:30-33`) to load a bundled
  medical CT scan (`vispy.io.load_data_file('volume/stent.npz')`) into
  GPU memory on startup.
- [SOLVED] **Unfinished per-chemical naming**
  ([`chemistry.md`](chemistry.md#open-questions)): Commented-out `name`
  attribute and `model_post_init` in
  `snngine_v4/chemistry/chem_models.py:14,32-35` suggest `'C0'`/`'C1'`
  string labeling was planned but abandoned or unfinished.
  - **Resolution** (detailed in
    [`chemistry.md#open-questions`](chemistry.md#open-questions)):
    Redundant instance-level `name` fields were deliberately abandoned in
    favor of container attribute keys (`'C0'`, `'C1'`). The GUI
    `ParameterBuilder`
    (`gui/parameter_trees/parameter_builder/parameter_builder.py:199,204`)
    and XML serialization (`.snngine/template.xml:550-575`) already use
    container keys; adding explicit `name` fields generated redundant
    editable rows in parameter trees. Parallel to commented camera names
    in `vispy_camera_configs.py:31`.

### [`geometry/`](geometry.md#open-questions)
- [SOLVED] **Malformed exception call**
  ([`geometry.md`](geometry.md#open-questions)): `Shape3Di32.model_post_init`
  (`snngine_v4/geometry/spatial_pars.py:134-138`) invokes `raise
  ValidationError(...)` with a single string, which may raise a
  `TypeError` due to Pydantic v2's multi-argument `ValidationError`
  constructor signature.
  - **Resolution** (detailed in
    [`geometry.md#open-questions`](geometry.md#open-questions)): Verified
    empirically. In Pydantic v2, `ValidationError` requires `title` and
    `line_errors`; passing a single string raises `TypeError:
    ValidationError.__new__() missing 1 required positional argument:
    'line_errors'`. Custom validators should raise standard `ValueError`.
- [SOLVED] **Unimported module reference**
  ([`geometry.md`](geometry.md#open-questions)): `grid_mask_maker.extend_mask`
  (`snngine_v4/geometry/grid/grid_mask_maker.py:37-38`) branches on
  `isinstance(data, torch.Tensor)` but does not import `torch`
  (`snngine_v4/geometry/grid/grid_mask_maker.py:5`), risking a `NameError`
  if invoked with a tensor.
  - **Resolution** (detailed in
    [`geometry.md#open-questions`](geometry.md#open-questions)): Verified
    latent bug and SNNgine3D migration relic. `# import torch` was
    commented out at line 5; passing a torch tensor immediately fails
    with `NameError: name 'torch' is not defined`. Its only torch-based
    downstream caller is the currently uncalled `FiniteGrid.get_hull_mask`
    (`finite_grid.py:92-106`).
- [SOLVED] **Direction ordering discrepancy**
  ([`geometry.md`](geometry.md#open-questions)): `GridDirectionsObject.coord`
  (`snngine_v4/geometry/grid/finite_grid_elements.py:12-19`) orders axes
  with X and Z swapped relative to `AxDir3D`
  (`snngine_v4/geometry/spatial_pars.py:36-43`).
  - **Resolution** (detailed in
    [`geometry.md#open-questions`](geometry.md#open-questions)): Verified
    as dead code. Neither `GridDirectionsObject.coord` nor `self.coord` is
    ever accessed across the codebase. Subclass `GridStep` completely
    overrides buffer ordering to align with `AxDir3D` and
    `GridDirectionsObject.__getitem__`.
- [SOLVED] **Unconsumed spatial definitions**
  ([`geometry.md`](geometry.md#open-questions)): `Directions3DBoolPars`
  (`snngine_v4/geometry/spatial_pars.py:62-68`) and `Pos2DVBO`/`Pos3DVBO`
  (`snngine_v4/geometry/spatial_pars.py:188-198`) are defined in
  `geometry/` but only consumed downstream in `visualization/` and `nn/`.
  - **Resolution** (detailed in
    [`geometry.md#open-questions`](geometry.md#open-questions)): Not dead
    leftovers, but canonical cross-subpackage spatial contracts.
    `Directions3DBoolPars` is consumed in `boxes.py:30` and
    `visual_builder.py:443`; `Pos2DVBO`/`Pos3DVBO` are consumed across
    `reservoir/nn_reservoir_config.py:116`, `markers.py:34`,
    `lines.py:36`, `multi_line_plot.py:65`, and GUI
    `options_builder.py:173`.

### [`construction/`](construction.md#open-questions)
- [SOLVED] **Class-level shared mutable state**
  ([`construction.md`](construction.md#open-questions)):
  `update_builder_class_attributes`
  (`snngine_v4/construction/engine_element.py:264-273`) mutates `ClassVar`
  dictionaries in place via `.update()`, causing builder map extensions
  in one child instance to pollute all instances of that subclass across
  the application.
  - **Resolution** (detailed in
    [`construction.md#open-questions`](construction.md#open-questions)):
    Verified architectural tension between `@classmethod`-based builders
    (`ModelObjectBuilder.cls_build_container`) and instance hierarchy.
    In-place mutation of class attributes causes builder extensions to
    leak across sibling instances of the same class under different
    parents.
- [SOLVED] **Dual ownership enforcement**
  ([`construction.md`](construction.md#open-questions)):
  `EngineElement.__setattr__`
  (`snngine_v4/construction/engine_element.py:156-168`) runtime permission
  checks overlap conceptually with `SHARED_RUNTIME_FIELDS` in
  `snngine_v4/gui/parameter_trees/connectors/object2object_links.py:10-24`.
  - **Resolution** (detailed in
    [`construction.md#open-questions`](construction.md#open-questions)):
    Guard distinct layers: `EngineElement.__setattr__` enforces declarative
    config consistency (forbids attaching unconfigured tensor state),
    while `SHARED_RUNTIME_FIELDS` (`object2object_links.py:266-272`)
    prevents GUI bindings from replacing shared GPU/VBO buffer identities.
- [SOLVED] **Lazy parent element lookup**
  ([`construction.md`](construction.md#open-questions)):
  `EngineElement.parent_element()`
  (`snngine_v4/construction/engine_element.py:234-243`) retrieves parents
  dynamically from `node_tree.parent(self.config)` rather than
  preserving the explicit reference supplied to `__init__`.
  - **Resolution** (detailed in
    [`construction.md#open-questions`](construction.md#open-questions)):
    Confirmed by design to enforce the Pydantic configuration tree
    (`node_tree: EngineNodes`) as the canonical source of truth for
    runtime element hierarchy. The `__init__` argument is used only
    transiently to seed builder maps.
- [SOLVED] **Relic mappings**
  ([`construction.md`](construction.md#open-questions)): `nn_builder.py`
  (`snngine_v4/construction/nn_builder.py:26`) contains a commented-out
  `FiniteGridConfig: FiniteGrid` mapping, reflecting shifting grid
  ownership.
  - **Resolution** (detailed in
    [`construction.md#open-questions`](construction.md#open-questions)):
    Confirmed relocation: `FiniteGridConfig` was moved into
    `SpatialNetwork.BUILDER_OBJECT_CLASS_MAP` (`snngine_v4/nn/spnn.py:34`)
    when grid ownership was nested under `SpatialNetworkConfig.grid`,
    rendering the top-level builder mapping redundant.

### [`config/`](config.md#open-questions)
- [SOLVED] **Asymmetric device defaults**
  ([`config.md`](config.md#open-questions)):
  `DeviceSettings.cuda: CudaSettings`
  (`snngine_v4/config/devices.py:25`) lacks a default, whereas
  `opengl: OpenGLSettings` (`snngine_v4/config/devices.py:24`) defaults to
  `OpenGLSettings()`.
  - **Resolution** (detailed in
    [`config.md#open-questions`](config.md#open-questions)): Syntactically
    asymmetric but functionally equivalent: Pydantic v2 automatically
    constructs submodels with all-default fields
    (`CudaSettings.b_require_pycuda: bool = False`) when omitted,
    instantiating `DeviceSettings()` cleanly with defaults for both
    devices.
- [SOLVED] **Missing explicit scene camera**
  ([`config.md`](config.md#open-questions)): `SceneSettings.main`
  (`snngine_v4/config/scenes.py:15-21`) specifies no camera parameters,
  while multiplot scenes explicitly configure `PanZoomCameraParameters`
  (`snngine_v4/config/scenes.py:27`).
  - **Resolution** (detailed in
    [`config.md#open-questions`](config.md#open-questions)): Confirmed by
    design: `VispyViewBoxConfig.camera` (`vispy_canvas_config.py:53-54`)
    defaults via `default_factory` to 3D `TurnTableCameraParameters()`.
    `main` relies on this default 3D camera for the network volume, while
    2D multiplot scenes explicitly override it with
    `PanZoomCameraParameters()`.
- [SOLVED] **Single-reservoir default**
  ([`config.md`](config.md#open-questions)): `snngine_config.py`
  (`snngine_v4/snngine_config.py:45-53`) defaults `template` to a single
  `NetworkReservoirConfig` on device 1, unconfirmed whether intended as
  shipped topology or development leftover.
  - **Resolution** (detailed in
    [`config.md#open-questions`](config.md#open-questions)): Confirmed
    canonical minimal topology: mirrors shipped XML preset
    `.snngine/template.xml:4,116` with a single 1000-neuron reservoir on
    dedicated CUDA `device=1`.
- [SOLVED] **Incomplete rename**
  ([`config.md`](config.md#open-questions)): Commented-out `Slots.CONSTR`
  alongside `Slots.SCENES` in `_xml_file_paths`
  (`snngine_v4/snngine_config.py:73`) indicates incomplete migration from
  `CONSTR` to `TEMPLATE`.
  - **Resolution** (detailed in
    [`config.md#open-questions`](config.md#open-questions)): Confirmed
    legacy rename leftover: field was renamed from `construction`
    (`Slots.CONSTR`) to `template` (`Slots.TEMPLATE`) in commit
    `14520fee67`. Global search confirms no other active occurrences of
    `CONSTR` remain.

### [`nn/`](nn.md#open-questions)
- [SOLVED] **Dead assignment in network constructor**
  ([`nn.md`](nn.md#open-questions)): `SpatialNetwork.__init__`
  (`snngine_v4/nn/spnn.py:60`) assigns
  `p = self.get_network_element(0).neuron_states.parent_element()`, but
  `p` is never used.
  - **Resolution** (detailed in
    [`nn.md#open-questions`](nn.md#open-questions)): Confirmed debug /
    smoke check verifying that `parent_element()` resolves from child
    `NeuronStates` up to the parent `NetworkReservoir` via `node_tree`
    without raising errors during construction.
- [SOLVED] **Leftover debug configuration field**
  ([`nn.md`](nn.md#open-questions)): `SpatialNetworkConfig.bools`
  (`snngine_v4/nn/config_models/spnn_config.py:29`) defaults to
  `[None, True, False, True]`.
  - **Resolution** (detailed in
    [`nn.md#open-questions`](nn.md#open-questions)): Confirmed XML
    serialization test artifact (commit `78bba4e7`) testing XML
    round-tripping of nullable boolean lists across
    `.snngine/template.xml:578-583`. Never read by runtime logic.
- [SOLVED] **Hardcoded single-chemical simulation coupling**
  ([`nn.md`](nn.md#open-questions)):
  `Simulation._make_simulator_backend`
  (`snngine_v4/nn/sim/simulation.py:151-160`) binds exclusively to
  `chemicals.C0`, ignoring any secondary chemical volumes (such as
  `C1`).
  - **Resolution** (detailed in
    [`nn.md#open-questions`](nn.md#open-questions)): Confirmed
    single-chemical architectural limit: the CUDA backend constructor
    (`snn_simulation_bindings.cu:65,279`) and diffusion kernel
    (`snn_simulation.cu:205,278`) accept only one set of 3D diffusion
    pointers (`C_old`, `C_new`, `C_source`).
- [SOLVED] **Python-side iterative synaptic corrections**
  ([`nn.md`](nn.md#open-questions)): `SynCounts.fill_tensors`
  (`snngine_v4/nn/synapses.py:127-156`) performs iterative distribution
  shaping (`output_correction`) and autapse masking on the CPU before
  passing indices to CUDA kernels.
  - **Resolution** (detailed in
    [`nn.md#open-questions`](nn.md#open-questions)): Confirmed
    algorithmic discretization and autapse-avoidance logic from NDKNV
    lineage (Nageswaran et al. 2009): iteratively redistributes integer
    rounding surplus across delay rows and ensures autapse avoidance
    before GPU representation indexing.

### [`visualization/`](visualization.md#open-questions)
- [SOLVED] **Dead visuals and empty modules**
  ([`visualization.md`](visualization.md#open-questions)):
  `visuals/plot_lines.py`
  (`snngine_v4/visualization/visuals/plot_lines.py:1-40`) is entirely
  commented out; `visuals/boxes/` and `plotting/` directories contain
  only empty `__init__.py` stubs.
  - **Resolution** (detailed in
    [`visualization.md#open-questions`](visualization.md#open-questions)):
    Confirmed legacy dead code and orphaned stubs. Plotting visual
    logic was unified onto standard VisPy scene visuals
    (`vispy.scene.visuals.Line`), while box visuals live in
    `visuals/boxes.py` (making `visuals/boxes/` and `plotting/` empty
    legacy stubs).
- [SOLVED] **Invisible bounding box default**
  ([`visualization.md`](visualization.md#open-questions)):
  `OuterGridVisualInitConfig.color`
  (`snngine_v4/visualization/config_models/visuals/boxes.py:59`) defaults
  to `None`, leaving faces transparent and rendering only white wireframe
  edges.
  - **Resolution** (detailed in
    [`visualization.md#open-questions`](visualization.md#open-questions)):
    Confirmed intentional: transparent faces (`color=None`) with white
    edges (`edge_color='white'`) create an unobtrusive bounding wireframe
    cage that does not occlude internal neurons or chemical volume
    rendering.
- [SOLVED] **Domain coupling in visual builder**
  ([`visualization.md`](visualization.md#open-questions)):
  `VispyVisualBuilder.get_model`
  (`snngine_v4/visualization/visual_builder.py:463-477`) hardcodes
  explicit `isinstance` branches for `FiniteGridConfig` and
  `NetworkReservoirConfig`.
  - **Resolution** (detailed in
    [`visualization.md#open-questions`](visualization.md#open-questions)):
    Confirmed adapter design: acts as an input model adapter converting
    raw simulation domain models into visual init configs
    (`OuterGridVisualInitConfig`, `MarkersVisualConfig`) before
    delegating to `ModelObjectBuilder`.
- [SOLVED] **Synchronous 3D texture copies**
  ([`visualization.md`](visualization.md#open-questions)):
  `GLTexture3DTensor`
  (`snngine_v4/visualization/cuda/gl_interop/gl_texture3d.py:85-115`)
  relies on synchronous `pycuda.driver.Memcpy3D()` and explicit
  synchronization rather than zero-copy interop.
  - **Resolution** (detailed in
    [`visualization.md#open-questions`](visualization.md#open-questions)):
    Hardware/driver constraint: OpenGL 3D texture memory is
    driver-tiled/non-linear and cannot be wrapped directly into a
    contiguous PyTorch tensor, necessitating separate buffer
    allocation, `Memcpy3D`, and stream synchronization
    (`torch.cuda.synchronize()`).

### [`utils/`](utils.md#open-questions)
- [SOLVED] **GUI framework coupling in reflection utilities**
  ([`utils.md`](utils.md#open-questions)): `field_utils.py`
  (`snngine_v4/utils/field_utils.py:14`) imports `pyqtgraph` directly at
  module level, coupling core Pydantic inspection helpers to Qt.
  - **Resolution** (detailed in
    [`utils.md#open-questions`](utils.md#open-questions)): Reuses
    `pyqtgraph.functions.eq(a, b)` inside `is_equal()` to safely
    compare heterogeneous objects (tensors, arrays, Qt objects)
    without ambiguous-truth-value errors, but introduces an unintentional
    module-level Qt dependency into headless data reflection utilities.
- [SOLVED] **Unused vendored HDF5 serialization**
  ([`utils.md`](utils.md#open-questions)): `deepdish` is vendored under
  `snngine_v4/utils/data_utils/deepdish_pack/`, but array persistence
  calls to `.h5` files in
  `snngine_v4/utils/settings/config_model_base.py:114-115` are commented
  out.
  - **Resolution** (detailed in
    [`utils.md#open-questions`](utils.md#open-questions)): Active on
    read, dormant on write: `XMLConfigSettingsSource` and
    `ArrayDictRW.extract_arrays` actively invoke `deepdish.io.load()` to
    deserialize companion `.h5` array files; automatic `.h5` generation on
    export is commented out.
- [SOLVED] **Strict container immutability**
  ([`utils.md`](utils.md#open-questions)): `ContainerConfig`
  (`snngine_v4/utils/containers/configurable_container.py:35-46`) defaults
  `b_clear_allowed=False` and `b_replace_allowed=False`, requiring
  explicit `b_force=True` bypasses when clearing or rebuilding engine
  state.
  - **Resolution** (detailed in
    [`utils.md#open-questions`](utils.md#open-questions)): Defensive
    design: engine containers hold live GPU VBOs and CUDA simulation
    handles; prohibiting silent key replacement and unintended clearing
    prevents orphaning mapped GPU memory or breaking active UI tree
    bindings. Containers needing resets opt in explicitly (e.g.
    `NetworkBuilder`).

### [`gui/`](gui.md#open-questions)
- [SOLVED] **Circular package import**
  ([`gui.md`](gui.md#open-questions)): `config/app.py`
  (`snngine_v4/config/app.py:3`) imports `gui/app_settings.py`, while
  `gui/app/engine_app.py` (`snngine_v4/gui/app/engine_app.py:11`) imports
  `config/app.py` and `snngine_config.py`.
  - **Resolution** (detailed in
    [`gui.md#open-questions`](gui.md#open-questions)): Acyclic DAG at
    module level (`utils` -> `gui/app_settings` -> `config/app` ->
    `snngine_config` -> `gui/app/engine_app`), but creates package-level
    cross-coupling because `AppSettings` lives in `gui/`. Moving
    `AppSettings` to `config/app.py` would enforce strict unidirectional
    package layering.
- [SOLVED] **Hardware MIDI dependencies**
  ([`gui.md`](gui.md#open-questions)): `devices/x_touch_mini/`
  (`snngine_v4/gui/devices/x_touch_mini/`) requires MIDI backend drivers
  (`mido`), requiring graceful degradation in headless or cloud
  environments lacking audio/MIDI ports.
  - **Resolution** (detailed in
    [`gui.md#open-questions`](gui.md#open-questions)): Safely isolated in
    `gui/devices/x_touch_mini/`: neither imported nor instantiated by
    default during `EngineApp` or `MainEngineWindow` launch, allowing
    headless and cloud simulations to run without MIDI hardware or
    drivers.
- [SOLVED] **Development test remnants**
  ([`gui.md`](gui.md#open-questions)): `MainEngineWindow.test_func()`
  (`snngine_v4/gui/windows/main_window.py:103-106`) contains
  commented-out simulation execution calls.
  - **Resolution** (detailed in
    [`gui.md#open-questions`](gui.md#open-questions)): Connected
    directly to `buttons_dock.test_button.clicked`
    (`snngine_v4/gui/windows/main_window_base.py:117`) as an interactive
    manual UI test hook for development scratchpad experimentation.
