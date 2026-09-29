# Task: Modernized GPU/CUDA-OpenGL-Interop Smoke Test v2 (Max Frontier Discovery)

## Objective & Scope

Push the Python, CUDA, PyTorch, and OpenGL zero-copy interop stack to the **absolute maximum possible versions** for the workstation's **NVIDIA GeForce RTX 3090** (Ampere `sm_86`).

There are **NO upper limits**, no version ceilings, and no pre-emptive caps. Go as high as possible across the entire stack—including Python 3.14+, CUDA 13+, bleeding-edge PyTorch, PyCUDA, Numba, VisPy, and PySide6.

Once the maximum operational environment is provisioned in an isolated Conda environment, validate the complete 5-link zero-copy interop pipeline across **all operational categories** (both host and containerized):

1. **Category 1: Headless (EGL)** — Unattended automated assertions and offscreen EGL snapshot readback without a display server.
2. **Category 2: Desktop GUI** — Native desktop windowing using PySide6 + VisPy with hardware acceleration.
3. **Category 3: Web Bridge** — Headless EGL offscreen rendering with real-time WebSocket frame streaming and browser-based 3D interaction.
4. **Category 4: Containerized Docker (v2)** — Full multi-mode containerized verification (`snngine-gpu-smoke:v2`) reproducing the v2 stack for cloud deployment.

> [!IMPORTANT]
> **CORE PRINCIPLE: NO UPPER LIMITS — GO MAXIMUM.**
> Do NOT impose any ceilings, caps, or conservative boundaries. Test the absolute highest bleeding-edge versions available (including Python 3.14+, CUDA 13+, nightlies, git master builds). Only if a component physically fails to compile, link, or run on the RTX 3090 do you document the exact failure reason and move to the next build. Never invent, presume, or restrict to an upper limit.

---

## Safety & System Guardrails

### 1. Desktop Windowing Safety (Verified Mutter Crash Risk)
- **GNOME Shell Tiling Assistant Guard**: On Ubuntu 24.04 LTS, newly mapped X11 windows during heavy GPU initialization can trigger an assertion failure in `tiling-assistant@ubuntu.com` (`meta_window_set_stack_position_no_sync: assertion 'window->stack_position >= 0' failed`), aborting the entire desktop session.
- **Execution Order**: Always run Category 1 (Headless EGL) first. When executing Category 2 (Desktop GUI), ensure GNOME Shell tiling extensions are temporarily disabled via an automated bash `trap` or run with maintainer presence.
- **Headless & Web Bridge Isolation**: Categories 1 and 3 run headlessly via native EGL without touching the X11 server socket.

### 2. Host Driver Protection (STRICT INVARIANT: DO NOT TOUCH THE HOST DRIVER)
- **NEVER TOUCH THE HOST DRIVER**: Under no circumstances should the host NVIDIA display driver or kernel modules be modified, upgraded, downgraded, reinstalled, or tampered with.
- **Userspace Only**: All toolkits (CUDA Toolkit, NVCC, cuDNN), Python runtimes, PyTorch binaries, and libraries must reside strictly in userspace inside the dedicated Conda environment. No `apt install nvidia-driver-*` or system-level driver changes.

### 3. Environment Isolation
- Create a dedicated Conda environment (e.g. `snngine-frontier` or `snngine-max`).
- Do not modify, overwrite, or mutate existing active environments (`base`, `snngine`, `agent-orchestration`, etc.).

### 4. File & Repository Boundaries
- All work, helper scripts, logs, and reports must remain strictly within [`setups/gpu-smoke-tests/`](file:///home/htm/snngine/snngineV4_cloud/snngineV4_agent_branches/setups/gpu-smoke-tests/).
- Reuse or adapt the verified test scripts:
  - [`interop_smoke_test_auto.py`](file:///home/htm/snngine/snngineV4_cloud/snngineV4_agent_branches/setups/gpu-smoke-tests/interop_smoke_test_auto.py)
  - [`interop_smoke_test_standalone_gui.py`](file:///home/htm/snngine/snngineV4_cloud/snngineV4_agent_branches/setups/gpu-smoke-tests/interop_smoke_test_standalone_gui.py)
  - [`interop_smoke_test_web_gui.py`](file:///home/htm/snngine/snngineV4_cloud/snngineV4_agent_branches/setups/gpu-smoke-tests/interop_smoke_test_web_gui.py)
- Reference code in `SNNgine3D_agent_branches/notebooks/simulation_demo/sim_demo_utils.py` is read-only.

---

## Target Hardware Platform

The target hardware for this smoke test:

- **GPU**: NVIDIA GeForce RTX 3090
- **Architecture**: Ampere (`sm_86`, Compute Capability 8.6)
- **VRAM**: 24,576 MiB (24 GB GDDR6X)
- **Host OS**: Ubuntu 24.04 LTS (`x86_64`, Linux kernel 6.8+)
- **Host NVIDIA Driver**: Static workstation invariant (Driver 595.91.07). **STRICT INVARIANT: DO NOT TOUCH, UPGRADE, DOWNGRADE, OR ALTER THE HOST DRIVER.**
- **Conda Binary**: `/home/htm/anaconda3/bin/conda`

---

## The 5-Link Zero-Copy Interop Chain

The frontier environment must successfully compile, bind, and execute the complete 5-link zero-copy pipeline:

```
[Link 1: PyCUDA SourceModule / CUDA Kernel]
                │
                ▼ (Primary Context dev.retain_primary_context())
[Link 2: pycuda.gl Context Binding]
                │
                ▼ (pycuda.gl.RegisteredBuffer)
[Link 3: OpenGL VBO Mapped Pointer]
                │
                ▼ (ExternalMemory with __cuda_memory__ = True)
[Link 4: Numba DeviceNDArray]
                │
                ▼ (torch.as_tensor)
[Link 5: PyTorch Tensor View (Exact VRAM Pointer Match)]
```

- **Live Write-Through**: Mutations executed by PyTorch or CUDA kernels must directly alter VBO data in VRAM, instantly reflected upon OpenGL draw calls (`glDrawArrays`) and readback (`glGetBufferSubData`).

---

## Maximum Frontier Probing Protocol (No Upper Limits)

Target the absolute bleeding edge across every package and dependency:

1. **Python Runtime**:
   - Probe the highest available Python versions (e.g. Python 3.14+, 3.13).
   - Do NOT restrict or cap Python version selection.
   - If a candidate release lacks builds or fails compilation with core packages, pinpoint the exact blocker and step to the adjacent release to find the highest operational runtime.

2. **CUDA Toolkit**:
   - Probe the latest available CUDA Toolkits (e.g. CUDA 13.x, 13.4, 13.2+).
   - Do NOT cap at CUDA 12.x or any arbitrary version ceiling.
   - Verify that `nvcc` compiles kernels targeting Ampere `compute_86,sm_86`.

3. **PyTorch**:
   - Target the newest bleeding-edge PyTorch releases, nightlies, or source builds pairing with the newest CUDA and Python.
   - Verify hardware initialization on RTX 3090:
     ```python
     import torch
     assert torch.cuda.is_available()
     assert torch.cuda.get_device_capability(0) == (8, 6)
     ```

4. **PyCUDA (with OpenGL Interop)**:
   - Build the latest PyCUDA git repository or newest release against the target CUDA toolkit and Python with OpenGL interop:
     ```bash
     python ./configure.py --cuda-root=<cuda_path> --cuda-enable-gl
     make install
     ```
   - Must link with OpenGL/EGL headers and support `pycuda.gl.RegisteredBuffer`.

5. **Numba**:
   - Install the newest Numba release or build compatible with the chosen Python.
   - Verify that `numba.cuda` initializes and supports `DeviceNDArray` with `__cuda_memory__ = True`.

6. **VisPy & PySide6**:
   - Target PySide6 (specifically `pyside6>=6.11.2` with `shiboken6`) as the required Qt binding instead of PyQt6.
   - Verify that VisPy initializes with both `vispy.use('egl')` (headless) and `vispy.use('pyside6')` (desktop).
   - Verify that `QtPy` dynamically binds to `PySide6` without PyQt6 being present.

---

## Phased Execution Plan

### Phase 0: Frontier Survey & Probing
1. Inspect live hardware state and driver environment via `nvidia-smi`.
2. Inspect package availability across Conda channels and PyPI for the bleeding edge.
3. Formulate the highest candidate matrix. If dependency conflicts arise during resolution, record the exact conflict and test the adjacent version until a coherent top-tier set is reached.

### Phase 1: Environment Provisioning & Import Diagnostics
1. Create the dedicated environment:
   ```bash
   /home/htm/anaconda3/bin/conda create -n snngine-frontier python=<discovered_max> -y
   ```
2. Install the discovered top-tier packages (CUDA toolkit, PyTorch, Numba, VisPy, PySide6).
3. Build PyCUDA with OpenGL interop enabled.
4. Run comprehensive import diagnostics:
   ```python
   import torch, pycuda.driver, pycuda.gl, numba.cuda, vispy, PySide6
   print(f"Python:  {sys.version}")
   print(f"PyTorch: {torch.__version__} (CUDA {torch.version.cuda})")
   print(f"PyCUDA:  {pycuda.VERSION_TEXT}")
   print(f"VisPy:   {vispy.__version__}")
   print(f"Numba:   {numba.__version__}")
   print(f"PySide6: {PySide6.__file__} (v{PySide6.__version__})")
   ```

### Phase 2: Category 1 — Headless EGL Smoke Test
1. Execute `interop_smoke_test_auto.py` inside the frontier environment:
   ```bash
   conda run -n snngine-frontier python setups/gpu-smoke-tests/interop_smoke_test_auto.py --snapshot setups/gpu-smoke-tests/rendered_frame.png
   ```
2. Assert that all 5 links pass with exit code `0`.
3. Verify that the offscreen snapshot `rendered_frame.png` is written and rasterizes markers correctly.

### Phase 3: Category 2 — Desktop GUI Smoke Test
1. Prepare the display safety guard (ensure GNOME Shell tiling assistant will not crash the desktop).
2. Execute `interop_smoke_test_standalone_gui.py`:
   ```bash
   conda run -n snngine-frontier python setups/gpu-smoke-tests/interop_smoke_test_standalone_gui.py
   ```
3. Visually verify the interactive 3D double torus running on the desktop monitor at ~33 FPS.
4. Verify both toggles:
   - Backend: CUDA Kernel vs PyTorch
   - Function: Izhikevich SNN vs Sine Wave

### Phase 4: Category 3 — Web Bridge Smoke Test
1. Launch `interop_smoke_test_web_gui.py` on port 6080:
   ```bash
   conda run -n snngine-frontier python setups/gpu-smoke-tests/interop_smoke_test_web_gui.py --port 6080
   ```
2. Connect via `http://localhost:6080` in a browser.
3. Verify live 800×600 RGBA frame streaming at 29+ FPS.
4. Verify interactive orbit/zoom, simulation pause/step, and live 4-way toggles over WebSocket.

### Phase 5: Containerized Docker Smoke Test (v2 Frontier)

Replicate the verified v2 frontier environment inside an isolated Docker container, ensuring identical 5-link zero-copy interop performance in a containerized environment (crucial for RunPod and cloud deployment).

#### 1. Container Architecture & Base Image
- **Image Name**: `snngine-gpu-smoke:v2`
- **Dockerfile**: [`setups/gpu-smoke-tests/Dockerfile.docker-smoke-v2`](file:///home/htm/snngine/snngineV4_cloud/snngineV4_agent_branches/setups/gpu-smoke-tests/Dockerfile.docker-smoke-v2)
- **Base Image**: `nvidia/cuda:12.6.2-devel-ubuntu24.04` (Ubuntu 24.04 LTS Noble Numbat)
- **Driver Injection**: Configure NVIDIA container runtime capabilities:
  ```dockerfile
  ENV NVIDIA_VISIBLE_DEVICES=all
  ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics,display
  ```
  *(Essential for injecting host NVIDIA EGL and OpenGL hardware acceleration drivers into container userspace).*

#### 2. Container v2 Environment Provisioning (Exact Independent Library Build)
Inside the container build (`Dockerfile.docker-smoke-v2`), build and install the exact verified v2 library versions independently from scratch (clean userspace build; **do not copy or bind-mount the host machine's local Conda directory**):
- **Independent Container Runtime**: Standalone Python 3.14 environment built inside the container.
- **Exact Pinned Library Versions**:
  - `python`: `3.14.7`
  - `cuda-toolkit`: `13.2.0` / `13.2.86`
  - `torch`: `2.15.0.dev20260929+cu132` (nightly cu132 wheel)
  - `pycuda`: `2026.1` (cloned and compiled from source inside Docker with `--cuda-enable-gl`)
  - `numba`: `0.67.0`
  - `vispy`: `0.17.0`
  - `pyside6`: `6.11.2` / `PySide6-Essentials 6.11.2` / `Shiboken6 6.11.2` (replaces PyQt6)
  - `pyopengl`: `3.1.10`
  - `websockets`: `17.1`
  - `scipy`: `1.18.1`
  - `pillow`: `12.3.0`
  - `qtpy`: `2.4.3`
- **Clean Image Artifact**: The Docker image must be fully self-contained, portable, and runnable on any NVIDIA GPU host or cloud instance without depending on the host workstation's local filesystem or conda environment.
- **Permission Hygiene**: Run container processes with mapped host user UID/GID (`--user $(id -u):$(id -g)`) or fix output ownership to prevent root-owned file collisions on mounted directories.

#### 3. Container Verification Across All Three Operational Modes
1. **Mode 1: Automated Headless EGL Smoke Test (Default)**
   - Unattended execution without display or X11 socket mounts.
   - Run `interop_smoke_test_auto.py --snapshot /output/rendered_frame_docker_v2.png`.
   - Assert all 5 zero-copy links pass with byte-for-byte readback fidelity and valid PNG snapshot.
2. **Mode 2: Desktop GUI Smoke Test (`--gui`)**
   - Bind-mount `/tmp/.X11-unix` and forward host `DISPLAY`.
   - Execute under an automated GNOME Shell safety trap (`trap 'gnome-extensions enable tiling-assistant@ubuntu.com' ...`).
   - Run `interop_smoke_test_standalone_gui.py` with `QT_XCB_GL_INTEGRATION=glx`.
3. **Mode 3: Interactive Web Bridge (`--web`)**
   - Expose container port `6080` (`-p 6080:6080`).
   - Run `interop_smoke_test_web_gui.py --port 6080`.
   - Validate live 800×600 RGBA WebSocket streaming at 29+ FPS from the container to a host browser.

#### 4. Automated Host Launcher Script
- **Launcher**: [`setups/gpu-smoke-tests/interop_smoke_test_docker_launcher_v2.sh`](file:///home/htm/snngine/snngineV4_cloud/snngineV4_agent_branches/setups/gpu-smoke-tests/interop_smoke_test_docker_launcher_v2.sh)
- Checks if `snngine-gpu-smoke:v2` exists locally; automatically triggers `docker build` from `Dockerfile.docker-smoke-v2` if missing.
- Dispatches `--headless`, `--gui`, and `--web` modes with correct volume mounts and GPU arguments.

### Phase 6: Reporting & Deliverables
1. Update and compile the findings report at [`setups/gpu-smoke-tests/gpu-smoke-test-report-v2.md`](file:///home/htm/snngine/snngineV4_cloud/snngineV4_agent_branches/setups/gpu-smoke-tests/gpu-smoke-test-report-v2.md) following `setups/report-format.md`.
2. Document:
   - **The Frontiers Tested**: Candidate configurations probed from the absolute bleeding edge downward.
   - **Build & Compatibility Boundaries**: The exact compile, link, or runtime failure reasons encountered when pushing packages beyond working boundaries.
   - **Final Verified Frontier Matrix**: The maximum operational package versions established across all 3 categories (Host & Docker).
   - **Benchmarks**: Frame rates and render latencies across Headless, GUI, Web, and Containerized Docker modes.

---

## Deliverables

All deliverables live inside [`setups/gpu-smoke-tests/`](file:///home/htm/snngine/snngineV4_cloud/snngineV4_agent_branches/setups/gpu-smoke-tests/) following the `v2` naming convention:

- `gpu-smoke-test-task-v2.md` — this task specification (Host & Docker).
- `gpu-smoke-test-report-v2.md` — findings, failure boundaries, and verification report.
- `create_v2_env.sh` — host environment bootstrap helper.
- `Dockerfile.docker-smoke-v2` — container specification for the v2 frontier stack.
- `interop_smoke_test_docker_launcher_v2.sh` — container build & run automation launcher.
- `rendered_frame_docker_v2.png` — containerized offscreen headless snapshot.
