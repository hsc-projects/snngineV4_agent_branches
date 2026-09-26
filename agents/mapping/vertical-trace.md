# Vertical trace

One concrete path through snngineV4, from the entry point down to the
CUDA/OpenGL interop layer (already documented in `agents/common.md` →
Core technical facts, and `agents/architecture-snngine_v4.md`). This is
**one path, not full coverage** — it necessarily skips side-branches (e.g.
the 3D-texture/chemistry path, which is known to diverge at the interop
layer). See `agents/mapping/<subpackage>.md` files (once written) for the
horizontal, per-directory pass.

## The chain

1. **`snngine_v4/main.py`** — adds the parent dir to `sys.path`, then
   `EngineApp().run()`.

2. **`gui/app/engine_app.py` (`EngineApp.__init__`)** — builds a default
   `EngineConfig` if none given, constructs the top-level `SNNgine`
   orchestrator, sets up the Qt dark theme, builds `MainEngineWindow`,
   exports config, then calls `self.window.construct_network()`.

3. **`gui/windows/main_window.py` (`MainEngineWindow.construct_network`)**
   — calls `self.engine.build(scene_tree, network_tree, selector_tree)`.

4. **`snngine.py` (`SNNgine.build`)** — the real orchestration sequence:
   - `build_network()` → delegates to `NetworkBuilder` (`construction/`)
     to build the network from config (`self.conf.template`).
   - `build_visuals()` → builds neuron/grid/plot/chemical-volume visuals
     via `SceneManager` (`visualization/scenes/scene_manager.py`).
   - `connect_visuals()` → `VispyConnector.cls_connect_tree` — links
     config models to Vispy `Visual` objects for the parameter-tree UI.
   - **If `b_pycuda_available`**: `build_cuda_gl_tensors()` →
     `CudaVispyConnector.cls_connect_tree` (`gui/parameter_trees/cuda_connector.py`)
     — this is the entry into the confirmed GPU-interop chain
     (`visualization/cuda/gl_interop/gl_buffer.py`, `gl_tensor.py`,
     `gl_texture3d.py`).
   - `connect_tensors()` → `TensorConnector.cls_connect_tree` — links
     config models to plain (non-GL) tensors.
   - `self.network.configure_simulator(element=0)`.

5. **Endpoint reached**: at this point the chain arrives at the same
   CUDA/OpenGL interop mechanism already documented — VisPy visual built
   first, PyCUDA registers its OpenGL buffer, wrapped via numba into a
   PyTorch tensor (VBO/IBO path), or the explicit-copy fallback (3D
   texture path).

## Key finding: simulation control is not wired

Everything above — config, network construction, visuals, CUDA/OpenGL
tensor buffers, GUI parameter trees — is built and connected by the time
`EngineApp.__init__` finishes. But the actual per-step simulation loop is
**not** invoked anywhere in the running app.

- `SNNgine.run_sim(n_steps)` (`snngine.py:204-227`) is a complete,
  SNNgine3D-pattern simulation loop: gets `simulator.simulations[element].backend`,
  loops `n_steps` times calling `sim.update(False, True)`, and refreshes
  the voltage/firing plot scenes each step.
- The only call to `run_sim()` in the entire codebase is in
  `main_window.py`'s `test_func`, a quick manual-debugging helper (per the
  user, not architecturally meaningful) — and it's commented out:
  ```python
  def test_func(self, ):
      # self.engine.run_sim(10)
      self.selection_tree.add_selector_box_visual(None)
  ```

**Confirms the user's own assessment** (given before this trace was run):
object-level wiring exists between Python and CUDA, but simulation control
itself — actually driving the step loop — is not currently wired into the
running application. This directly informs the paused migration question
in `agents/paused-migration-feature-simulation-stepping.md` and the
Backlog in `agents/feature-todos.md`.

## Case study: `N_pos` as a multiplexed CUDA↔VisPy channel

A concrete, verified example of how the Python/PyCUDA/VisPy/CUDA chain
actually behaves in practice, not just how it's wired. It serves as a
reference pattern for reading the rest of the CUDA↔visual interop, since
the same trick recurs (see `scatter_plot_data` below).

`N_pos` (passed into `SnnSimulation`, `nn/sim/simulation.py`) looks like a
plain xyz position buffer from its name and from the Python-side pointer
plumbing alone. It isn't: the kernel (`update_N_state_`,
`nn/cuda_backend/src/simulation/snn_simulation.cu`) treats it as a
stride-14-floats-per-marker buffer (`#define VISPY_MARKER_STRIDE 14`,
same file line 4). That stride is not arbitrary: it matches
`vispy==0.14.3`'s (the version pinned in `requirements.txt`) own internal
`MarkersVisual` vertex dtype exactly: `a_position`[3], `a_fg_color`[4],
`a_bg_color`[4], `a_size`[1], `a_edgewidth`[1], `a_symbol`[1] (confirmed
by reading the installed `vispy/visuals/markers.py:637-642` directly, not
inferred from docs). So the buffer VisPy expects for rendering *is* the
buffer CUDA writes into, with no translation layer in between. This is
the zero-copy interop pattern from `agents/common.md` applied at the
per-vertex level, not just the whole-buffer level.

Float index 10 in that layout is the alpha channel of `a_bg_color` (face
color). The kernel writes it directly: reset to `0.3` every step (line
41), bumped to `1.0` on the step a neuron fires (line 112). No color
pointer, no RGB write, no separate color buffer exists anywhere in
`cuda_backend/src` for this. The only other "color" mentions in the
entire backend are two dead, commented-out lines
(`renderer->neurons_bodies.pos_colors.map_buffer()`/`unmap_buffer()`)
referencing a class that doesn't exist in this codebase, left over from
the V2/SNNgine3D C++ renderer. "Firing" is rendered as a pure opacity
pulse against a static, config-set `face_color`
(`visualization/config_models/visuals/markers.py`'s
`face_color: BufferColorType`), not a color change.

The identical pattern appears a second time in the same kernel for a
different visual: `scatter_plot_data` (the voltage/firing scatter plot
buffer) uses the same `VISPY_MARKER_STRIDE` and the same offset-10 slot
(`scatter_plot_data[start_idx + VISPY_MARKER_STRIDE * t + 10] =
fired[n]`, lines 185-189), so this offset-10-is-alpha convention is a
project-wide assumption baked into multiple kernels, not a one-off.

**Reading pattern this suggests for the rest of the CUDA/visual interop:**
a Python-side buffer name (`N_pos`, `pos_vbo`, etc.) does not reliably
describe what the kernel actually writes into it: check the kernel's own
indexing arithmetic and any `#define ..._STRIDE` constants before assuming
a buffer's shape or purpose from its Python name or docstring alone.

Not yet traced: what `face_color` is actually configured to (RGB values)
in this project, and which specific visual instance(s) bind to `N_pos`
(i.e. confirm this is actually the 3D neuron-body marker visual and not
some other consumer).

Additional remarks (partial answers found after the above was written,
worth a closer confirmed pass later rather than re-opening the case study
above): `MarkersVisualConfig.face_color` (`markers.py:48`) defaults to
`'white'`, consistent with the low-alpha state genuinely reading as
white, not just plausible in theory. It is not confirmed whether this
default is overridden per-instance anywhere. Independent corroboration
of the
`a_bg_color`/`a_fg_color` field mapping (i.e. not just from reading VisPy's
source) turned up in `gui/parameter_trees/connectors/vispy_links.py:444-448`,
which maps this project's own config field names to VisPy attribute names:
`'face_color': 'a_bg_color'`, `'edge_color': 'a_fg_color'`, plus `pos`,
`size`, `edge_width`. This is a second, independent source, and it agrees
with the first. `visual_builder.py:333` maps `NetworkReservoirConfig` to the
`Markers` visual class, consistent with `N_pos` being the 3D neuron-body
marker visual's position buffer, but the full instance-binding chain
(`NetworkReservoirConfig` → specific `NetworkReservoir` element →
`pos_vbo` → the actual `N_pos` pointer) hasn't been walked step by step
yet.
