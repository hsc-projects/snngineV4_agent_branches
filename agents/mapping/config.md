# config/

Engine-level pydantic settings: `app.py`, `devices.py` (CUDA/OpenGL device
selection), `scenes.py`, `template.py`. `snngine_config.py`, at the
`snngine_v4/` package root rather than inside `config/` itself, ties these
into `EngineConfig`; it's covered here too since the architecture-md
description already grouped it with this subpackage. Four non-empty files
under `config/` (plus an empty `__init__.py`) and the one root-level file,
all fully read for this write-up.

## Files and classes

- **`devices.py`** — `OpenGLSettings` (`gloo_target: str = "gl+"`),
  `CudaSettings` (`b_require_pycuda: bool = False`), and `DeviceSettings`
  (`b_use_cuda: bool = True`, `opengl: OpenGLSettings = OpenGLSettings()`,
  `cuda: CudaSettings` with **no default**, unlike `opengl` — see Open
  questions). Tagged `config-driven`; no logic beyond field declarations.

- **`template.py`** — `EngineConstructionConfig(XMLSettingsContainerModel)`:
  one field, `network: SpatialNetworkConfig | None = None`. This is
  exactly the config type `construction.md`'s `NetworkBuilder` operates
  on (`container_model`/`build_model` in `NetworkBuilder.__init__`/
  `.build()`).

- **`scenes.py`** — `SceneSettings(ConfigModel)`: three pre-configured
  `VispyCanvasConfig` fields (`visualization/config_models/`, not yet
  mapped) — `main` (titled `'NetworkView'`), `multiplot_voltage`, and
  `multiplot_firings` (titled `'Voltage'`/`'Firings'`). Both multiplot
  scenes explicitly set `PanZoomCameraParameters()` on their view; `main`
  does not set an explicit camera — not confirmed whether that's
  deliberate (a different default camera suits a 3D network view vs. 2D
  plots) or an oversight. A commented-out `# second=VispyViewBoxConfig()`
  in `main`'s views — tagged `legacy-dead`.

- **`app.py`** — `EngineAppSettings(AppSettings)`: a one-line subclass of
  `gui/app_settings.py`'s `AppSettings` (not yet mapped), overriding only
  `parameter_ui_opts` to `readonly=True`. Notable: `config/` already
  reaches into `gui/` for this base class — an early, concrete sign that
  `config/` and `gui/` are mutually coupled, not that `config/` is purely
  upstream of `gui/` (see Relationships).

- **`snngine_config.py`** (package root) — `EngineConfig(XMLSettingsModel)`,
  the single top-level settings container tying every other file here
  together: `app: EngineAppSettings`, `devices: DeviceSettings`,
  `scenes: SceneSettings`, `template: EngineConstructionConfig`, `built:
  EngineConstructionConfig`.
  - `template`'s `default_factory` builds a concrete default network — a
    `SpatialNetworkConfig(device=1, elements=[NetworkReservoirConfig()])`
    — with two commented-out `EngineElementConfig()` placeholders
    alongside the one real element. Not confirmed whether this
    single-reservoir default is the intended out-of-the-box topology or
    a leftover development default (parallel to the `b_test_init`
    caveat already flagged in `chemistry.md`) — see Open questions.
  - `built: EngineConstructionConfig` (no default) is the separate,
    already-built-and-persisted counterpart to `template` — matches
    `agents/architecture-snngine_v4.md`'s note on `.snngine/built.xml`
    as a serialized state snapshot.
  - `Slots` class vars (`TEMPLATE`, `SCENES`, `BUILT`) name specific
    model fields; `_xml_file_paths` (classmethod) excludes
    `cls.Slots.SCENES` from the per-field XML-file split (each other
    field gets its own `<field>.xml` file via a substituted filename
    pattern) — a commented-out `# cls.Slots.CONSTR` alongside it in the
    same exclusion list suggests `template` was previously named
    differently (`CONSTR`/construction) and this file wasn't fully
    updated after the rename. Not confirmed why `scenes` specifically is
    excluded from separate-file persistence. A commented-out
    `_export_submodels` method — tagged `legacy-dead`.

## Relationships within the subpackage

`template.py`'s `EngineConstructionConfig` and `devices.py`/`scenes.py`/
`app.py`'s settings classes are all leaf pieces with no cross-file
dependencies on each other; `snngine_config.py`'s `EngineConfig` is the
one place that assembles them into a single settings tree. The
`app.py` → `gui/app_settings.py` dependency runs the opposite direction
from what a top-down "config feeds everything else" mental model would
suggest — `config/` isn't purely upstream of `gui/`, at least for this
one base class.

## Generic vs. particular

This subpackage doesn't have the generic/particular split found in
`construction.md`; it's settings data, not builder machinery. The one
notable particular-ish choice is `snngine_config.py`'s hard-coded default
network topology in `template`'s `default_factory` — a concrete,
hand-chosen default rather than something derived generically, but not
a fixed-external-API edge in the sense of `config-build-pattern.md`'s
edges.

## Cross-links

- `agents/mapping/construction.md` — `EngineConstructionConfig`
  (`template.py`) is exactly what `NetworkBuilder` consumes; the
  `template`/`built` distinction on `EngineConfig` maps directly onto
  `NetworkBuilder.build()`'s config-in / built-state-out behavior.
- `agents/mapping/vertical-trace.md` — step 2 of the traced chain
  ("builds a default `EngineConfig` if none given") is exactly
  `snngine_config.py`'s `EngineConfig`, with its `template` default
  producing the one-reservoir network actually built at startup.
- `agents/mapping/chemistry.md` — the `b_test_init`-default caveat there
  parallels the unconfirmed-default-topology question raised here for
  `template`'s `default_factory`.
- `gui/`, `visualization/config_models/`, `utils/settings/xml_settings.py`
  (none yet mapped) — `AppSettings`, `VispyCanvasConfig`/
  `PanZoomCameraParameters`, and `XMLSettingsModel`/
  `XMLSettingsContainerModel` are all defined there; this subpackage
  consumes but doesn't define them.

## Runtime configuration lifecycle and serialization

`config/` (anchored by package-root `snngine_config.py`) orchestrates engine settings and multi-file XML persistence:

### 1. Unified settings aggregation (`EngineConfig`)
`EngineConfig` (`snngine_v4/snngine_config.py`) serves as the central configuration tree unifying five distinct domain submodels:
- **Application UI defaults**: `app: EngineAppSettings` (`snngine_v4/config/app.py`, subclassing `snngine_v4/gui/app_settings.py:AppSettings`) sets top-level GUI flags, enforcing read-only parameter inspection modes by default (`parameter_ui_opts = {'readonly': True}`).
- **Hardware device allocation**: `devices: DeviceSettings` (`snngine_v4/config/devices.py`) configures OpenGL rendering targets (`OpenGLSettings.gloo_target = "gl+"`) and CUDA execution requirements (`CudaSettings.b_require_pycuda = False`).
- **Visual canvases and viewports**: `scenes: SceneSettings` (`snngine_v4/config/scenes.py`) provisions VisPy canvas topologies for `main` (3D network view using `TurnTableCameraParameters`), `multiplot_voltage`, and `multiplot_firings` (2D time series and spike rasters using `PanZoomCameraParameters`).
- **Declarative template vs. built snapshot**: `template: EngineConstructionConfig` defines the declarative blueprint for network generation (`SpatialNetworkConfig` with child reservoirs and simulation hyperparameters). Once built by `NetworkBuilder`, the materialized runtime graph is recorded into `built: EngineConstructionConfig`, cleanly separating input parameters from running simulation state snapshots.

### 2. Modular multi-file XML persistence (`.snngine/`)
Unlike monolithic configuration dumps, `EngineConfig` integrates with `XMLSettingsModel` (`snngine_v4/utils/settings/xml_settings.py`) to serialize submodels into separate XML files under `.snngine/`:
- `_xml_file_paths` maps submodel fields to discrete files (`app.xml`, `devices.xml`, `template.xml`, `built.xml`) using `BaseSettingsSlots.SUB_SETTINGS_FILE_NAME_PATTERN`.
- **Exclusion of `scenes`**: `_xml_file_paths` explicitly omits `Slots.SCENES`, ensuring that canvas dimensions, viewports, and cameras are instantiated directly from Python code defaults (`SceneSettings`) rather than being overridden by stale XML presets on disk.
- **Companion array storage**: For dense numeric data (such as neuron positions or synaptic matrices), `XMLSettingsSource` integrates with `deepdish.io.load` to store companion `.h5` files alongside XML documents, keeping markup lightweight while preserving binary tensor data.

## SNNgine3D legacy differences (sister-repo cross-check)

A comparative audit against `SNNgine3D` (`snngine3d/configuration/deprecated/engine_config.py` and `network_config.py`) documents the modernization of configuration architecture:

### 1. Partitioning of monolithic settings
- **SNNgine3D**: `EngineConfig` (`snngine3d/configuration/deprecated/engine_config.py`) combined disparate concerns into a single flat model: integer screen IDs (`screen: int = 1`), file loading dialog flags (`b_open_file_dialog: bool = False`), hardcoded neural topology (`N=3000`, `reservoir_shape=(6, 6, 1)`), and UI dock display modes (`PlotViewMode.MAIN`, `PlotViewMode.DOCKED`).
- **snngine_v4**: Modularized into specialized submodels under `config/`: hardware backends in `DeviceSettings`, UI application flags in `EngineAppSettings`, VisPy canvases in `SceneSettings`, and neural network topology in `EngineConstructionConfig`. Dock view modes were removed from core settings and relocated entirely to the PySide6 UI layer.

### 2. Separation of display and simulation CUDA devices
- **SNNgine3D**: Declared a single global integer `device: int = 0` shared across OpenGL rendering, UI, and CUDA simulation.
- **snngine_v4**: Decouples display from simulation compute. While `DeviceSettings` manages global OpenGL and CUDA driver flags, `SpatialNetworkConfig` explicitly assigns CUDA simulation workloads to dedicated GPU devices (`device = 1` by default in `.snngine/template.xml` and `snngine_v4/snngine_config.py`), isolating compute kernels from display GPU device 0.

### 3. Pydantic v2 `XMLSettingsModel` vs. ad-hoc `XMLHandler`
- **SNNgine3D**: Relied on an imperative custom reflection walker in `snngine3d/utils/xml_handler.py` (`XMLHandler.convert_to_xml`), which traversed Python dictionaries and constructed XML `ElementTree` hierarchies with explicit type attributes (`IntEnum`, `DictItem`, `SequenceElement`).
- **snngine_v4**: Replaced custom XML parsing with Pydantic v2-backed `XMLSettingsModel` / `XMLSettingsContainerModel` (`snngine_v4/utils/settings/xml_settings.py`), embedding automated schema validation, type conversion, modular submodel routing, and companion HDF5 array storage directly into model lifecycles.

## Open questions

Indexed centrally in [`README.md` → Consolidated open questions](README.md#config):

- [SOLVED] `DeviceSettings.cuda: CudaSettings` has no default, while its sibling
  `opengl: OpenGLSettings = OpenGLSettings()` does — not confirmed
  whether this asymmetry is intentional (e.g. CUDA settings must always
  be supplied explicitly) or an oversight.
  - **Resolution**: Syntactically asymmetric but semantically equivalent under Pydantic v2.
    `CudaSettings` (`snngine_v4/config/devices.py:13-16`) defines all its fields with defaults
    (`b_require_pycuda: bool = False`). Under Pydantic v2, fields annotated with defaultable
    submodels are automatically constructed with their defaults if omitted during parent instantiation.
    Instantiating `DeviceSettings()` succeeds without arguments and initializes `cuda` to
    `CudaSettings(b_require_pycuda=False)`.
    See [`README.md#config`](README.md#config).
- [SOLVED] `SceneSettings.main`'s view has no explicit `camera`, unlike both
  multiplot scenes' `PanZoomCameraParameters()`. Not confirmed whether
  this is deliberate.
  - **Resolution**: Confirmed by design. `VispyViewBoxConfig.camera`
    (`snngine_v4/visualization/config_models/vispy_canvas_config.py:53-54`) defaults via
    `default_factory` to `TurnTableCameraParameters()`. The main scene (`SceneSettings.main` in
    `snngine_v4/config/scenes.py:15-21`) displays the 3D network and chemical volume, so it relies
    on this default 3D orbit camera. The multiplot scenes (`multiplot_voltage`, `multiplot_firings` in
    `scenes.py:23-41`) render 2D time series and spike rasters, so they explicitly override the 3D
    camera with `PanZoomCameraParameters()`.
    See [`README.md#config`](README.md#config).
- [SOLVED] `snngine_config.py`'s `template` default (`SpatialNetworkConfig` with
  one `NetworkReservoirConfig`) — not confirmed whether this is the
  intended shipped default or a development-era leftover, matching the
  same open caveat already raised for `chemistry/`'s test-data default.
  - **Resolution**: Confirmed shipped default topology. A runnable `SpatialNetwork` requires at
    least one recurrent neuron pool (`NetworkReservoirConfig`). The `default_factory` on
    `EngineConfig.template` (`snngine_v4/snngine_config.py:45-53`) mirrors the shipped XML preset
    (`.snngine/template.xml:4,116`), configuring a single 1000-neuron reservoir on dedicated CUDA
    `device=1`. The commented-out `# EngineElementConfig(),` lines indicate that `elements` is designed
    to support heterogeneous multi-reservoir topologies.
    See [`README.md#config`](README.md#config).
- [SOLVED] The commented-out `Slots.CONSTR` alongside the live `Slots.SCENES`
  exclusion in `_xml_file_paths` suggests an incomplete rename
  (`CONSTR`/construction → `TEMPLATE`); not confirmed whether any other
  leftover references to the old name exist elsewhere in the codebase.
  - **Resolution**: Confirmed legacy rename leftover. In earlier iterations, the `template` field
    was named `construction` (with slot `CONSTR` or `CONSTRUCTION`, commit `14520fee67`). When renamed
    to `template` (`Slots.TEMPLATE = 'template'` in `snngine_v4/snngine_config.py:30`), the old
    `CONSTR` exclusion was commented out in `_xml_file_paths` (`snngine_config.py:73`). A codebase-wide
    search confirms no active occurrences of `CONSTR` remain.
    See [`README.md#config`](README.md#config).
- [SOLVED] Why `scenes` specifically is excluded from the per-field XML-file split
  (while `app`/`devices`/`template`/`built` presumably each get their own
  file) isn't confirmed without reading `utils/settings/xml_settings.py`.
  - **Resolution**: Confirmed development workflow design. Excluded from `_xml_file_paths`
    (`snngine_v4/snngine_config.py:74`) so that `EngineConfig` initializes `scenes` from Python code
    defaults (`SceneSettings` in `snngine_v4/config/scenes.py`) rather than deserializing `.snngine/scenes.xml`.
    This ensures that ongoing modifications to VisPy canvas, camera, and axis settings in Python take
    immediate effect at startup without being overridden by stale XML presets on disk.
