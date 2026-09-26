# chemistry/

`chem_models.py`, `chem_volume.py`: volumetric "chemical" diffusion fields
associated with network elements, visualized as 3D textures. Two files
only, both fully read for this write-up.

Per the user: this subpackage's migration from SNNgine3D (the old
version) may not be fully complete or integrated. Several findings below
(the `Chemicals`/`DefaultChemicals` field mismatch, the unused
`depreciation` field, the unfinished per-chemical naming) are consistent
with this and are flagged as open questions rather than assumed bugs.

## Files and classes

- **`chem_models.py`** — the config side, pydantic only, no runtime logic.
  - `ChemicalConcentrationModel(VolumeConfig, EngineElementConfigMixin)`:
    the per-chemical config. `color` (an `RGBAColorType`, default
    `'white'`) and `k_val` (default `.16`, a commented-out `Field(gt=0.,
    lt=1.)` suggests it was meant to be constrained to `(0, 1)` but this
    constraint isn't currently enforced) are the only chemistry-specific
    fields; `depreciation` (default `0.0`) is present but unused anywhere
    else in this subpackage. `b_test_init` (default `True`) gates
    synthetic test-data initialization in `chem_volume.py` (see below) —
    tagged `legacy-dead`-adjacent (not fully dead, since it's read, but a
    debug/test path left switched on by default, not a normal production
    flag). Inherits `VolumeConfig` (`geometry/volume.py`) for `shape`
    (`VolumeShapeHDW`) and the `linked_grid_config` cached property.
  - `ChemicalContainerModel(ConfigContainerModel, EngineElementConfigMixin)`
    — an empty pass-through container class; tagged `generic-machinery`
    (adds no chemistry-specific fields or logic of its own).
  - `DefaultChemicals(ChemicalContainerModel)` — hard-codes exactly two
    chemical slots, `C0` and `C1`, both typed `ChemicalConcentrationModel`.
    A commented-out `model_post_init` would have assigned `name = 'C0'`/
    `'C1'` to each; currently unimplemented, so the (commented-out) `name`
    field on `ChemicalConcentrationModel` is never populated. Tagged
    `hand-written-edge`: the two-chemical count is fixed by this class
    definition, not driven by any config value.

- **`chem_volume.py`** — the runtime/built side.
  - `ChemicalConcentrationVolume(EngineElement)` — the built counterpart
    of `ChemicalConcentrationModel` (`config: ChemicalConcentrationModel`).
    Declares its own `BUILDER_OBJECT_CLASS_MAP = {LinkedVolumeGridConfig:
    FiniteGrid}`, an instance-level addition to the generic builder
    mechanism described in `agents/mapping/config-build-pattern.md`
    (tagged `generic-machinery` + `config-driven`: it participates in
    that same class-map convention, just with a chemistry-specific
    entry). `__init__` allocates a zero-filled CPU array sized to
    `self.config.shape.shape_wdh` and, if `b_test_init` is set, overwrites
    it with a bundled VisPy sample volume (`vispy.io.load_data_file
    ('volume/stent.npz')`, cropped to fit) via
    `init_test_data_cpu` — tagged `legacy-dead`: a hard-coded medical-scan
    test asset with no relation to actual chemical simulation, left as
    the default path (`b_test_init` defaults to `True` in
    `ChemicalConcentrationModel`). It then calls `self.add_build(...)`
    on its own `linked_grid_config`, tying itself into the generic
    construction (`EngineElement`) machinery from `construction/`.
  - Three GPU-tensor-valued cached/plain properties — `c_next`,
    `c_current`, `c_source` — all ultimately views or clones of
    `texture_3d_tensor`. `c_next` is a direct alias (no clone); `c_current`
    and `c_source` are `torch.clone()`s taken at first access
    (`cached_property`, so each is fixed after its first read, not
    re-synced to `texture_3d_tensor` later). `c_source` additionally
    zeroes itself and calls `set_test_values_gpu` — tagged
    `legacy-dead`: this hard-codes three fixed voxel-slice values (2000,
    1800, 1800) into the last three depth-slices of `c_current`, `c_next`,
    and the local clone `t`, then calls `texture_3d.copy_to_texture()`,
    mixing production-shaped tensor plumbing with baked-in debug values.
  - `texture_3d` / `texture_3d_tensor` — both read from
    `self.cuda_gl_dict.str2gl[GLBufferTypes.TEXTURE_3D.name]` /
    `self.cuda_gl_dict[GLBufferTypes.TEXTURE_3D.name]`
    (`gui/parameter_trees/cuda_connector.py`'s `GLBufferTypes` enum) —
    tagged `hand-written-edge` + `cuda-adjacent`: this is this
    subpackage's own instance of the CUDA/OpenGL interop boundary
    documented in `agents/common.md` and
    `agents/architecture-snngine_v4.md`'s interop section, specifically
    the 3D-texture (non-zero-copy) path (`GLTexture3DTensor`, imported
    from `visualization/cuda/gl_interop/gl_texture3d.py`), not the
    zero-copy VBO/IBO path `N_pos` uses (see
    `agents/mapping/vertical-trace.md`'s case study). No kernel source
    was opened to write this entry, per the existing `cuda-adjacent`
    convention.
  - `inner_grid` — returns `self[self.config.linked_grid_config]`,
    i.e. looks up the already-built `FiniteGrid` (from `geometry/grid/`)
    keyed by the same `LinkedVolumeGridConfig` instance used in
    `BUILDER_OBJECT_CLASS_MAP` and passed to `add_build` — confirms the
    generic `EngineElement` container (a `BuilderDict`, per
    `config-build-pattern.md`) is being used exactly as documented
    elsewhere, with no chemistry-specific override of that lookup
    mechanism.
  - `Chemicals(EngineElement)` — a two-line stub: declares only
    `C0: ChemicalConcentrationVolume`. The mirrored `C1` field seen in
    `DefaultChemicals` (the config side) is absent here — see Open
    questions.

## Relationships within the subpackage

`chem_models.py` defines the config/template side (`ChemicalConcentrationModel`,
`ChemicalContainerModel`, `DefaultChemicals`); `chem_volume.py` defines the
built/runtime side (`ChemicalConcentrationVolume`, `Chemicals`), following
the general config→build split from `construction/engine_element.py`.
`ChemicalConcentrationVolume.config` is typed as exactly
`ChemicalConcentrationModel`, and its `BUILDER_OBJECT_CLASS_MAP` entry
(`LinkedVolumeGridConfig` → `FiniteGrid`) is populated from
`VolumeConfig.linked_grid_config` (`geometry/volume.py`), a property this
subpackage's config class inherits rather than defines itself — the actual
grid-shape derivation (`LinkedVolumeGridConfig.shape` reads
`parent_config.shape.shape_wdh`) lives entirely in `geometry/`, not here.

## Generic vs. particular

Follows the same generic/particular split found in
`agents/mapping/config-build-pattern.md`: the config→build wiring
(`BUILDER_OBJECT_CLASS_MAP`, `add_build`, container lookup via `self[...]`)
is the same generic machinery used project-wide, applied here with no
chemistry-specific extension to the mechanism itself. The particular edge
in this subpackage is the CUDA/OpenGL 3D-texture boundary
(`texture_3d`/`texture_3d_tensor`), a hand-written, chemistry-instance-specific
binding to a fixed external interop API, matching the shape of edges (1)
and (2) in `config-build-pattern.md` (a compiled/external boundary the
generic layer cannot reach past).

## Cross-links

- `agents/mapping/config-build-pattern.md` — the generic config→build
  machinery this subpackage's `BUILDER_OBJECT_CLASS_MAP` and `add_build`
  usage instantiates.
- `agents/mapping/vertical-trace.md` — the zero-copy VBO/IBO interop
  pattern (`N_pos` case study), contrasted here with the non-zero-copy
  3D-texture path this subpackage actually uses.
- `agents/common.md` → Core technical facts — the CUDA/OpenGL interop
  chain overview, including the 3D-texture exception this subpackage is
  a concrete instance of.
- `geometry/` (not yet mapped) — `VolumeConfig`, `VolumeShapeHDW`,
  `LinkedVolumeGridConfig`, `FiniteGrid` all live there; this subpackage
  depends on it directly rather than duplicating spatial-shape logic.

## Open questions

- `Chemicals` declares only `C0: ChemicalConcentrationVolume`, while its
  config counterpart `DefaultChemicals` declares both `C0` and `C1`. Not
  confirmed whether this is a real mismatch (a bug/incompleteness) or
  whether `Chemicals` is meant to be a partial/example stub rather than
  the actual built counterpart of `DefaultChemicals`.
- `depreciation` (`ChemicalConcentrationModel`) has no reader anywhere in
  either file in this subpackage. Not confirmed whether it's consumed
  elsewhere (e.g. a CUDA kernel) or genuinely unused.
- The commented-out `name` field and `model_post_init` in `chem_models.py`
  suggest per-chemical naming (`'C0'`/`'C1'`) was intended but not
  finished. Not confirmed whether this is planned future work or an
  abandoned idea.
- `set_test_values_gpu`'s hard-coded voxel values (2000, 1800, 1800) and
  `init_test_data_cpu`'s bundled stent-scan volume are both live by
  default (`b_test_init: bool = True`). Not confirmed whether this
  default is intentional (e.g. no real chemical-diffusion source exists
  yet, so test data is the only current content) or leftover debug state
  that should default to off.
