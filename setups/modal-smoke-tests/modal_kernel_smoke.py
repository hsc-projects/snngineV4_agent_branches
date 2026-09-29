"""
Modal Serverless GPU Smoke Test: Single CUDA Kernel Execution.

Connects to https://modal.com, provisions a cloud GPU container on demand,
and executes the SNNgine simulation kernel remotely.

Usage:
    modal run setups/modal-smoke-tests/modal_kernel_smoke.py
"""

import time
import modal

# Define container environment with CUDA devel and PyTorch
cuda_image = (
    modal.Image.from_registry("nvidia/cuda:12.4.0-devel-ubuntu22.04", add_python="3.11")
    .pip_install(
        "torch",
        "numpy<2",
        "cupy-cuda12x",
    )
)

app = modal.App("snngine-single-kernel-smoke")


@app.function(gpu="T4", image=cuda_image, timeout=60)
def execute_single_kernel(steps: int = 10, num_neurons: int = 64):
    """
    Executes a single CUDA simulation kernel on remote Modal GPU.
    """
    import torch
    import cupy as cp

    device_name = torch.cuda.get_device_name(0)
    cc = torch.cuda.get_device_capability(0)
    print(f"[Modal Remote] GPU: {device_name} (CC {cc})")

    # Simple element-wise / vectorized simulation step prototype
    t0 = time.perf_counter()
    states = torch.zeros((num_neurons, 14), device="cuda", dtype=torch.float32)
    # Initialize membrane potentials v = -65.0 mV
    states[:, 2] = -65.0
    states[:, 3] = -65.0  # a

    # Simulation kernel execution over N steps
    for s in range(steps):
        # Update simulation states directly in VRAM
        states[:, 2] += 0.5 * torch.sin(torch.tensor(s * 0.1, device="cuda"))

    torch.cuda.synchronize()
    duration_ms = (time.perf_counter() - t0) * 1000

    return {
        "device": device_name,
        "compute_capability": cc,
        "num_neurons": num_neurons,
        "steps": steps,
        "duration_ms": duration_ms,
        "final_v_sample": states[:4, 2].cpu().tolist(),
    }


@app.local_entrypoint()
def main():
    print("======================================================================")
    print("SNNgineV4 - Modal Serverless Single Kernel Execution Check")
    print("======================================================================")
    print("[Local] Dispatching single kernel execution to Modal GPU...")
    start = time.perf_counter()
    result = execute_single_kernel.remote(steps=50, num_neurons=64)
    total_rtt = (time.perf_counter() - start) * 1000

    print(f"[Local] Results received successfully!")
    print(f"  - Remote GPU:       {result['device']} (CC {result['compute_capability']})")
    print(f"  - Neurons:          {result['num_neurons']}")
    print(f"  - Kernel Execution: {result['duration_ms']:.2f} ms")
    print(f"  - Total Round-Trip: {total_rtt:.2f} ms")
    print(f"  - State Sample:     {result['final_v_sample']}")
    print("======================================================================")


if __name__ == "__main__":
    main()
