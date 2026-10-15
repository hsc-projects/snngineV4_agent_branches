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

## Confirmed runtime & memory layout invariants

- **TensorDataFrame C-Contiguity Requirement**:
  `TensorDataFrame` backing tensors initialized from `pandas.DataFrame.values` inherit pandas' internal Fortran layout (column-major, stride `(1, N_rows)`). Native C++/CUDA kernels (e.g. `fill_N_flags_group_id_and_G_neuron_count_per_type_`) compute flat 1D offsets assuming standard C-contiguous (row-major) layout: `offset = n + row * N`. Passing non-contiguous device pointers (`data_ptr()`) causes linear memory writes to wrap across row boundaries (e.g., Row 2 `L_group` writes overwriting Row 1 `N_type`), causing silent state corruption or validation assertion failures. Enforcing `.contiguous()` (`gpu_t = gpu_t.contiguous()`) in `TensorSeries.make_gpu_data` / `TensorDataFrame` is mandatory for native CUDA backend interop.
- **Headless Buffer Contracts (3D Texture & Plot VBOs)**:
  `Simulator._make_simulator_backend` unconditionally binds raw device pointers for marker/plot VBOs (`POS_VBO`) and chemical diffusion concentration volumes (`TEXTURE_3D` for `chemicals.C0` and `C1`). In headless environments without active VisPy GLIR canvases, the simulation loop executes natively without GUI dependencies by mapping these keys in `SpatialNetwork.cuda_opengl_map` to zero-initialized device tensors wrapped in `MockGLTensorDict` structures providing no-op `.copy_to_texture()` callbacks.
- **Numpydantic Dynamic Identity in ArrayInterfaces**:
  Evaluating `numpydantic.NDArray[Shape, Dtype]` generates a new dynamic class object on each call (`id(dt1) != id(dt2)`). Inverse lookups in `ArrayInterfaces().dtype_interface_map.inv` fail with `KeyError` unless resolution matches by `(shape, dtype)` attributes rather than Python object identity.

