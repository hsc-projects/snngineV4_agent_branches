# Tags

A running registry of tags used across `agents/mapping/*.md`, so tags stay
consistent instead of drifting. Check here before introducing a new tag —
reuse an existing one if it fits. Propose new tags to the user before
adding them.

- **`generic-machinery`** — abstract, reusable, not domain-specific (the
  `config-build-pattern.md` sense). Used in `chemistry.md`.
- **`hand-written-edge`** — where generic machinery meets an external
  fixed API. Used in `chemistry.md`.
- **`config-driven`** — part of the pydantic config → template → build
  chain. Used in `chemistry.md`.
- **`cuda-adjacent`** — Python-side code touching the CUDA/kernel
  boundary by intent only; kernel-level detail deliberately not opened.
  Used in `chemistry.md`.
- **`legacy-dead`** — dead code, unused, or a leftover from the
  V2/SNNgine3D C++ port. Used in `chemistry.md`.
