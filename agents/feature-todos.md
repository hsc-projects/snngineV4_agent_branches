# Feature to-dos

Tracks features/work items across SNNgine3D and snngineV4. Confirm entries
with the user before adding/moving them (same as any other fact in this
`agents/` directory) — see `agents/common.md` → Workflow.

Each entry gets a priority: **high**, **mid**, or **low**.

## Now

- [high] Generate main feature specifications:
  - Specification pipeline overview: `agents/main_feature/README.md`.
  - Active Level 1 task: `agents/main_feature/generate_specs_task/generate-main-feature-specs-task.md`.
  - Target deliverable: Authoritative task specifications in `agents/main_feature/specs/` (Level 2).
  - Status: Phase 1 — Discussion & Scoping.

## Completed

- [high] Horizontal mapping pass across `snngine_v4/` subpackages:
  - Completed all 8 subpackage mapping write-ups (`chemistry.md`, `geometry.md`, `construction.md`, `config.md`, `nn.md`, `visualization.md`, `utils.md`, `gui.md`), `vertical-trace.md`, `config-build-pattern.md`, and system-wide orchestration cross-check `module-interactions.md`. Central index at `agents/mapping/README.md`.
- [high] Runpod headless engine simulation smoke test:
  - Validated headless Double-Tree assembly, C++/CUDA backend bindings, and 100-step simulation execution on NVIDIA RTX 4090 with resting potential stability. Report: `setups/runpod-engine-smoke-test/runpod-engine-smoke-test-report.md`.
- [high] Runpod headless simulation video generation:
  - Validated hardware-accelerated offscreen EGL VisPy 3D neural activity rendering and H.264/H.265 MP4 encoding across 720p, 1080p, and 4K UHD resolutions, plus 3-panel composite telemetry (reservoir, rolling spike raster, stacked voltage traces) on RTX PRO 4000 Blackwell. Report: `setups/runpod-engine-smoke-test/runpod-engine-video-report.md`.
- [high] Runpod 3D chemical diffusion video generation:
  - Validated headless volumetric chemical concentration simulation and 3D visual rendering on cloud GPU. Report: `setups/runpod-chem-diffusion/runpod-chem-diffusion-report.md`.

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
