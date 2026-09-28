# Task: containerized GPU/CUDA-OpenGL-interop smoke test (Docker)

## Safety and boundaries (read before running any Docker command)

### 1. Docker isolation and host boundaries
- **Only touch this task's containers and images**: Never inspect, stop, modify, or remove other containers or images on this host (e.g. `docker-agent-sandbox`, `blender-agent`, `web-fetch-*`, etc.). Name all containers and images for this task with a clear task prefix: `snngine-gpu-smoke:*` or `gpu-smoke-docker:*`.
- **No sensitive host mounts**: Never mount the host root `/`, `/home/htm/.ssh`, or host system configuration into a container. Mount only the required workspace directory or specific test scripts as read-only or scoped volumes (e.g. `-v $(pwd):/workspace:ro`).
- **No unconfined or privileged execution without need**: Use standard `--gpus all` with default container security options. Do not add `--privileged` or drop host capabilities unless specifically diagnosed and justified.
- **Rule against unprompted workarounds**: Never create unprompted custom scripts, proxy wrappers, or ad-hoc bridges to work around tool or authentication limitations. If a workaround is necessary, explain why first, propose it, and wait for approval. Helper build and run scripts inside `setups/gpu-smoke-test/` are explicitly permitted.

### 2. Display and desktop safety (verified 2026-09-28)
- **Host GNOME Shell crash risk**: On 2026-09-28, a Mutter assertion failure in the host's `tiling-assistant@ubuntu.com` GNOME Shell extension caused `gnome-shell` to abort (SIGABRT) when a newly mapped X11 window was created during heavy initialization.
- **Headless first (Phase 1)**: Phase 1 runs completely headlessly via EGL. It does NOT touch X11, does NOT mount `/tmp/.X11-unix`, and does NOT set `DISPLAY`. It is completely isolated and safe to run autonomously.
- **Visual check (Phase 2)**: Do NOT bind-mount the host X11 socket (`-v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=:1`) to launch an interactive GUI window on the host desktop without maintainer presence or without disabling `tiling-assistant@ubuntu.com`. Prefer offscreen EGL framebuffer rendering to image files (`.png`) or dedicated container streaming (e.g. VirtualGL/TurboVNC).

### 3. Scope: this host only
Do not touch RunPod, cloud credentials, or any external cloud resource. The goal of this task is to verify that the GPU zero-copy interop chain runs inside a Docker container on this local machine. Once proven locally, deploying to a RunPod pod is a separate follow-up task.

### 4. Working directory and file boundary
- **Working directory**: All paths below are given relative to `snngineV4_agent_branches/`. If your working directory is the parent (`snngineV4_cloud/`), prefix paths with `snngineV4_agent_branches/`.
- **Deliverables directory**: All Dockerfiles, build scripts, run helpers, and reports must live strictly inside `setups/gpu-smoke-test/`.
- **Reference code**: You may read `setups/gpu-smoke-test/` (the host-verified scripts) and `SNNgine3D_agent_branches/notebooks/simulation_demo/sim_demo_utils.py` (read-only sister repo). Do not modify files in those directories.

---

## Where this task fits

1. **Host baseline established (`setups/gpu-smoke-test/`)**:
   - The 5-link zero-copy CUDA-OpenGL interop chain was successfully decoupled from the engine's config/network/parameter-tree stack.
   - `interop_smoke_test_auto.py` runs unattended under headless EGL, asserting on PyCUDA VBO mapping, Numba `DeviceNDArray`, PyTorch `as_tensor` zero-copy pointer identity, live CUDA kernel write-through, and `sim_demo_utils.update_N_state` execution. All 5 links pass with 100% byte-for-byte readback fidelity.
   - `interop_smoke_test_standalone_gui.py` runs live on the host RTX 3090 at ~33 FPS with live spike-to-alpha pulse modulation and PyTorch fallback toggle.
2. **The containerization requirement (`runpod-rationale.md` open item 0)**:
   - RunPod GPU pods run containers using the NVIDIA Container Toolkit (`--gpus all` / `nvidia-container-runtime`).
   - To deploy SNNgine 3D/4 onto RunPod or any containerized cloud GPU infrastructure, the zero-copy CUDA-OpenGL interop stack must function inside a containerized Linux environment where the NVIDIA driver and EGL/OpenGL libraries are injected via the container runtime.

---

## Working autonomously

- **Permissions and tool approvals**: Proactively identify anything in this project's configuration (e.g. `/permissions`, command allowlists, environment variables) that would allow end-to-end execution with fewer approval prompts. Propose exact changes in `gpu-smoke-test-report-docker.md`.
- **Helper scripts permitted**: Helper scripts that automate Docker image building, container execution, or test log extraction (e.g. `build.sh`, `run_auto.sh`) are explicitly permitted inside `setups/gpu-smoke-test/`.

---

## Prior attempt and caveats (reference only, do not restart from here)

In the sister repo (`SNNgine3D`), a prior Docker-based attempt was preserved in `setups/Dockerfile-SNNgine3D-nomachine` and `setups/Dockerfile-SNNgine3D-nomachine-base`.

### What that attempt was
- Based on `nvidia/cudagl:11.4.2-devel-ubuntu20.04`.
- Installed a full XFCE4 desktop session inside the container, plus NoMachine (`nxserver`) as the remote-desktop protocol.
- Installed conda/micromamba, JupyterLab, Bokeh, Plotly, PyCharm Community, Poetry, PyTorch 1.13.1, and PyCUDA v2022.2 built from source with `--cuda-enable-gl`.

### Critical caveats — why it failed and why NOT to reuse it
1. **Outdated OS and toolchains**: Ubuntu 20.04 and CUDA 11.4 are obsolete. The host is Ubuntu 24.04 with NVIDIA driver `595.91.07` (CUDA 13.2 / 12.x driver capability) and an Ampere RTX 3090 (compute capability 8.6). Installing CUDA 11.4 packages causes driver and toolchain mismatches.
2. **Massive unnecessary bloat**: The image bundled hundreds of unrelated packages (Jupyter, PyCharm, XFCE desktop, Poetry). Building it takes tens of gigabytes and hours, introducing numerous failure points unrelated to GPU interop.
3. **GPU rendering failed under NoMachine**: While NoMachine remote-desktop network connectivity worked, hardware-accelerated OpenGL rendering inside the session did not. This is why the Docker approach was abandoned in SNNgine3D.
4. **No targeted smoke test**: The old image only copied PyCUDA's generic test suite, never testing OpenGL VBO registration or PyTorch zero-copy sharing.
5. **The single useful reference**: The PyCUDA build step in that Dockerfile illustrates how PyCUDA must be configured to link against CUDA OpenGL headers:
   ```bash
   python ./configure.py --cuda-root=/usr/local/cuda --cuda-enable-gl
   make install
   ```

---

## The interop chain to exercise

The container must execute and validate the 5-link zero-copy chain (see `agents/common.md` and `agents/glossary.md`):
1. **Link 1 (Hand-written CUDA simulation code)**: Compiles and executes a CUDA kernel (e.g. `sim_demo_utils.update_N_state_kernel` or an inline test kernel via `pycuda.compiler.SourceModule`).
2. **Link 2 (PyCUDA OpenGL interop)**: Retains and binds the CUDA Primary Context (`dev.retain_primary_context()`) shared seamlessly with PyTorch.
3. **Link 3 (OpenGL buffer ↔ PyCUDA)**: An OpenGL Vertex Buffer Object (VBO) is registered with `pycuda.gl.RegisteredBuffer` and mapped to a device pointer.
4. **Link 4 (Numba device array)**: Mapped device pointer is wrapped into a `numba.cuda.cudadrv.devicearray.DeviceNDArray` via an `ExternalMemory` adapter (`__cuda_memory__ = True`).
5. **Link 5 (PyTorch tensor view)**: `torch.as_tensor(numba_arr, device='cuda')` creates a PyTorch tensor sharing the exact same VRAM pointer (`tensor.data_ptr() == mapped_ptr`).
6. **Live write-through**: Values written by PyTorch or CUDA kernels must be immediately visible in the OpenGL buffer on readback (`glGetBufferSubData`) with zero CPU copy.

---

## Environment on this host

- **Operating System**: Ubuntu 24.04 LTS (x86_64).
- **GPU**: NVIDIA GeForce RTX 3090 (24 GB VRAM, Compute Capability 8.6).
- **NVIDIA Driver**: `595.91.07` (Driver CUDA capability: 13.2).
- **Docker Engine**: Version `29.8.1`, Docker Compose `v5.5.1`.
- **NVIDIA Container Runtime**: Configured and functional. Verified:
  ```bash
  docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
  ```
  successfully enumerates the RTX 3090 with full GPU memory.
- **Reference host conda env**: `/home/htm/anaconda3/envs/snngine` (Python 3.12, PyTorch 2.8.0+cu129, CUDA Toolkit 12.0).

---

## Goal — two phases, work through both autonomously

### Phase 1: Automated Headless EGL in Docker (Priority 1 — Top Pick)
Build a minimal, modern container and run the automated headless test inside it.

1. **Construct a lightweight `Dockerfile`** in `setups/gpu-smoke-test/` (e.g. `Dockerfile.docker-smoke` or `Dockerfile`):
   - Use a modern CUDA development base image, e.g. `nvidia/cuda:12.4.1-devel-ubuntu22.04` (or `nvidia/cuda:12.6.x-devel-ubuntu24.04`), with OpenGL/EGL support:
     ```dockerfile
     ENV NVIDIA_DRIVER_CAPABILITIES compute,utility,graphics,display
     ```
   - Install required system libraries: Python (3.11 or 3.12), `libegl1`, `libgles2`, `libgl1-mesa-dev`, `libegl1-mesa-dev`, build essentials, git.
   - Install Python dependencies: PyTorch with CUDA matching the image (e.g. `pip install torch --index-url https://download.pytorch.org/whl/cu124`), Numba, NumPy, PyOpenGL.
   - Build PyCUDA from source with OpenGL interop enabled (`--cuda-enable-gl`).
2. **Execute `interop_smoke_test_auto.py` inside the container**:
   - Run the container with GPU passthrough:
     ```bash
     docker run --rm --gpus all \
       -v /home/htm/snngine/snngineV4_cloud/snngineV4_agent_branches/setups/gpu-smoke-test/interop_smoke_test_auto.py:/app/interop_smoke_test_auto.py:ro \
       -v /home/htm/snngine/snngineV4_cloud/SNNgine3D_agent_branches:/app/SNNgine3D_agent_branches:ro \
       -e PYTHONPATH=/app:/app/SNNgine3D_agent_branches/notebooks/simulation_demo \
       snngine-gpu-smoke:headless python /app/interop_smoke_test_auto.py
     ```
3. **Verify automated assertions**:
   - EGL context initializes against the containerized NVIDIA driver.
   - PyCUDA binds primary context.
   - VBO maps to device pointer.
   - Pointer identity: `tensor.data_ptr() == mapped_ptr`.
   - Test A: Direct PyTorch write-through passes with exact byte-for-byte readback.
   - Tests B & C: CUDA kernel write-through and PyTorch live VRAM consistency pass.
   - Test D: Sister repo `update_N_state` executes cleanly.
4. **Document Phase 1**: Write results and build logs into `gpu-smoke-test-report-docker.md`.

---

### Phase 2: Visual Confirmation from Docker (Priority 2)
Once headless EGL passes, explore visual confirmation. Do not try to resurrect monolithic NoMachine desktop sessions. Instead, evaluate the options ranked below:

1. **Option A: Offscreen EGL Render to Image File (Recommended)**:
   - Add a test mode that initializes an EGL framebuffer, renders several frames of the VisPy marker visual, reads the framebuffer pixels (`glReadPixels`), and saves an image (`rendered_frame.png`) to an output directory mounted from the host.
   - The maintainer can inspect the image on the host to visually confirm 3D marker geometry and alpha modulation without running an X server or remote desktop.
2. **Option B: VirtualGL + TurboVNC (Optional interactive path)**:
   - If interactive live viewing inside the container is required, use VirtualGL + TurboVNC (lightweight, purpose-built for 3D OpenGL streaming), rather than a full heavyweight desktop.
3. **Option C: Guarded X11 Socket Passthrough**:
   - Pass the host X11 socket (`-v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=:1`) only with the extension safety guard (`gnome-extensions disable tiling-assistant@ubuntu.com`) active on the host and with maintainer confirmation.

---

## Deliverables (all in this same `setups/gpu-smoke-test/` directory)

- `gpu-smoke-test-task-docker.md` — this task write-up.
- `Dockerfile.docker-smoke` — minimal, reproducible Dockerfile for containerized interop testing.
- `interop_smoke_test_docker_launcher.sh` — host launcher script following the repo's naming pattern; inspects if the Docker image exists, builds it automatically from `Dockerfile.docker-smoke` if missing, mounts volumes, configures `--gpus all`, and executes the test inside the container.
- `gpu-smoke-test-report-docker.md` — a comprehensive report following `setups/report-format.md`, documenting build steps, image sizes, test execution outputs, hiccups hit, and resolutions.

---

## Reporting format

Each phase's entry in `gpu-smoke-test-report-docker.md` follows `setups/report-format.md`'s shared convention:
- **Summary at the top**: What was done, outcome (worked / worked with caveats / didn't work).
- **Subsections below**: What was built (base image, dependencies, Dockerfile), how to build and run, hiccups hit along the way and how they were resolved, and next steps for cloud/RunPod deployment.
