# visualization/

Vispy-based 3D scene rendering, live GPU plotting, visual construction
machinery, custom OpenGL geometry/volume shaders, and the CUDA/OpenGL
interoperability bridge. All 21 non-empty Python files (~2,690 LOC) across
`visualization/`, `visualization/cuda/gl_interop/`, `visualization/scenes/`,
`visualization/visuals/`, and `visualization/config_models/` were read for
this write-up.

## Files and classes

### CUDA / OpenGL interop layer (`cuda/gl_interop/`)

- **`gl_buffer.py`**
  - `ExternalMemory` — lightweight ctypes wrapper holding device pointer
    and allocation byte size (`__cuda_memory__ = True`).
  - `GLBuffer` — maps an existing OpenGL buffer handle (`opengl_id`) into
    PyCUDA via `pycuda.gl.RegisteredBuffer(opengl_id)` and
    `RegisteredMapping.device_ptr_and_size()`. Exposes `numba_device_array`
    as a `numba.cuda.cudadrv.devicearray.DeviceNDArray`. Tagged
    `hand-written-edge` + `cuda-adjacent`.
  - `GLBufferMap(SingletonDict)` — process-wide registry of active
    `GLBuffer` instances by OpenGL buffer ID; supports bulk unregistration
    via `unregister_all()`.

- **`gl_tensor.py`**
  - `GLBufferTensor` — bridges the numba device array from `GLBuffer` into
    PyTorch via `torch.as_tensor(self.gl_buffer.numba_device_array)`.
    Enables zero-copy tensor operations on OpenGL buffers without CPU
    roundtrips. Exposes `.data_ptr()` for passing device memory addresses
    directly to CUDA kernels.
  - `GLVBOTensor(GLBufferTensor)` (float32 vertex buffers) and
    `GLIBOTensor(GLBufferTensor)` (int32 index buffers). Tagged
    `hand-written-edge`.

- **`gl_texture3d.py`**
  - `GLRegisteredTexture3D(GLBuffer)` — wraps 3D OpenGL textures via
    `pycuda.gl.RegisteredImage(opengl_id, gl.GL_TEXTURE_3D)`.
  - `GLTexture3DTensor(GLBufferTensor)` — the 3D texture exception noted in
    `agents/common.md`. True zero-copy interop was not achieved for 3D
    textures; this class allocates an independent PyTorch tensor
    (`torch.zeros(...)`) and executes explicit GPU-to-GPU copies via
    `pycuda.driver.Memcpy3D()` (`copy_to_texture`, `copy_to_tensor`).
    Tagged `hand-written-edge` + `cuda-adjacent`.

- **`gl_tensor_dict.py`**
  - `GLTensorDict(TensorDict)`, `TensorToGLBufferTensorMap`,
    `StringToGLBufferTensorMap` — dictionary container simultaneously
    indexing registered buffers by string names and by PyTorch tensor
    references. Tagged `generic-machinery`.

### Visual building machinery (`visual_builder.py`, `buffer_utils.py`)

- **`visual_builder.py`** — central builder edge connecting Pydantic visual
  configs to VisPy visuals:
  - `VisualMixin` — mixin applied to VisPy visuals. Injects an `EmitterMap`
    and adds event hooks (`SetAttributeEvent`, `MeshDataChangedEvent`) to
    relay property updates (e.g. `color`, `visible`, scale, translation)
    back to model / parameter tree listeners.
  - `VisualMixins(ClassMixer)` — dynamic class mixer decorating VisPy
    visual classes (`Line`, `Box`, `Markers`, `MeshVisual`, `VolumeVisual`,
    `FiniteGridLinesVisual`) with `VisualMixin`.
  - `VispyVisualBuilder(BuilderDict)` — one of the three confirmed
    `hand-written-edge` implementations described in
    `agents/mapping/config-build-pattern.md`:
    - Maps Pydantic visual configs (`BoxVisualInitConfig`, `FiniteGridConfig`,
      `MarkersVisualConfig`, `LineVisualConfig`, `MultiLinePlotConfig`,
      `VolumeConfig`) to corresponding VisPy classes.
    - Translates engine domain parameters (`Shape3Df32`, `Segmentation3D`,
      `RGBAColor`, `Directions3DBoolPars`) into VisPy-specific keyword
      arguments (`WDHKw`, `WDHSegKw`, RGBA tuples).
    - Recursively processes compound visuals and subvisuals
      (`_make_sub_visual_models`).
    - Applies OpenGL rasterization and depth states (`apply_open_gl_kwargs`).
    - Special-case model coercion: converts `FiniteGridConfig` &rarr;
      `OuterGridVisualInitConfig` and `NetworkReservoirConfig` &rarr;
      `MarkersVisualConfig`.

- **`buffer_utils.py`** — utility functions `is_2d_buffer_array` and
  `adapt_dim` (appends or truncates buffer slices along an axis).

### Scenes and camera management (`scenes/`)

- **`scenes/scene_manager.py`**
  - `SceneManager(BuilderDict)` — central registry mapping
    `VispyCanvasConfig` models to `EngineSceneCanvas` instances.
    Coordinates visual construction (`cls_build_visuals`), camera
    construction via `CameraBuilder`, and maintains `model2model_map`
    and `sub_visual_super_map`. Tagged `generic-machinery`.
  - `CameraBuilder(ModelObjectBuilder)` — builds `EventPanZoomCamera` or
    `EventTurntableCamera` from camera config models.
  - `VispyMap(Model2ObjectMap)` — structured container mapping configuration
    models to built VisPy nodes and subvisual maps.

- **`scenes/main_network_scene.py`**
  - `EngineSceneCanvas(SceneCanvas)` — customized VisPy canvas holding
    references to cameras (`camera_dict`), viewboxes (`view_dict`),
    visual nodes (`visual_node_dict`), and subvisual hierarchies.

- **`scenes/event_camera.py`** & **`scenes/setattribute_event.py`**
  - `EventCameraMixin`, `EventTurntableCamera`, `EventPanZoomCamera` — camera
    subclasses intercepting attribute assignment (`azimuth`, `elevation`,
    `distance`, `fov`, `center`, `roll`, `scale_factor`) to emit
    `SetAttributeEvent`, synchronizing interactive mouse manipulation with
    Pydantic config state.
  - `SetAttributeEvent`, `Set3DAttributeEvent`, `MeshDataChangedEvent` —
    VisPy event definitions.

### Custom visuals (`visuals/`)

- **`visuals/grid_lines.py`**
  - `GSGLLineVisual(_GLLineVisual)`, `GSLineVisual(LineVisual)` — line visual
    subclass accepting custom OpenGL geometry shaders (`gcode`).
  - `MultiBoxLinesVisual(GSLineVisual)` — renders multiple 3D wireframe box
    lattices using a custom geometry shader (`layout (lines) in; layout
    (line_strip, max_vertices=16) out;`) that expands line segments into
    12-edge box wireframes on the GPU.
  - `FiniteGridLinesVisual(BoxVisual)` — compound visual combining a VisPy
    `BoxVisual` with `MultiBoxLinesVisual`. Implements the finite grid VisPy
    rendering workaround documented in `agents/mapping/geometry.md`. Tagged
    `hand-written-edge`.

- **`visuals/volumetric.py`**
  - `R32fVolumeVisual(VolumeVisual)`, `R32fVolume`,
    `CompoundR32fVolumeVisual(CompoundVisual)`, `CompoundR32fVolume` —
    specialized volume visual configuring 3D textures with internal format
    `r32f` for visualizing scalar diffusion fields.

- **`visuals/compound_markers.py`**
  - `CompoundMarkersVisual(CompoundVisual)` — compound marker container with
    preconfigured translucent blending and depth-test GL state.

- **`visuals/plot_lines.py`**
  - Contains commented-out `PlotLine` implementation — tagged `legacy-dead`.

- **`visuals/boxes/`** & **`plotting/`**
  - Directories containing only empty `__init__.py` files — tagged `legacy-dead`.

### Configuration models (`config_models/`)

- **`config_models/vispy_canvas_config.py`**
  - `VispyOpenGLConfig` (color/depth bit depths, double buffering, multisampling).
  - `VispyWidgetConfig`, `VispyViewBoxConfig` (borders, padding, default camera).
  - `SceneViews`, `SceneVisuals`, `SceneCameras` (`ConfigContainerModel` subclasses).
  - `VispyCanvasConfigOptions`, `VispyCanvasConfig` (canvas title, window size,
    fullscreen, vsync, background color). Tagged `config-driven`.

- **`config_models/vispy_camera_configs.py`**
  - `CameraCenter(EnginePos3D)`.
  - `TurnTableCameraParameters` (`fov`, `elevation`, `azimuth`, `roll`, `distance`,
    `translate_speed`, `scale_factor`).
  - `PanZoomCameraParameters`. Tagged `config-driven`.

- **`config_models/visuals/`**
  - `visual_config.py`: `VisualConfig` (`visible`, `pos_origin: EnginePos3D`), `SubVisualConfig`.
  - `mesh.py`: `MeshVisualConfig` (`color: RGBAColorType`).
  - `markers.py`: `MarkersVisualConfig` (`pos: Pos3DVBO`, `size`, `edge_width`,
    `edge_color`, `face_color`). Documents Phase 3 field ownership policies
    (`SHARED_RUNTIME_FIELDS = frozenset({'pos'})`).
  - `boxes.py`: `BoxVisualInitConfig`, `OuterGridVisualInitConfig` (planes,
    face/edge colors, mesh OpenGL state).
  - `lines.py`: `LineVisualConfig`, `XYZAxisVisualConfig`, `MultiBoxLinesVisualConfig`.
  - `parameters.py`: `RGBAColor`, `RGBAEnum`, `WDHKw`, `WDHSegKw`, `VispyKeyWords`,
    `OpenGLState`, `OpenGlStateType`.

- **`config_models/plotting/multi_line_plot.py`**
  - `PlotViewMode(IntEnum)` (`DOCKED`, `WINDOWED`, `SCENE`, `NONE`).
  - `LinePlotConfigBase`, `PlotConfig`, `SepLineData`.
  - `MultiLinePlotConfig` (voltage traces, `n_plots`, `size_x`, `sep_lines`, `map`).
  - `MultiScatterPlotConfig` (spike event scatter rasters). Tagged `config-driven`.

## Relationships within the subpackage

`VispyCanvasConfig` specifies views, visuals, and cameras. `SceneManager`
instantiates `EngineSceneCanvas`, builds cameras via `CameraBuilder`, and
invokes `VispyVisualBuilder` to convert visual configuration trees into
VisPy `VisualNode` instances.

The interop layer (`cuda/gl_interop/`) operates as a downstream bridge:
VisPy visuals allocate OpenGL buffer objects (VBOs, IBOs, 3D textures) first.
`gui/parameter_trees/cuda_connector.py` reads those OpenGL IDs from VisPy's
GLIR parser, passing them to `GLBufferTensor` / `GLTexture3DTensor`, which
PyTorch wraps and passes directly to CUDA simulation kernels.

## Generic vs. particular

- **Generic**:
  - `SceneManager`, `CameraBuilder`, and `VispyVisualBuilder` implement the
    declarative builder pattern (`BuilderDict`, `ModelObjectBuilder`).
  - `VisualMixins` and `EventCameraMixin` generically attach event emitters
    to arbitrary VisPy classes.
- **Particular**:
  - `VispyVisualBuilder.get_model()` hardcodes direct mapping conversions
    for domain classes `FiniteGridConfig` and `NetworkReservoirConfig`.
  - `GLTexture3DTensor` hardcodes a 3D float32 texture structure and
    explicit `pycuda.driver.Memcpy3D` parameters because generic zero-copy
    was not possible.
  - `MultiBoxLinesVisual` embeds custom GLSL geometry shader source directly
    in Python strings to draw wireframe grid boxes.

## Cross-links

- `agents/mapping/vertical-trace.md` — steps 4–7 detail the exact VisPy
  visual construction and `GLBufferTensor` wrapping sequence traced in
  the `N_pos` case study.
- `agents/mapping/config-build-pattern.md` — analyzes `VispyVisualBuilder`
  as one of the three confirmed hand-written builder edges.
- `agents/mapping/geometry.md` — `FiniteGridLinesVisual` is the built
  visual counterpart of `FiniteGridConfig`, resolving the rendering
  workaround for finite grid visualization.
- `agents/mapping/chemistry.md` — `ChemicalConcentrationVolume` relies on
  `CompoundR32fVolumeVisual` and `GLTexture3DTensor`.
- `agents/mapping/nn.md` — `Simulator` plots (`voltage_plot`,
  `firings_scatter_plot`) map to `MultiLinePlotConfig` and `PlotElement`.
- `gui/` (not yet mapped) — `CudaVispyConnector` and `VispyConnector` query
  VisPy GLIR handles and bind visual properties to parameter trees.

## Open questions

Indexed centrally in [`README.md` → Consolidated open questions](README.md#visualization):

- [SOLVED] `visuals/plot_lines.py` is entirely commented out (`legacy-dead`), and
  the directories `visuals/boxes/` and `plotting/` contain only empty
  `__init__.py` files.
  - **Resolution**: Confirmed legacy dead code and orphaned package stubs.
    1. `PlotLine` in `snngine_v4/visualization/visuals/plot_lines.py:1-27` was superseded by
       standard VisPy scene visuals (`vispy.scene.visuals.Line`) instantiated and wired via
       `VispyVisualBuilder.BUILDER_OBJECT_CLASS_MAP[MultiLinePlotConfig]` (`visual_builder.py:336`).
    2. Box visual implementations live in `snngine_v4/visualization/visuals/boxes.py` (a single module),
       leaving `visuals/boxes/` as an empty folder with a 0-byte `__init__.py`.
    3. Plotting models live in `config_models/plotting/`, while plot visuals use built-in VisPy visuals,
       leaving `snngine_v4/visualization/plotting/` as an unused empty package stub.
    See [`README.md#visualization`](README.md#visualization).
- [SOLVED] `OuterGridVisualInitConfig.color` defaults to `None` while `edge_color`
  defaults to `'white'`. This causes the bounding box faces to remain
  invisible by default (wireframe-only), which appears intentional for a
  bounding cage but is not documented.
  - **Resolution**: Confirmed intentional visualization design.
    `OuterGridVisualInitConfig` (`snngine_v4/visualization/config_models/visuals/boxes.py:51-72`) defines
    the outer bounding box enclosing the 3D finite grid (the neural reservoir and chemical volume).
    If `color` was opaque or non-None, the faces of the outer bounding box would render as solid surfaces,
    completely occluding internal neurons, synapses, and chemical volume data inside the grid.
    Defaulting `color = None` and `edge_color = 'white'` renders a transparent wireframe cage.
    See [`README.md#visualization`](README.md#visualization).
- [SOLVED] `VispyVisualBuilder.get_model` has hard-coded `isinstance` branches for
  `FiniteGridConfig` and `NetworkReservoirConfig`. This tightly couples
  the visual builder to specific domain models outside `visualization/`.
  - **Resolution**: Confirmed adapter layer by design. In `snngine_v4/visualization/visual_builder.py:463-477`,
    `VispyVisualBuilder.get_model` transforms domain simulation models into visual configuration models
    (`FiniteGridConfig` -> `OuterGridVisualInitConfig`, and `NetworkReservoirConfig` -> `MarkersVisualConfig(pos=dump['pos'])`).
    Because `VispyVisualBuilder` inherits from `ModelObjectBuilder`, which keys builder mappings by input model
    class, this hook acts as a domain-to-visual adapter so callers can pass domain models directly without
    manually instantiating visual configs. Documented in `config-build-pattern.md` as a hand-written builder edge.
    See [`README.md#visualization`](README.md#visualization).
- [SOLVED] `GLTexture3DTensor` copying remains synchronous with explicit `torch.cuda.synchronize()`
  calls and `TODO: Restrict copying to actually modified data` notes in the
  method body.
  - **Resolution**: Hardware constraint and planned optimization. In `GLTexture3DTensor`
    (`snngine_v4/visualization/cuda/gl_interop/gl_texture3d.py:75-125`), OpenGL 3D textures are backed
    by non-linear driver-managed memory (`CUDA_ARRAY3D` via `pycuda.gl.RegisteredImage`), which PyTorch
    cannot wrap directly as a contiguous zero-copy strided tensor. A separate linear PyTorch tensor is
    allocated, and `pycuda.driver.Memcpy3D()` synchronizes data between PyTorch and OpenGL.
    `torch.cuda.synchronize()` ensures asynchronous PyTorch compute finishes before PyCUDA initiates the 3D
    texture copy. The `TODO` note is a future optimization to copy sub-volume bounding boxes rather than the
    entire 3D volume at each step.
    See [`README.md#visualization`](README.md#visualization).
