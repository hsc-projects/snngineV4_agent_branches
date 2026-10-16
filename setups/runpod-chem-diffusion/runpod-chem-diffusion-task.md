# Task: Runpod Headless 3D Chemical Source & Volumetric Diffusion Video Generation

## Context and where this task fits

Prior tasks in [`setups/runpod-engine-smoke-test/`](file:///E:/dev/snngineV4_agent_branches/setups/runpod-engine-smoke-test/) validated headless simulation execution and synchronized 3-panel composite video rendering (3D neural reservoir, rolling spike raster, and stacked membrane potential waveforms) on Runpod GPU infrastructure.

This standalone task focuses on **3D chemical concentration diffusion (`chemicals.C0`) in `snngine_v4`**. The objective is to define a localized 3D chemical source inside the spatial reservoir, run the compiled C++/CUDA 3D finite-difference diffusion kernel, and record a synchronized composite video showing the chemical concentration building up around the source and diffusing outward over time $t$—both as a 3D volumetric plume inside the reservoir cage and as radial concentration curves $C(r, t)$ across concentric shells around the source—without modifying any files in `snngine_v4/` or other `setups/` task directories.

---

## Primary-Source Verification: Chemical Diffusion Mechanics (`snngine_v4` vs. `SNNgine3D`)

Direct inspection of [`snn_simulation.cu`](file:///E:/dev/snngineV4_agent_branches/snngine_v4/nn/cuda_backend/src/simulation/snn_simulation.cu#L201-L290), [`snn_simulation.cuh`](file:///E:/dev/snngineV4_agent_branches/snngine_v4/nn/cuda_backend/src/simulation/snn_simulation.cuh#L109-L120), and [`chem_volume.py`](file:///E:/dev/snngineV4_agent_branches/snngine_v4/chemistry/chem_volume.py) establishes the following verified invariants:

1. **Kernel Activation & Setter Bug (`snn_simulation.cu:462-464, 1209-1216`)**:
   - Although `b_update_chemical_concentrations` is declared `false` in [`snn_simulation.cuh:119`](file:///E:/dev/snngineV4_agent_branches/snngine_v4/nn/cuda_backend/src/simulation/snn_simulation.cuh#L119), the constructor in [`snn_simulation.cu:462-464`](file:///E:/dev/snngineV4_agent_branches/snngine_v4/nn/cuda_backend/src/simulation/snn_simulation.cu#L462-L464) automatically sets `b_update_chemical_concentrations = true` whenever `chem_grid_w * chem_grid_h * chem_grid_d > 0` ($100^3 = 1,000,000$).
   - Furthermore, [`SnnSimulation::set_b_update_chemical_concentrations()`](file:///E:/dev/snngineV4_agent_branches/snngine_v4/nn/cuda_backend/src/simulation/snn_simulation.cu#L1209-L1216) contains a guard bug (`if (!b_update_chemical_concentrations_)`): if toggled to `False`, the property setter can never set it back to `True` when grid volume $> 0$. Therefore, the script must leave `b_update_chemical_concentrations` untouched (`True` from construction).

2. **3D Explicit Finite-Difference Equation & Von Neumann Stability Limit (`snn_simulation.cu:266-279`)**:
   - Voxels with `C_source[idx] > 0.f` clamp to `C_source[idx]`. All other voxels update via the 7-point 3D Laplacian stencil:
     $$c_{\text{new}} = \min\!\Big(2000,\; \max\!\big(0,\; (1 - 6 k_{\text{val}}) c_{\text{old}} + k_{\text{val}} \sum_{n \in \mathcal{N}_6} c_n - \text{depreciation}\big)\Big)$$
   - **Stability constraint**: Positivity of the self-weight requires $1 - 6 k_{\text{val}} \ge 0 \implies \mathbf{k_{\text{val}} \le \frac{1}{6} \approx 0.1667}$. Values $> 1/6$ cause unstable checkerboard oscillations. The [`ChemicalConcentrationModel`](file:///E:/dev/snngineV4_agent_branches/snngine_v4/chemistry/chem_models.py#L16) default `k_val = 0.16` sits right at the stable maximum and is used as the default.

3. **In-Place Dual Buffer Write (`snn_simulation.cu:286-287`)**:
   - `_update_sim_pointers()` only advances spike ring-buffer pointers; it does not swap `C_old` and `C_new`.
   - Instead, `update_chemical_concentrations_` stages `C_old` into shared memory `Mat[10][10][10]` and writes the updated value into **both** `C_new[idx]` (`c_next`) and `C_old[idx]` (`c_current`) at the end of every step.

4. **Linear Memory Indexing `(i=height, j=width, k=depth)` vs. VisPy `VolumeVisual` `(Z, Y, X)` (`snn_simulation.cu:216-224`)**:
   - The CUDA kernel computes linear offsets as `idx = i * (grid_w * grid_d) + j * grid_d + k`, where `i` is height (axis 0), `j` is width (axis 1), and `k` is depth (axis 2).
   - VisPy's `VolumeVisual` indexes 3D numpy arrays as `(Z, Y, X)` corresponding to scene `(X, Y, Z)`. Reshaping the flat buffer as `(H, W, D)` and transposing to `(H, D, W)` (or using a symmetric/aligned coordinate mapping) ensures the rendered 3D plume aligns with the wireframe source box and 3D neuron positions `N_pos`.

5. **Boundary Over-Read Guard (`snn_simulation.cu:221, 237`)**:
   - Line 221 tests `if ((i <= grid_h) && (j <= grid_w) && (k <= grid_d))` before reading `C_old[idx]` on line 237 (whereas the write on line 262 tests `<`). With $8 \times 8 \times 8$ thread blocks on a $100^3$ grid ($13 \times 8 = 104$ threads/axis), boundary threads at `i = 100`, `j = 100`, or `k = 100` read up to `idx = 1,010,100` ($10,101$ floats past $100^3$).
   - Allocating the backing tensors (`c_current`, `c_next`, `c_source`) with $+2$ padding along each axis (e.g. $102 \times 102 \times 102$ floats) while passing `chem_grid_w = chem_grid_h = chem_grid_d = 100` prevents any out-of-bounds global memory reads.

6. **Why Chemical Diffusion Was Invisible in Prior `snngine_v4` Runs**:
   - [`ChemicalConcentrationVolume`](file:///E:/dev/snngineV4_agent_branches/snngine_v4/chemistry/chem_volume.py#L32-L76) defaults to `b_test_init = True` (loading `volume/stent.npz` on CPU and setting flat back-face boundary slices `[:, :, -3:] = 1800..2000` in `set_test_values_gpu()`), [`SNNgine.run_sim()`](file:///E:/dev/snngineV4_agent_branches/snngine_v4/snngine.py#L222-L227) omits per-step `copy_to_texture()`, and [`EngineSelectorTree`](file:///E:/dev/snngineV4_agent_branches/snngine_v4/gui/parameter_trees/selector_tree/engine_selector_tree.py) is not yet wired to `c_source`.

---

## Safety, Boundaries, and Financial Discipline

1. **Strict Task Directory Confinement**:
   - All scripts, task docs, reports, and downloaded outputs for this task live strictly in `setups/runpod-chem-diffusion/`.
   - Do not modify any files in `snngine_v4/`, `snngine3d/`, or sibling directories under `setups/`.
2. **Financial Discipline & Ephemeral GPU Pod Lifecycle**:
   - Provision a GPU pod in `EU-RO-1` (`SECURE` cloud, attached to persistent volume `qze81dpw7q` at `/workspace`) only when ready to execute.
   - Terminate the GPU pod immediately via Runpod MCP `delete-pod` upon artifact download, and verify `list-pods` returns `[]` ($0.00/hr active compute spend).
3. **VCS Output Hygiene**:
   - `setups/runpod-chem-diffusion/output/.gitignore` ignores all generated media and telemetry files (`*`, `!.gitignore`). Never stage `.mp4` or `.json` output artifacts into git.

---

## File & Folder Structure

```text
setups/runpod-chem-diffusion/
├── runpod-chem-diffusion-task.md        # Task specification (this file)
├── generate_chem_diffusion_video.py     # Headless 3D chemical source + volumetric diffusion video generator
├── runpod_chem_runner.sh                # Remote pod execution & rolling volume retention runner
├── runpod-chem-diffusion-report.md      # Execution report & diffusion telemetry (created upon completion)
└── output/                              # Gitignored local artifact directory (`*` / `!.gitignore`)
    ├── .gitignore
    ├── simulation_chem_1080p_<ts>.mp4   # Downloaded video artifact (untracked)
    └── simulation_chem_1080p_<ts>.json  # Downloaded diffusion & spike telemetry (untracked)
```

---

## Substeps & Technical Specification

### Substep 1: Padded Buffer Allocation & Localized 3D Chemical Source Setup
1. Construct the `SpatialNetwork` and `SnnSimulation` backend on the GPU, allocating `C0` backing tensors with boundary-read padding ($\ge 1,020,000$ elements for a $100^3$ active grid).
2. Clear the default `set_test_values_gpu` back-face boundary slices (`[:, :, -3:]`) by zeroing `c_current`, `c_next`, and `c_source` in-place.
3. Define a localized 3D chemical source cube in `c_source` (default $12 \times 12 \times 12$ voxels centered inside the $100 \times 100 \times 100$ grid, co-located with the focal stimulated neuron cluster, set to concentration `2000.0`).
4. Verify `sim_backend.b_update_chemical_concentrations == True` and configure `sim_backend.chem_k_val` (`--chem-k-val`, default `0.16`, constrained to $(0, 1/6]$) and `sim_backend.chem_depreciation` (`--chem-depreciation`, default `0.005`).

### Substep 2: 3D Volumetric Plume, Source Wireframe & Radial Shell Curves
1. **Left Panel (50% width, full height) — 3D Reservoir + Chemical Volume + Source Box**:
   - **Volumetric Plume (`scene.visuals.Volume`)**: Attach a translucent VisPy `Volume` visual (`method='translucent'`, `clim=(0.0, 2000.0)`) scaled by `(elt_w / chem_w, elt_d / chem_d, elt_h / chem_h)` and axis-aligned so the $100^3$ voxel grid maps 1:1 onto the 3D reservoir bounding cage.
   - **Source Selector Wireframe (`scene.visuals.Box`)**: Render a 3D wireframe box (`color=None`, `edge_color=(0.2, 1.0, 0.4, 0.9)`) outlining the exact 3D bounds of the `c_source` injection zone (recreating `SNNgine3D`'s `source_visual` hull).
   - **3D Neurons**: Render the 200 reservoir neurons with dynamic membrane potential colors and white spike flashes inside the same 3D scene.
2. **Top-Right Panel (50% width, 50% height) — Radial Chemical Concentration Curves $C(r, t)$**:
   - Plot real-time concentration vs. time $C(r, t)$ across concentric spherical/cubic shells around the source boundary ($r = 0\text{ (source)}, 2, 5, 10, 18\text{ voxels}$), directly illustrating concentration building up around the source and the diffusion front arriving at progressively farther distances over time $t$.
3. **Bottom-Right Panel (50% width, 50% height) — Rolling Spike Raster & Voltage Traces**:
   - Display the synchronized neural firing / membrane potential activity alongside the chemical diffusion plot.

### Substep 3: Remote GPU Execution, Artifact Retrieval & Immediate Teardown
1. Provision an ephemeral GPU pod in `EU-RO-1` with network volume `qze81dpw7q` mounted at `/workspace`.
2. Sync `setups/runpod-chem-diffusion/` to `/workspace/snngineV4_agent_branches/setups/runpod-chem-diffusion/` and run:
   ```bash
   python setups/runpod-engine-smoke-test/exec_pod.py --host <POD_IP> --port <POD_PORT> cmd "bash /workspace/snngineV4_agent_branches/setups/runpod-chem-diffusion/runpod_chem_runner.sh generate --steps 1200 --stride 2 --fps 30 --resolution 1080p"
   ```
3. Download `simulation_chem_1080p_<ts>.mp4` and `.json` to `setups/runpod-chem-diffusion/output/`.
4. Immediately terminate the GPU pod via `delete-pod`, confirm `list-pods` returns `[]`, and document results in `setups/runpod-chem-diffusion/runpod-chem-diffusion-report.md`.

---

## Pass / Fail Verification Criteria

- **PASS**:
  1. `c_source` is localized to the target 3D sub-volume (default back-face test slices cleared) and $k_{\text{val}} \le 1/6$ preserves smooth, non-oscillatory diffusion.
  2. Active diffused voxel count ($C > 1.0$ outside the source box) and radial shell concentrations $C(r, t)$ increase monotonically over simulation time $t$.
  3. The 3D chemical plume, source wireframe box, 3D neurons, and radial concentration curves render cleanly and in spatial/temporal alignment in the output MP4.
  4. Output `.mp4` and `.json` remain gitignored, no files outside `setups/runpod-chem-diffusion/` (and index docs) are modified, and the GPU pod is terminated immediately.
- **FAIL**:
  1. Chemical concentration remains static or exhibits checkerboard instability ($k_{\text{val}} > 1/6$).
  2. Volume visual axes or scale do not align with the 3D source wireframe box and reservoir cage.
  3. Out-of-bounds CUDA memory access at `i == grid_h` / `j == grid_w` / `k == grid_d`.
  4. Any core file in `snngine_v4/` or sibling `setups/` task directory is modified, or any output artifact enters VCS.

---

## Follow-Up Sub-Task 1: Multi-Panel Composite View (2-Way 3D Left Column + 3-Way Time-Series Right Column)

### Objective
Extend [`generate_chem_diffusion_video.py`](file:///E:/dev/snngineV4_agent_branches/setups/runpod-chem-diffusion/generate_chem_diffusion_video.py) and [`runpod_chem_runner.sh`](file:///E:/dev/snngineV4_agent_branches/setups/runpod-chem-diffusion/runpod_chem_runner.sh) to support a synchronized **5-panel composite layout (2-way 3D left column + 3-way 2D time-series right column)** (`--layout 5way`, default `5way`, with `4way` accepted as an alias), incorporating both the dedicated **3D Neural Network Reservoir view** and the **Firing Scatter Plot (Spike Raster)** from [`setups/runpod-engine-smoke-test/generate_composite_video.py`](file:///E:/dev/snngineV4_agent_branches/setups/runpod-engine-smoke-test/generate_composite_video.py) alongside the 3D chemical diffusion views.

### Viewport Grid Layout ($6\text{ rows} \times 2\text{ columns}$, $\text{lcm}(2, 3) = 6$) & Synchronization
- **Left Column (`col=0`, 50% width — 2 Equal-Height 3D Views, 50% height each)**:
  1. **Top-Left (`row=0, col=0, row_span=3, col_span=1`, 50% width $\times$ 50% height): 3D Chemical Source & Volumetric Plume View (`3d_chemical_plume`)**:
     - Displays the 3D reservoir bounding cage, the localized 3D chemical source wireframe box (`[44, 56]^3`), and the translucent 3D volumetric chemical diffusion plume (`visuals.Volume` for `chemicals.C0`), providing an unobstructed view of volumetric concentration buildup and outward diffusion.
  2. **Bottom-Left (`row=3, col=0, row_span=3, col_span=1`, 50% width $\times$ 50% height): 3D Neural Network Reservoir View (`3d_neural_network`, from `runpod-engine-smoke-test`)**:
     - Displays the 3D reservoir bounding cage (`visuals.Box` with translucent faces `(0.2, 0.4, 0.6, 0.15)` and edge color `(0.3, 0.6, 0.9, 0.4)`) and the 200 3D reservoir neurons (`visuals.Markers`) colored dynamically by membrane potential $v(t)$ (`compute_neuron_colors`) with brilliant white spike flashes on firing events (`fired_mask = stride_fired | (v_current >= -30.0)`), completely unobscured by the volumetric plume.
     - **Synchronized Orbital Camera**: Shares the exact per-frame `TurntableCamera` `azimuth`, `elevation`, `center`, `fov`, and `distance` with Top-Left so that both 3D views rotate in lockstep for direct spatial comparison.
- **Right Column (`col=1`, 50% width — 3 Equal-Height 2D Time-Series Views, $33.3\%$ height each)**:
  3. **Top-Right (`row=0, col=1, row_span=2, col_span=1`, 50% width $\times$ 33.3% height): Radial Chemical Concentration Curves $C(r, t)$ (`radial_chemical_concentration_shells`)**:
     - Plots real-time mean chemical concentration $\bar{C}(d, t)$ across the 5 concentric Chebyshev distance shells ($d \in \{1, 3, 6, 12, 20\}$ voxels outside the source boundary) over the rolling time window.
  4. **Middle-Right (`row=2, col=1, row_span=2, col_span=1`, 50% width $\times$ 33.3% height): Firing Scatter Plot / Spike Raster (`spike_raster`, from `runpod-engine-smoke-test`)**:
     - Displays action potential firing events `(t, neuron_id)` across all 200 neurons over the synchronized rolling time window, color-coded by neuron group (`GROUP_COLORS`) with horizontal group divider lines and a right-edge time cursor.
  5. **Bottom-Right (`row=4, col=1, row_span=2, col_span=1`, 50% width $\times$ 33.3% height): Multi-Trace Membrane Potential Waveforms $v(t)$ (`voltage_waveforms`)**:
     - Plots synchronized rolling membrane potential waveforms $v(t)$ for the 6 representative neurons (focal stimulated, recurrent excitatory, and baseline).

### Artifact Naming & Verification Criteria
- Output files use the prefix `simulation_chem_5way_<res>_<YYYY-MM-DD_HH-MM-SS>.mp4` (and `.json`), stored in `setups/runpod-chem-diffusion/output/` (gitignored).
- JSON sidecar records `"layout": "5way"` and all five active viewport identifiers (`["3d_chemical_plume", "3d_neural_network", "radial_chemical_concentration_shells", "spike_raster", "voltage_waveforms"]`) in `"panels"`.
- Ephemeral GPU pod in `EU-RO-1` is terminated immediately via `delete-pod` after artifact retrieval, with `list-pods` verified empty (`[]`).



