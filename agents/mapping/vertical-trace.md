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
