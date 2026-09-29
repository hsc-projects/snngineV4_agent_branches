# Task: Modal Serverless GPU Single Kernel Execution Smoke Test

## Objective & Scope

Evaluate **[Modal](https://modal.com)** as a serverless GPU execution backend for **SNNgineV4** simulation kernels, specifically targeting **single kernel execution** (`single kernel exec`).

The goal is to determine the feasibility, latency, developer ergonomics, and cost structure of dispatching individual CUDA/PyTorch simulation kernels on-demand to Modal's serverless GPU infrastructure without requiring maintainers to provision, manage, or keep persistent cloud GPU instances (such as RunPod pods) running.

---

## Architectural Context: Single Kernel Exec on Serverless GPU

### 1. The Core SNNgine Simulation Step
In SNNgineV4, neural simulation can be executed in discrete iterations (time steps):
- **Input**: Neuron state vectors (membrane potentials `v`, recovery variables `u`, synaptic inputs `i`, parameters `a, b, c, d`, coordinates `pt`).
- **Compute**: Execution of the Izhikevich simulation kernel (`update_N_state_kernel`) or custom PyTorch tensor updates.
- **Output**: Mutated neuron state vectors, spike events, and updated 3D coordinate representations.

### 2. The Serverless Execution Paradigm
Instead of keeping a dedicated workstation GPU or remote RunPod instance active 24/7, Modal enables:
- **Code-defined serverless containers** via `modal.Image`.
- **Function decorators** (`@app.function(gpu="T4")` / `gpu="L4"` / `gpu="A100"` / `gpu="A10G"`).
- **Remote on-demand execution**: The local Python code calls `remote_simulate.remote(states)` or `.call()`, passing state tensors into Modal's cloud GPU, executing the kernel in VRAM, and returning the results.
- **Per-second billing with scale-to-zero**: Zero idle cost when no simulation steps are running.

---

## Platform & Technical Requirements

### 1. Modal Container Image Specification
Custom CUDA kernel execution requires the CUDA Toolkit (including `nvcc` and CUDA headers) inside the remote container:
```python
import modal

cuda_image = (
    modal.Image.from_registry("nvidia/cuda:12.4.0-devel-ubuntu22.04", add_python="3.11")
    .pip_install(
        "torch",
        "numba",
        "numpy<2",
        "cupy-cuda12x",
        "pytools",
    )
)

app = modal.App("snngine-kernel-exec")
```

### 2. Single Kernel Execution Paradigms to Evaluate

1. **Paradigm A: Python CUDA JIT (CuPy / Numba CUDA)**
   - Element-wise or custom kernel defined directly in Python.
   - Ideal for low-friction single kernel prototyping.
   - Example:
     ```python
     @app.function(gpu="T4", image=cuda_image)
     def exec_numba_kernel(neuron_states: list) -> list:
         import numba.cuda as ncuda
         # Execute CUDA kernel on remote GPU
         ...
     ```

2. **Paradigm B: Hand-Written CUDA Kernel (C++ / NVCC / PyCUDA)**
   - Compiling and executing the genuine `update_N_state_kernel` C++ CUDA source from `sim_demo_utils.py`.
   - Requires compilation either during image build (`image.run_commands(...)`) or JIT via `pycuda.compiler.SourceModule` / `cupy.RawKernel`.

3. **Paradigm C: PyTorch Vectorized GPU Tensor Operation**
   - High-throughput vectorized tensor simulation executed via PyTorch CUDA on Modal GPUs.

---

## Phased Execution Plan

### Phase 0: CLI Setup & Authentication
1. Install Modal CLI locally:
   ```bash
   pip install modal
   ```
2. Verify authentication and token status via `modal token show` or `modal setup`.
3. Check quota, tier, and available GPU catalog (T4, L4, A10G, A100, H100).

### Phase 1: Minimal Serverless GPU Capability Smoke Test
1. Create a minimal Modal test script [`modal_kernel_smoke.py`](file:///home/htm/snngine/snngineV4_cloud/snngineV4_agent_branches/setups/modal-smoke-tests/modal_kernel_smoke.py).
2. Remote function to verify:
   - Remote CUDA initialization (`torch.cuda.is_available()`).
   - Device name, compute capability, VRAM size.
   - Basic tensor allocation in remote VRAM.
3. Execute remotely:
   ```bash
   modal run setups/modal-smoke-tests/modal_kernel_smoke.py
   ```

### Phase 2: Single Kernel Execution Prototype (Izhikevich Simulation)
1. Implement the SNNgine `update_N_state` kernel as a remote Modal function:
   - Accept initial 32/64 neuron state vectors from the local host.
   - Allocate VRAM buffer on Modal GPU.
   - Execute kernel over $N$ simulation steps.
   - Transfer updated states back to local host.
2. Verify numerical correctness against local workstation baseline.

### Phase 3: Latency & Cost Profiling
1. **Cold Start Latency**: Time to spin up container, pull image, attach GPU, and execute first kernel.
2. **Warm Execution Latency**: Overhead of Modal RPC dispatch vs actual CUDA kernel execution time.
3. **Data Transfer Bottleneck**: Network round-trip time for passing state arrays across WAN vs running kernels in batch.
4. **Cost Analysis**: Compare per-call execution cost on Modal vs hourly cost on RunPod / local workstation.

### Phase 4: Architectural Fit Analysis for SNNgine
Evaluate whether serverless single-kernel execution fits SNNgine's real-time visualization:
- Does SNNgine require persistent VRAM (stateful 60 FPS zero-copy loop)?
- Can Modal support persistent stateful streaming via WebSockets / WebRTC, or is it better suited for offline batch parameter search / training?
- Document recommendations in [`setups/modal-smoke-tests/modal-smoke-test-report.md`](file:///home/htm/snngine/snngineV4_cloud/snngineV4_agent_branches/setups/modal-smoke-tests/modal-smoke-test-report.md).

---

## Deliverables

- `setups/modal-smoke-tests/modal-smoke-test-task.md` — this specification.
- `setups/modal-smoke-tests/modal_kernel_smoke.py` — prototype script for remote kernel dispatch.
- `setups/modal-smoke-tests/modal-smoke-test-report.md` — empirical results, latency benchmarks, and architectural evaluation.
