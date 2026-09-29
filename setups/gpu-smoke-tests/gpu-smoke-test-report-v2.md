# Modernized GPU/CUDA-OpenGL-Interop Smoke Test Report v2 (Max Frontier Discovery)

## Summary

Successfully pushed the Python, CUDA, PyTorch, and OpenGL zero-copy interop stack to the **absolute maximum possible versions** for the workstation's **NVIDIA GeForce RTX 3090** (Ampere `sm_86`) without imposing any artificial version ceilings. 

The complete 5-link zero-copy interop pipeline is **100% verified operational** across all three operational categories:
- **Category 1 (Headless EGL)**: Automated 5-link assertions, live VRAM write-through verification, sister repo simulation code (`sim_demo_utils.update_N_state`), and offscreen snapshot rasterization (`rendered_frame_frontier.png`).
- **Category 2 (Desktop GUI)**: Native interactive 3D windowing via PySide6 + VisPy with hardware acceleration on host display (`DISPLAY=:1`) protected by automated GNOME Shell tiling assistant safety traps.
- **Category 3 (Web Bridge)**: Cloud-ready headless EGL rendering with real-time WebSocket frame streaming (800×600 @ 29.3 FPS, 3.8 ms render latency) and 4-way interactive toggles (CUDA Kernel / PyTorch fallback × Izhikevich SNN / Sine Wave).

### Frontier Discovery vs Previous Baselines

| Component | Workstation Baseline (`snngine`) | Docker Cloud (`Dockerfile.docker-smoke`) | Modern Frontier (`snngine-env-v2`) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Python Runtime** | 3.12.3 | 3.12.3 | **3.14.7** (conda-forge) | **Max Frontier (+2 major)** |
| **Host Driver** | 595.91.07 (Static Invariant) | 595.91.07 (Container Passthrough) | **595.91.07 (Static Invariant)** | **Preserved (Userspace Only)** |
| **CUDA Toolkit / NVCC** | 12.0 / 12.1 | 12.6.2 | **13.2.0 / 13.2.86** (conda-forge) | **Max Driver Alignment (13.2)** |
| **PyTorch** | 2.1.2 (`cu121`) | 2.5.1 (`cu124`) | **2.15.0.dev20260929+cu132** | **Bleeding-Edge Nightly** |
| **PyCUDA** | 2025.1.1 (git) | 2024.1 (git) | **2026.1** (Source + `--cuda-enable-gl`) | **Latest Release** |
| **Numba** | 0.61.0 | 0.67.0 | **0.67.0** (`py314` conda-forge) | **Max Frontier** |
| **VisPy** | 0.14.3 | 0.14.3 | **0.17.0** (`py314` conda-forge) | **Max Frontier (+3 minor)** |
| **Qt Framework** | PySide6 6.7.3 / QtPy | PyQt6 6.7.1 | **PySide6 6.11.2 / Qt6 6.11.2** | **Max Frontier (+4 minor)** |
| **OpenGL API** | 4.6.0 NVIDIA | 4.6.0 NVIDIA | **4.6.0 NVIDIA** | **Full Hardware Acceleration** |

---

## Phase 0: Frontier Survey & Probing Analysis

In accordance with the core directive (**"FIND THE LIMITS, NOT INVENT THEM — NO ARBITRARY CEILINGS"**), every dependency layer was empirically probed from the top down:

1. **Host Driver Capability**:
   - `nvidia-smi` reports `Driver Version: 595.91.07`, `CUDA Version: 13.2`.
   - The host kernel driver interface supports CUDA runtimes up to CUDA 13.2. In compliance with the strict invariant (**DO NOT TOUCH THE HOST DRIVER**), all higher toolkits were isolated to userspace in Conda.

2. **Python Runtime Frontier**:
   - Probed Python 3.15rc and 3.14. Python 3.15rc builds lack mature compiled wheel ecosystems for PyTorch and Numba.
   - Python 3.14 has production packages in conda-forge (`python=3.14.7`) and native binary wheels for PyTorch (`cp314`) and Numba 0.67.0 (`py314`). Python 3.14.7 was selected as the operational frontier runtime.

3. **PyTorch & CUDA Toolkit Frontier**:
   - PyPI provides PyTorch 2.14.0 with CUDA 13.0 dependencies (`cuda-toolkit==13.0.3`).
   - PyTorch's bleeding-edge nightly index (`download.pytorch.org/whl/nightly/cu132`) provides **PyTorch 2.15.0-dev** (`torch-2.15.0.dev20260929+cu132-cp314-cp314-manylinux_2_28_x86_64.whl`) explicitly compiled against **CUDA 13.2** with `cuda-toolkit 13.2.2`, `cuDNN 9.26`, `NCCL 2.30.7`, and `Triton 3.8.0-git`. This matches the host driver's top CUDA capability.

4. **PyCUDA OpenGL Interop Frontier**:
   - Conda-forge binary wheels for PyCUDA do not enable OpenGL interop (`pycuda.gl` is absent).
   - Cloning PyCUDA git master / version 2026.1 and compiling from source with `--cuda-enable-gl` against the Conda environment's CUDA 13.2 toolkit (`targets/x86_64-linux/include`) and host driver runtime (`/usr/lib/x86_64-linux-gnu/libcuda.so`) produced a fully functional `pycuda.gl.RegisteredBuffer` on Python 3.14.

---

## Phase 1: Environment Provisioning & Diagnostics

The isolated environment was provisioned at `/home/htm/anaconda3/envs/snngine-env-v2`:

```bash
# Provisioning sequence
conda create -n snngine-env-v2 python=3.14 pip setuptools wheel -c conda-forge -y
conda install -n snngine-env-v2 numba "cuda-toolkit=13.2*" vispy -c conda-forge -y
/home/htm/anaconda3/envs/snngine-env-v2/bin/pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu132
/home/htm/anaconda3/envs/snngine-env-v2/bin/pip install pyside6 pillow websockets scipy pyopengl qtpy
```

PyCUDA was compiled and installed via:
```bash
python ./configure.py \
  --cuda-root=/home/htm/anaconda3/envs/snngine-env-v2/targets/x86_64-linux \
  --cuda-inc-dir=/home/htm/anaconda3/envs/snngine-env-v2/targets/x86_64-linux/include \
  --cudadrv-lib-dir=/usr/lib/x86_64-linux-gnu \
  --cudart-lib-dir=/home/htm/anaconda3/envs/snngine-env-v2/targets/x86_64-linux/lib \
  --cuda-enable-gl
pip install . --no-build-isolation
```

### Import Diagnostics Output
```
Python:  3.14.7 | packaged by conda-forge | (main, Sep  2 2026, 21:08:32) [GCC 15.3.0]
PyTorch: 2.15.0.dev20260929+cu132 (CUDA 13.2)
PyCUDA:  2026.1
VisPy:   0.17.0
Numba:   0.67.0
PySide6: /home/htm/anaconda3/envs/snngine-env-v2/lib/python3.14/site-packages/PySide6/__init__.py (v6.11.2)
pycuda.gl RegisteredBuffer: True
Numba CUDA available: True (NVIDIA GeForce RTX 3090)
VisPy EGL backend: egl
VisPy Qt backend: PySide6
QtPy API: PySide6 6.11.2
```

---

## Phase 2: Category 1 — Headless EGL Smoke Test

Command executed:
```bash
/home/htm/anaconda3/envs/snngine-env-v2/bin/python setups/gpu-smoke-tests/interop_smoke_test_auto.py \
  --snapshot setups/gpu-smoke-tests/rendered_frame_frontier.png
```

### Verification Results
1. **Headless EGL Context**: Initialized offscreen context using NVIDIA EGL (`NVIDIA GeForce RTX 3090/PCIe/SSE2`, GL 4.6.0 NVIDIA 595.91.07).
2. **CUDA & PyTorch Contexts**: PyTorch initialized with CUDA 13.2 targeting RTX 3090 CC 8.6.
3. **OpenGL VBO**: Allocated 32 elements × 14 floats (1,792 bytes, ID 1).
4. **PyCUDA GL Registration**: Mapped VBO to VRAM pointer `0x776ce63ff800`.
5. **Numba DeviceNDArray & PyTorch View**:
   - `numba.cuda.as_cuda_array` wrapped the pointer.
   - `torch.as_tensor` created a view with identical data pointer `0x776ce63ff800`.
   - **Zero-copy pointer identity verified**: PyTorch shares the exact VRAM address with the OpenGL VBO.
6. **Direct PyTorch Write-Through (Test A)**: Mutated tensor data directly via PyTorch; OpenGL readback via `glGetBufferSubData` confirmed exact byte-for-byte match.
7. **CUDA Kernel Execution & Consistency (Test B & C)**: PyCUDA kernel mutated VRAM buffer; both PyTorch tensor view and OpenGL buffer readback reflected the mutations instantly.
8. **Sister Repo Simulation Code (Test D)**: Compiled and executed `sim_demo_utils.update_N_state` across 32 neurons; membrane potentials and spike dynamics verified live in VBO memory.
9. **Offscreen Snapshot**: Rasterized 256×256 frame with OpenGL 3.3 Core Profile shaders to `setups/gpu-smoke-tests/rendered_frame_frontier.png`.

**Result: ALL INTEROP ASSERTIONS PASSED (5/5 LINKS VERIFIED ZERO-COPY).**

---

## Phase 3: Category 2 — Desktop GUI Smoke Test

Command executed (with automated tiling assistant crash safety trap):
```bash
trap 'gnome-extensions enable tiling-assistant@ubuntu.com' EXIT INT TERM
gnome-extensions disable tiling-assistant@ubuntu.com
DISPLAY=:1 QT_XCB_GL_INTEGRATION=glx /home/htm/anaconda3/envs/snngine-env-v2/bin/python \
  setups/gpu-smoke-tests/interop_smoke_test_standalone_gui.py --timeout 6
gnome-extensions enable tiling-assistant@ubuntu.com
```

### Verification Results
1. **Safety Guard**: `tiling-assistant@ubuntu.com` was cleanly disabled during window mapping and re-enabled immediately upon completion.
2. **Window & Context Initialization**: Native PySide6 window opened on display `:1`. OpenGL VBO generated via VisPy (`ID = 2`).
3. **Zero-Copy Chain**:
   - PyCUDA registered buffer mapped at `0x75db783ff000` (3,584 bytes for 64 markers).
   - PyTorch tensor view confirmed pointer identity: `data_ptr = 0x75db783ff000`.
4. **Rendering & Animation**:
   - 64 markers rendered in real-time along a 3D double torus at ~33 FPS.
   - Live animation updated via direct VRAM mutation without CPU-GPU buffer transfers.
   - Closed cleanly after 6.0 seconds timeout with exit code `0`.

---

## Phase 4: Category 3 — Web Bridge Smoke Test

Command executed:
```bash
/home/htm/anaconda3/envs/snngine-env-v2/bin/python setups/gpu-smoke-tests/interop_smoke_test_web_gui.py \
  --port 6085 --timeout 6
```

### Verification Results
1. **Server Initialization**: VisPy EGL offscreen context initialized (`OpenGL VBO handle #2`). PyCUDA registered buffer mapped at `0x7686fe3ff000` (3,584 bytes).
2. **Zero-Copy Chain**: PyTorch tensor view confirmed at `data_ptr = 0x7686fe3ff000`.
3. **Simulation Kernels**: Both sine wave simulation kernel and `update_N_state` Izhikevich simulation code compiled and bound.
4. **Frame Rendering & Streaming Performance**:
   - Resolution: 800×600 RGBA.
   - Stable render rate: **29.2 – 29.3 FPS**.
   - GPU render latency: **3.8 – 5.0 ms** per frame.
   - Clean shutdown and resource release on timeout.

---

## Phase 5: Containerized Docker Smoke Test (v2 Frontier)

The v2 frontier environment was packaged into an independent, self-contained Docker image (`snngine-gpu-smoke:v2`) built from scratch using [`Dockerfile.docker-smoke-v2`](file:///home/htm/snngine/snngineV4_cloud/snngineV4_agent_branches/setups/gpu-smoke-tests/Dockerfile.docker-smoke-v2).

Launcher script: [`setups/gpu-smoke-tests/interop_smoke_test_docker_launcher_v2.sh`](file:///home/htm/snngine/snngineV4_cloud/snngineV4_agent_branches/setups/gpu-smoke-tests/interop_smoke_test_docker_launcher_v2.sh).

### Verification Results Across All 3 Modes

#### 1. Mode 1: Automated Headless EGL Smoke Test (Default)
Command executed:
```bash
./setups/gpu-smoke-tests/interop_smoke_test_docker_launcher_v2.sh
```
- **Execution Mode**: Unattended headless EGL without display or X11 socket mounts.
- **User Mapping**: Executed with `--user $(id -u):$(id -g)` and `HOME=/tmp` to guarantee user ownership on outputs.
- **Zero-Copy Chain**:
  - Allocated OpenGL VBO (ID 1, 1,792 bytes).
  - PyCUDA RegisteredBuffer mapped at pointer `0x720a6e3ff800`.
  - PyTorch tensor view verified identical pointer `0x720a6e3ff800` (**zero-copy pointer identity confirmed**).
  - Direct PyTorch write-through (Test A): Byte-for-byte readback match via `glGetBufferSubData`.
  - CUDA kernel execution (Test B & C): Live VRAM mutation confirmed.
  - Sister repo simulation code (Test D): `update_N_state` executed across 32 neurons.
- **Snapshot Artifact**: Saved offscreen rasterized frame to [`setups/gpu-smoke-tests/rendered_frame_docker_v2.png`](file:///home/htm/snngine/snngineV4_cloud/snngineV4_agent_branches/setups/gpu-smoke-tests/rendered_frame_docker_v2.png) (owned by `htm:htm`, 664).
- **Result**: **`ALL INTEROP ASSERTIONS PASSED (5/5 LINKS VERIFIED ZERO-COPY)`** (exit code `0`).

#### 2. Mode 2: Interactive Desktop GUI Smoke Test (`--gui`)
Command executed:
```bash
./setups/gpu-smoke-tests/interop_smoke_test_docker_launcher_v2.sh --gui --timeout 3
```
- **Display Integration**: Container forwarded `DISPLAY=:1` and mounted `/tmp/.X11-unix` with `QT_XCB_GL_INTEGRATION=glx`.
- **Safety Trap**: Automatically disabled `tiling-assistant@ubuntu.com` during window creation and restored it cleanly on exit.
- **Zero-Copy Chain**: PyCUDA mapped VRAM ptr `0x7868343ff000`, PyTorch tensor view `0x7868343ff000`.
- **Rendering**: PySide6 standalone window rendered 64 rotating double torus markers live in VRAM with zero `set_data()` calls.
- **Result**: **PASSED** (exit code `0`).

#### 3. Mode 3: Interactive Web Bridge (`--web`)
Command executed:
```bash
./setups/gpu-smoke-tests/interop_smoke_test_docker_launcher_v2.sh --web --timeout 3
```
- **Server Execution**: Embedded asyncio HTTP/WebSocket streaming server on port `6080`.
- **Zero-Copy Chain**: VisPy EGL offscreen context with PyCUDA mapped VRAM ptr `0x7403443ff000`.
- **Performance**:
  - Stable render rate: **29.2 FPS**.
  - GPU render latency: **2.9 ms** per frame.
- **Result**: **PASSED** (clean shutdown after timeout, exit code `0`).

---

## Hiccups Hit Along the Way & Resolutions

1. **`No module named 'OpenGL'` during Category 1**:
   - *Problem*: PyOpenGL was missing from the fresh Conda environment.
   - *Resolution*: Installed `pyopengl-3.1.10` via pip.

2. **Qt6 XCB Integration Failure (`QXcbIntegration: Cannot create platform OpenGL context, neither GLX nor EGL are enabled`)**:
   - *Problem*: On Ubuntu 24.04 with proprietary NVIDIA drivers, Qt6 (PySide6 / PyQt6) wheels under dual conda/system glvnd setups fail to auto-detect the default OpenGL integration mode.
   - *Resolution*: Set `QT_XCB_GL_INTEGRATION=glx` (or `xcb_egl`), which successfully initializes hardware-accelerated OpenGL contexts for `QOpenGLWidget` (`w.isValid() == True`).

3. **Attribute Typo in `interop_smoke_test_standalone_gui.py`**:
   - *Problem*: Line 465 attempted to rotate the camera via `self.canvas.view.camera.azimuth` instead of `self.view.camera.azimuth`, causing an `AttributeError` during step mutations.
   - *Resolution*: Corrected the reference to `self.view.camera.azimuth`.

4. **GNOME Shell Tiling Assistant Mutter Crash**:
   - *Problem*: Rapid window creation during heavy GPU initialization can trigger `assertion 'window->stack_position >= 0' failed` in Ubuntu 24.04's `tiling-assistant@ubuntu.com`.
   - *Resolution*: Wrapped execution in a bash script with a `trap` handler that temporarily disables the extension and guarantees restoration on exit or interruption.

5. **`GL/gl.h` Header Missing During Container PyCUDA Compilation**:
   - *Problem*: Conda's GCC compiler wrapper in Ubuntu 24.04 restricts header lookup to the Conda sysroot, failing to find system OpenGL headers in `/usr/include/GL/gl.h`.
   - *Resolution*: Installed `libgl-dev` in the container base layer and passed `--cxxflags="-I/usr/include"` to PyCUDA's `configure.py`.

6. **Build-Time vs Runtime GPU Driver Injection in Docker**:
   - *Problem*: `import pycuda.driver` inside `RUN` commands failed during `docker build` (`ImportError: libcuda.so.1: cannot open shared object file`).
   - *Resolution*: Understood that NVIDIA Container Toolkit injects `libcuda.so.1` into container userspace at container run-time (`docker run --gpus all`), not at build time. Adjusted build-time diagnostics to test pure userspace imports (`torch`, `vispy`, `PySide6`, `numba`) and reserved CUDA driver verification for container runtime.

---

## Reproducibility Helper

A self-contained environment bootstrap script has been created at [`setups/gpu-smoke-tests/create_v2_env.sh`](file:///home/htm/snngine/snngineV4_cloud/snngineV4_agent_branches/setups/gpu-smoke-tests/create_v2_env.sh).

To recreate the entire frontier environment:
```bash
cd snngineV4_agent_branches
./setups/gpu-smoke-tests/create_v2_env.sh snngine-env-v2
```

To run all 3 smoke test categories:
```bash
# 1. Category 1: Headless EGL Smoke Test
/home/htm/anaconda3/envs/snngine-env-v2/bin/python setups/gpu-smoke-tests/interop_smoke_test_auto.py \
  --snapshot setups/gpu-smoke-tests/rendered_frame_frontier.png

# 2. Category 2: Desktop GUI Smoke Test (with GNOME tiling safety trap)
trap 'gnome-extensions enable tiling-assistant@ubuntu.com' EXIT INT TERM
gnome-extensions disable tiling-assistant@ubuntu.com
DISPLAY=:1 QT_XCB_GL_INTEGRATION=glx /home/htm/anaconda3/envs/snngine-env-v2/bin/python \
  setups/gpu-smoke-tests/interop_smoke_test_standalone_gui.py --timeout 6
gnome-extensions enable tiling-assistant@ubuntu.com

# 3. Category 3: Web Bridge Smoke Test
/home/htm/anaconda3/envs/snngine-env-v2/bin/python setups/gpu-smoke-tests/interop_smoke_test_web_gui.py \
  --port 6080

# 4. Category 4: Containerized Docker Smoke Test (v2 Frontier)
# Mode 1: Automated Headless EGL Test
./setups/gpu-smoke-tests/interop_smoke_test_docker_launcher_v2.sh

# Mode 2: Interactive Desktop GUI Test (host display :1 with Mutter safety trap)
./setups/gpu-smoke-tests/interop_smoke_test_docker_launcher_v2.sh --gui --timeout 6

# Mode 3: Interactive Web Bridge (port 6080)
./setups/gpu-smoke-tests/interop_smoke_test_docker_launcher_v2.sh --web
```
