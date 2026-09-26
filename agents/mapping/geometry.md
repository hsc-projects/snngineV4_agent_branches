# geometry/

Spatial parameters, volume shapes (`VolumeShapeHDW`), and a `grid/`
submodule — spatial layout for neurons/elements. Six non-empty files (plus
two empty `__init__.py`s), all fully read for this write-up.
`geometry/volume.py` was already read during the `chemistry/` session (see
`agents/mapping/chemistry.md`); it's covered here rather than duplicated.

## Files and classes

- **`spatial_pars.py`** — the base spatial vocabulary, no grid logic.
  - `Ax2D`/`Ax3D`/`AxDir3D` (`IntEnum`s): axis and signed-direction
    indices. `AxDir3D.vispy_name_alias` maps each direction to VisPy's own
    `'+x'`/`'-x'`-style axis-name strings — tagged `hand-written-edge`
    (a fixed translation table to an external library's naming
    convention).
  - `XYZPars(SeriesModel)`: a 3-element `data` array addressable by axis
    name (`'X'`/`'Y'`/`'Z'`) or index via `Ax3D`. A commented-out
    alternate implementation (as a plain `ConfigModel` with `X`/`Y`/`Z`
    scalar fields instead of an array) is left in place — tagged
    `legacy-dead`.
  - `Shape3Di32`/`Shape3Df32`/`Segmentation3D` (all `XYZPars` subclasses):
    int/float shape triples and a segmentation triple (default `(10, 10,
    10)`). `Shape3Di32.model_post_init` is meant to reject non-positive
    values, but does `raise ValidationError(f"...")` directly with a
    single string argument — pydantic's `ValidationError` normally
    expects structured error data, not a bare string, so this likely
    raises a `TypeError` rather than the intended validation error. See
    Open questions.
  - `EnginePos3D(XYZPars)`: declares a nested `Slots.POS_ORIGIN =
    'pos_origin'` class var; the base `Slots` class itself lives in
    `SeriesModel` (`utils/data_utils/dataframe_config.py`, not read for
    this pass — cross-subpackage dependency, see Cross-links).
  - `Object3DConfig(ConfigModel)`: `pos_origin: EnginePos3D` — the shared
    base every positioned config extends (`chemistry.md`'s `VolumeConfig`
    included, confirmed there already).
  - `Directions3DBoolPars`: six named booleans (`XP`/`XM`/`YP`/.../`ZM`,
    matching `AxDir3D`'s members) — presumably per-face flags (e.g.
    boundary conditions), tagged `config-driven`; no consumer of this
    class was found inside `geometry/` itself (see Open questions).
  - `Pos2DVBO`/`Pos3DVBO`: type aliases via
    `ArrayInterfaces().vbo_array_type(n)` — named after VisPy's
    Vertex Buffer Object concept, tagged `hand-written-edge` (a type
    shaped for a specific external rendering API, defined here for reuse
    by config models elsewhere), though no direct usage of either alias
    was found within `geometry/` itself.

- **`grid/finite_grid_config.py`** — the grid's own config side.
  - `TechnicalValues`: one field, `max_z` (default `100`) — a rendering
    technicality (see `FiniteGrid._make_pos` below), not a physical grid
    parameter.
  - `LinkedFiniteGridConfig(ConfigModel)`: holds a `parent_config:
    Object3DConfig` (excluded from serialization) and forwards
    `pos_origin` from it; declares `shape`/`seg` as properties that
    `raise NotImplementedError` — an abstract base meant to be
    subclassed. `chemistry.md`'s `LinkedVolumeGridConfig` (defined in
    `geometry/volume.py`) is exactly such a subclass, overriding both
    properties to derive them from its own parent's `shape` field. Tagged
    `generic-machinery` (the abstract half of this small
    generic/particular split — see Generic vs. particular).
  - `FiniteGridConfig(Object3DConfig)`: the standalone counterpart —
    `shape`/`seg` are plain fields (`Shape3Df32`/`Segmentation3D`), not
    derived from a parent. Used when a grid isn't linked to an existing
    volume/network element.

- **`grid/finite_grid_elements.py`**
  - `GridDirectionsObject`: wraps an array so it can be indexed either by
    int or by `AxDir3D` member name. Declares a class-level `coord`
    array of six unit direction vectors, but this attribute is never
    actually read anywhere in the class's own methods (`__getitem__`/
    `__iter__` both index `self._obj`, the constructor argument, not
    `self.coord`) — dead, tagged `legacy-dead`. It is also internally
    inconsistent with `AxDir3D`'s own ordering: `coord[0]` is `[-1,0,0]`
    (the `-x`/`XM` direction) while `AxDir3D.XP` is index `0`, and the
    same swap recurs on the Z axis; only the Y-axis entries line up.
    Since the attribute is unused, this doesn't currently cause a
    behavioral bug, but it's a real inconsistency, see Open questions.
  - `GridStep(GridDirectionsObject)`: builds its *own* six-vector array
    from a `lattice` triple in `__init__`, independently of the unused
    `coord` table above, and this one **is** consistent with `AxDir3D`
    ordering (index `0`/`XP` → `[+lattice[0], 0, 0]`, etc., verified
    directly against all six entries).

- **`grid/grid_mask_maker.py`** — generic 3D boolean-mask utilities,
  tagged `generic-machinery` throughout (no grid- or neuron-specific
  logic): `mask_value_interval` (pandas `Interval`-based thresholding),
  `mask_inner`/`mask_corners`/`mask_edges` (structural region masks),
  `extend_mask` (zero-padding a mask by `extension` cells), `n_neighbours`
  (6-connectivity neighbor count via `extend_mask` + slicing), and
  `MaskMaker`, an immutable-builder wrapper class around the free
  functions (`__call__` returns a new `MaskMaker` with merged
  `ref_array`/`initial_mask`). One likely bug: `extend_mask` branches on
  `isinstance(mask, torch.Tensor)`, but `torch` is only ever
  `# import torch`-commented at the top of this file — calling that
  branch would raise `NameError`, not the intended torch path (the numpy
  branch is unaffected and evidently the one actually exercised). See
  Open questions.

- **`grid/finite_grid.py`** — the runtime class, `FiniteGrid`.
  - `__init__(model: FiniteGridConfig | LinkedFiniteGridConfig)` reads
    `model.technical.max_z`, `model.pos_origin.data`, `model.shape.data`,
    `model.seg.data` from whichever config type it's given. The two
    config types share no common formal base for this beyond
    `Object3DConfig` in `FiniteGridConfig`'s case (`LinkedFiniteGridConfig`
    is a plain `ConfigModel`, not an `Object3DConfig` subclass) — `FiniteGrid`
    relies on duck typing (both expose `technical`/`pos_origin`/`shape`/`seg`)
    rather than a shared declared interface. A large block of commented-out
    legacy constructor logic (manual dict/list coercion, length checks)
    follows immediately after, tagged `legacy-dead`.
  - `_lattice`: per-axis cell size, `shape / segmentation`.
  - `steps` (`GridStep(self._lattice)`): the confirmed-consistent
    direction-vector table from `finite_grid_elements.py`, scaled to this
    grid's lattice.
  - `_make_pos`/`_pos`/`_pos_end`: computes grid-segment positions, then
    appends one extra "technical" segment positioned past `max_z + 1` —
    per its own comment, so it renders invisibly in VisPy without needing
    a geometry-shader primitive-restart index, "simpler w.r.t. vispy."
    Tagged `hand-written-edge` (a VisPy-rendering-specific workaround).
    The public `pos`/`pos_end` properties strip this technical entry back
    off before exposing positions to callers.
  - `shaped_index`: a flat segment-index array reshaped (and transposed)
    to the grid's 3D segmentation shape; feeds `mask_maker`
    (`grid_mask_maker.MaskMaker`, keyed to this array as `ref_array`).
  - `get_hull_mask` (`staticmethod`): value-range mask combined with a
    "fewer than 6 full neighbors" test (via `grid_mask_maker.n_neighbours`)
    to find surface/hull cells; does a local `import torch` — the actual
    torch-consuming path in this subpackage (contrast with the broken
    `torch.Tensor` branch in `grid_mask_maker.extend_mask` above).
  - `grid_coordinates`/`cls_grid_coordinates`: convert real positions to
    integer grid-cell coordinates via `floor((pos / outer_shape) *
    segmentation)`.
  - `get_idx_from_grid_pos`/`validate_pos`/`is_cube`: small index/bounds
    helpers, no notable behavior beyond their names.

## Relationships within the subpackage

`spatial_pars.py` is the shared vocabulary (`Object3DConfig`,
`Shape3Di32`/`Shape3Df32`/`Segmentation3D`, `AxDir3D`) that both
`finite_grid_config.py` and `volume.py` (`chemistry.md`'s cross-reference)
build on. `finite_grid_config.py`'s `LinkedFiniteGridConfig`/
`FiniteGridConfig` pair is the config side; `finite_grid.py`'s
`FiniteGrid` is the one runtime class built from either, duck-typing over
their shared `technical`/`pos_origin`/`shape`/`seg` surface.
`finite_grid_elements.py`'s `GridStep` and `grid_mask_maker.py`'s
`MaskMaker`/mask functions are both internal helpers `FiniteGrid`
composes (`self.steps`, `self.mask_maker`) rather than either being
constructed independently elsewhere in this subpackage.

## Generic vs. particular

`LinkedFiniteGridConfig`/`FiniteGridConfig` is a small instance of the
generic/particular split from `config-build-pattern.md`, but inverted in
scale: here the "abstract" side (`LinkedFiniteGridConfig`'s
`NotImplementedError` properties) is a two-property abstract base with a
single confirmed concrete subclass (`LinkedVolumeGridConfig` in
`chemistry.md`), not a large reusable machinery layer. The
`grid_mask_maker.py` utilities are uniformly generic (no grid- or
neuron-specific logic); the VisPy-rendering workaround in
`FiniteGrid._make_pos` (the technical off-screen segment) is this
subpackage's one clear hand-written edge, matching the shape of the
edges in `config-build-pattern.md` (an external rendering API's own
constraints — no primitive-restart support used here — driving a
particular, one-off solution).

## Cross-links

- `agents/mapping/chemistry.md` — `VolumeConfig`/`LinkedVolumeGridConfig`
  (defined in `geometry/volume.py`, part of this subpackage) is the
  confirmed concrete subclass of this subpackage's
  `LinkedFiniteGridConfig` abstract base, and `chemistry/`'s
  `ChemicalConcentrationVolume` builds a `FiniteGrid` from it via the
  same generic builder machinery.
- `agents/mapping/config-build-pattern.md` — the generic/particular
  vocabulary this file reuses for the `LinkedFiniteGridConfig`/
  `FiniteGridConfig` split and the VisPy-rendering workaround.
- `agents/mapping/vertical-trace.md` — general CUDA/VisPy interop
  background; not directly touched by this subpackage (no CUDA code
  here), only VisPy-rendering conventions (`AxDir3D.vispy_name_alias`,
  the technical off-screen grid segment).
- `utils/data_utils/dataframe_config.py` (not yet mapped) — defines
  `SeriesModel`/`SeriesModel.Slots`, which `XYZPars`/`EnginePos3D`
  extend; not opened for this pass.

## Open questions

Indexed centrally in [`README.md` → Consolidated open questions](README.md#geometry):

- [SOLVED] `Shape3Di32.model_post_init` calls `raise ValidationError(f"...")`
  with a single string argument. Not confirmed whether this actually
  raises pydantic's intended validation error or a `TypeError` from a
  malformed constructor call — no test or call site exercising a
  non-positive shape value was found to confirm behavior empirically.
  - **Resolution**: Empirically verified as a bug. In Pydantic v2, `ValidationError`
    cannot be instantiated with a single string argument; its constructor requires
    `title` and `line_errors` (or creation via `ValidationError.from_exception_data`).
    Instantiating `Shape3Di32(data=np.array([0, 1, 1], dtype=np.int32))` raises:
    `TypeError: ValidationError.__new__() missing 1 required positional argument: 'line_errors'`.
    In Pydantic v2, custom validation logic inside `model_post_init` or field validators
    should raise `ValueError`, which Pydantic either catches and wraps into a proper
    `ValidationError` or propagates cleanly.
    See [`README.md#geometry`](README.md#geometry).
- [SOLVED] `grid_mask_maker.extend_mask`'s `torch.Tensor` branch references an
  unimported `torch`. Not confirmed whether this is simply unreachable
  dead code (all real callers pass numpy arrays) or a latent bug waiting
  on a torch-based caller.
  - **Resolution**: Verified as a latent bug and migration relic.
    `# import torch` is commented out at `snngine_v4/geometry/grid/grid_mask_maker.py:5`.
    Passing a PyTorch tensor to `extend_mask` immediately crashes with
    `NameError: name 'torch' is not defined` at line 37.
    Its only torch-oriented downstream caller is `FiniteGrid.get_hull_mask`
    (`snngine_v4/geometry/grid/finite_grid.py:92-106`), which locally imports `torch`
    and passes `count_array=torch.zeros_like(tensor)` to `n_neighbours`
    (`grid_mask_maker.py:189-211`), which in turn calls `extend_mask`.
    However, `get_hull_mask` is currently uncalled across the codebase, and all active
    production callers pass `np.ndarray`.
    See [`README.md#geometry`](README.md#geometry).
- [SOLVED] `GridDirectionsObject.coord`'s direction ordering (X and Z axes appear
  swapped relative to `AxDir3D`) is unused dead code today, but not
  confirmed whether it was ever live, or whether some other part of the
  codebase (outside this subpackage) still relies on `AxDir3D`'s literal
  integer values matching a similar convention.
  - **Resolution**: Verified as dead legacy code.
    `GridDirectionsObject.coord` (`snngine_v4/geometry/grid/finite_grid_elements.py:12-19`)
    defines row offsets where the negative and positive directions for X and Z are swapped
    relative to `AxDir3D` (`XP=0`, `XM=1`, `YP=2`, `YM=3`, `ZP=4`, `ZM=5` in `spatial_pars.py:36-43`).
    A codebase-wide search confirms that `GridDirectionsObject.coord` is never referenced anywhere
    in `snngine_v4`. Its subclass `GridStep` (`finite_grid_elements.py:35-54`) completely overrides
    `self._obj` with vectors matching `AxDir3D` order, and `GridDirectionsObject.__getitem__`
    directly indexes `self._obj` via `AxDir3D[item]`. `coord` is an unreferenced relic from SNNgine3D.
    See [`README.md#geometry`](README.md#geometry).
- [SOLVED] `Directions3DBoolPars` and `Pos2DVBO`/`Pos3DVBO` have no consumer
  within `geometry/` itself. Not confirmed whether they're used from
  another subpackage (e.g. `visualization/` or `nn/`) or are unused
  leftovers.
  - **Resolution**: Confirmed to be central cross-subpackage domain types, not dead leftovers.
    `spatial_pars.py` serves as the foundational spatial and buffer type registry for the whole engine:
    1. `Directions3DBoolPars` (`snngine_v4/geometry/spatial_pars.py:177-190`) is consumed by
       `BoxFacesVisualInitConfig.planes` (`snngine_v4/visualization/config_models/visuals/boxes.py:30`)
       and parsed by `VispyVisualBuilder.get_model` (`snngine_v4/visualization/visual_builder.py:443`).
    2. `Pos2DVBO` and `Pos3DVBO` (`snngine_v4/geometry/spatial_pars.py:192-193`) define GPU VBO buffer
       type aliases consumed by `NetworkReservoirConfig.pos` (`snngine_v4/nn/config_models/reservoir/nn_reservoir_config.py:116`),
       `MarkerVisualConfig.pos` (`snngine_v4/visualization/config_models/visuals/markers.py:34`),
       `GridLinesVisualInitConfig.pos` (`snngine_v4/visualization/config_models/visuals/lines.py:36,46`),
       `MultiLinePlotSubVisualInitConfig.pos` (`snngine_v4/visualization/config_models/plotting/multi_line_plot.py:65,99,213`),
       and `OptionsBuilder` (`snngine_v4/gui/parameter_trees/parameter_builder/options_builder.py:173,175`).
    See [`README.md#geometry`](README.md#geometry).
- [SOLVED] Per the user's earlier note on `chemistry/`: this subpackage's
  migration completeness from SNNgine3D is likewise not confirmed one
  way or the other; the dead/commented-out code found here (the
  alternate `XYZPars` implementation, `FiniteGrid`'s legacy constructor
  block, the unused `GridDirectionsObject.coord`) is consistent with
  that same caveat, not necessarily its own separate issue.
  - **Resolution**: Confirmed through systematic audit. `geometry/` contains
    several unpruned legacy artifacts from SNNgine3D (e.g. commented-out `# import torch`
    in `grid_mask_maker.py:5`, unused `GridDirectionsObject.coord`, commented-out
    `XYZPars` property implementations in `spatial_pars.py:115-127`, and uncalled
    `FiniteGrid.get_hull_mask`), while core runtime classes (`FiniteGrid`, `VolumeConfig`,
    `Shape3Di32`, `AxDir3D`) are fully functional and integrated with downstream subsystems.
