# Task: Runpod Headless Engine Simulation Smoke Test

## Context and where this task fits

We have completed the horizontal mapping pass across all subpackages in [`agents/mapping/`](file:///E:/dev/snngineV4_agent_branches/agents/mapping/) and established the system-wide cross-subpackage orchestration documentation in [`module-interactions.md`](file:///E:/dev/snngineV4_agent_branches/agents/mapping/module-interactions.md).

Prior infrastructure work in [`setups/runpod-smoke-tests/`](file:///E:/dev/snngineV4_agent_branches/setups/runpod-smoke-tests/) verified low-level zero-copy CUDA/OpenGL VBO interoperability and offscreen EGL snapshotting on remote cloud GPUs.

This task extends that foundation to **the actual `snngine_v4` domain and simulation engine**. The objective is to verify that the full `snngine_v4` execution pipeline—declarative configuration, Double-Tree construction via `NetworkBuilder`, C++/CUDA simulation backend pointer compilation via `Simulation._make_simulator_backend`, and multi-step simulation stepping via `SNNgine.run_sim`—builds and executes successfully on a remote Runpod GPU instance without requiring an active X11 display, PySide6 GUI window, or physical monitor.

---

## Safety, boundaries, and financial discipline

### 1. Financial discipline & ephemeral GPU pod lifecycle
- **Explicit launch & prompt teardown**: GPU pods incur continuous hourly charges. A GPU pod for this task must be provisioned only after explicit maintainer authorization and must be terminated immediately once compilation and execution test assertions complete.
- **Network volume preservation**: The persistent network volume (`qze81dpw7q`, 20GB Standard) in `EU-RO-1` must remain preserved. Never delete, reformat, or recreate the volume.

### 2. Region and hardware constraints
- **Region pinning (`EU-RO-1`)**: Volume `qze81dpw7q` is physically pinned to data center `EU-RO-1`. Any pod provisioned for this task must be created in `EU-RO-1` to mount the workspace volume.
- **Target GPU**: NVIDIA RTX 2000 Ada (16GB VRAM, Compute Capability 8.9) or available Ada/Ampere equivalent in `EU-RO-1` (e.g. RTX 4000 Ada, RTX A4500).
- **CUDA Architecture**: When building C++/CUDA extensions with NVCC, target Ada Lovelace SM 89 (`-DCMAKE_CUDA_ARCHITECTURES=89`) or native device architecture.

### 3. Credential hygiene
- **No Runpod API keys inside the pod**: Runpod API credentials stay exclusively at the host orchestration layer (CLI/MCP). Never pass, store, or echo Runpod API keys into the pod environment or disk.

### 4. Working directory and file boundaries
- **Local working directory**: `snngineV4_agent_branches/` (or relative from repo root).
- **Deliverables directory**: All task specifications, execution logs, runners, and reports for this test must live strictly in `setups/runpod-engine-smoke-test/`.
- **Allowed scripts**: Pod-side automation scripts (`runpod_engine_test_runner.sh`, `test_headless_engine_sim.py`) are permitted to eliminate manual shell boilerplate and conserve context tokens.

---

## Low-Token & Low-Compute Agent Iteration Design

Because CUDA and C++ extension development can encounter repetitive compilation or kernel debugging iterations, the test harness is explicitly structured to minimize token overhead and cloud spend:

1. **Granular subcommands in `runpod_engine_test_runner.sh`**:
   - `env`: Validates hardware and PyTorch CUDA support in seconds without touching the build tree.
   - `build`: Isolated C++/CUDA compilation. Output is redirected to `logs/build_cuda.log`. On failure, only the top 15 actionable compiler errors (`error:`, `fatal error:`) are output to stdout, preventing 500-line NVCC template dumps from polluting agent context.
   - `test`: Executes `test_headless_engine_sim.py` with forwarded flags.
   - `all`: Runs the complete pipeline sequentially.

2. **Progressive testing stages in `test_headless_engine_sim.py`**:
   - `--stage contracts`: Verifies declarative configuration, `NetworkBuilder` element instantiation, and headless OpenGL buffer mock allocations without executing any simulation steps. Can run with `--mock-backend` on CPU hosts for zero compute spend.
   - `--stage 1step` (or `--quick`): Executes exactly 1 simulation step. Fails immediately on invalid memory pointers or kernel launch failures before running multi-step loops.
   - `--stage full`: Executes 100 simulation steps and verifies numerical bounds.

3. **Compact output & error isolation**:
   - `--compact`: Outputs a single summary line on success (`PASS [full]: 100 steps in 0.04s | v min=-65.2 max=28.1 | spikes=142`).
   - On exception: Produces a 3-line error summary indicating the root exception type, message, and file/line location. The full multiline stack trace is redirected to `logs/headless_engine_sim.log`.
   - Structured run metrics are written to `logs/headless_engine_sim_result.json`.

4. **Watchdog execution**:
   - Test execution is wrapped in a 60-second watchdog timeout (`timeout --preserve-status 60s`) to prevent hung simulation loops from burning continuous cloud spend.

---

## Phased execution plan

### Phase 1: Pod provisioning & environment validation
1. **Catalog & stock verification**:
   - Check available GPU stock in `EU-RO-1` for RTX 2000 Ada (or fallback Ada/Ampere GPU).
2. **Pod creation**:
   - Region: `EU-RO-1`.
   - Cloud tier: `SECURE` (enforced by network volume requirements; Community Cloud does not support volumes).
   - Volume: `qze81dpw7q` mounted at `/workspace`.
   - Exposed ports: `22` (SSH).
   - Base image: `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404` (verified in prior smoke test: Ubuntu 24.04 LTS, Python 3.12, CUDA 12.8, PyTorch 2.8.0).
3. **Host-to-Pod Code Transfer (from Windows Host)**:
   - Synchronize the test harness directory from the local machine to `/workspace`:
     ```powershell
     # From local Windows PowerShell (replace <pod_ssh_port> and <pod_ip> with active pod SSH details):
     scp -P <pod_ssh_port> -r setups\runpod-engine-smoke-test root@<pod_ip>:/workspace/snngineV4_agent_branches/setups/
     ```
   - *Note on remote volume structure*: If `/workspace` contains a nested `snngineV4_cloud/` root from prior tests, the runner script automatically detects either path (`/workspace/snngineV4_agent_branches` or `/workspace/snngineV4_cloud/snngineV4_agent_branches`).
4. **Environment validation & dependency bootstrap via SSH**:
   - Verify SSH connectivity.
   - Run `nvidia-smi` on the pod: confirm GPU identity, driver capability, and VRAM.
   - Confirm `/workspace` is mounted read-write (note: MFS volume rejects `chown`; use `rsync -rtv` without `-o -g`).
   - Run the automated bootstrap command to install Mesa/OpenGL headers and Python dependencies:
     ```bash
     bash /workspace/snngineV4_agent_branches/setups/runpod-engine-smoke-test/runpod_engine_test_runner.sh bootstrap
     ```
   - Confirm `/usr/local/cuda/bin` is in `PATH` so `nvcc` and CMake locate the CUDA toolkit.

---

### Phase 2: C++/CUDA simulation backend build
1. **Toolchain check**:
   - Verify `cmake` (>= 3.18), `gcc`/`g++` (12+), `nvcc` (CUDA 12.x), and Python 3.12 development headers.
2. **CMake configuration reference (Original vs. Proposed Task Staging)**:
   - **Original (`snngine_v4/nn/cuda_backend/CMakeLists.txt`)**: Preserved untouched in git. Contains known potential failure points:
     - Unconditional `testing_executable` target referencing non-existent `./tests/tests_main.cu` and `./tests/tests.cu`.
     - Hardcoded `PYTHON_EXECUTABLE` (`/usr/local/bin/python3.12`) and `PYTHON_LIBRARY` paths that fail on standard Ubuntu/Runpod images where Python is at `/usr/bin/python3`.
     - Default `CMAKE_CUDA_ARCHITECTURES 61` (Pascal 2016).
   - **Proposed (`setups/runpod-engine-smoke-test/CMakeLists.txt`)**: Staged in this task directory for testing and verification without mutating the main tree:
     - Guards `testing_executable` with `if(EXISTS ...)` so missing tests do not abort the build.
     - Uses dynamic `find_program` and `find_package(Python 3.10 COMPONENTS Interpreter Development REQUIRED)` for robust environment discovery.
     - Defaults to SM 89 (Ada Lovelace) with CLI override support.
     - Explicitly links `cusparse` in `target_link_libraries`.
3. **Compilation**:
   - Execute the runner:
     ```bash
     bash /workspace/snngineV4_agent_branches/setups/runpod-engine-smoke-test/runpod_engine_test_runner.sh build
     ```
   - The runner script attempts compilation with the original `CMakeLists.txt` first. If CMake fails on missing `./tests/` sources or Python paths, it automatically swaps in `setups/runpod-engine-smoke-test/CMakeLists.txt` for the build, and **immediately restores the original** file upon completion so git remains clean.
4. **Module import assertion**:
   - Confirm built shared libraries (`snn_simulation_gpu`, `snn_utils`, `snn_construction_gpu`) import cleanly into Python:
     ```bash
     python3 -c "from snngine_v4.nn.cuda_backend import snn_simulation_gpu, snn_utils; print('Backend loaded successfully')"
     ```

---

### Phase 3: Standalone headless engine simulation execution
1. **Fast smoke execution**:
   - Run the 1-step quick check first:
     ```bash
     bash /workspace/snngineV4_agent_branches/setups/runpod-engine-smoke-test/runpod_engine_test_runner.sh test --quick
     ```
2. **Full simulation stepping**:
   - Run the full 100-step simulation:
     ```bash
     bash /workspace/snngineV4_agent_branches/setups/runpod-engine-smoke-test/runpod_engine_test_runner.sh test --stage full --steps 100 --compact
     ```
3. **Verification assertions in `test_headless_engine_sim.py`**:
   - **Double-Tree construction**: `NetworkBuilder` instantiates `SpatialNetworkConfig`, generating `SpatialNetwork`, `NetworkReservoir`, `FiniteGrid`, `NeuronState`, `Synapses`, and `ChemicalConcentrationVolume`.
   - **Backend pointer resolution**: `Simulation._make_simulator_backend()` resolves and passes ~45 contiguous device pointers into `snn_simulation_gpu.SnnSimulation`.
   - **Multi-step execution**: Executes 100 simulation steps via `sim.update(b_stdp=False, verbose=False)`.
   - **Numerical sanity checks**:
     - Membrane potentials ($v$) in `NeuronState.N_props.gpu_values[2, :]` evolve dynamically away from initial conditions.
     - Spiking array `fired` registers valid non-zero events.
     - Ring buffer write/read heads advance consistently without CUDA memory faults or NaN/Inf explosions.
     - Average step duration is measured and reported in milliseconds.

---

### Phase 4: Teardown & reporting
1. **Artifact collection**:
   - Record execution logs and performance metrics into `setups/runpod-engine-smoke-test/runpod-engine-smoke-test-report.md`.
2. **Pod termination**:
   - Immediately terminate the GPU pod via Runpod CLI/MCP.
   - Confirm pod status is `TERMINATED` and no active hourly compute billing remains.

---

## Pass/Fail criteria

- **PASS**:
  1. CUDA backend compiles cleanly without errors.
  2. `test_headless_engine_sim.py` executes 100 steps headlessly with exit code `0`.
  3. Membrane potentials and spike events are non-trivial and mathematically valid.
  4. GPU pod is terminated cleanly.
- **FAIL**:
  1. Compilation fails due to missing toolkit headers or incompatible CUDA architecture flags.
  2. Execution crashes due to missing X11/Qt display dependencies.
  3. CUDA kernel panics (e.g. invalid memory access or launch configuration error).
  4. Pod remains active and unmonitored after execution.
