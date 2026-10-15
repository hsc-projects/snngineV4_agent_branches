# Task: Runpod Headless Engine Simulation Video Generation and Download

## Context and where this task fits

In [`runpod-engine-smoke-test-report.md`](file:///E:/dev/snngineV4_agent_branches/setups/runpod-engine-smoke-test/runpod-engine-smoke-test-report.md), we validated the core headless simulation pipeline of `snngine_v4` on a Runpod GPU instance (NVIDIA RTX 4090, CUDA 12.8), verifying C++/CUDA backend numerical stability, zero-copy buffer layouts, and C-contiguous memory handling across 100 ODE simulation steps without a physical display or GUI loop.

This task advances from pure numerical assertions to **visual simulation recording and automated artifact delivery**. The objective is to:
1. Run a multi-step neural simulation on a remote cloud GPU in Runpod.
2. Render 3D neural activity and membrane dynamics headlessly via hardware-accelerated offscreen EGL OpenGL.
3. Encode the rendered frames into a high-definition H.264 video.
4. Automatically transfer the generated video artifact to the local `setups/runpod-engine-smoke-test/output/` directory on the host machine.
5. Immediately terminate the GPU pod to eliminate idle spend.

---

## Safety, Boundaries, and Financial Discipline

### 1. Financial discipline & ephemeral GPU pod lifecycle
- **Explicit launch & prompt teardown**: GPU pods bill continuously per second. Pods provisioned for this task must be terminated immediately upon successful generation and download of the video artifact.
- **Network volume preservation**: The persistent network volume (`qze81dpw7q`, 20GB Standard) in `EU-RO-1` must remain preserved. Never delete, reformat, or recreate the volume.

### 2. Zone pinning and flexible GPU selection
- **Zone pinned to `EU-RO-1`**: Pods must be provisioned in data center `EU-RO-1` so they can attach network volume `qze81dpw7q` at `/workspace`, retaining pre-compiled C++/CUDA backend binaries and dependencies.
- **Cloud tier**: Must be `SECURE` (enforced by Runpod API; `COMMUNITY` cloud does not support network volume attachment).
- **Flexible GPU selection**: Do not restrict to a single GPU model. At launch time, query live capacity within `EU-RO-1` via `get-capacity` / `list-gpu-types` and select whichever modern NVIDIA GPU with $\ge 16\text{GB}$ VRAM (e.g. RTX 4090, RTX 2000 Ada, RTX 4000 Ada, RTX A4500, RTX A5000) currently has available stock at the lowest hourly rate.

### 3. Credential hygiene
- **No Runpod API keys inside the pod**: Runpod API credentials stay exclusively on the host orchestration layer (CLI/MCP). Never pass, store, or log Runpod API keys into the pod environment or disk.
- **SSH Private Key Location**: The private SSH key for pod authentication is located at `setups/.secrets/id_ed25519`. The matching public key is pre-registered on the Runpod account.

### 4. Working directory and file boundaries
- **Local working directory**: `E:\dev\snngineV4_agent_branches` (repository root).
- **Task deliverables directory**: All scripts, task specifications, and reports live strictly in `setups/runpod-engine-smoke-test/`.
- **Artifact download location**: Video artifacts must be downloaded to `setups/runpod-engine-smoke-test/output/`.

---

## Exact Provisioning Parameters

When creating the GPU pod via the Runpod MCP tool `create-pod`, use the following parameters:

| Parameter | Value | Rationale |
| :--- | :--- | :--- |
| `cloudType` | `"SECURE"` | Required for network volume attachment |
| `dataCenterId` | `"EU-RO-1"` | Pinned location of persistent volume `qze81dpw7q` |
| `networkVolumeId` | `"qze81dpw7q"` | Preserves workspace, build cache, and Python packages |
| `volumeMountPath` | `"/workspace"` | Standard workspace root |
| `imageName` | `"runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404"` | Verified stack: Ubuntu 24.04, Python 3.12, CUDA 12.8, PyTorch 2.8.0 |
| `ports` | `"22/tcp"` | Enables direct SSH and SCP transport |
| `gpuTypeId` | Dynamic lowest-cost | Checked via `get-capacity` in `EU-RO-1` ($\ge 16\text{GB}$ VRAM) |
| `containerDiskInGb` | `20` | Sufficient root disk for container layers |
| `volumeInGb` | `0` | Set to 0 because network volume `qze81dpw7q` is attached |

---

## Artifact Naming and Collision Resolution

To prevent overwriting previous simulation runs, video artifacts follow a deterministic, timestamped naming scheme with automatic duplicate collision handling:

1. **Standard Filename Format**:
   ```text
   simulation_YYYY-MM-DD_HH-MM-SS.mp4
   ```
   Example: `simulation_2026-10-15_19-35-00.mp4`

2. **Sub-Second Duplicate Resolution**:
   If a file with the target timestamp already exists in `output/` (e.g. generated within the same second), append a sequential index:
   ```text
   simulation_YYYY-MM-DD_HH-MM-SS (1).mp4
   simulation_YYYY-MM-DD_HH-MM-SS (2).mp4
   ```

3. **Git Hygiene**:
   `setups/runpod-engine-smoke-test/output/.gitignore` must ignore all large binary media files (`*.mp4`, `*.avi`, `*.webm`, `*.mov`) so that video outputs remain strictly local artifacts and do not bloat git repository history.

---

## Video Rendering & Headless EGL Pipeline

1. **Simulation Domain & Dynamic States**:
   - Double-Tree construction via `NetworkBuilder` instantiating `SpatialNetworkConfig` and `NetworkReservoir`.
   - Simulation loop running $T$ timesteps (default: 300 steps, $\Delta t = 1.0\text{ ms}$).
   - Extracts dynamic state at each frame:
     - 3D spatial neuron coordinates $\mathbf{x}_i \in \mathbb{R}^3$.
     - Membrane potential values $v_i(t) \in [-75, 30] \text{ mV}$.
     - Binary spike events $f_i(t) \in \{0, 1\}$.

2. **Offscreen EGL Rendering (`EngineSceneCanvas`)**:
   - Hardware-accelerated OpenGL rendering via VisPy [`EngineSceneCanvas`](file:///E:/dev/snngineV4_agent_branches/snngine_v4/visualization/scenes/main_network_scene.py#L8) using the EGL backend (`PYOPENGL_PLATFORM=egl`, `QT_QPA_PLATFORM=offscreen`).
   - Visual nodes:
     - 3D reservoir neuron scatter bodies with color mapped continuously to $v_i(t)$ (resting/hyperpolarized: deep blue; threshold: yellow/cyan; spiking: bright white).
     - 3D bounding box / grid boundaries.
     - Smooth turntable camera orbit rotating continuously around the 3D reservoir center to provide spatial depth.
   - Resolution: $1280 \times 720$ (720p) at 30 fps.

3. **Video Encoding**:
   - Frames captured directly via `canvas.render()` into RGB numpy arrays.
   - Encoded into an H.264 `.mp4` video stream via `imageio-ffmpeg` with `yuv420p` pixel format for universal playback compatibility.

---

## Phased Execution Plan (Copy-Pasteable for Agents)

### Phase 1: Stock Discovery & Pod Provisioning
1. Query available GPU types and capacity in `EU-RO-1`:
   - Call Runpod MCP `get-capacity` filtering for `dataCenterId="EU-RO-1"`.
   - Identify the lowest-cost available GPU with $\ge 16\text{GB}$ VRAM (e.g. `NVIDIA RTX 4090`, `NVIDIA RTX 2000 Ada Generation`, `NVIDIA RTX 4000 Ada Generation`).
2. Provision the pod via Runpod MCP `create-pod` with the parameters specified above.
3. Retrieve pod connection details via `get-pod`:
   - Extract public IP (`runtime.ports[22].ip` or direct IP).
   - Extract public port (`runtime.ports[22].public_port`).

### Phase 2: Code Sync & Dependency Bootstrap
1. Synchronize the local smoke test directory to the remote volume:
   ```bash
   python setups/runpod-engine-smoke-test/exec_pod.py --host <POD_IP> --port <POD_PORT> sync --src setups/runpod-engine-smoke-test --dest /workspace/snngineV4_agent_branches/setups/
   ```
2. Bootstrap video dependencies (`ffmpeg`, `imageio`, `imageio-ffmpeg`, `vispy`) on the pod:
   ```bash
   python setups/runpod-engine-smoke-test/exec_pod.py --host <POD_IP> --port <POD_PORT> cmd "bash /workspace/snngineV4_agent_branches/setups/runpod-engine-smoke-test/runpod_video_runner.sh bootstrap"
   ```

### Phase 3: Headless Video Generation
1. Launch the headless simulation video generator on the remote GPU:
   ```bash
   python setups/runpod-engine-smoke-test/exec_pod.py --host <POD_IP> --port <POD_PORT> cmd "bash /workspace/snngineV4_agent_branches/setups/runpod-engine-smoke-test/runpod_video_runner.sh generate --steps 300 --stride 2 --fps 30 --output-dir /workspace/output"
   ```
2. The generator writes `/workspace/output/simulation_YYYY-MM-DD_HH-MM-SS.mp4` and a companion `.json` metadata file.

### Phase 4: Automated Download to Host
1. Retrieve the generated video filename:
   ```bash
   python setups/runpod-engine-smoke-test/exec_pod.py --host <POD_IP> --port <POD_PORT> cmd "ls -1 /workspace/output/*.mp4 | tail -n 1"
   ```
2. Download the video artifact to the local `output/` directory using the built-in collision-resolving downloader:
   ```bash
   python setups/runpod-engine-smoke-test/exec_pod.py --host <POD_IP> --port <POD_PORT> download --remote-src /workspace/output/<LATEST_VIDEO_FILENAME>.mp4 --dest-dir setups/runpod-engine-smoke-test/output
   ```
3. Assert that the downloaded file exists locally in `setups/runpod-engine-smoke-test/output/` and has a size $> 0$ bytes.

### Phase 5: Financial Teardown & Documentation
1. Terminate the remote GPU pod immediately via Runpod MCP `delete-pod(podId=...)`.
2. Confirm pod list via `list-pods` shows zero running compute pods.
3. Record execution metrics in `setups/runpod-engine-smoke-test/runpod-engine-video-report.md`.

---

## Pass / Fail Verification Criteria

- **PASS**:
  1. `generate_simulation_video.py` completes execution on remote pod with exit code `0`.
  2. Output video file is a valid H.264 MP4 with readable headers, non-zero duration, and correct dimensions ($1280 \times 720$).
  3. File is successfully transferred to host `setups/runpod-engine-smoke-test/output/` without corruption.
  4. Timestamp and collision numbering `(1)`, `(2)` logic functions as designed.
  5. Pod compute billing is halted immediately following transfer.
- **FAIL**:
  1. Offscreen EGL context initialization fails on remote pod.
  2. Video encoding errors (e.g. missing ffmpeg codecs or invalid color format).
  3. Incomplete or failed SCP transfer.
  4. Remote pod left running unmonitored.

---

## Follow-Up Sub-Task: Video Quality, High-Resolution Scaling, and Compression Optimization

### Objective
Triggered immediately following the first successful baseline video generation and download. The goal is to elevate visual fidelity, enable high-resolution rendering targets up to 4K UHD, enhance dynamic presentation of neural events, and achieve optimal compression efficiency across resolution tiers.

---

### Key Optimization Vectors

1. **High-Resolution Scaling (1080p, 1440p / 2K, 2160p / 4K UHD)**:
   - **Configurable Resolution Presets**: Support CLI flags `--resolution 1080p` ($1920 \times 1080$), `1440p` ($2560 \times 1440$), `4k` ($3840 \times 2160$), or arbitrary `WIDTHxHEIGHT`.
   - **Offscreen EGL Framebuffer Scaling**: Allocate high-resolution offscreen render buffers on the GPU ($3840 \times 2160$ RGBA $\approx 33\text{ MB}$ per buffer, well within $\ge 16\text{GB}$ VRAM limits).
   - **Point Sprite Size & Line Width Scaling**: Dynamically scale neuron marker sizes, stroke widths, and HUD elements proportionally with rendering resolution to maintain visual clarity at 1440p and 4K.

2. **Advanced Codecs & Bitrate Control for Ultra-HD**:
   - **H.265 / HEVC and AV1 Support**: For $\ge 1440\text{p}$ and 4K resolutions, enable H.265 (`libx265` or `hevc_nvenc`) to achieve $40\%\text{–}50\%$ smaller file sizes than H.264 at equivalent visual quality.
   - **Constant Rate Factor (CRF) Tuning**: Use calibrated CRF rate control (`crf=20`–`22` for H.264; `crf=22`–`24` for H.265) with `-preset slow` for optimal rate-distortion trade-offs.
   - **Burst Flash Throttling**: Configure VBV maximum bitrate caps (`-maxrate` / `-bufsize`) to prevent network bursting events from generating bitstream spikes.

3. **Offscreen Anti-Aliasing & Rendering Fidelity**:
   - **Multisample Anti-Aliasing (MSAA)**: Enable $4\times$ or $8\times$ MSAA on the VisPy offscreen EGL framebuffer to eliminate point-edge shimmering and jagged lines.
   - **Point Sprite & Glow Shaders**: Add dynamic radius scaling and halo/glow shaders to spiking neurons to visually distinguish action potentials from sub-threshold depolarizations.
   - **Depth Sorting**: Ensure correct back-to-front alpha blending for dense 3D reservoirs with overlapping semi-transparent neuron bodies.

4. **Multi-View Composition & Telemetry HUD**:
   - **Composite Multi-Panel Layout**: Render a synchronized split-screen or inset panel: 3D reservoir geometry on the left and real-time membrane potential traces ($v(t)$) or spike raster plots on the right.
   - **Live Telemetry Overlay**: Render an in-frame scientific HUD displaying elapsed simulation time ($t \text{ in ms}$), active firing rate ($\text{Hz}$), and a membrane potential colormap scale bar.

5. **Camera Trajectory & Temporal Dynamics**:
   - **Smooth Orbital Easing**: Replace linear camera azimuth increments with eased spline trajectories (e.g. smooth orbit with gentle pitch oscillations) to highlight 3D topological structure.
   - **Sub-Step Temporal Integration**: Adjust simulation-to-frame stride with intermediate state interpolation to capture fast spike bursts without temporal aliasing.

---

### Resolution Tiers & Target Benchmarks

| Tier | Resolution | Recommended Codec | Target Bitrate | Max Target Size (10s @ 60fps) |
| :--- | :--- | :--- | :--- | :--- |
| **Full HD** | $1920 \times 1080$ | H.264 (`libx264` / `h264_nvenc`) | $4\text{–}8\text{ Mbps}$ | $\le 12\text{ MB}$ |
| **2K QHD** | $2560 \times 1440$ | H.264 / H.265 | $8\text{–}14\text{ Mbps}$ | $\le 20\text{ MB}$ |
| **4K UHD** | $3840 \times 2160$ | H.265 (`libx265` / `hevc_nvenc`) | $15\text{–}25\text{ Mbps}$ | $\le 35\text{ MB}$ |

---

### Deliverables
- **Optimized Video Artifact**: Saved with resolution tag and timestamp, e.g. `simulation_4k_YYYY-MM-DD_HH-MM-SS.mp4`.
- **Comparative Report**: Visual quality, frame render times, and compression metrics logged in `runpod-engine-video-report.md`.

---

## Follow-Up Sub-Task 2: Unified Composite Video Generation (3D Reservoir + Spike Raster + Voltage Waveforms)

### Objective
Advance from a standalone 3D spatial recording to a single, synchronized multi-panel composite video. In a unified frame, the viewer observes the 3D anatomical reservoir alongside real-time electrophysiological telemetry, recreating the complete multi-plot diagnostic interface from the legacy SNNgine3D engine.

---

### Frame Composition & Screen Layout

The video is rendered onto a single offscreen canvas partitioned into three synchronized viewports:

```text
+------------------------------------+------------------------------------+
|                                    |                                    |
|                                    |    Firing Scatter Plot             |
|                                    |    (Spike Raster over rolling time)|
|                                    |                                    |
|         3D Neural Reservoir        +------------------------------------+
|    (Turntable orbit, dynamic 3D    |                                    |
|     neuron bodies colored by v)    |    Membrane Potential Multi-Plot   |
|                                    |    (Continuous voltage traces v(t) |
|                                    |     per monitored neuron group)    |
|                                    |                                    |
+------------------------------------+------------------------------------+
```

1. **Left Panel — 3D Spatial Reservoir (50% Frame Width)**:
   - **View**: 3D perspective with continuous turntable camera orbit.
   - **Elements**: 3D neuron bodies colored continuously by instantaneous membrane potential $v \in [-75, 30] \text{ mV}$, with bright white flashes on firing events and reservoir bounding grid.

2. **Top Right Panel — Firing Scatter Plot (50% Width, 50% Height)**:
   - **View**: 2D sliding time buffer ($t \in [0, W]$, e.g. 100–250 ms window).
   - **Elements**: Discrete point markers for every action potential timestamp, indexed vertically by neuron ID and color-coded by group, with horizontal dashed group divider lines.

3. **Bottom Right Panel — Voltage Potential Multi-Plot (50% Width, 50% Height)**:
   - **View**: Synchronized 2D sliding time buffer ($t \in [0, W]$).
   - **Elements**: Continuous multi-line traces ($v(t)$) for monitored neuron groups with vertical baseline offsets, showing sub-threshold oscillations, threshold approach, and post-spike reset dynamics.

---

### Technical Synchronization & Rendering

- **Single Canvas Render Pipeline**:
  - VisPy `EngineSceneCanvas` configures a grid layout with three `ViewBox` widgets:
    - `view_3d = canvas.central_widget.add_view(row=0, col=0, row_span=2, col_span=1)`
    - `view_raster = canvas.central_widget.add_view(row=0, col=1, row_span=1, col_span=1)`
    - `view_voltage = canvas.central_widget.add_view(row=1, col=1, row_span=1, col_span=1)`
  - Each simulation step advances both the 3D neuron states and the scrolling circular plot buffers (`simulator.voltage_plot` and `simulator.firings_scatter_plot`).
  - A single `canvas.render()` call captures all three panels simultaneously, guaranteeing frame-level temporal synchronization between spatial spikes and waveform peaks.

- **High-Resolution Multi-Panel Allocation**:
  Dividing the canvas makes high-resolution tiers especially advantageous for crisp line rendering:

| Tier | Total Resolution | Left 3D Panel | Each Telemetry Panel (Right) | Recommended Codec | Max Target Size (10s @ 60fps) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **720p** | $1280 \times 720$ | $640 \times 720$ | $640 \times 360$ | H.264 | $\le 6\text{ MB}$ |
| **1080p** | $1920 \times 1080$ | $960 \times 1080$ | $960 \times 540$ | H.264 | $\le 12\text{ MB}$ |
| **1440p / 2K** | $2560 \times 1440$ | $1280 \times 1440$ | $1280 \times 720$ | H.264 / H.265 | $\le 20\text{ MB}$ |
| **4K UHD** | $3840 \times 2160$ | $1920 \times 2160$ | $1920 \times 1080$ | H.265 (`libx265` / `hevc_nvenc`) | $\le 35\text{ MB}$ |

*(At 4K UHD, each telemetry plot receives a full $1920 \times 1080$ viewport, rendering dense multi-neuron voltage waveforms and individual spike dots with pristine sharpness).*

---

### Output Artifacts & Naming

- **Filename Format**:
  `simulation_composite_YYYY-MM-DD_HH-MM-SS.mp4`
  (with automatic duplicate collision handling: `simulation_composite_YYYY-MM-DD_HH-MM-SS (1).mp4`).
- **Telemetry Log**:
  Companion `simulation_composite_YYYY-MM-DD_HH-MM-SS.json` logging simulation steps, mean firing frequency, voltage bounds, and render duration.
- **Destination**:
  Downloaded automatically via `exec_pod.py download` to `setups/runpod-engine-smoke-test/output/`.
