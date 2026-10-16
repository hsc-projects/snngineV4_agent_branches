# Install / build — snngine_v4 (new repo)

- **Install:** `pip install -r requirements.txt` (no `pyproject.toml`/`setup.py`/venv config in the repo). Expects an Nvidia/CUDA host setup. `pycuda~=2025.1` has a large comment block in `requirements.txt` on manual build/install steps and GLIBCXX troubleshooting; it's finicky to install correctly.
- **C++/CUDA extension build:** `snngine_v4/nn/cuda_backend/` is a pybind11/CMake C++/CUDA project that compiles three shared libraries: `snn_simulation_gpu`, `snn_utils`, and `snn_construction_gpu`. It must be built via CMake targeting the host GPU architecture (e.g. SM 89 for Ada Lovelace, SM 86 for Ampere):
  ```bash
  cd snngine_v4/nn/cuda_backend
  cmake -B build -S . -DCMAKE_CUDA_ARCHITECTURES=89 -DCMAKE_BUILD_TYPE=Release
  cmake --build build --config Release -j$(nproc)
  export PYTHONPATH="$(pwd)/build:$PYTHONPATH"
  ```
- **Entry point:** `snngine_v4/main.py` (instantiates `snngine_v4.gui.app.engine_app.EngineApp`, a PySide6/Qt GUI app), with `gui/app/debug_app.py` as a debug variant — see `agents/common.md` → Workflow for why this isn't run here. Headless engine execution on NVIDIA GPUs is verified via `setups/runpod-engine-smoke-test/test_headless_engine_sim.py`.
- **PyCUDA with OpenGL interop on NumPy 2.x:** Released `pycuda` versions (`<=2025.1`) fail to compile against NumPy 2.x due to removed C-API symbols (`PyArray_Descr.elsize`, `PyArray_CORDER`) and relocated headers (`numpy/_core/include`). Building with `CUDA_ENABLE_GL = True` on NumPy 2.x requires building from PyCUDA `main` (`pycuda-2026.1`), passing `CXXFLAGS = ['-I' + numpy.get_include()]` in `siteconf.py`, and symlinking `numpy/_core/include/numpy` to `numpy/core/include/numpy`.
- **Multi-architecture CUDA build:** When targeting multiple GPU generations (e.g. Ampere SM 86, Ada SM 89, Blackwell SM 120), pass `-DCMAKE_CUDA_ARCHITECTURES="86;89;120"` (or `native`) to CMake so the compiled `.so`/`.pyd` binaries do not fail with `cudaErrorNoKernelImageForDevice` when moving across GPUs.

Key deps (from `requirements.txt`): numpy/scipy/pandas, numba (CUDA-capable), `torch==2.8.0` (cu129), `pycuda~=2025.1`, pyopengl + vispy (GPU visualization), PySide6/pyqtgraph/qtpy/pyqtdarktheme/darkdetect (Qt GUI/theme), pydantic/pydantic-settings/numpydantic (config models), PyMeasure (instrument control, e.g. an X-Touch-Mini MIDI controller), tables (HDF5), lxml, deepdiff.
