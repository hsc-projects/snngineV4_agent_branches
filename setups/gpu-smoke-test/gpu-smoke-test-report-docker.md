# GPU Smoke Test Report (Docker Containerization)

## Summary

Successfully containerized and verified the local GPU CUDA-OpenGL zero-copy interop smoke test inside a lightweight Docker container (`snngine-gpu-smoke:headless`) using NVIDIA Container Runtime (`--gpus all`). The containerized pipeline executes all 5 links of the zero-copy interop chain unattended under headless EGL (GL 4.6.0 NVIDIA on RTX 3090, Driver 595.91.07), verifying PyCUDA VBO mapping, Numba `DeviceNDArray`, PyTorch `torch.as_tensor` zero-copy pointer identity, direct PyTorch write-through, CUDA kernel write-through, and real self-compiled simulation code (`sim_demo_utils.update_N_state`). In addition, an offscreen EGL framebuffer snapshot (`rendered_frame.png`) was rendered and verified with zero desktop/X11 dependency. All assertions passed with 100% byte-for-byte readback fidelity and exit code 0.

---

## What Was Built

- **Dockerfile**: `setups/gpu-smoke-test/Dockerfile.docker-smoke`
  - Base: `nvidia/cuda:12.4.1-devel-ubuntu22.04`
  - Environment: `NVIDIA_VISIBLE_DEVICES=all`, `NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics,display` (essential for injecting host NVIDIA EGL and OpenGL driver libraries into the container).
  - Python Stack: Python 3.10, PyTorch 2.5.1 (`cu124`), NumPy 1.26.4 (`numpy<2`), Numba, PyOpenGL, PyOpenGL_accelerate.
  - PyCUDA: Built from source from git tag `v2024.1` with `--cuda-enable-gl` and `--cuda-root=/usr/local/cuda`.
- **Host Launcher Script**: `setups/gpu-smoke-test/interop_smoke_test_docker_launcher.sh`
  - Follows the project's `interop_smoke_test_<descriptor>` convention.
  - Autonomously checks whether the `snngine-gpu-smoke:headless` image exists locally; if missing, automatically triggers `docker build` from `Dockerfile.docker-smoke`.
  - Launches container with `--gpus all`, mounts the workspace, configures `PYTHONPATH`, and passes the `--snapshot /output/rendered_frame.png` argument.
- **Headless Test & Visual Snapshot**: `setups/gpu-smoke-test/interop_smoke_test_auto.py`
  - Added pure standard-library PNG serialization (`write_png` via `struct` and `zlib`, zero third-party dependencies).
  - Added headless offscreen snapshot rendering using OpenGL 3.3 Core Profile shader program (`VERTEX_SHADER` + `FRAGMENT_SHADER`), rendering the zero-copy VBO points and connecting circle to a 256x256 RGBA frame.

---

## How to Run

From `snngineV4_agent_branches/`:
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

---

## Execution Results (Containerized Run Verified 2026-09-28)

```
======================================================================
SNNgineV4 - Docker GPU Interop Smoke Test Launcher
======================================================================
[Launcher] Docker image 'snngine-gpu-smoke:headless' found.
[Launcher] Launching container with --gpus all...

==========
== CUDA ==
==========

CUDA Version 12.4.1

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
  - Mapped Ptr:    0x748af63ff800
  - Mapped Size:   1792 bytes (expected 1792)

[Step 5/7] Wrapping mapped pointer via Numba into PyTorch tensor...
  - Numba Array:   shape=(32, 14), dtype=float32
  - PyTorch View:  shape=torch.Size([32, 14]), device=cuda:0
  - Tensor Ptr:    0x748af63ff800
  ✓ Zero-copy pointer identity verified: PyTorch shares exact VRAM address.

[Step 6/7] Test A: PyTorch tensor direct write-through assertion...
  ✓ Direct PyTorch write-through confirmed: OpenGL readback matches byte-for-byte.

[Step 7/7] Test B & C: CUDA kernel execution and PyTorch view consistency...
  ✓ PyTorch view consistency confirmed: sees CUDA kernel writes live in VRAM.
  ✓ CUDA kernel write-through confirmed: OpenGL readback matches byte-for-byte.

[Step 7B/7] Test D: Sister repo self-compiled CUDA simulation code (update_N_state)...
neuron states:
	N0: pt=0.73, u=0.00, v=-65.00, a=-65.00, b=0.23, c=-71.35, d=-11.46, i=0.00
	N1: pt=0.13, u=0.00, v=-65.00, a=-65.00, b=0.24, c=-66.08, d=-13.57, i=0.00
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
   - *Resolution*: Added `pytools`, `appdirs`, and `mako` to the `pip3 install` step in `Dockerfile.docker-smoke`.
3. **Container Path Resolution (`PROJECT_ROOT` / Sister Repo `IndexError`)**:
   - *Problem*: `interop_smoke_test_auto.py` hardcoded `parents[2]` and `parents[3]` for finding the project root and sister repo. When mounted in `/app`, `len(parents)` was $\le 2$, triggering `IndexError: 2`.
   - *Resolution*: Updated `interop_smoke_test_auto.py` to check `len(parents)` before indexing and fall back to `sys.path`. Updated the launcher script to bind-mount the parent directory (`snngineV4_cloud`) at `/workspace/snngineV4_cloud`, preserving identical directory depth.
4. **Sister Repo Top-Level `import pandas as pd`**:
   - *Problem*: Line 5 of `SNNgine3D_agent_branches/notebooks/simulation_demo/sim_demo_utils.py` imports `pandas as pd` for notebook dataframe display. `pandas` was not installed in the minimal container, failing Test D.
   - *Resolution*: Added a lightweight mock for `pandas` in `interop_smoke_test_auto.py` (matching the existing `IPython` mock), allowing `sim_demo_utils.py` to import and execute its CUDA kernel without dragging in heavy data-science dependencies.
5. **PyOpenGL EGL Context Tracking for Offscreen Snapshot**:
   - *Problem*: PyOpenGL's legacy `glVertexPointer` failed with `Attempt to retrieve context when no valid context` under EGL because PyOpenGL defaults to tracking GLX context state.
   - *Resolution*: Set `os.environ['PYOPENGL_PLATFORM'] = 'egl'` at module initialization and implemented offscreen snapshot rendering using OpenGL 3.3 Core Profile VAOs, VBOs, and shaders (`glUseProgram`, `glDrawArrays`) rather than legacy fixed-function client state.

---

## Comparison with Prior SNNgine3D NoMachine Attempt

| Feature | Prior Attempt (`Dockerfile-SNNgine3D-nomachine`) | New Implementation (`Dockerfile.docker-smoke`) |
|---|---|---|
| **Base Image** | `nvidia/cudagl:11.4.2-devel-ubuntu20.04` (Obsolete) | `nvidia/cuda:12.4.1-devel-ubuntu22.04` (Modern CUDA 12) |
| **GPU / Driver** | CUDA 11.4 (Incompatible with modern 595+ drivers) | CUDA 12.4 + Driver 595.91 (RTX 3090 Ampere sm 8.6) |
| **Desktop / Display** | Full XFCE4 desktop + NoMachine (`nxserver`) daemon | Headless EGL offscreen (zero desktop / zero X11) |
| **Image Size / Bloat** | Tens of gigabytes (Jupyter, PyCharm, Bokeh, Poetry) | Lightweight (~3.5 GB including PyTorch + CUDA devel) |
| **GPU Acceleration** | **Failed**: Remote desktop worked, GPU rendering failed | **Passed**: 100% hardware GPU acceleration verified |
| **Zero-Copy Assertions** | None (only ran generic PyCUDA tests) | Rigorous automated assertions across all 5 links |
| **Visual Check** | Required NoMachine client connection | Headless snapshot dump to `rendered_frame.png` |

---

## Next Steps for Cloud / RunPod Deployment

With local containerized zero-copy interop proven:
1. **Feed Findings into `runpod-rationale.md`**: Open item 0 is fully resolved: the CUDA-OpenGL zero-copy interop stack functions reliably inside a Docker container using NVIDIA's standard EGL driver injection (`compute,utility,graphics,display`).
2. **RunPod Pod Template**: This `Dockerfile.docker-smoke` can serve as the clean base image for RunPod GPU pods. Workloads can run headlessly via EGL or expose offscreen framebuffers without running heavy remote-desktop stacks.
