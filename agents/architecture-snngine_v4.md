# Architecture — snngine_v4 (new repo)

Config-driven construction throughout: pydantic `BaseModel` config objects (in
`config/`, `nn/config_models/`, `visualization/config_models/`) are passed to
builder/connector classes (`NetworkBuilder`, `TensorConnector`, `VispyConnector`,
`CudaVispyConnector`) that walk the config tree and instantiate matching runtime
objects (tensors, Vispy visuals, GUI parameter-tree nodes).

The main `SNNgine` class (`snngine_v4/snngine.py`) orchestrates: build config →
build network (CUDA/torch tensors) → build visuals → connect CUDA-OpenGL interop
buffers → connect GUI parameter trees, then `run_sim(n_steps)` calls
`simulator.simulations[element].backend.update()` per step and refreshes Vispy
plot scenes. CUDA availability degrades gracefully in several places
(`try/except ModuleNotFoundError` around `pycuda` imports, `b_pycuda_available`
cached property).

Top-level subpackages under `snngine_v4/`:

- **nn/** — simulation core. `spnn.py` (`SpatialNetwork`) and `spnn_reservoir.py`
  (`NetworkReservoir`) are the main network/element classes; `neuron_states.py`
  and `synapses.py` hold neuron/synapse state; `nn/sim/` has `simulator.py`,
  `simulation.py`, `sim_parameters.py`, `gpu_plots.py` (the sim loop and
  GPU-backed plotting of voltage/firing data); `nn/cuda_backend/` (CMakeLists.txt
  + `src/`) is CUDA kernel source, compiled separately from Python; `nn/config_models/`
  holds pydantic config schemas for network construction; `nn/NDKNV/` references
  the CUDA SNN algorithm paper this is based on (Nageswaran et al., "Efficient
  simulation of large-scale spiking Neural networks using cuda Graphics processors").
- **construction/** — `nn_builder.py` (`NetworkBuilder`) builds a network from a
  config/template into runtime objects (`engine_element.py`, `engine_element_config.py`).
- **config/** — engine-level pydantic settings: `app.py`, `devices.py`
  (CUDA/OpenGL device selection), `scenes.py`, `template.py`; `snngine_config.py`
  at package root ties these into `EngineConfig`.
- **chemistry/** — see `agents/mapping/chemistry.md` (migrated out of this
  file).
- **geometry/** — spatial parameters, volume shapes (`VolumeShapeHDW`), and a
  `grid/` submodule — spatial layout for neurons/elements.
- **visualization/** — Vispy-based rendering: `visual_builder.py`,
  `scenes/scene_manager.py` (`SceneManager`, central registry mapping config
  models to scenes/visuals), `visuals/`, `plotting/`, `cuda/gl_interop/`
  (CUDA-OpenGL interop buffer mapping, `gl_buffer.py`/`GLBufferMap`, for
  zero-copy GPU sim-to-render — see `agents/common.md` → Core technical
  facts for the interop chain and its 3D-texture exception).
- **gui/** — PySide6 application shell: `app/engine_app.py` (`EngineApp`) and
  `app/debug_app.py`; `parameter_trees/` (pyqtgraph-based parameter trees
  connecting config models to UI — `EngineParameterTree`, `EngineSelectorTree`,
  plus connector classes `TensorConnector`, `VispyConnector`, `CudaVispyConnector`);
  `devices/` (hardware controllers, e.g. X-Touch-Mini MIDI); `windows/`, `views/`,
  `common/`, `icons/`.
- **utils/** — cross-cutting helpers: `object_builder/` (the generic
  build-from-config pattern), `containers/`, `cuda_utils/`, `data_utils/`,
  `settings/`, `class_mixer.py`, `core_utils.py` (e.g. `type_assertion`),
  `field_utils.py`.
- **.snngine/** — stored XML config presets (`app.xml`, `built.xml`,
  `devices.xml`, `scenes.xml`, `template.xml`) — serialized state/config
  snapshots, not code.

## Confirmed interop details (from direct code reading this session)

- `visualization/cuda/gl_interop/gl_buffer.py` — `GLBuffer.from_id()` calls
  `pycuda.gl.RegisteredBuffer(opengl_id)` to register an *existing* OpenGL
  buffer with CUDA, then wraps the mapped memory as a
  `numba.cuda.cudadrv.devicearray.DeviceNDArray`.
- `visualization/cuda/gl_interop/gl_tensor.py` — `GLBufferTensor.tensor`
  wraps that numba device array via `torch.as_tensor(...)`. PyTorch does
  not wrap PyCUDA buffers directly; numba is the bridge.
- `visualization/cuda/gl_interop/gl_texture3d.py` — 3D textures use
  `pycuda.gl.RegisteredImage` instead of `RegisteredBuffer`, and are
  **not** zero-copy: `GLTexture3DTensor.tensor` is a separate
  `torch.zeros(...)` allocation, synced via explicit
  `pycuda.driver.Memcpy3D()` copies (`copy_to_texture`/`copy_to_tensor`).
- `gui/parameter_trees/cuda_connector.py` (`CudaVispyConnector`) —
  `gl_buffer_id()` reads the real OpenGL handle out of VisPy's internal
  GLIR object registry (`get_current_canvas().context.shared.parser._objects[...]`)
  for an already-built VisPy visual (e.g. `obj._vbo.id`, `obj._texture.id`).
  This confirms VisPy visuals are constructed first, and PyCUDA/CUDA
  buffers are wired to them afterward.
- `gui/parameter_trees/vispy_connector.py` (`VispyConnector`) — separate,
  more general connector linking pydantic config models to VisPy `Visual`
  objects for the parameter tree UI; distinct from the CUDA-specific
  buffer connector above.
