# Runpod Headless 3D Chemical Source & Volumetric Diffusion Report

## Summary

Executed the standalone headless 3D chemical concentration diffusion simulation and 3-panel 1080p diagnostic video pipeline (`setups/runpod-chem-diffusion/generate_chem_diffusion_video.py`) on an ephemeral Runpod GPU pod (`6ru5a4wlemsz8u`, `NVIDIA RTX PRO 4000 Blackwell` in `EU-RO-1` attached to persistent network volume `qze81dpw7q`). **Outcome: Worked.** Across 1,200 neural simulation steps (2,400 explicit 3D chemical diffusion steps at $k_{\text{val}} = 0.16, \text{depreciation} = 0.002$), chemical concentration `chemicals.C0` injected inside a localized $12 \times 12 \times 12$ cubic source (`i, j, k in [44, 56)` at $C = 2000.0$) smoothly diffused outward through the $100 \times 100 \times 100$ reservoir grid, expanding from `4,375` active plume voxels ($C > 5.0$) to `998,272` voxels and producing a 600-frame, 20.0-second H.264 `.mp4` (`simulation_chem_1080p_2026-10-16_12-22-32.mp4`, `2,900,754 bytes`) in `35.08s` (`17.11 fps`). The ephemeral pod was immediately terminated after downloading the video and JSON telemetry sidecar (`0` active pods remaining).

---

## Phase 1: 3D Chemical Source Configuration & CUDA Kernel Verification

**Summary:** Configured `snngine_v4`'s existing CUDA chemical diffusion kernel (`update_chemical_concentrations_gpu` in `snn_simulation.cu`) from Python without modifying any files under `snngine_v4/`, clearing the default back-face boundary condition and injecting a localized cubic chemical source at the center of the reservoir. **Outcome: Worked.**

### What Was Built
- **Padded Chemical Grid Allocation (`(102, 100, 100)`)**: `generate_chem_diffusion_video.py` passes an explicit `chem_tensor = torch.zeros((102, 100, 100), dtype=torch.float32, device=device)` ($1,020,000$ floats) to `Chemicals.__init__`, while `SimulationConfig.grid_size` remains `(100, 100, 100)`. This provides a 2-slice guard buffer along axis 0 (`i = height`) so that `update_chemical_concentrations_gpu`'s boundary check (`i <= grid_h` at `snn_simulation.cu:221`) never reads out-of-bounds GPU memory at `i = 100, j = 100, k = 100` (linear offset `1,010,100`).
- **Clearing Default Back-Face Boundary Values & Injecting Localized 3D Source**:
  - After `SimulationBackend(sim)` initializes `C0` via `set_test_values_gpu` (which populates the back 3 depth slices `[:, :, -3:]`), `configure_localized_chemical_source()` zeroes `c_current`, `c_next`, and `c_source` in-place via `.gpu_values.zero_()`.
  - Injects a localized $12 \times 12 \times 12$ cubic source at `i in [44, 56), j in [44, 56), k in [44, 56)` with `c_source = 2000.0` and initial concentration `2000.0`.
- **Numerically Stable Explicit 3D Stencil Parameters**:
  - Sets `sim_backend._sim.chem_k_val = 0.16` (satisfying the 3D 6-neighbor explicit stability bound $k_{\text{val}} \le \frac{1}{6} \approx 0.1667$) and `sim_backend._sim.chem_depreciation = 0.002`.
  - Preserves `b_update_chemical_concentrations = True` as initialized by the C++ `SnnSimulation` constructor (avoiding the one-way setter latch in `snn_simulation.cu:1209-1216`).

### Quantitative Diffusion Telemetry (`simulation_chem_1080p_2026-10-16_12-22-32.json`)
| Metric | Initial (Frame 1) | Midpoint (Frame 300) | Final (Frame 600) |
|---|---|---|---|
| Active Plume Voxels ($C > 5.0$) | `4,375` | `826,253` | `998,272` |
| Total Plume Mass ($\sum C$) | `906,533.0` | — | `98,657,568.0` |
| Shell $d = 1$ voxel (`#ff5252`) | `694.38` | `1677.9` | `1700.11` |
| Shell $d = 3$ voxels (`#ffab40`) | `13.03` | — | `1229.53` |
| Shell $d = 6$ voxels (`#ffd740`) | `0.00` | `725.4` | `807.82` |
| Shell $d = 12$ voxels (`#69f0ae`) | `0.00` | — | `399.53` |
| Shell $d = 20$ voxels (`#40c4ff`) | `0.00` | — | `173.97` |

---

## Phase 2: Headless 3-Panel Volumetric Video Generation & Runpod Execution

**Summary:** Rendered a 600-frame, 30 fps 1080p (`1920x1080`) H.264 video combining the 3D neural reservoir + 3D chemical source wireframe box + translucent 3D volumetric chemical plume (`VolumeVisual`), radial concentration curves $C(r, t)$, and neural membrane potential waveforms $v(t)$. **Outcome: Worked.**

### What Was Built & How to Run It
- **Standalone Task Scripts (`setups/runpod-chem-diffusion/`)**:
  - `generate_chem_diffusion_video.py`: 3-panel headless EGL + VisPy composite renderer:
    1. **Left Panel (`3d_reservoir_and_chemical_plume`)**: Renders the $100 \times 100 \times 100$ reservoir cage, a bright cyan/gold 3D wireframe box around the source (`[44, 56]^3`), 200 dynamic 3D neurons colored by membrane potential $v(t)$ with spike-flash highlighting, and a custom translucent `VolumeVisual` (`translucent` method, 256-entry custom RGBA colormap with exact $\alpha = 0.0$ at $C = 0$ so zero-concentration background voxels never occlude neurons).
    2. **Top-Right Panel (`radial_chemical_concentration_shells`)**: Plots mean chemical concentration $\bar{C}(d, t)$ across 5 concentric Chebyshev shells ($d \in \{1, 3, 6, 12, 20\}$ voxels outside the source cube) over a 240-step rolling window.
    3. **Bottom-Right Panel (`voltage_waveforms`)**: Plots synchronized membrane potential traces $v(t)$ for 6 representative neurons (`[15, 154, 0, 46, 95, 199]`).
  - `runpod_chem_runner.sh`: Pod-side runner script that activates `/workspace/venv`, ensures headless EGL/ffmpeg and `PyOpenGL` are installed, runs `generate_chem_diffusion_video.py`, and enforces rolling 5-video retention on `/workspace/output`.
- **Single-Command Remote Execution**:
  ```powershell
  python setups/runpod-engine-smoke-test/exec_pod.py --host <POD_IP> --port <SSH_PORT> sync --src setups/runpod-chem-diffusion --dest /workspace/snngineV4_cloud/snngineV4_agent_branches/setups/ ; if ($?) { python setups/runpod-engine-smoke-test/exec_pod.py --host <POD_IP> --port <SSH_PORT> cmd --timeout 600 "sed -i 's/\r$//' /workspace/snngineV4_cloud/snngineV4_agent_branches/setups/runpod-chem-diffusion/runpod_chem_runner.sh && bash /workspace/snngineV4_cloud/snngineV4_agent_branches/setups/runpod-chem-diffusion/runpod_chem_runner.sh generate --steps 1200 --stride 2 --chem-substeps 2 --fps 30 --resolution 1080p" }
  ```

### Hiccups Hit & How They Were Resolved
1. **`sim_instance.Fired` Tensor Type (`torch.Tensor` vs `MappedTensor`)**:
   - *Hiccup*: `sim_instance.Fired` in `snngine_v4` is a raw `torch.Tensor` (created via `torch.zeros`), unlike `element.neuron_states.N_props` which is a `MappedTensor` exposing `.gpu_values`. Calling `sim_instance.Fired.gpu_values` raised `AttributeError: 'Tensor' object has no attribute 'gpu_values'`.
   - *Fix*: Used `getattr(sim_instance.Fired, "gpu_values", sim_instance.Fired).cpu().numpy() > 0.0` in `generate_chem_diffusion_video.py`.
2. **VisPy `VolumeVisual` 3D Texture Upload Requires `PyOpenGL`**:
   - *Hiccup*: While 2D `Line` and `Markers` visuals in VisPy use standard OpenGL ES 2.0 calls via `vispy.gloo`, `VolumeVisual` uploads a 3D texture via `glTexImage3D`, which explicitly imports `OpenGL.GL` (`PyOpenGL`). Because `/workspace/venv` only had `vispy` and `pycuda` installed from earlier 2D/scatter smoke tests, the first render pass raised `ImportError: PyOpenGL is required for 3D texture support`.
   - *Fix*: Added an automatic `python3 -c "import OpenGL.GL"` check and `pip install -q PyOpenGL` step inside `ensure_system_packages()` in `runpod_chem_runner.sh`, persisting `PyOpenGL` on the network volume `/workspace/venv`.

### Ephemeral Pod Lifecycle & Financial Teardown
- **Provisioned**: Pod `6ru5a4wlemsz8u` (`NVIDIA RTX PRO 4000 Blackwell`, $0.57/hr in `EU-RO-1`, mounted `qze81dpw7q` at `/workspace`).
- **Artifacts Retrieved**:
  - `setups/runpod-chem-diffusion/output/simulation_chem_1080p_2026-10-16_12-22-32.mp4` (`2,900,754 bytes`, gitignored)
  - `setups/runpod-chem-diffusion/output/simulation_chem_1080p_2026-10-16_12-22-32.json` (`1,665 bytes`, gitignored)
- **Terminated**: Called `delete-pod(id="6ru5a4wlemsz8u")` (`HTTP 204`) and verified `list-pods` returned `"pods": []` ($0.00/hr active compute spend; total pod runtime ~8.5 minutes $\approx \$0.08$).

---

## Phase 3 (Follow-Up Sub-Task 1): 5-Panel Composite View (2-Way 3D Left Column + 3-Way Time-Series Right Column)

**Summary:** Extended `generate_chem_diffusion_video.py` to render a 5-panel composite layout (`--layout 5way`, default `5way`, using a $6\text{-row} \times 2\text{-column}$ VisPy `Grid`) combining 2 equal-height 3D views on the left column and 3 equal-height 2D time-series plots on the right column, and executed it on ephemeral Runpod GPU pod `7hejsf6v71fxgy` (`NVIDIA L4` in `EU-RO-1`). **Outcome: Worked.** Rendered 600 frames (`1920x1080` @ 30 fps, `4,801,918 bytes`) in `23.62s` (`25.40 fps`), downloaded `simulation_chem_5way_1080p_2026-10-16_14-09-58.mp4` and `.json`, and immediately terminated the pod (`0` active pods remaining).

### What Was Built & Viewport Architecture ($6\text{ rows} \times 2\text{ columns}$, $\text{lcm}(2, 3) = 6$)
- **Left Column (`col=0`, 50% width — 2 Equal-Height 3D Views, `row_span=3` = 50% height each)**:
  1. **Top-Left (`row=0, col=0, row_span=3`) — 3D Chemical Source & Volumetric Plume (`3d_chemical_plume`)**: Outer reservoir wireframe cage + localized 3D chemical source wireframe box (`[44, 56]^3`) + translucent 3D volumetric chemical diffusion plume (`visuals.Volume` for `chemicals.C0`), providing an unobstructed view of volumetric concentration buildup and outward diffusion.
  2. **Bottom-Left (`row=3, col=0, row_span=3`) — 3D Neural Network Reservoir (`3d_neural_network`, from `runpod-engine-smoke-test`)**: Translucent 3D reservoir bounding box (`visuals.Box`) + 200 dynamic 3D neurons (`visuals.Markers`) colored by membrane potential $v(t)$ with white spike flashes (`fired_mask = fired_accum | (v_curr >= -30.0)`), rotating in lockstep (`TurntableCamera` `azimuth`, `elevation`, `center`, `distance`) with the 3D chemical plume view above it.
- **Right Column (`col=1`, 50% width — 3 Equal-Height 2D Time-Series Views, `row_span=2` = 33.3% height each)**:
  3. **Top-Right (`row=0, col=1, row_span=2`) — Radial Chemical Concentration Curves $C(r, t)$ (`radial_chemical_concentration_shells`)**: Mean chemical concentration across the 5 concentric Chebyshev distance shells ($d \in \{1, 3, 6, 12, 20\}$ voxels outside the source boundary).
  4. **Middle-Right (`row=2, col=1, row_span=2`) — Firing Scatter Plot / Spike Raster (`spike_raster`, from `runpod-engine-smoke-test`)**: Rolling 200 ms action potential raster `(t, neuron_id)` across all 200 neurons, color-coded by neuron group (`GROUP_COLORS`) with horizontal group dividers and right-edge time cursor.
  5. **Bottom-Right (`row=4, col=1, row_span=2`) — Multi-Trace Membrane Potential Waveforms $v(t)$ (`voltage_waveforms`)**: Rolling voltage waveforms for 6 representative neurons (`[1, 158, 0, 52, 96, 199]`).

### Quantitative Telemetry (`simulation_chem_5way_1080p_2026-10-16_14-09-58.json`)
| Metric | Initial (Frame 1) | Midpoint (Frame 300) | Final (Frame 600) |
|---|---|---|---|
| Active Plume Voxels ($C > 1.0$) | `4,417` | `828,812` | `998,272` |
| Total Plume Mass ($\sum C$) | `911,278.81` | — | `99,046,640.0` |
| Shell $d = 1$ voxel | `696.67` | `1677.9` | `1700.23` |
| Shell $d = 3$ voxels | `13.27` | — | `1229.84` |
| Shell $d = 6$ voxels | `0.00` | `725.8` | `808.29` |
| Shell $d = 12$ voxels | `0.00` | — | `400.10` |
| Shell $d = 20$ voxels | `0.00` | — | `174.52` |
| Total Neural Spikes | — | — | `1,022` |

### Hiccups Hit & How They Were Resolved
- **Avoiding Recursive Upload of Local `output/*.mp4` During `exec_pod.py sync`**:
  - *Hiccup*: Running `exec_pod.py sync --src setups/runpod-chem-diffusion` after Phase 2 attempted to recursively SCP the local 2.9 MB `.mp4` inside `setups/runpod-chem-diffusion/output/` back up to the pod, hitting the 60s SCP upload timeout.
  - *Fix*: Synced the script file directly (`--src setups/runpod-chem-diffusion/generate_chem_diffusion_video.py --dest /workspace/snngineV4_cloud/snngineV4_agent_branches/setups/runpod-chem-diffusion/`), which completed in `< 1s`.

### Ephemeral Pod Lifecycle & Financial Teardown
- **Provisioned**: Pod `7hejsf6v71fxgy` (`NVIDIA L4`, $0.59/hr in `EU-RO-1`, mounted `qze81dpw7q` at `/workspace`).
- **Artifacts Retrieved**:
  - `setups/runpod-chem-diffusion/output/simulation_chem_5way_1080p_2026-10-16_14-09-58.mp4` (`4,801,918 bytes`, gitignored)
  - `setups/runpod-chem-diffusion/output/simulation_chem_5way_1080p_2026-10-16_14-09-58.json` (`1,725 bytes`, gitignored)
- **Terminated**: Called `delete-pod(id="7hejsf6v71fxgy")` (`HTTP 204`) and verified `list-pods` returned `"pods": []` ($0.00/hr active compute spend; total pod runtime ~5 minutes $\approx \$0.05$).

