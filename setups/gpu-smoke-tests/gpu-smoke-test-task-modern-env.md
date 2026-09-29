# Task: Modernized GPU/CUDA-OpenGL-Interop Smoke Test (Max Frontier Discovery)

## Objective & Scope

Push the Python, CUDA, PyTorch, and OpenGL zero-copy interop stack to the **absolute maximum possible versions** for the workstation's **NVIDIA GeForce RTX 3090** (Ampere `sm_86`).

There are **NO upper limits**, no version ceilings, and no pre-emptive caps. Go as high as possible across the entire stack—including Python 3.14+, CUDA 13+, bleeding-edge PyTorch, PyCUDA, Numba, VisPy, and PyQt6.

Once the maximum operational environment is provisioned in an isolated Conda environment, validate the complete 5-link zero-copy interop pipeline across **all three operational categories**:

1. **Category 1: Headless (EGL)** — Unattended automated assertions and offscreen EGL snapshot readback without a display server.
2. **Category 2: Desktop GUI** — Native desktop windowing using PyQt6 + VisPy with hardware acceleration.
3. **Category 3: Web Bridge** — Headless EGL offscreen rendering with real-time WebSocket frame streaming and browser-based 3D interaction.

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

6. **VisPy & PyQt6**:
   - Install the latest VisPy and PyQt6 packages.
   - Verify that VisPy initializes with both `vispy.use('egl')` (headless) and `vispy.use('pyqt6')` (desktop).

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
2. Install the discovered top-tier packages (CUDA toolkit, PyTorch, Numba, VisPy, PyQt6).
3. Build PyCUDA with OpenGL interop enabled.
4. Run comprehensive import diagnostics:
   ```python
   import torch, pycuda.driver, pycuda.gl, numba.cuda, vispy, PyQt6
   print(f"Python:  {sys.version}")
   print(f"PyTorch: {torch.__version__} (CUDA {torch.version.cuda})")
   print(f"PyCUDA:  {pycuda.VERSION_TEXT}")
   print(f"VisPy:   {vispy.__version__}")
   print(f"Numba:   {numba.__version__}")
   print(f"PyQt6:   {PyQt6.__file__}")
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

### Phase 5: Reporting & Deliverables
1. Compile the findings report at `setups/gpu-smoke-tests/gpu-smoke-test-report-modern-env.md` following `setups/report-format.md`.
2. Document:
   - **The Frontiers Tested**: Candidate configurations probed from the absolute bleeding edge downward.
   - **Build & Compatibility Boundaries**: The exact compile, link, or runtime failure reasons encountered when pushing packages beyond working boundaries.
   - **Final Verified Frontier Matrix**: The maximum operational package versions established across all 3 categories.
   - **Benchmarks**: Frame rates and render latencies across Headless, GUI, and Web modes.

---

## Deliverables

All deliverables live inside [`setups/gpu-smoke-tests/`](file:///home/htm/snngine/snngineV4_cloud/snngineV4_agent_branches/setups/gpu-smoke-tests/):

- `gpu-smoke-test-task-modern-env.md` — this task specification.
- `gpu-smoke-test-report-modern-env.md` — findings, failure boundaries, and verification report (created upon execution).
- Optional helper scripts: `create_modern_env.sh` (environment bootstrap helper if needed).
