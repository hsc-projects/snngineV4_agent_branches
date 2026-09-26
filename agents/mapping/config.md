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

## Open questions

- `DeviceSettings.cuda: CudaSettings` has no default, while its sibling
  `opengl: OpenGLSettings = OpenGLSettings()` does — not confirmed
  whether this asymmetry is intentional (e.g. CUDA settings must always
  be supplied explicitly) or an oversight.
- `SceneSettings.main`'s view has no explicit `camera`, unlike both
  multiplot scenes' `PanZoomCameraParameters()`. Not confirmed whether
  this is deliberate.
- `snngine_config.py`'s `template` default (`SpatialNetworkConfig` with
  one `NetworkReservoirConfig`) — not confirmed whether this is the
  intended shipped default or a development-era leftover, matching the
  same open caveat already raised for `chemistry/`'s test-data default.
- The commented-out `Slots.CONSTR` alongside the live `Slots.SCENES`
  exclusion in `_xml_file_paths` suggests an incomplete rename
  (`CONSTR`/construction → `TEMPLATE`); not confirmed whether any other
  leftover references to the old name exist elsewhere in the codebase.
- Why `scenes` specifically is excluded from the per-field XML-file split
  (while `app`/`devices`/`template`/`built` presumably each get their own
  file) isn't confirmed without reading `utils/settings/xml_settings.py`.
