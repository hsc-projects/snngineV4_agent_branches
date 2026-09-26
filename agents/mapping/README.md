# agents/mapping/ index

Per-topic write-ups produced by the horizontal mapping pass (one file per
`snngine_v4/` subpackage, plus the earlier vertical trace and the
config/build architecture note). Suggested reading order:

1. **`vertical-trace.md`** — one concrete construction/wiring path through
   the whole engine, entry point to CUDA/OpenGL interop; also contains the
   `N_pos` zero-copy CUDA↔VisPy case study. Not full coverage of the
   codebase, one path only.
2. **`config-build-pattern.md`** — the config→template→build architecture:
   the generic Pydantic builder machinery, and the three confirmed
   hand-written edges where it meets a fixed external API (CUDA/pybind11,
   VisPy visual construction, field-ownership between base and visual
   configs).
3. **`chemistry.md`** — the `chemistry/` subpackage: volumetric "chemical"
   diffusion fields, their config/build split, and the 3D-texture
   CUDA/OpenGL interop boundary (contrasted with the zero-copy path in
   `vertical-trace.md`).
4. **`geometry.md`** — the `geometry/` subpackage: spatial parameter
   vocabulary, the finite-grid config/build split, and its VisPy-rendering
   workaround; also notes some found dead code and internal
   inconsistencies (direction-ordering mismatch, an unimported-`torch`
   branch) not yet confirmed as bugs.

Remaining subpackages (`construction/`, `config/`, `nn/`,
`visualization/`, `utils/`, `gui/`) are planned but not yet written; see
the plan for the horizontal mapping pass for the intended order and
reasoning.

`architecture-snngine_v4.md` is being migrated into this directory
subpackage by subpackage (each migrated bullet is replaced there with a
pointer to its new file here); see that file's own remaining content for
what hasn't been migrated yet.
