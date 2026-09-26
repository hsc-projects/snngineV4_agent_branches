# utils/

Foundational infrastructure subpackage: declarative object builder machinery,
type-enforced container abstractions, dual-backed CPU/GPU tensor dataframes,
Pydantic configuration models with XML/HDF5 serialization, numpy array
validation interfaces, and introspection utilities. All 33 non-vendored Python
files (~5,665 LOC) were read for this write-up; the vendored `deepdish_pack`
(HDF5 utility) is noted as an external dependency.

## Files and classes

### Object builder machinery (`object_builder/`)

- **`object_builder.py`**
  - `ModelObjectBuilder` — the generic, reflective factory engine central to
    the architecture described in `agents/mapping/config-build-pattern.md`.
    Maintains class mappings (`BUILDER_OBJECT_CLASS_MAP`,
    `BUILDER_OBJECT_SUPERCLASS_MAP`, `BUILDER_OBJECT_CLASS_MIXER`).
    Builds single objects via `cls_build_obj()` returning a `BuildResult(built, model, kwargs)`,
    and walks nested configuration trees via `cls_build_container()` returning
    a `ContainerBuildResult`. Supports three initialization signatures
    defined by `ObjectInitializationType` (`KWARGS`, `MODEL`, `MODEL_AND_KWARGS`).
    Tagged `generic-machinery`.

- **`object_builder_dict.py`**
  - `BuilderDict(Model2ObjectMap, ModelObjectBuilder)` — merges declarative
    dictionary storage with builder execution. Intercepts `add_build()` to
    construct runtime objects from Pydantic models, store them indexed by model,
    and register them into an attached `ModelTree` (`node_tree`). Base class
    for `NetworkBuilder`, `VispyVisualBuilder`, and `SceneManager`. Tagged
    `generic-machinery`.

### Container hierarchy (`containers/`)

- **`configurable_container.py`** & **`configurable_dict.py`** & **`configurable_list.py`**
  - `ContainerConfig(ConfigModel)` — frozen Pydantic specification defining
    strict collection behavior: type constraints (`allowed_types`, `forbidden_types`),
    mutation permissions (`b_duplicates_allowed`, `b_replace_allowed`,
    `b_pop_allowed`, `b_clear_allowed`), and identity-based deduplication
    (`b_duplicate_key_check_by_id`, `b_duplicate_value_check_by_id`).
  - `ConfigurableDict(UserDict)` and `ConfigurableList(UserList)` — collections
    strictly governed by `ContainerConfig`. Disallow unpermitted operations
    (raising `PermissionError` on unauthorized `clear()` or `pop()`).
  - `SingletonDict(ConfigurableDict)` — singleton variant used for system-wide
    registries (e.g. `GLBufferMap`, `PresetsContainer`). Tagged `generic-machinery`.

- **`mappings.py`**
  - `Object2ObjectMap(ConfigurableDict)` — bidirectional mapping maintaining
    an automatic inverse map (`self.inv`) and a reference list (`self.refs`).
  - `Model2ObjectMap(Object2ObjectMap)` — specialized mapping where keys are
    Pydantic `BaseModel` instances and values are constructed runtime objects.
    Tagged `generic-machinery`.

- **`node_map.py`** & **`typed_node.py`** & **`super_maps.py`**
  - `TreeNode`, `NodeTree(Object2ObjectMap)`, `ModelTree` — tree hierarchy
    tracking parent/child relationships between models and runtime objects.
    Enforces root freezing and categorizes unattached nodes in `free_elements`.
  - Underpins `EngineNodes` in `construction/engine_element.py`.

### CUDA utilities and tensor dataframes (`cuda_utils/`)

- **`tensor_dataframe.py`**
  - `TensorSeries`, `TensorDataFrame` — dual-backed data structures maintaining
    a CPU `pandas.DataFrame` / `Series` synchronized with a GPU `torch.Tensor`
    (`gpu_values`).
  - Allows semantic, named row/column access via `IndexConfig` / `RowOrColumn`
    while exposing `.data_ptr()` for raw device memory transfer into CUDA
    kernels. Used for `NeuronState` (`N_flags`, `N_props`) and synapse counts.
    Tagged `cuda-adjacent` + `hand-written-edge`.

- **`tensor_dict.py`**
  - `TensorDict(Object2ObjectMap)` — multi-indexed dictionary supporting dual
    lookup by string name and PyTorch tensor reference. Manages 3D tensor
    slices (`update_from_dataframe_3d_config`) and device synchronization
    (`sync_to_cpu`). Used for group-to-group interaction matrices. Tagged
    `cuda-adjacent`.

- **`cuda_functions.py`**
  - `simplify_device()`, `compare_devices()`, `assert_device_equivalency()`.
  - `CudaVariables(metaclass=Singleton)` and memory diagnostics
    `save_current_allocated_memory()`, `print_allocated_memory_diff()`.

### Configuration models and serialization (`settings/`)

- **`config_model.py`** & **`config_model_base.py`**
  - `ConfigModel(BaseModel, ConfigModelMixin)` — standard base model across
    the engine, configured with strict typing, enum value handling, assignment
    validation, and extra-class polymorphism (`post_init_process_extra_classes()`).
  - `ConfigContainerModel(ConfigModel)` — container model with `extra='allow'`.
  - `ConfigModelMixin` — provides reflective introspection (`cls_model_keys`,
    `filtered_model_dict`, `filtered_model_dump`), validation hooks, and XML
    submodel exporting (`_export_submodels`).
  - Implements default `_xml_file_paths()` which resolves `{field}.xml`
    patterns, resolving the open question noted in `agents/mapping/config.md`.
    Tagged `config-driven` + `generic-machinery`.

- **`xml_settings.py`** & **`xml_converter/`**
  - `XMLSettingsModel(BaseSettings, ConfigModelMixin)`, `XMLSettingsContainerModel`
    — bridges Pydantic models to filesystem storage by registering
    `XMLConfigSettingsSource`.
  - `xml_converter/` (`XMLConverter`, `XMLSettingsSource`, `XMLConverterOptions`)
    — custom parser converting between XML element trees and Pydantic models.
    Drives `.snngine/*.xml` configuration persistence.

- **`ui_parameter_options.py`**
  - `ParamOpts`, `FrozenParamOpts`, `SpatialParUIOpts` — UI presentation metadata
    attached to config classes (`parameter_ui_opts`), controlling expanded/collapsed
    states, numeric grouping, and read-only flags in PyQtGraph parameter trees.

### Data utilities and array validation (`data_utils/`)

- **`dataframe_config.py`** & **`index_config.py`**
  - Typed Pydantic models for array/tabular configurations: `SeriesModel`,
    `TypedDataFrameModel`, `DataFrameF32`, `DataFrameI32`, `DataFrameF32D3`,
    `DataFrameI32D3`.
  - `IndexConfig`, `RowOrColumn`, `Row`, `RowF32`, `Column` — declarative
    schema definitions for tabular rows and columns, with initial scalar defaults.

- **`interval_utils.py`**
  - Interval math and bounds checking helpers (`make_interval`, `validate_interval`).

- **`validation/`**
  - `array_annotation.py` (`ArrayInterfaces`, `f32_3D`, `Bool1D`, `i32_2D`, `Pos3DVBO`)
    — validation types enforcing exact numpy dimensions and dtypes in Pydantic models.
  - `dtype_annotation.py` (`UInt8`, `UInt64`, `Float32`).
  - `np_interface.py` (`TypedNumpyInterface`), `array_io.py` (`ArrayDictRW`).

- **`deepdish_pack/`**
  - Vendored copy of `deepdish` (HDF5 serialization library). Tagged `legacy-dead`-adjacent
    (referenced in `config_model_base.py` for `.h5` export, but the call is commented out).

### Root-level helpers

- **`class_mixer.py`**
  - `ClassMixer(SingletonMap)` — dynamic class generation caching mixin compositions
    via `type(name, (class_item, *mixins), kwargs)`. Used by `VisualMixins` in
    `visualization/visual_builder.py`. Tagged `generic-machinery`.

- **`core_utils.py`**
  - `PostInitCaller`, `FrozenPostInitCaller` (attribute freezing/unfreezing),
    `type_assertion`, `get_intenum_member`, `ConvertingEnum`, `Singleton`.

- **`field_utils.py`**
  - 620+ lines of field introspection, annotation inspection (`b_is_annotated`,
    `extract_basemodel_from_annotation`), default value extraction, and dictionary
    manipulation. Imports `pyqtgraph` directly at module level.

- **`list_parameter_model.py`**
  - `ListParameterModel(ConfigModel)` — encapsulates discrete parameter choices
    (`limits: list`, `value: str`).

## Relationships within the subpackage

`object_builder/` relies on `containers/mappings.py` (`Model2ObjectMap`) and
`settings/settings_keywords.py`. `settings/` builds on `data_utils/` for array
annotations and HDF5 IO. `cuda_utils/` bridges `data_utils/` tabular models
(`TypedDataFrameBase3D`) to GPU memory (`torch.Tensor`).

Together, these components form the substrate upon which all higher-level
subpackages (`construction/`, `geometry/`, `chemistry/`, `nn/`, `visualization/`,
and `gui/`) are built.

## Generic vs. particular

- **Generic**: Virtually the entire subpackage is abstract, reusable framework code
  designed to operate on arbitrary Pydantic schemas, VisPy visuals, and CUDA tensors.
- **Particular**:
  - `field_utils.py` directly imports `pyqtgraph`, coupling generic reflection
    helpers to a specific GUI framework.
  - `config_model_base.py._xml_file_paths()` specifically accounts for `{field}.xml`
    naming conventions designed for `.snngine/` presets.
  - `data_utils/validation/array_annotation.py` explicitly defines domain-specific
    VBO buffer types (`Pos3DVBO`, `Pos2DVBO`).

## Cross-links

- `agents/mapping/config-build-pattern.md` — analyzes `ModelObjectBuilder` and
  `BuilderDict` as the engine's core generic construction pattern.
- `agents/mapping/construction.md` — `EngineElement` inherits `BuilderDict` and
  `EngineNodes` wraps `ModelTree`.
- `agents/mapping/config.md` — `EngineConfig` inherits `XMLSettingsModel`;
  the `_xml_file_paths()` implementation in `config_model_base.py` explains
  the per-field XML split mechanism.
- `agents/mapping/nn.md` — `NeuronState` and `Synapses` use `TensorDataFrame`
  and `TensorDict` for GPU/CPU synchronized state representations.
- `agents/mapping/visualization.md` — `VispyVisualBuilder` inherits `BuilderDict`
  and uses `ClassMixer` to compose `VisualMixin`.
- `gui/` (not yet mapped) — parameter trees directly read `parameter_ui_opts`
  and `FrozenParamOpts` defined in `utils/settings/ui_parameter_options.py`.

## Open questions

Indexed centrally in [`README.md` → Consolidated open questions](README.md#utils):

- [SOLVED] `field_utils.py` imports `pyqtgraph` at module level, coupling core data reflection
  utilities to the GUI framework.
  - **Resolution**: Confirmed intentional equality helper reuse with unintended framework coupling.
    In `snngine_v4/utils/field_utils.py:14,622`, `is_equal(a, b)` delegates fallback comparison to
    `pyqtgraph.functions.eq(a, b)` to safely compare heterogeneous objects (NumPy arrays, PyTorch
    tensors, Qt objects, Pydantic models) without triggering Python's ambiguous-truth-value `ValueError`.
    However, importing `pyqtgraph` at module level couples headless data utilities to Qt.
    See [`README.md#utils`](README.md#utils).
- [SOLVED] `deepdish` is vendored under `data_utils/deepdish_pack/`, but the call to save
  arrays to `.h5` files in `config_model_base.py` (lines 113–116) is commented out.
  Not confirmed whether HDF5 persistence for array fields is planned future work
  or abandoned.
  - **Resolution**: Confirmed active on read, dormant on write. The reading pipeline is fully wired:
    `XMLConfigSettingsSource.cls_read_files` (`snngine_v4/utils/settings/xml_converter/xml_settings_source.py:114-122`)
    checks for companion `.h5` files and deserializes binary array fields via `ArrayDictRW.extract_arrays`
    (`snngine_v4/utils/data_utils/validation/array_io.py:103`), which calls `deepdish.io.load()`.
    Automatic saving of companion `.h5` files during XML export was temporarily commented out in
    `snngine_v4/utils/settings/config_model_base.py:113-116` during migration to prevent creating unneeded
    binary files for minimal presets.
    See [`README.md#utils`](README.md#utils).
- [SOLVED] `ContainerConfig` defaults `b_clear_allowed=False` and `b_replace_allowed=False`.
  This enforces strict immutability by default, requiring explicit `b_force=True`
  overrides when rebuilding engine elements.
  - **Resolution**: Confirmed defensive architectural design. Containers in `snngine_v4` hold live
    GPU allocations, PyTorch tensor views, and GUI parameter bindings. Permitting silent replacements
    or uncoordinated clears (`b_replace_allowed=True`, `b_clear_allowed=True`) would orphan mapped GPU/VBO
    memory or invalidate active UI bindings. Containers that legitimately require clearing explicitly
    opt in via subclassing (e.g. `NetworkBuilder.ContainerConfigClass.b_clear_allowed = True` in
    `snngine_v4/construction/nn_builder.py:23`).
    See [`README.md#utils`](README.md#utils).
