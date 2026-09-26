# gui/

PySide6 application shell, PyQtGraph parameter tree docking framework,
bidirectional reactive connectors (`CudaVispyConnector`, `VispyConnector`,
`TensorConnector`), custom interactive parameter widgets (spinbox-sliders,
color pickers, array/dataframe table editors), and Behringer X-Touch Mini
hardware MIDI controller integration. All 42 Python source files (~11,710 LOC)
were read for this write-up.

## Files and classes

### Application shell and windows (`app/`, `windows/`, `views/`)

- **`app/engine_app.py`**
  - `EngineApp(Application)` — main application entry point inheriting
    VisPy's `Application` (which initializes the underlying Qt event loop).
    Initializes `SNNgine`, applies `qdarktheme` dark palette styling,
    instantiates `MainEngineWindow`, exports settings snapshots, and calls
    `construct_network()`. Tagged `generic-machinery`.
  - `app/debug_app.py` — debug launcher script; tagged `legacy-dead`-adjacent.

- **`app_settings.py`**
  - `AppSettings(ConfigModel)` — base application settings container:
    `theme`, `corner_shape`, `backend_name` (`'PySide6'`), and window
    dimensions. Imported upstream by `config/app.py` for `EngineAppSettings`.
    Tagged `config-driven`.

- **`windows/main_window.py`** & **`windows/main_window_base.py`**
  - `MainEngineWindow(MainEngineWindowBase)` — primary multi-dock application
    window. Hosts docks for configuration parameter trees (Template, Built),
    the element selection tree (`selection_tree_dock`), the hardware controls
    linker tree (`controls_dock`), secondary VisPy scenes (`ViewArea`), and
    tabular array editors (`ArrayEditorDockWidget`).
  - Calls `self.engine.build()` during `construct_network()` to synchronize
    the simulation core, VisPy visuals, and parameter trees.
  - Contains `test_func()` with commented-out simulation runs — tagged `legacy-dead`.
  - `windows/settings_window.py`, `windows/extra_parameters.py` — secondary
    dockable parameter panels.

- **`views/view_area.py`**
  - `ViewArea(QtWidgets.QWidget)` — manages secondary VisPy canvas embedding
    and layout within Qt dock widgets.

### Parameter trees and reactive connectors (`parameter_trees/`)

- **`engine_parameter_tree.py`**
  - `EngineParameterTree(ParameterTree)` — pyqtgraph parameter tree reflecting
    Pydantic configuration models into interactive GUI parameter items.
    Manages expanding/collapsing, validation updates, and model signal dispatching
    via an attached `ExtendedModelSignalsRegister`. Tagged `generic-machinery`.

- **`cuda_connector.py`**
  - `CudaVispyConnector(ParameterConnector)` — one of the confirmed
    `hand-written-edge` implementations:
    - Queries VisPy's internal GLIR object registry (`get_current_canvas().context.shared.parser._objects[...]`)
      for an already-constructed visual to extract real OpenGL buffer/image handles
      (`_vbo.id`, `_texture.id`).
    - Wraps extracted handles in `GLVBOTensor` or `GLTexture3DTensor`.
    - Confirms the fundamental lifecycle order: VisPy OpenGL visuals are
      constructed first, their OpenGL IDs are resolved by `CudaVispyConnector`,
      and CUDA device pointers are mapped into PyTorch tensors afterward.
    - Tagged `hand-written-edge` + `cuda-adjacent`.

- **`vispy_connector.py`**
  - `VispyConnector(ParameterConnector)` — binds Pydantic configuration models
    to VisPy `VisualNode` properties via `VispyLinks`. Translates interactive
    property edits in parameter trees into live VisPy visual updates (`color`,
    `edge_color`, `size`, `visible`). Tagged `hand-written-edge`.

- **`tensor_connector.py`**
  - `TensorConnector(ParameterConnector)` — binds `TensorParameter` and
    `TensorDictParameter` tree nodes directly to live device tensors in
    `model.tensor_dict` on each `EngineElement`. Tagged `hand-written-edge`.

- **`selector_tree/`**
  - `EngineSelectorTree(EngineParameterTree)`, `SelectorModel` — hierarchical
    tree UI allowing users to selectively toggle visibility and active state
    for network sub-elements and visual bounding boxes. Tagged `config-driven`.

- **`linker_tree/`**
  - `EngineLinkerTree`, `LinkerWidget`, `ControlsMap`, `RangeMapWidget`,
    `DeviceInputWidget` — interactive parameter-mapping subsystem. Allows
    users to bind hardware MIDI controls (rotary encoders, faders, buttons)
    to arbitrary engine parameters, configuring min/max transfer ranges and
    toggle modes. Tagged `generic-machinery`.

- **`parameter_builder/`**
  - `ParameterBuilder`, `OptionsBuilder` — walks Pydantic model schemas and
    generates pyqtgraph `Parameter` definition dictionaries, respecting UI
    metadata (`FrozenParamOpts`, `ParamOpts`). Tagged `generic-machinery`.

- **`connectors/`**
  - `ModelParameterLinks`, `VispyLinks`, `ModelSignalsRegister`, `Object2ObjectLinks`
    — underlying reactive event binding layer coordinating synchronization
    between Pydantic models, Qt signals, and VisPy visual events.

### Custom parameter items and widgets (`parameters/`)

- **`parameters/`** — custom pyqtgraph `Parameter` / `ParameterItem` classes:
  - `spin_box_slider_parameter.py` (`SpinBoxSliderParameter`) — dual-input widget
    combining a continuous horizontal slider with an exact numeric spinbox.
  - `color_type_parameter.py` (`ColorTypeParameter`) — RGBA color selector with
    color swatch preview.
  - `array/` (`ArrayParameter`, `TensorParameter`, `TensorDictParameter`) —
    array inspection parameter nodes opening tabular edit docks.
  - `preset_parameter.py` (`PresetParameter`) — preset dropdown selector for
    Izhikevich firing regimes.
  - `index_parameter.py`, `linker_parameter.py`, `reference_parameter.py`,
    `multi_type_parameter.py`, `none_type_parameter.py`.
- **`widgets/table/`**
  - `QDataFrame`, `DFTableWidget`, `ArrayEditorDockWidget` — full PyQt table
    editor for inspecting and editing tabular data (`pandas.DataFrame` /
    `TensorDataFrame`).

### Hardware devices (`devices/`)

- **`devices/x_touch_mini/`**
  - `XTouchMiniDevice` — USB MIDI hardware controller interface for the
    Behringer X-Touch Mini (using `mido` / `rtmidi`). Reads and emits MIDI
    Control Change (CC) and note on/off events.
  - `xtm_state.py` (`XTMState`) — thread-safe state model tracking the physical
    controller layout: 8 continuous rotary encoders with 13-LED ring indicators,
    16 backlit buttons, 2 hardware control layers (A and B), and 1 master fader.
  - `xtm_ui/` (`XTMDeviceWidget`, `XTMKnobWidget`, `XTMFaderWidget`, `XTMButtonWidget`)
    — complete virtual UI rendering a photorealistic simulation of the physical
    X-Touch Mini device on screen. Tagged `hand-written-edge`.

## Relationships within the subpackage

`MainEngineWindow` acts as the master visual shell. It instantiates
`EngineParameterTree` panels for engine configuration models, builds
connections to VisPy scenes via `VispyConnector`, extracts OpenGL handles
via `CudaVispyConnector`, and bridges parameter adjustments to physical MIDI
knobs via `EngineLinkerTree` and `XTouchMiniDevice`.

## Generic vs. particular

- **Generic**:
  - `EngineParameterTree`, `ParameterBuilder`, and `ParameterConnector` provide
    an abstract, schema-driven bridge between arbitrary Pydantic models and
    pyqtgraph parameter trees.
  - `SpinBoxSliderParameter`, `ColorTypeParameter`, and `DFTableWidget` are
    reusable Qt/pyqtgraph widgets.
- **Particular**:
  - `CudaVispyConnector` specifically queries VisPy GLIR private registry
    structures (`shared.parser._objects`) for exact OpenGL buffer attributes
    (`_vbo.id`, `_texture.id`).
  - `devices/x_touch_mini/` is specifically tailored to the physical layout,
    MIDI CC mappings, and LED ring modes of the Behringer X-Touch Mini.

## Cross-links

- `agents/mapping/vertical-trace.md` — steps 6–7 describe the execution of
  `CudaVispyConnector.to_gl_buffer()` and parameter tree registration.
- `agents/mapping/config.md` — `config/app.py` inherits `AppSettings` from
  `gui/app_settings.py`; `snngine_config.py` options drive parameter tree docks.
- `agents/mapping/visualization.md` — `VispyConnector` binds to VisPy visuals
  mixed with `VisualMixin`; `CudaVispyConnector` queries `GLBufferTensor` and
  `GLTexture3DTensor`.
- `agents/mapping/construction.md` — `TensorConnector` binds runtime tensors
  from `EngineElement.tensor_dict`.
- `agents/mapping/utils.md` — `ParameterBuilder` reads UI metadata (`FrozenParamOpts`,
  `ParamOpts`) defined in `utils/settings/ui_parameter_options.py`.

## Open questions

Indexed centrally in [`README.md` → Consolidated open questions](README.md#gui):

- [SOLVED] **Circular dependency with `config/`**: `config/app.py` imports `gui/app_settings.py`,
  while `gui/app/engine_app.py` imports `config/app.py` and `snngine_config.py`.
  - **Resolution**: Confirmed package-level cross-coupling, but strictly acyclic at module level.
    The import path forms an acyclic DAG: `utils/settings/config_model.py` -> `gui/app_settings.py` ->
    `config/app.py` -> `snngine_config.py` -> `gui/app/engine_app.py`. Python imports load cleanly without
    recursion. However, placing the base `AppSettings` model in `gui/` instead of `config/` creates an
    architectural cross-dependency where `config/` depends on `gui/`. Moving `AppSettings` into `config/app.py`
    would restore strict unidirectional package layering (`utils` -> `config` -> `gui`).
    See [`README.md#gui`](README.md#gui).
- [SOLVED] **Hardware/headless dependency**: `devices/x_touch_mini/` requires MIDI backend
  libraries (`mido`). In headless CI/cloud environments lacking audio/MIDI subsystems,
  MIDI initialization requires graceful degradation.
  - **Resolution**: Confirmed safely isolated. `XTouchMiniDevice` (`snngine_v4/gui/devices/x_touch_mini/x_touch_mini_device.py:15`)
    is used exclusively inside `devices/x_touch_mini/` for physical MIDI controller integration.
    It is neither imported nor instantiated by `EngineApp` or `MainEngineWindow` during standard application
    startup. Headless simulations and standard GUI runs execute without touching `mido` or requiring MIDI hardware.
    See [`README.md#gui`](README.md#gui).
- [SOLVED] `MainEngineWindow.test_func()` contains commented-out simulation step calls
  (`# self.engine.run_sim(10)`) and an orphaned visual selector call.
  - **Resolution**: Confirmed developer UI test button slot. In `snngine_v4/gui/windows/main_window_base.py:117`,
    `self.test_func` is connected to `buttons_dock.test_button.clicked`. It provides an interactive
    manual test hook in the UI to step the simulation or exercise visual selection during development.
