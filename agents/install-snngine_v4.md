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

Key deps (from `requirements.txt`): numpy/scipy/pandas, numba (CUDA-capable), `torch==2.8.0` (cu129), `pycuda~=2025.1`, pyopengl + vispy (GPU visualization), PySide6/pyqtgraph/qtpy/pyqtdarktheme/darkdetect (Qt GUI/theme), pydantic/pydantic-settings/numpydantic (config models), PyMeasure (instrument control, e.g. an X-Touch-Mini MIDI controller), tables (HDF5), lxml, deepdiff.
