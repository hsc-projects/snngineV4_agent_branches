# RunPod GPU Cloud Deployment & Zero-Copy Interop Smoke Test Report

## Summary
- **Outcome**: **Worked** (100% of headless assertions passed, zero-copy pointer identity verified, live EGL web bridge streamed successfully from cloud GPU and visually verified by maintainer).
- **Hardware Used**: NVIDIA RTX PRO 4500 Blackwell (32 GB VRAM, Compute Capability 12.0, Driver 595.91.07, CUDA 13.2 / PyTorch 2.8.0+cu128).
- **Cloud Infrastructure**: RunPod Secure Cloud in `EU-RO-1` with 20GB persistent network volume `qze81dpw7q` attached at `/workspace`.
- **Total Pod Runtime**: 21 minutes 11 seconds (from `2026-09-29T10:53:29Z` to `2026-09-29T11:14:40Z`).
- **Total Compute Cost**: **$0.25** (25 cents billed at $0.72/hr).
- **Storage Cost**: Network volume preserved in `EU-RO-1` at standard storage rates ($0.07/GB/mo, ~$1.40/mo).

---

## Phase 1: Ephemeral Pod Provisioning & Environment Bootstrap

### Summary
The ephemeral GPU pod was provisioned via the official hosted RunPod MCP server (`https://mcp.getrunpod.io/`) using OAuth credentials. Hardware environment diagnostics, CUDA toolchains, EGL drivers, and persistent network volume attachments were verified over direct SSH (`port 26895`).

### Provisioning Details
- **Pod ID**: `5t484plqc5teyh`
- **Data Center**: `EU-RO-1` (Bucharest, Romania)
- **Cloud Tier**: `SECURE` (enforced by network volume requirements)
- **Image**: `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404` (Ubuntu 24.04 LTS, Python 3.12.3, CUDA 12.8 runtime)
- **Ports Exposed**: `22/tcp` (Direct SSH on public port 26895), `6080/http` (Web Bridge)
- **Storage Mount**: Network volume `qze81dpw7q` mounted read-write at `/workspace` (`mfs#euro-3.runpod.net:9421`)
- **GPU Detected**:
  ```text
  NVIDIA RTX PRO 4500 Blackwell, 595.91.07, 32623 MiB, Compute Capability 12.0
  ```

### Build & Package Bootstrap
1. **Mesa & EGL Development Headers**:
   ```bash
   apt-get update && apt-get install -y --no-install-recommends \
       libgl1-mesa-dev libegl1-mesa-dev libgles2-mesa-dev libglvnd-dev
   ```
2. **Scientific Python Dependencies**:
   Installed `numpy<2` (1.26.4), `numba` (0.67.0), `PyOpenGL` (3.1.10), `PyOpenGL_accelerate` (3.1.10), `vispy` (0.17.0), `websockets` (17.1), `pytools`, `appdirs`, `mako`.
3. **PyCUDA with Native OpenGL Interop**:
   Standard pip wheels for PyCUDA lack OpenGL interop (`pycuda.gl`). Compiled and installed PyCUDA v2024.1 from source against host CUDA 12.8 with `--cuda-enable-gl`:
   ```bash
   git clone --recurse-submodules -b v2024.1 https://github.com/inducer/pycuda.git /tmp/pycuda
   cd /tmp/pycuda
   python3 ./configure.py --cuda-root=/usr/local/cuda --cuda-enable-gl
   pip install --break-system-packages --no-cache-dir --no-build-isolation .
   ```

---

## Phase 2: Remote Headless EGL Smoke Test (5-Link Zero-Copy Interop)

### Summary
The automated headless test suite (`interop_smoke_test_auto.py`) executed via the pod-side runner (`runpod_smoke_test_runner.sh --headless`). All 5 links of the zero-copy pipeline passed without error, and an offscreen 256×256 EGL snapshot was written to disk.

### Test Execution Output
```text
======================================================================
SNNgineV4 - Phase 2: Automated Headless Interop Smoke Test
======================================================================

[Step 1/7] Initializing headless EGL OpenGL context...
  - EGL Renderer:  NVIDIA RTX PRO 4500 Blackwell/PCIe/SSE2
  - EGL Vendor:    NVIDIA Corporation
  - GL Version:    4.6.0 NVIDIA 595.91.07

[Step 2/7] Initializing PyCUDA & PyTorch CUDA contexts...
  - CUDA Device:   NVIDIA RTX PRO 4500 Blackwell (Compute Capability 12.0)
  - PyTorch CUDA:  v12.8, is_available=True

[Step 3/7] Creating OpenGL Vertex Buffer Object (VBO)...
  - VBO ID:        1
  - Buffer Layout: 32 elements x 14 floats (1792 bytes)

[Step 4/7] Registering VBO with PyCUDA OpenGL interop...
  - Mapped Ptr:    0x7b392827f800
  - Mapped Size:   1792 bytes (expected 1792)

[Step 5/7] Wrapping mapped pointer via Numba into PyTorch tensor...
  - Numba Array:   shape=(32, 14), dtype=float32
  - PyTorch View:  shape=torch.Size([32, 14]), device=cuda:0
  - Tensor Ptr:    0x7b392827f800
  ✓ Zero-copy pointer identity verified: PyTorch shares exact VRAM address.

[Step 6/7] Test A: PyTorch tensor direct write-through assertion...
  ✓ Direct PyTorch write-through confirmed: OpenGL readback matches byte-for-byte.

[Step 7/7] Test B & C: CUDA kernel execution and PyTorch view consistency...
  ✓ PyTorch view consistency confirmed: sees CUDA kernel writes live in VRAM.
  ✓ CUDA kernel write-through confirmed: OpenGL readback matches byte-for-byte.

[Step 7B/7] Test D: Sister repo self-compiled CUDA simulation code (update_N_state)...
  ✓ Sister repo self-compiled simulation kernel (update_N_state) executed and verified.

[Visual Check] Rendering offscreen frame to: rendered_frame.png
  ✓ Offscreen frame rendered and saved (256x256 PNG).

======================================================================
ALL INTEROP ASSERTIONS PASSED (5/5 LINKS VERIFIED ZERO-COPY)
======================================================================
```

### Verification Findings
- **Zero-Copy Identity**: The PyCUDA mapped buffer pointer `0x7b392827f800` matched the PyTorch tensor `data_ptr()` exactly.
- **Offscreen Snapshot**: Readback from the EGL framebuffer confirmed proper rasterization of the circular neuron arrangement without X11 or display server overhead. Snapshot was retrieved and verified at [`setups/runpod-smoke-tests/rendered_frame.png`](file:///home/htm/snngine/snngineV4_cloud/snngineV4_agent_branches/setups/runpod-smoke-tests/rendered_frame.png).

---

## Phase 3: Remote Interactive Web Bridge & Visual Handshake (Port 6080)

### Summary
The native EGL web bridge (`interop_smoke_test_web_gui.py`) was started on the Blackwell pod on port `6080`. The maintainer connected via the RunPod public proxy (`https://5t484plqc5teyh-6080.proxy.runpod.net`), performed camera navigation, tested simulation pausing and kernel toggles, and compared the cloud stream against the local RTX 3090 container running in parallel on `http://localhost:6080`.

### Handshake & Observations
1. **Interactive Functionality**:
   - WebSocket bi-directional communication established successfully across Cloudflare WSS proxy.
   - Mouse click-and-drag camera orbit, wheel zoom, pause/resume, and PyTorch fallback toggle responded correctly.
2. **Visual Fidelity ("Falling Snow" Observation)**:
   - The maintainer observed that some markers appeared scattered/oscillating ("like falling snow").
   - Running the local container (`snngine-gpu-smoke:headless` on local RTX 3090) in parallel confirmed that the behavior was **identical between local and cloud**.
   - **Root Cause**: In Mode A (`update_N_state`), individual neuron membrane potentials $v$ modulate each neuron's minor radius:
     ```python
     r_mod = 3.5 + 1.5 * ((v + 65.0) / 95.0)
     ```
     As individual neurons fire and reset, their individual radii expand and contract along the toroidal trajectory. Switching to **PyTorch Fallback** mode produced the expected smooth geometric ring in both environments.
3. **Bandwidth & Stuttering Analysis**:
   - The web bridge streams raw uncompressed 800×600 RGBA frame buffers (`1.92 MB` per frame).
   - At 30 FPS, this requires **~57.6 MB/s (460 Mbps)** of sustained uplink from Romania (`EU-RO-1`) through Cloudflare to the client browser.
   - On local loopback (`http://localhost:6080`), bandwidth is effectively unlimited, resulting in smooth 29+ FPS. Over the public WAN proxy, the 460 Mbps raw stream caused TCP window buffering, packet jitter, and visual stutter.
   - **Recommendation for Production Cloud Web Streaming**: Implement JPEG / WebP / H.264 compression on the server side prior to WebSocket transmission to reduce frame payload from 1.92 MB to ~40–80 KB (~1.5–2.5 MB/s total bandwidth).

---

## Phase 4: Clean Teardown & Cost Accounting

### Summary
Upon maintainer confirmation and sign-off, the ephemeral GPU pod was immediately destroyed using the RunPod MCP control plane. Account resources were verified to guarantee zero ongoing compute charges.

### Accounting Summary
| Resource | ID | Region | Status | Billed Rate | Duration | Total Billed |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GPU Pod** | `5t484plqc5teyh` | `EU-RO-1` | **TERMINATED** | $0.72/hr | 21 min 11 sec | **$0.25** |
| **Network Volume** | `qze81dpw7q` | `EU-RO-1` | **ACTIVE** | $0.07/GB/mo | Standing (20 GB) | ~$1.40/month |
| **Account Active Pods**| — | — | **0 Running** | $0.00/hr | — | **$0.00** |

---

## Hiccups Hit & Resolutions

1. **Secure Cloud vs. Community Cloud Constraint**:
   - *Problem*: Community Cloud GPUs are cheaper ($0.12–$0.34/hr), but network volume `qze81dpw7q` could not be attached to Community Cloud.
   - *Resolution*: Verified RunPod constraint that network volumes are strictly limited to Secure Cloud. Confirmed with user and deployed to Secure Cloud.
2. **Fast-Moving Stock in `EU-RO-1`**:
   - *Problem*: Lower-tier GPUs (RTX 2000 Ada @ $0.24/hr and L4 @ $0.49/hr) showed low stock and were claimed before allocation could complete.
   - *Resolution*: Queried live catalog availability scoped to Romania (`countryCodes: ['RO']`), identified the available NVIDIA RTX PRO 4500 Blackwell ($0.72/hr) and RTX 4090 ($0.74/hr), presented the choice to the maintainer, and proceeded with Option 1 upon approval.
3. **Network Volume `rsync` Permissions**:
   - *Problem*: Standard `rsync -avz` failed with `Operation not permitted (1)` when attempting `chown` on files transferred into `/workspace`.
   - *Resolution*: Network mounts (MFS/NFS) do not permit arbitrary UID/GID reassignment by clients. Omitted owner/group preservation flags when syncing files.
4. **PyCUDA OpenGL Interop Support**:
   - *Problem*: PyPI binary wheels for PyCUDA do not build against OpenGL headers and lack `pycuda.gl`.
   - *Resolution*: Installed `libgl1-mesa-dev` / `libegl1-mesa-dev` via apt, and compiled PyCUDA v2024.1 from source specifying `--cuda-root=/usr/local/cuda` and `--cuda-enable-gl`.
5. **Runtime NVCC Availability**:
   - *Problem*: PyCUDA's `SourceModule` JIT compiles CUDA kernels at runtime by invoking `nvcc`, which was not in default container `PATH`.
   - *Resolution*: Explicitly prepended `/usr/local/cuda/bin` to `PATH` in `runpod_smoke_test_runner.sh`.
