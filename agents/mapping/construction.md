# construction/

`nn_builder.py` (`NetworkBuilder`) builds a network from a config/template
into runtime objects (`engine_element.py`, `engine_element_config.py`).
This is the generic config→build machinery already described at a
conceptual level in `agents/mapping/config-build-pattern.md`; this file
grounds that description per-file. Three non-empty files (plus an empty
`__init__.py`), all fully read for this write-up.

## Files and classes

- **`engine_element_config.py`** — the config-side mixin and base class.
  - `EngineElementConfigMixin`: four filtering accessors —
    `elt_dict`/`elt_values` (fields typed as `EngineElementConfigMixin`
    itself) and `tdf_dict`/`tdf_values` (fields typed as `SeriesModel`,
    from `utils/data_utils/dataframe_config.py`, not opened this pass).
    Both delegate to `self.filtered_model_dict`/`filtered_model_values`
    (defined on `ConfigModel`, `utils/settings/config_model.py`, also not
    opened). Tagged `generic-machinery`.
  - `EngineElementConfig(ConfigModel, EngineElementConfigMixin)`: adds a
    nested `Slots.INITIALIZER` class var and a `reset_array` staticmethod
    that zeroes out a data array in place, handling two shapes of input
    (`value` as a raw dict vs. an object exposing `.data`/`.zeroes(...)`).
  - `EngineElementConfig3D(EngineElementConfig, Object3DConfig)`: a bare
    combination of engine-element config behavior with 3D positioning
    (`geometry/spatial_pars.py`'s `Object3DConfig`, confirmed in
    `agents/mapping/geometry.md`). Notably, `chemistry.md`'s
    `ChemicalConcentrationModel` does **not** subclass this; it instead
    combines `VolumeConfig` (itself an `Object3DConfig` subclass) with
    `EngineElementConfigMixin` directly. So there are two coexisting
    routes to the same "positioned + buildable" combination — see Open
    questions.

- **`engine_element.py`** — the runtime side, and the largest file here.
  - `EngineNodesConfig(ModelNodeTreeElementConfig)`/`EngineNodes(ModelTree)`
    (both from `utils/containers/node_map.py`, not opened): config and
    tree-walking classes for `EngineElement.node_tree`. `EngineNodes`
    pins an `InvertedConfigClass` class var to `(EngineNodesConfig,
    EngineElementConfigMixin)`; what specifically "inverted" refers to
    here isn't confirmed without reading `node_map.py` — see Open
    questions.
  - A commented-out `UndefinedEngineElement(BuilderDict)` stub — tagged
    `legacy-dead`.
  - `EngineElement(BuilderDict)`: the generic builder base already
    introduced in `config-build-pattern.md`
    (`BUILDER_OBJECT_CLASS_MAP`/`BUILDER_OBJECT_SUPERCLASS_MAP`). Reading
    the full class surfaces several things not previously grounded:
    - `BUILDER_OBJECT_SUPERCLASS_MAP`'s three generic dataframe→tensor
      conversions carry an explicit `# Keep order (n/3)` comment,
      implying the matching order against these types matters (most
      likely first-match against an MRO walk in the underlying object
      builder, `utils/object_builder/`, not opened) — tagged
      `generic-machinery`, ordering mechanism itself unconfirmed.
    - `__init__` accepts either a single `model` (config and build model
      combined) or a separate `config`/`build_model` pair (mutually
      exclusive, enforced by `raise ValueError`); if only `config` is
      given, `build_model` defaults to
      `config.tdf_values() + config.elt_values()` — a direct, concrete
      use of `EngineElementConfigMixin`'s filtering methods to decide
      what actually gets built.
    - **Class-level mutation via `update_builder_class_attributes`**: for
      any non-root `EngineElement`, `__init__` calls
      `self.BUILDER_OBJECT_CLASS_MAP.update(other.BUILDER_OBJECT_CLASS_MAP)`
      (and the same for the other three builder-map class vars). Since
      these are `ClassVar` dicts, `.update()` mutates the dict object
      shared by the whole class, not a per-instance copy — constructing
      one non-root element merges maps onto every instance of that
      class, not just itself. Not confirmed whether this is deliberate
      (a way of propagating a parent's builder-map extensions downward)
      or an unintended shared-mutable-state side effect — see Open
      questions.
    - `curand_states` is only allocated when `n_curand_states > 0` and
      `b_cuda_backend_available` is true; tagged `cuda-adjacent`
      (imports the compiled `nn.cuda_backend.snn_utils` module inside a
      `try/except ModuleNotFoundError`, matching the graceful-degradation
      convention already noted in `architecture-snngine_v4.md`).
    - `__setattr__` intercepts any `TensorSeries`/`TensorDict`/
      `torch.Tensor`-valued attribute (except `tensor_dict` itself),
      mirrors it into `self.tensor_dict[key]`, and — specifically for
      `TensorSeries`/`TensorDict` values — raises `PermissionError`
      ("missing configuration for '...'") if the attribute doesn't exist
      yet, the value is already present in `self.inv` (`BuilderDict`'s
      own inverse map), and `self.config` has no matching field. This is
      a **separate** ownership-enforcement mechanism from the
      `SHARED_RUNTIME_FIELDS`/`set_attr` check documented in
      `config-build-pattern.md` (that one lives in
      `gui/parameter_trees/connectors/object2object_links.py`); not
      confirmed how, or whether, the two interact — see Open questions.
    - `__setitem__` forwards every set into `root_element` too (unless
      `self` already is the root), keeping a flat root-level registry in
      sync with each element's own local storage.
    - `cuda_gl_dict` (property): `self.cuda_opengl_map[self.config]` —
      this is exactly what `chemistry.md`'s
      `ChemicalConcentrationVolume.texture_3d`/`texture_3d_tensor`
      build on, confirming `ChemicalConcentrationVolume` is a direct
      `EngineElement` subclass using this base-class property, not
      reimplementing its own lookup.
    - `make_object_kwargs` (classmethod): strips `node_tree`/
      `root_element`/`parent_element` kwargs whenever the object being
      built isn't itself an `EngineElement` subclass — this is precisely
      why `chemistry.md`'s `FiniteGrid` (a plain class, not an
      `EngineElement`) can be built through the same generic map without
      needing tree/parent wiring.
    - `cuda_opengl_map`/setter: delegates through
      `root_element._cuda_opengl_map`; the setter raises `AttributeError`
      if already set — single-assignment-once, enforced only at the
      root element.
    - `parent_element` (a method, not a property, despite the
      `PARENT_ELEMENT_KW = 'parent_element'` constructor-kwarg name it
      shares): computes the parent lazily via
      `self.node_tree.parent(self.config)` rather than returning a
      stored reference. Not confirmed whether this is guaranteed
      consistent with whatever `parent_element` value was actually
      passed into `__init__` — see Open questions.
    - `set_tensor_attr`: for each field in `config.tdf_dict()`/
      `config.elt_dict()` already present in `self` (the `BuilderDict`
      container), does `setattr(self, key, self[model])` — the step that
      turns built sub-objects into named attributes on the element
      itself, e.g. what ultimately gives `ChemicalConcentrationVolume`
      its populated instance attributes.
    - `validate_consistency`: an empty `pass` stub; no override was found
      in any subpackage read so far (`chemistry/`, `geometry/`,
      `construction/` itself) — see Open questions.

- **`nn_builder.py`** — `NetworkBuilder(BuilderDict)`, the top-level
  concrete builder, already introduced conceptually in
  `config-build-pattern.md`.
  - `BUILDER_OBJECT_CLASS_MAP` has exactly one live entry,
    `SpatialNetworkConfig: SpatialNetwork`, plus a commented-out
    `# FiniteGridConfig: FiniteGrid` — concrete evidence that grid
    building was once wired (or considered) at this top level, rather
    than per-instance the way `chemistry/`'s
    `ChemicalConcentrationVolume` does it today (its own instance-level
    `BUILDER_OBJECT_CLASS_MAP` addition, confirmed in `chemistry.md`).
    Not confirmed which came first, or why the mapping moved — see Open
    questions.
  - `OBJECT_INIT_SUPER_TYPES = {SpatialNetworkConfig:
    ObjectInitializationType.MODEL_AND_KWARGS}` — a different
    initialization strategy than `EngineElement`'s own
    `DEFAULT_OBJECT_INIT_TYPE` of `.MODEL`; the behavioral difference
    between the two isn't confirmed (`utils/object_builder/` not opened
    this pass).
  - `clear()`: beyond the base `BuilderDict.clear()`, additionally
    records `container_model_class` and then `del self.container_model`
    entirely — clearing doesn't just empty the container, it removes the
    config reference outright, so a subsequent `build()` must supply a
    model again to reconstruct one.
  - `build(m=None, **kwargs)`: when `m` is a pydantic `BaseModel`,
    deep-copies and re-dumps it (the "deep-copies and re-dumps it" step
    already mentioned in `config-build-pattern.md`, now grounded exactly:
    `deepcopy` → `.model_dump()` → re-instantiate
    `container_model_class(**dump)`), then walks every field key of the
    freshly-built `container_model` and asserts each field's value (or,
    for list/tuple fields, every element) is already a built key in
    `self` — an internal consistency check confirming the build actually
    populated everything the config declared. When `m` is given but
    isn't a `BaseModel`, this whole reconstruction-and-check path is
    skipped in favor of a plain `self.update(m)`.

## Relationships within the subpackage

`engine_element_config.py` is the config side (`EngineElementConfig`,
`EngineElementConfig3D`, the `EngineElementConfigMixin` filtering
methods); `engine_element.py`'s `EngineElement` is the one generic
runtime base every domain `EngineElement` subclass extends
(`ChemicalConcentrationVolume` from `chemistry/` confirmed as one such
subclass); `nn_builder.py`'s `NetworkBuilder` is a second, sibling
`BuilderDict` subclass — not an `EngineElement` itself, but the top-level
entry point that walks `EngineConstructionConfig`
(`config/template.py`, not yet mapped) into the whole runtime graph,
`EngineElement` instances included.

## Generic vs. particular

Overwhelmingly generic-machinery, consistent with
`config-build-pattern.md`'s description: every class in this subpackage
is either config-filtering machinery, the one generic `EngineElement`
builder base, or `NetworkBuilder`'s (also generic) top-level driving
logic. The one hand-written/particular edge inside the subpackage itself
is the CUDA-backend availability check (`b_cuda_backend_available`,
`curand_states`) — a `try/except ModuleNotFoundError` around a compiled
pybind11 extension, matching edge (1) from `config-build-pattern.md`
(nothing here is model-driven; it's a fixed import boundary).

## Cross-links

- `agents/mapping/config-build-pattern.md` — the conceptual description
  this file grounds per-class; read that first for the overall
  generic/particular framing.
- `agents/mapping/chemistry.md` — `ChemicalConcentrationVolume` is a
  concrete `EngineElement` subclass; its `cuda_gl_dict`/`texture_3d`
  properties are direct uses of `EngineElement.cuda_gl_dict`, and its own
  `BUILDER_OBJECT_CLASS_MAP` addition is the per-instance counterpart to
  `nn_builder.py`'s now-commented-out top-level grid mapping.
  `FiniteGrid` (not an `EngineElement`) is the concrete case
  `make_object_kwargs`'s kwarg-stripping branch exists for.
- `agents/mapping/geometry.md` — `EngineElementConfig3D` combines with
  `geometry/spatial_pars.py`'s `Object3DConfig`; contrast with
  `chemistry/`'s different route to the same combination (see Open
  questions).
- `config/template.py` (not yet mapped) — `EngineConstructionConfig`,
  the model type `NetworkBuilder.__init__`/`build` operate on.
- `utils/object_builder/`, `utils/containers/node_map.py`,
  `utils/cuda_utils/` (not yet mapped) — `BuilderDict`,
  `ObjectInitializationType`, `ModelTree`, `TensorDict`/`TensorSeries`/
  `TensorDataFrame` are all defined there; this subpackage consumes but
  doesn't define them.

## Open questions

- `update_builder_class_attributes` mutates `ClassVar` dicts in place
  (`.update()`), affecting the whole class, not just the constructing
  instance. Concretely: two sibling non-root `EngineElement` instances
  of the *same* subclass, constructed under different parents with
  different builder-map extensions, could end up sharing a merged map
  neither parent intended, since the underlying dict object is shared
  class-wide. Not confirmed whether this is deliberate.
- `EngineElement.__setattr__`'s `PermissionError` check and
  `config-build-pattern.md`'s documented `SHARED_RUNTIME_FIELDS`/
  `object2object_links.py` check are two distinct ownership-enforcement
  mechanisms found in two different files. Not confirmed whether they're
  meant to compose, overlap, or guard genuinely different cases.
- `parent_element` (method) computes the parent lazily from
  `node_tree.parent(self.config)`, independent of whatever
  `parent_element` value was actually passed to `__init__`. Not
  confirmed these are guaranteed to agree in all cases.
- `validate_consistency` is an empty stub with no confirmed override
  anywhere read so far. Not confirmed whether it's genuinely unused or
  overridden in an unread subpackage (`nn/`, `visualization/`).
- `nn_builder.py`'s commented-out `FiniteGridConfig: FiniteGrid` entry
  suggests grid construction moved from a top-level mapping to a
  per-instance one (as seen in `chemistry/`). Not confirmed which came
  first or why.
- `EngineNodes.InvertedConfigClass`'s "inverted" naming isn't explained
  by this subpackage alone; not confirmed without reading
  `utils/containers/node_map.py`.
- Two coexisting routes to a "positioned + buildable" config combination
  exist: `EngineElementConfig3D(EngineElementConfig, Object3DConfig)`
  here, versus `chemistry/`'s `ChemicalConcentrationModel(VolumeConfig,
  EngineElementConfigMixin)` (a lighter mixin, not the full
  `EngineElementConfig` base). Not confirmed whether this is an
  intentional distinction (e.g. based on whether `reset_array`/`Slots`
  are needed) or drift between two ways of expressing the same thing.
