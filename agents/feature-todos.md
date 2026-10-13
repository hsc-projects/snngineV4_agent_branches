# Feature to-dos

Tracks features/work items across SNNgine3D and snngineV4. Confirm entries
with the user before adding/moving them (same as any other fact in this
`agents/` directory) — see `agents/common.md` → Workflow.

Each entry gets a priority: **high**, **mid**, or **low**.

## Now

- [high] Horizontal mapping pass across `snngine_v4/` subpackages:
  - **Completed in this pass**:
    - `chemistry/` (`agents/mapping/chemistry.md`): added end-to-end integration, legacy SNNgine3D differences (interactive `SelectorBox`, `stent.npz`, `additive`, stepping sync gap), and corrected Open Question 4.
    - `geometry/` (`agents/mapping/geometry.md`): added `volume.py` catalog, neuron position discretization and spatial sorting (`sort_pos`), VisPy GLSL geometry shader clipping (`technical_max_z_value`), and SNNgine3D legacy cross-check (decoupling from VisPy visuals, `VolumeShapeHDW` Pydantic model vs `VolumetricMixin`, `max_z` clipping origin, and `coord` direction relic).
    - `construction/` (`agents/mapping/construction.md`): added recursive build cascade, Double-Tree Architecture (`node_tree: EngineNodes` vs `root_element: SpatialNetwork`), and SNNgine3D legacy cross-check (transition from monolithic `Engine` imperative assembly, abolition of `VspNN` visual inheritance hierarchy, and strict declarative attribute guarding).
    - `config/` (`agents/mapping/config.md`): added runtime lifecycle and multi-file XML persistence (`.snngine/`), and SNNgine3D legacy cross-check (partitioning of monolithic `EngineConfig`, dedicated simulation CUDA device assignment, Pydantic v2 `XMLSettingsModel` vs custom `XMLHandler`).
    - `nn/` (`agents/mapping/nn.md`): added runtime simulation execution, ring-buffer spike tracking, in-situ GPU plot streaming, and SNNgine3D legacy cross-check (elimination of host `GPURecorder`, modular `SynCounts` delay correction and autapse masking, headless simulation decoupling).
    - `visualization/` (`agents/mapping/visualization.md`): added two-phase visual lifecycle, zero-copy VBO vs 3D texture interop, and SNNgine3D legacy cross-check (abolition of intrusive `CudaNode` hierarchy, GLSL geometry shader culling, bidirectional camera event reflection).
    - `utils/` (`agents/mapping/utils.md`): added runtime container lifecycles, dual-backed tensor synchronization, and SNNgine3D legacy cross-check (`StateTensor` to `TensorDataFrame` transition, bidirectional `Object2ObjectMap`, generic `ModelObjectBuilder` reflection).
    - `gui/` (`agents/mapping/gui.md`): added application initialization lifecycle, reactive connector architecture, shared buffer protection, and SNNgine3D legacy cross-check (transition from imperative collapsible frames to schema-driven `ParameterTree`, decoupled connector layer, `EngineLinkerTree` MIDI hardware mapping).
  - **All horizontal mapping subpackages and sister-repo cross-checks are now complete.**
- [high] Runpod headless engine simulation smoke test:
  - Specification: `setups/runpod-engine-smoke-test/runpod-engine-test-task.md`.
  - Automation scripts: `runpod_engine_test_runner.sh` and `test_headless_engine_sim.py` (supporting contracts check, 1-step quick smoke, and full 100-step execution with compact error pruning).
  - Target environment: NVIDIA RTX 2000 Ada in `EU-RO-1` mounting persistent volume `qze81dpw7q`.
  - Report artifact: `setups/runpod-engine-smoke-test/runpod-engine-smoke-test-report.md`.

## Backlog

- [high] Implement progressive automated testing suite — introduce an initial
  unit testing framework (e.g. pytest) covering headless, CPU-bound modules
  first (Pydantic config validation, construction element hierarchies,
  reflection helpers in `utils/field_utils.py`, and spatial geometry models),
  progressively expanding toward mocked pipeline execution and GPU/CUDA kernel
  verification as environment capabilities permit.
- [high] Implement progressive linting and code quality checks — establish
  standalone static analysis tooling (e.g. ruff, flake8, or mypy) independent
  of IDE inspections, starting with pure-Python headless subpackages (config,
  utils, construction) and progressively rolling out across the codebase.
- [high] Fix `ValidationError` constructor signature in
  `Shape3Di32.model_post_init` (`snngine_v4/geometry/spatial_pars.py:134-138`)
  — replace `raise ValidationError(...)` with `raise ValueError(...)` to
  prevent `TypeError: ValidationError.__new__() missing 1 required
  positional argument: 'line_errors'` when non-positive shape values are
  passed.
- [mid] Resolve unimported `torch` reference in `grid_mask_maker.extend_mask`
  (`snngine_v4/geometry/grid/grid_mask_maker.py:5,37-41`) — either restore
  `import torch` inside the tensor branch or standardize `grid_mask_maker`
  on NumPy and remove the orphaned torch branch to prevent `NameError` on
  tensor inputs.
- [mid] Decouple `pyqtgraph` from core reflection utilities in
  `field_utils.py` (`snngine_v4/utils/field_utils.py:14,622`) — replace
  `pyqtgraph.functions.eq` with an internal array/object equality helper to
  avoid importing Qt into foundational headless data and builder utilities.
- [mid] Isolate builder mapping attributes in `EngineElement`
  (`snngine_v4/construction/engine_element.py:264-273`) — prevent
  `self.update_builder_class_attributes()` from mutating class-level
  `ClassVar` dictionaries in place, which leaks builder map extensions
  across sibling instances of the same subclass under different parents.
- [mid] Neural-chemical coupling — distinguishes between two approaches:
  custom, currently unspecified interaction mechanisms, and standard coupling.
- [low] Eliminate circular cross-package dependency between `config/` and
  `gui/` — move the base `AppSettings` model from
  `snngine_v4/gui/app_settings.py` into `snngine_v4/config/app.py` so that
  `config/` has no dependency on `gui/`.
- [low] Prune verified legacy relics and orphaned stubs — remove unused
  `GridDirectionsObject.coord` (`finite_grid_elements.py:12-19`),
  commented-out `plot_lines.py` (`visuals/plot_lines.py:1-27`), dead parent
  assignment (`nn/spnn.py:60`), test config field
  `SpatialNetworkConfig.bools` (`nn/config_models/spnn_config.py:29`), and
  empty directory stubs `visuals/boxes/` and `plotting/`.
- [low] Expand CUDA simulation backend to support multi-chemical diffusion
  — extend CUDA kernel signatures, launch parameters, and runtime volume
  bindings to simulate multiple chemical species (`C0`, `C1`, etc.) rather
  than hardcoding to `C0`.
- [low] Fetch and read the "shared memory" paper (currently the
  provisional Fidjeland & Shanahan match, unconfirmed). Purpose in this
  codebase is not remembered: possibly STDP, possibly the simulation
  loop, possibly the chemical diffusion computation. Good to have in
  mind, not confirmed relevant to a specific subsystem.
- [mid] Implement an additional, less compute-intensive spiking neuron model
  — Integrate-and-Fire (IF) or Leaky Integrate-and-Fire (LIF) — alongside
  the existing Izhikevich model.
- [low] Revisit the 3D volumetric texture copy path (currently explicit
  `pycuda.driver.Memcpy3D` GPU-to-GPU copy, see `agents/common.md` → Core
  technical facts) — try again to achieve true zero-copy OpenGL interop for
  3D textures, or implement sub-volume bounding box dirty updates to copy
  only modified voxel regions (`gl_texture3d.py:107`).
- [low] Restart a pure C++ version of the engine (a "sister" project to
  snngineV4, in the spirit of V2) developed in parallel and kept in sync
  with the Python version. If pursued, this would be managed by agents.
- [mid] Investigate slow application startup — specifically, importing the
  libraries (PyQt, Pydantic, etc.) at launch appears slow, before any
  network/simulation is loaded. Suspected culprits: PyQt itself, or the
  large number of Pydantic config models — unconfirmed which. Suspicion
  leans toward PyQt because the same slow-import pattern was observed in a
  separate, unrelated app that used no GPU/CUDA at all. Part of the
  motivation for the low-priority C++ sister-project idea above.
- [low] Survey related existing SNN simulation frameworks — BindsNET,
  Brian2 (and its GPU backends Brian2CUDA/Brian2GeNN), NeuroML — for
  relevant ideas or possible future interop. Not a core design driver, just
  worth being aware of what exists in this space.

## Paused

- [mid] Migrating the "simulation stepping" feature from SNNgine3D — see
  `agents/paused-migration-feature-simulation-stepping.md`.

## Questions

(nothing yet)
