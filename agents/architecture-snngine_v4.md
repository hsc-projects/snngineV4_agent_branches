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

- **nn/** — see `agents/mapping/nn.md` (migrated out of this file).
- **construction/** — see `agents/mapping/construction.md` (migrated out
  of this file).
- **config/** — see `agents/mapping/config.md` (migrated out of this
  file).
- **chemistry/** — see `agents/mapping/chemistry.md` (migrated out of this
  file).
- **geometry/** — see `agents/mapping/geometry.md` (migrated out of this
  file).
- **visualization/** — see `agents/mapping/visualization.md` (migrated out of this file).
- **gui/** — see `agents/mapping/gui.md` (migrated out of this file).
- **utils/** — see `agents/mapping/utils.md` (migrated out of this file).
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
