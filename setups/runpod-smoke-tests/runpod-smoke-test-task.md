# Task: RunPod GPU Cloud Deployment & Zero-Copy Interop Smoke Test

## Context and where this task fits

We have established and verified the 5-link zero-copy CUDA-OpenGL interop pipeline and native EGL web bridge locally under [`setups/gpu-smoke-tests/`](file:///home/htm/snngine/snngineV4_cloud/snngineV4_agent_branches/setups/gpu-smoke-tests/):
- **Phase 1 (Headless EGL)**: Automated unattended assertions passing 100% on containerized Ubuntu 24.04 (CUDA 12.6.2, Python 3.12).
- **Phase 2 (Visual Confirmation)**: Offscreen framebuffer snapshot (`rendered_frame.png`) rendered via pure EGL and saved without display dependencies.
- **Phase 3 (Guarded Local GUI)**: Live VisPy + PyQt interactive desktop GUI running with GNOME Shell crash guards.
- **Phase 4 (EGL Web Bridge)**: Browser-based interactive native EGL rendering over an embedded WebSocket server (port 6080), verified with full camera orbit/zoom and live zero-copy VRAM mutations.

This task extends that verification to **remote cloud infrastructure on RunPod**, addressing Open Item 0 of [`setups/runpod-rationale.md`](file:///home/htm/snngine/snngineV4_cloud/snngineV4_agent_branches/setups/runpod-rationale.md). The objective is to verify that the zero-copy interop pipeline and browser-based web bridge execute on remote cloud hardware with zero physical display, zero X11/Xvfb overhead, and seamless remote browser interaction.

---

## Safety, boundaries, and financial discipline

### 1. Financial discipline & ephemeral GPU pod lifecycle
- **Manual launch & prompt termination**: GPU pods incur hourly billing. The GPU pod for this smoke test must be spun up only on explicit maintainer approval and terminated immediately once test phases and visual inspection are complete.
- **Persistent storage preservation**: The persistent network volume (`qze81dpw7q`, 20GB Standard) in `EU-RO-1` must remain preserved. Do not delete or recreate the network volume.

### 2. Region and hardware constraints
- **Region pinning (`EU-RO-1`)**: Network volume `qze81dpw7q` is physically pinned to data center `EU-RO-1`. Any pod provisioned for this task must be created in `EU-RO-1` so the volume can mount.
- **Target GPU**: NVIDIA RTX 2000 Ada (16GB VRAM, Compute Capability 8.9) or current active stock in `EU-RO-1` (e.g. RTX 4000 Ada, RTX A4500). Verify live stock prior to provisioning.

### 3. Credential hygiene
- **No RunPod API keys inside the pod**: RunPod API credentials stay exclusively at the host orchestration layer (CLI/MCP). Never pass, store, or echo RunPod API keys into the pod environment or disk.

### 4. Working directory and file boundaries
- **Local working directory**: `snngineV4_agent_branches/` (or relative from repo root).
- **Deliverables directory**: All task specifications, execution logs, and reports for this cloud deployment must live strictly in `setups/runpod-smoke-tests/`.
- **Reference scripts**: Reuse the verified test scripts from [`setups/gpu-smoke-tests/`](file:///home/htm/snngine/snngineV4_cloud/snngineV4_agent_branches/setups/gpu-smoke-tests/):
  - `interop_smoke_test_auto.py`
  - `interop_smoke_test_web_gui.py`
- **Helper scripts permitted**: Helper scripts that automate pod setup, execution, and test verification are explicitly permitted in `setups/runpod-smoke-tests/` to eliminate repetitive boilerplate and conserve context tokens across commands (see "Helper scripts are permitted" below).

---

## Helper scripts are permitted

Write task-local helper scripts freely inside `setups/runpod-smoke-tests/` to reduce manual boilerplate, consolidate multi-step shell commands, and conserve context tokens across interactions. Naming convention: `runpod_smoke_test_<descriptor>.sh`.

Anticipated helper scripts:
- `runpod_smoke_test_runner.sh`: Pod-side runner that verifies the runtime environment (`PYTHONPATH`, CUDA, EGL, VisPy), executes automated headless interop assertions (`interop_smoke_test_auto.py`), checks offscreen snapshot generation, or launches the interactive EGL web bridge (`interop_smoke_test_web_gui.py --web`).
- Provisioning or connection helpers if needed to consolidate RunPod CLI commands, SSH checks, and clean teardown.


## Human verification protocol (Mandatory handshake)

Automated assertion passes alone do not complete an interactive milestone:
1. Automated provisioning, setup commands, and headless assertions will execute first.
2. Before declaring the task complete or initiating pod termination, the agent must present the live RunPod HTTP proxy URL (`https://<pod-id>-6080.proxy.runpod.net`) and request that the maintainer open it in a local browser.
3. The maintainer must visually inspect the 3D rotating simulation, orbit/zoom controls, and VRAM fallback toggle.
4. Only upon maintainer confirmation will teardown and final reporting proceed.

---

## Phased execution plan

### Phase 1: Ephemeral pod provisioning & environment bootstrap
1. **Catalog & stock verification**:
   - Check available GPU stock in `EU-RO-1` for RTX 2000 Ada (or fallback Ampere/Ada GPU).
2. **Pod creation**:
   - Region: `EU-RO-1`.
   - Volume: `qze81dpw7q` mounted at `/workspace`.
   - Exposed ports: `22` (SSH) and `6080` (HTTP/WebSocket Web Bridge).
   - Base image: RunPod official PyTorch/CUDA template or lightweight container environment with NVIDIA driver passthrough.
3. **Environment validation via SSH**:
   - Verify SSH connectivity.
   - Run `nvidia-smi` on the pod: confirm GPU identity, driver capability, and VRAM.
   - Confirm `/workspace` is mounted read-write.

---

### Phase 2: Remote headless EGL smoke test (5-link zero-copy interop)
1. **Dependency check & test execution**:
   - Run headless test via the task runner:
     ```bash
     bash /workspace/snngineV4_cloud/snngineV4_agent_branches/setups/runpod-smoke-tests/runpod_smoke_test_runner.sh --headless
     ```
2. **Verify 5-link assertion chain**:
   - **Link 1**: CUDA simulation code (`update_N_state_kernel` or inline kernel via PyCUDA `SourceModule`).
   - **Link 2**: PyCUDA binds primary CUDA context (`dev.retain_primary_context()`) shared with PyTorch.
   - **Link 3**: VisPy OpenGL VBO registered and mapped via `pycuda.gl.RegisteredBuffer`.
   - **Link 4**: Device pointer wrapped into Numba `DeviceNDArray`.
   - **Link 5**: PyTorch tensor view created via `torch.as_tensor(numba_arr, device='cuda')` sharing exact pointer (`tensor.data_ptr() == mapped_ptr`).
   - **Readback fidelity**: Confirm byte-for-byte readback after PyTorch and CUDA kernel writes.
3. **Offscreen snapshot confirmation**:
   - Confirm offscreen snapshot `rendered_frame.png` is written to disk via EGL framebuffer readback.

---

### Phase 3: Remote interactive web bridge & visual handshake (Port 6080)
1. **Launch cloud web bridge**:
   - Start the native EGL web server via the task runner:
     ```bash
     bash /workspace/snngineV4_cloud/snngineV4_agent_branches/setups/runpod-smoke-tests/runpod_smoke_test_runner.sh --web
     ```
   - Server binds embedded HTTP/WebSocket service to `0.0.0.0:6080`.
2. **Connect via RunPod public proxy**:
   - Retrieve public proxy endpoint: `https://<pod-id>-6080.proxy.runpod.net`.
   - Verify WebSocket handshake over secure WSS proxy connection.
3. **Visual inspection handshake**:
   - Maintainer tests interaction in local browser:
     - 64 3D markers rotating in a double torus driven by CUDA kernel updates.
     - Live pulse animation on firing neurons.
     - Interactive camera orbiting and zooming via mouse/trackpad.
     - Interactive simulation pause, single-stepping, and toggle to PyTorch fallback.

---

### Phase 4: Clean teardown, cost accounting & reporting
1. **Pod termination**:
   - Terminate the ephemeral GPU pod immediately upon maintainer sign-off to halt hourly billing.
   - Verify volume `qze81dpw7q` remains intact in `EU-RO-1`.
2. **Compile final report**:
   - Document all steps, timings, cloud latency observations, hiccups, and total compute cost in `runpod-smoke-test-report.md`.

---

## Deliverables (in `setups/runpod-smoke-tests/`)

- `runpod-smoke-test-task.md` — this task specification.
- `runpod_smoke_test_runner.sh` — pod-side runner for environment validation, headless test execution, offscreen snapshot check, and web bridge startup.
- `runpod-smoke-test-report.md` — execution report following `setups/report-format.md`.

---

## Reporting format

`runpod-smoke-test-report.md` follows the conventions in `setups/report-format.md`:
- **Summary at the top**: Outcome (worked / worked with caveats / didn't work), GPU hardware used, total run time, total cost.
- **Subsections below**: Pod environment details, test execution steps, hiccups hit and their resolutions, and performance comparison against the local RTX 3090 baseline.
