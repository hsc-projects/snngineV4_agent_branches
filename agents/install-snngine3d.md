# Install / build — SNNgine3D (old repo)

- **Install:** `poetry install` (Python `>=3.10, <3.12`).
- **CUDA extension build:** `snngine3d/nn/cuda_backend` is a separate pybind11/CMake C++/CUDA project (git submodule `pybind11` at `src/include/pybind11`), **not** wired into the Poetry build — it must be built manually via CMake. Requires CUDA toolkit (nvcc), Python 3.11 dev headers, and OpenGL. There is no documented one-line build command.
- Note: `cli.py` sets `QT_API=pyside6` even though `pyqt6` is the declared Poetry dependency — a possible inconsistency worth checking if Qt import errors show up.
- `notebooks/simulation_demo/` has a working example (`simulation.ipynb` + `sim_demo_utils.py`) of constructing/running a simulation without the full PyQt engine, using a precompiled CUDA extension in `sim_demo_precompiled/`.
