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

---

## Phase 4: Follow-Up Sub-Task 2 — Large-Scale Flat-Slab Reservoir (`(6, 6, 1)`), Dual Chemical Sources, Depth-Transparent Visuals & GPU VRAM/Throughput Scaling

**Summary:** Successfully implemented and verified **Follow-Up Sub-Task 2** on ephemeral Runpod GPU pod `1ozjtxxxj0eryv` (`NVIDIA RTX PRO 4000 Blackwell` in `EU-RO-1`). Configured a 30,000-neuron ($6,690,000$ synapses), non-cubic flat-slab reservoir geometry (`reservoir_shape = (6, 6, 1)` matching legacy SNNgine3D) with dual spatially separated 3D chemical sources in opposite quadrants, depth-transparent neuron visuals (`resting_alpha = 0.16` with variable marker sizing), and active GPU VRAM stress-scaling reaching **19,670.4 MB / 23,986.0 MB (82.01% VRAM utilization)**. Rendered 600 frames (`1920x1080` @ 30 fps, `11,980,816 bytes`) in `44.31s` (`13.54 fps`), downloaded `simulation_chem_5way_slab_1080p_2026-10-16_15-12-27.mp4` and `.json`, and immediately terminated the pod (`0` active pods remaining).

### Architectural Innovations & Geometry Configuration
1. **Flat-Slab Reservoir Geometry (`reservoir_shape = (6, 6, 1)`)**:
   - Replicated legacy `SNNgine3D` geometry (`reservoir_shape = (6, 6, 1)` from `snngine3d/configuration/deprecated/engine_config.py`).
   - Automatically computed spatial segmentation `seg = (12, 12, 2)` yielding `G = 288` cubic location groups with lattice spacing `(0.5, 0.5, 0.5)`.
   - Prevented CPU/GPU floating-point boundary rounding mismatches in `sort_pos` by clamping neuron positions strictly to cell interiors (`[1e-3, 1 - 1e-3]`).
2. **Dual Localized 3D Chemical Sources & Dual Focal Thalamic Foci**:
   - Chemical grid sized to `(H=52, W=156, D=156)`: satisfies both `FiniteGrid._make_pos` height limit (`H <= 100`) and partial-block CUDA alignment (`52 % 8 == 4`, `156 % 8 == 4`).
   - Injected **Source 1** at $(i=26, j=46, k=46)$ (front-left quadrant) with emerald wireframe box, and **Source 2** at $(i=26, j=110, k=110)$ (back-right quadrant) with amber-gold wireframe box.
   - Dual focal thalamic stimulation activated at the centroid of each chemical source, driving concurrent traveling neural waves across the wide slab.
3. **Depth-Transparent Neuron Visuals & Adaptive Sizing**:
   - Resting neurons ($v < -55\text{ mV}$): small markers ($2.94\text{ px}$) and low opacity ($\alpha = 0.16$), creating an ethereal translucent background allowing deep activity to remain visible.
   - Sub-threshold depolarizing neurons ($-55 \le v < -30\text{ mV}$): vibrant cyan-emerald with rising opacity ($\alpha \approx 0.50 \to 0.85$) and $1.35\times$ size ($3.9\text{ px}$).
   - Spiking neurons ($v \ge -30\text{ mV}$ or fired): bright warm gold-white flash at full opacity ($\alpha = 1.0$) and $2.35\times$ size ($6.9\text{ px}$).
4. **VRAM Scaling & Fast-Path DataFrame Synchronization**:
   - Patched `TensorSeries.sync_to_df` for $N > 500$ to build a single 2D NumPy block in $O(1)$ instead of iterating column slices in Pandas 2.x, dropping reservoir build time to `1.75s` for 30,000 neurons.
   - Allocated GPU simulation state and volumetric history cache up to target fraction `0.82`, utilizing **19.67 GB / 23.99 GB VRAM** while maintaining 4.3 GB free headroom for EGL rendering.

### Quantitative Telemetry (`simulation_chem_5way_slab_1080p_2026-10-16_15-39-18.json` — Brightened Inactive Palette)
| Metric | Initial (Frame 1) | Midpoint (Frame 300) | Final (Frame 600) |
|---|---|---|---|
| Active Plume Voxels ($C > 1.0$) | `13,717` | `1,077,419` | `1,238,003` |
| Total Plume Mass ($\sum C$) | `3,361,898.25` | — | `336,897,408.0` |
| Shell $d = 1$ voxel | `854.51` | `1735.8` | `1767.92` |
| Shell $d = 3$ voxels | `44.00` | `1160.5` | `1384.95` |
| Shell $d = 6$ voxels | `0.01` | `885.6` | `1018.91` |
| Shell $d = 12$ voxels | `0.00` | `512.7` | `642.79` |
| Shell $d = 20$ voxels | `0.00` | `265.3` | `374.19` |
| Total Neural Spikes | — | — | `154,259` |
| GPU VRAM Device Used | — | — | `19,670.44 MB (82.01%)` |
| PyTorch Allocated VRAM | — | — | `19,296.74 MB` |
| Synapses per Neuron ($S$) | — | — | `223` |
| Total Network Synapses | — | — | `6,690,000` |

### Inactive Neuron Contrast & Luminance Tuning
Following visual inspection showing inactive neurons were previously too dark against the `#0c0e17` deep background, the visualizer palette in `compute_slab_neuron_colors_and_sizes` was tuned:
1. **Luminous Sky-Blue/Cyan Resting Baseline**:
   - Resting neurons ($v < -55\text{ mV}$) elevated to luminous cyan-blue `(0.25..0.40, 0.65..0.85, 0.95..1.00)` with `resting_alpha = 0.40` (increased from `0.16`) and base marker size `2.8 px` (increased from `2.4 px`).
   - Retains translucent 3D depth perception while guaranteeing crisp, starry visibility across all 30,000 neurons regardless of view angle.
2. **Distinct Multi-Stage Activation Progression**:
   - Sub-threshold depolarizing neurons transition smoothly into vivid chartreuse-gold $\to$ warm amber ($\alpha \approx 0.65 \to 0.90$, size $1.35\times$).
   - Spiking neurons deliver a brilliant white-hot flash at full opacity ($\alpha = 1.0$, size $2.4\times$).

### Ephemeral Pod Lifecycle & Financial Teardown
- **Provisioned**: Pod `1ozjtxxxj0eryv` (first run) and `novm5nt2m062bm` (palette update run, `NVIDIA RTX PRO 4000 Blackwell`, $0.57/hr in `EU-RO-1`, attached to `qze81dpw7q` at `/workspace`).
- **Artifacts Retrieved**:
  - `setups/runpod-chem-diffusion/output/simulation_chem_5way_slab_1080p_2026-10-16_15-12-27.mp4` (`11,980,816 bytes`, gitignored)
  - `setups/runpod-chem-diffusion/output/simulation_chem_5way_slab_1080p_2026-10-16_15-39-18.mp4` (`19,568,608 bytes`, gitignored, brightened inactive neurons)
  - `setups/runpod-chem-diffusion/output/simulation_chem_5way_slab_1080p_2026-10-16_15-39-18.json` (`3,060 bytes`, gitignored)
- **Terminated**: Called `delete-pod(id="novm5nt2m062bm")` (`HTTP 204`) and verified `list-pods` returned `"pods": []` ($0.00/hr active compute spend; pod active runtime ~7 minutes $\approx \$0.07$).


