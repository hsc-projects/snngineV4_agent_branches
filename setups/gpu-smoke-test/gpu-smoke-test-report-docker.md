# GPU Smoke Test Report (Docker Containerization)

## Summary

Successfully containerized and verified the local GPU CUDA-OpenGL zero-copy interop smoke test across **all three phases** (Headless EGL, Offscreen Snapshot, and Interactive PyQt+VisPy GUI) on **Ubuntu 24.04 LTS (Noble Numbat)** with **CUDA 12.6.2** and native **Python 3.12** inside a clean Docker image (`snngine-gpu-smoke:headless`) using NVIDIA Container Runtime (`--gpus all`).

The containerized pipeline executes all 5 links of the zero-copy interop chain unattended under headless EGL (GL 4.6.0 NVIDIA on RTX 3090, Driver 595.91.07), verifying PyCUDA VBO mapping, Numba `DeviceNDArray`, PyTorch `torch.as_tensor` zero-copy pointer identity, direct PyTorch write-through, CUDA kernel write-through, and real self-compiled simulation code (`sim_demo_utils.update_N_state`). In addition, an offscreen EGL framebuffer snapshot (`rendered_frame.png`) was rendered and verified with zero desktop/X11 dependency. Finally, Phase 3 executes the interactive 3D VisPy scene on host display with full safety traps against GNOME Shell crashes. All assertions passed with 100% byte-for-byte readback fidelity and exit code 0.

---

## What Was Built

- **Dockerfile**: `setups/gpu-smoke-test/Dockerfile.docker-smoke`
  - Base: `nvidia/cuda:12.6.2-devel-ubuntu24.04` (Ubuntu 24.04 LTS Noble Numbat)
  - Environment: `NVIDIA_VISIBLE_DEVICES=all`, `NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics,display` (essential for injecting host NVIDIA EGL and OpenGL driver libraries into the container).
  - Python Environment: Native Python 3.12 isolated in `/opt/venv`, avoiding Debian 24.04 package manager collisions (`RECORD file not found` / PEP 668).
  - Python Stack: PyTorch 2.5.1 (`cu124`), NumPy 1.26.4 (`numpy<2`), Numba 0.67, PyOpenGL, PyOpenGL_accelerate, PyQt6, QtPy, VisPy.
  - PyCUDA: Built from source from git tag `v2024.1` with `--cuda-enable-gl` and `--cuda-root=/usr/local/cuda` via `--no-build-isolation`.
  - System Libraries: Ubuntu 24.04 Noble packages (`libglib2.0-0t64`, `libfontconfig1`, `libxkbcommon-x11-0`, `libxcb-*`).
- **Host Launcher Script**: `setups/gpu-smoke-test/interop_smoke_test_docker_launcher.sh`
  - Follows the project's `interop_smoke_test_<descriptor>` convention.
  - Autonomously checks whether the `snngine-gpu-smoke:headless` image exists locally; if missing, automatically triggers `docker build` from `Dockerfile.docker-smoke`.
  - **Headless Mode** (default): Launches container with `--gpus all`, mounts the workspace, configures `PYTHONPATH`, and executes `interop_smoke_test_auto.py --snapshot /output/rendered_frame.png`.
  - **Interactive GUI Mode** (`--gui`): Mounts `/tmp/.X11-unix`, authorizes X11 access via `xhost +local:root`, disables GNOME Shell `tiling-assistant@ubuntu.com` with an automated bash `trap ... EXIT` restoration handler, and launches `interop_smoke_test_standalone_gui.py`.
- **Headless Test & Visual Snapshot**: `setups/gpu-smoke-test/interop_smoke_test_auto.py`
  - Pure standard-library PNG serialization (`write_png` via `struct` and `zlib`, zero third-party dependencies).
  - Headless offscreen snapshot rendering using OpenGL 3.3 Core Profile shader program (`VERTEX_SHADER` + `FRAGMENT_SHADER`), rendering the zero-copy VBO points and connecting circle to a 256x256 RGBA frame.
- **Interactive GUI Test**: `setups/gpu-smoke-test/interop_smoke_test_standalone_gui.py`
  - Standalone PyQt6 + VisPy application displaying 64 animated markers arranged along a 3D double torus.
  - Complete zero-copy VBO mutation loop per frame without CPU-GPU transfers.
  - CLI argument parsing (`--timeout`, `--markers`) enabling both automated verification and interactive human inspection.

---

## How to Run

From `snngineV4_agent_branches/`:

### 1. Phase 1 & 2: Automated Headless EGL Test + Offscreen Snapshot
```bash
setups/gpu-smoke-test/interop_smoke_test_docker_launcher.sh
```

**What this does:**
1. Checks for Docker image `snngine-gpu-smoke:headless` (builds it if missing).
2. Spawns an isolated container with `--gpus all`.
3. Initializes headless EGL directly against the host NVIDIA driver.
4. Executes Tests A, B, C, and D across all 5 links of the zero-copy chain.
5. Renders a 256x256 offscreen snapshot of the VBO markers and saves it to `setups/gpu-smoke-test/rendered_frame.png`.
6. Exits with code 0 on complete pass.

### 2. Phase 3: Interactive GUI Check (Host X11 Display)
```bash
setups/gpu-smoke-test/interop_smoke_test_docker_launcher.sh --gui
```

**What this does:**
1. Applies GNOME Shell extension safety guard (`gnome-extensions disable tiling-assistant@ubuntu.com`).
2. Configures container X11 access (`xhost +local:root`).
3. Launches interactive PyQt6 + VisPy window on host `DISPLAY=:1`.
4. Executes live 3D rendering driven purely by zero-copy VRAM mutations.
5. Restores GNOME Shell extension cleanly on exit via trap handler.

---

## Execution Results (Ubuntu 24.04 Container Verified 2026-09-28)

### Phase 1 & 2: Automated Headless EGL Execution Log
```
======================================================================
SNNgineV4 - Docker GPU Interop Smoke Test Launcher
======================================================================
[Launcher] Docker image 'snngine-gpu-smoke:headless' found.
======================================================================
[Launcher] Mode: Phase 1 & 2 Automated Headless EGL + Offscreen Snapshot
======================================================================

==========
== CUDA ==
==========

CUDA Version 12.6.2

Container image Copyright (c) 2016-2023, NVIDIA CORPORATION & AFFILIATES. All rights reserved.

======================================================================
SNNgineV4 - Phase 2: Automated Headless Interop Smoke Test
======================================================================

[Step 1/7] Initializing headless EGL OpenGL context...
  - EGL Renderer:  NVIDIA GeForce RTX 3090/PCIe/SSE2
  - EGL Vendor:    NVIDIA Corporation
  - GL Version:    4.6.0 NVIDIA 595.91.07

[Step 2/7] Initializing PyCUDA & PyTorch CUDA contexts...
  - CUDA Device:   NVIDIA GeForce RTX 3090 (Compute Capability 8.6)
  - PyTorch CUDA:  v12.4, is_available=True

[Step 3/7] Creating OpenGL Vertex Buffer Object (VBO)...
  - VBO ID:        1
  - Buffer Layout: 32 elements x 14 floats (1792 bytes)

[Step 4/7] Registering VBO with PyCUDA OpenGL interop...
  - Mapped Ptr:    0x7f1f083ff800
  - Mapped Size:   1792 bytes (expected 1792)

[Step 5/7] Wrapping mapped pointer via Numba into PyTorch tensor...
  - Numba Array:   shape=(32, 14), dtype=float32
  - PyTorch View:  shape=torch.Size([32, 14]), device=cuda:0
  - Tensor Ptr:    0x7f1f083ff800
  ✓ Zero-copy pointer identity verified: PyTorch shares exact VRAM address.

[Step 6/7] Test A: PyTorch tensor direct write-through assertion...
  ✓ Direct PyTorch write-through confirmed: OpenGL readback matches byte-for-byte.

[Step 7/7] Test B & C: CUDA kernel execution and PyTorch view consistency...
  ✓ PyTorch view consistency confirmed: sees CUDA kernel writes live in VRAM.
  ✓ CUDA kernel write-through confirmed: OpenGL readback matches byte-for-byte.

[Step 7B/7] Test D: Sister repo self-compiled CUDA simulation code (update_N_state)...
neuron states:
	N0: pt=0.75, u=0.00, v=-65.00, a=-65.00, b=0.23, c=-70.04, d=-11.98, i=0.00
	N1: pt=0.34, u=0.00, v=-65.00, a=-65.00, b=0.21, c=-81.43, d=-7.43, i=0.00
...
  ✓ Sister repo self-compiled simulation kernel (update_N_state) executed and verified.

[Visual Check] Rendering offscreen frame to: /output/rendered_frame.png
  ✓ Offscreen frame rendered and saved (256x256 PNG).

======================================================================
ALL INTEROP ASSERTIONS PASSED (5/5 LINKS VERIFIED ZERO-COPY)
======================================================================
======================================================================
[Launcher] Test container exited with code: 0
======================================================================
```

### Phase 3: Interactive GUI Execution Log
```
======================================================================
SNNgineV4 - Docker GPU Interop Smoke Test Launcher
======================================================================
[Launcher] Docker image 'snngine-gpu-smoke:headless' found.
======================================================================
[Launcher] Mode: Phase 3 Interactive GUI (standalone VisPy double torus)
======================================================================
[Launcher] Applying host GNOME Shell extension safety guard...
[Launcher] Launching GUI container on DISPLAY=:1...

==========
== CUDA ==
==========

CUDA Version 12.6.2

======================================================================
Launching SNNgineV4 Standalone Interop Smoke Test (Phase 1 Visual Check)
======================================================================
Application window is open.

======================================================================
SNNgineV4 - Standalone Interop Chain Setup:
======================================================================
1. OpenGL VBO generated via VisPy: ID = 2
2. CUDA Device: NVIDIA GeForce RTX 3090 (Compute Capability (8, 6))
3. PyCUDA RegisteredBuffer mapped: VRAM ptr = 0x7ca20a3ff000, size = 3584 bytes
4. Numba DeviceNDArray: shape=(64, 14), dtype=float32
5. PyTorch Tensor View: shape=torch.Size([64, 14]), device=cuda:0
   Tensor data_ptr = 0x7ca20a3ff000
   ✓ Verified: PyTorch shares exact memory address with OpenGL VBO (zero-copy).
neuron states:
	N0: pt=0.44, u=0.00, v=-65.00, a=-65.00, b=0.20, c=-79.11, d=-2.35, i=0.00
...
Link 1: Successfully integrated self-compiled CUDA simulation code (update_N_state from sim_demo_utils).
======================================================================

======================================================================
[Launcher] Test container exited with code: 0
======================================================================
[Launcher] Restoring tiling-assistant extension...
```

---

## Phase 2 Visual Check Verification

- **Rendered Output**: `setups/gpu-smoke-test/rendered_frame.png`
- **Format**: 256x256 RGBA 8-bit PNG.
- **Pixel Breakdown**:
  - Background (Dark Navy `[16, 20, 25, 255]`): 61,772 pixels.
  - Foreground (Cyan VBO Marker Points & Circle `[49, 206, 255, 255]`): 3,764 pixels.
- **Visual Outcome**: Visually confirmed 32 circular marker points arranged in a circular ring, rendered completely offscreen via EGL without an X server or desktop display.

---

## Hiccups Hit & How They Were Resolved

1. **PyCUDA v2024.1 C++ Compilation with NumPy 2**:
   - *Problem*: PyCUDA v2024.1's build system expects headers at `numpy/core/include/numpy/arrayobject.h`. Default pip install of `numpy` pulled NumPy 2.x, which moved headers to `_core/include`, causing a fatal C++ compilation error (`numpy/arrayobject.h: No such file or directory`).
   - *Resolution*: Pinned `"numpy<2"` (`numpy==1.26.4`) in `Dockerfile.docker-smoke`.
2. **Missing PyCUDA Runtime Dependencies**:
   - *Problem*: Building PyCUDA via `make install` installed the C extension and Python package but did not install its Python runtime dependencies (`pytools`, `appdirs`, `mako`), causing `ModuleNotFoundError: No module named 'pytools'` at `from pycuda.compiler import SourceModule`.
   - *Resolution*: Added `pytools`, `appdirs`, and `mako` to the dependencies installed prior to PyCUDA.
3. **Ubuntu 24.04 Debian Package Uninstall Collision (`RECORD file not found`)**:
   - *Problem*: In Ubuntu 24.04, `pip3 install --upgrade pip` fails with `ERROR: Cannot uninstall pip 24.0, RECORD file not found. Hint: The package was installed by debian`.
   - *Resolution*: Isolated all Python packages in a dedicated virtual environment `/opt/venv` (`ENV PATH="/opt/venv/bin:$PATH"`). This completely decouples pip and site-packages from Debian system packages without needing `--break-system-packages`.
4. **Ubuntu 24.04 64-bit time_t Package Transition (`libglib2.0-0t64`)**:
   - *Problem*: Ubuntu 24.04 Noble Numbat transitioned `libglib2.0-0` to `libglib2.0-0t64`. Installing the legacy name failed or pulled transitional packages.
   - *Resolution*: Updated `Dockerfile.docker-smoke` to install `libglib2.0-0t64` along with `libxcb-*` and `libxkbcommon-x11-0`.
5. **Sister Repo Top-Level `import pandas as pd`**:
   - *Problem*: Line 5 of `SNNgine3D_agent_branches/notebooks/simulation_demo/sim_demo_utils.py` imports `pandas as pd` for notebook dataframe display. `pandas` was not installed in the minimal container, failing Test D.
   - *Resolution*: Added a lightweight mock for `pandas` in both `interop_smoke_test_auto.py` and `interop_smoke_test_standalone_gui.py`, allowing `sim_demo_utils.py` to import and execute its CUDA kernel without dragging in heavy data-science dependencies.
6. **PyOpenGL EGL Context Tracking for Offscreen Snapshot**:
   - *Problem*: PyOpenGL's legacy `glVertexPointer` failed with `Attempt to retrieve context when no valid context` under EGL because PyOpenGL defaults to tracking GLX context state.
   - *Resolution*: Set `os.environ['PYOPENGL_PLATFORM'] = 'egl'` at module initialization and implemented offscreen snapshot rendering using OpenGL 3.3 Core Profile VAOs, VBOs, and shaders (`glUseProgram`, `glDrawArrays`) rather than legacy fixed-function client state.
7. **GNOME Shell Mutter Assertion Crash on Interactive GUI Window Creation**:
   - *Problem*: On Ubuntu 24.04 host running GNOME 46, rapid window mapping/unmapping from containerized Qt apps can trigger a known Mutter window-stack assertion crash in `tiling-assistant@ubuntu.com` (`window->stack_position >= 0`).
   - *Resolution*: Built a safety guard in `interop_smoke_test_docker_launcher.sh` that temporarily disables `tiling-assistant@ubuntu.com` before container launch and restores it automatically upon process termination via a bash `trap ... EXIT` handler.

---

## Comparison Matrix

| Feature | Prior SNNgine3D Attempt (`Dockerfile-SNNgine3D-nomachine`) | Ubuntu 22.04 Prototype | Ubuntu 24.04 Final Stack (`Dockerfile.docker-smoke`) |
|---|---|---|---|
| **Base OS** | Ubuntu 20.04 Focal | Ubuntu 22.04 Jammy | **Ubuntu 24.04 Noble Numbat** |
| **CUDA Version** | CUDA 11.4 (Obsolete) | CUDA 12.4.1 | **CUDA 12.6.2** |
| **Python Version** | Python 3.8 | Python 3.10 | **Python 3.12** (matches host) |
| **Desktop / Display** | Full XFCE4 desktop + NoMachine daemon | Headless EGL offscreen | **Dual-mode: Headless EGL + Host X11 GUI** |
| **Image Size / Bloat** | Tens of GBs (IDE, desktop, notebooks) | ~3.5 GB | **Clean ~4 GB container** |
| **GPU Acceleration** | **Failed** | **Passed** | **Passed (100% hardware acceleration)** |
| **Zero-Copy Chain** | Unverified | Verified 5/5 links | **Verified 5/5 links (Headless + GUI)** |
| **Host Crash Guard** | None | None | **Automated tiling-assistant guard** |
