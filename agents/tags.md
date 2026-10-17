# Tags

A running registry of tags used across `agents/mapping/*.md`, so tags stay
consistent instead of drifting. Check here before introducing a new tag —
reuse an existing one if it fits. Propose new tags to the user before
adding them.

- **`generic-machinery`** — abstract, reusable, not domain-specific (the
  `config-build-pattern.md` sense). Used across mapping documents (`chemistry.md`, `construction.md`, `utils.md`, etc.).
- **`hand-written-edge`** — where generic machinery meets an external
  fixed API. Used across mapping documents (`chemistry.md`, `nn.md`, `visualization.md`, etc.).
- **`config-driven`** — part of the pydantic config → template → build
  chain. Used across mapping documents (`chemistry.md`, `config.md`, `nn.md`, `gui.md`, etc.).
- **`cuda-adjacent`** — Python-side code touching the CUDA/kernel
  boundary by intent only; kernel-level detail deliberately not opened.
  Used across mapping documents (`chemistry.md`, `geometry.md`, `nn.md`, `visualization.md`, etc.).
- **`legacy-dead`** — dead code, unused, or a leftover from the
  V2/SNNgine3D C++ port. Used across mapping documents (`chemistry.md`, `geometry.md`, `nn.md`, `visualization.md`, etc.).
