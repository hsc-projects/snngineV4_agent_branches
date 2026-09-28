# Install / build — snngine_v4 (new repo)

- **Install:** `pip install -r requirements.txt` (no `pyproject.toml`/`setup.py`/venv config in the repo). Expects an Nvidia/CUDA host setup. `pycuda~=2025.1` has a large comment block in `requirements.txt` on manual build/install steps and GLIBCXX troubleshooting; it's finicky to install correctly.
- Entry point is `snngine_v4/main.py` (instantiates `snngine_v4.gui.app.engine_app.EngineApp`, a PySide6/Qt GUI app), with `gui/app/debug_app.py` as a debug variant — see AGENTS.md → Workflow for why this isn't run here.

Key deps (from `requirements.txt`): numpy/scipy/pandas, numba (CUDA-capable), `torch==2.8.0` (cu129), `pycuda~=2025.1`, pyopengl + vispy (GPU visualization), PySide6/pyqtgraph/qtpy/pyqtdarktheme/darkdetect (Qt GUI/theme), pydantic/pydantic-settings/numpydantic (config models), PyMeasure (instrument control, e.g. an X-Touch-Mini MIDI controller), tables (HDF5), lxml, deepdiff.
