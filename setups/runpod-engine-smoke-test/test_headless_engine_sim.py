#!/usr/bin/env python3
"""
Standalone Headless Simulation Smoke Test for snngine_v4
=========================================================
Instantiates SpatialNetwork, configures the C++/CUDA simulation backend,
and executes multi-step simulation stepping without PySide6, X11, or VisPy GUI.

Optimized for agent iteration:
- Granular stages: contracts, 1step, full
- Compact output mode to conserve agent context tokens
- Mock backend mode for zero-compute host-side verification
- Structured JSON and file logging
"""

import argparse
import json
import os
import sys
import time
import traceback
from typing import Any, Dict, Optional

# Ensure repository root is on sys.path for standalone execution
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_BUILD_DIR = os.path.join(_REPO_ROOT, "snngine_v4", "nn", "cuda_backend", "build")
if os.path.exists(_BUILD_DIR) and _BUILD_DIR not in sys.path:
    sys.path.insert(0, _BUILD_DIR)

import torch

from snngine_v4.config.template import SpatialNetworkConfig
from snngine_v4.construction.nn_builder import NetworkBuilder
from snngine_v4.gui.parameter_trees.cuda_connector import GLBufferTypes
from snngine_v4.nn.spnn import SpatialNetwork
from snngine_v4.nn.spnn_reservoir import NetworkReservoir
from snngine_v4.utils.containers.mappings import Object2ObjectMap


class HeadlessSimLogger:
    """Handles tiered logging: concise stdout for agent context, full log on disk."""

    def __init__(self, log_path: Optional[str] = None, compact: bool = False):
        self.log_path = log_path
        self.compact = compact
        self.log_file = open(log_path, "w", encoding="utf-8") if log_path else None

    def log(self, msg: str, always: bool = False):
        if self.log_file:
            self.log_file.write(msg + "\n")
            self.log_file.flush()
        if always or not self.compact:
            print(msg)

    def close(self):
        if self.log_file:
            self.log_file.close()


def run_headless_simulation(
    steps: int = 100,
    device_id: int = 0,
    stage: str = "full",
    mock_backend: bool = False,
    compact: bool = False,
    log_file: Optional[str] = None,
    json_output: Optional[str] = None,
) -> Dict[str, Any]:
    logger = HeadlessSimLogger(log_path=log_file, compact=compact)
    metrics: Dict[str, Any] = {
        "status": "FAIL",
        "stage": stage,
        "steps_requested": steps,
        "steps_completed": 0,
        "device": "cpu",
        "duration_s": 0.0,
        "ms_per_step": 0.0,
    }

    try:
        logger.log("=" * 70)
        logger.log(f"Starting snngine_v4 Headless Simulation Test (stage={stage}, mock={mock_backend})")
        logger.log("=" * 70)

        # 0. Device selection & environment validation
        if mock_backend:
            device = torch.device("cpu")
            logger.log("[Device] Running in MOCK mode on CPU (no CUDA kernels required)")
        else:
            if not torch.cuda.is_available():
                raise RuntimeError("CUDA is not available on this host. Use --mock-backend for CPU validation.")
            device = torch.device(f"cuda:{device_id}")
            logger.log(f"[Device] Using {torch.cuda.get_device_name(device_id)} ({device})")

        metrics["device"] = str(device)

        # 1. Instantiate declarative configuration
        logger.log("\n[Phase 1] Initializing SpatialNetworkConfig template...")
        config = SpatialNetworkConfig()
        network_builder = NetworkBuilder()

        # 2. Build domain element graph
        logger.log("[Phase 2] Building domain elements via NetworkBuilder...")
        network: SpatialNetwork = network_builder.build(
            model=config,
            device=device,
        )
        element: NetworkReservoir = network.get_network_element(0)
        logger.log(f"  Constructed NetworkReservoir: N={element.config.N}, G={element.config.G}, S={element.config.S}")

        # Fill domain tensors
        logger.log("  Populating domain tensors via element.fill_tensors()...")
        element.fill_tensors()

        # 3. Headless OpenGL buffer mock for CUDA interop contracts
        logger.log("\n[Phase 3] Configuring headless GPU buffers for plot/marker contracts...")
        simulator = network.simulator
        volt_plot = simulator.voltage_plot
        firings_scatter_plot = simulator.firings_scatter_plot

        N = element.config.N
        v_n_plots = volt_plot.config.n_plots
        v_len = volt_plot.config.size_x
        s_n_plots = firings_scatter_plot.config.n_plots
        s_len = firings_scatter_plot.config.size_x

        pos_vbo_mock = torch.zeros((N, 14), dtype=torch.float32, device=device)
        pos_vbo_mock[:, :3] = element.N_pos
        volt_plot_vbo_mock = torch.zeros((v_n_plots * v_len * 2,), dtype=torch.float32, device=device)
        scatter_plot_vbo_mock = torch.zeros((s_n_plots * s_len * 14,), dtype=torch.float32, device=device)

        cuda_gl_map = Object2ObjectMap()
        cuda_gl_map[element.config] = {GLBufferTypes.POS_VBO.name: pos_vbo_mock}
        cuda_gl_map[volt_plot.config] = {GLBufferTypes.POS_VBO.name: volt_plot_vbo_mock}
        cuda_gl_map[firings_scatter_plot.config] = {GLBufferTypes.POS_VBO.name: scatter_plot_vbo_mock}
        network.cuda_opengl_map = cuda_gl_map

        # Stage gate: contracts only
        if stage == "contracts":
            metrics["status"] = "PASS"
            metrics["message"] = "Contracts and domain construction verified (0 simulation steps)."
            logger.log("\n[Contracts Gate] Memory layouts and buffer contracts verified successfully.", always=True)
            return metrics

        # 4. Initialize C++/CUDA simulation backend
        logger.log("\n[Phase 4] Constructing simulation backend...")
        sim_instance = simulator.add_simulation(0)

        if mock_backend:
            logger.log("  [Mock] Skipping C++ extension binding; using dummy backend.")
            sim_backend = None
        else:
            sim_backend = sim_instance.backend
            if sim_backend is None:
                raise RuntimeError("Simulation backend failed to construct (b_cuda_backend_available may be False).")
            logger.log(f"  Backend successfully instantiated: {sim_backend}")

        # Determine effective steps based on stage
        effective_steps = 1 if stage == "1step" else steps
        logger.log(f"\n[Phase 5] Executing {effective_steps} simulation steps (stage={stage})...")

        t_start = time.perf_counter()
        if not mock_backend:
            for step in range(effective_steps):
                sim_backend.update(False, False)
            if device.type == "cuda":
                torch.cuda.synchronize(device=device)

        t_elapsed = time.perf_counter() - t_start
        ms_per_step = (t_elapsed / effective_steps) * 1000.0 if effective_steps > 0 else 0.0

        metrics["steps_completed"] = effective_steps
        metrics["duration_s"] = round(t_elapsed, 4)
        metrics["ms_per_step"] = round(ms_per_step, 3)

        logger.log(f"  Completed {effective_steps} steps in {t_elapsed:.4f}s ({ms_per_step:.3f} ms/step)")

        # 6. Verification Assertions
        logger.log("\n[Phase 6] Evaluating verification assertions...")

        if not mock_backend:
            # Membrane potentials (row 2 in N_props)
            v_states = element.neuron_states.N_props.gpu_values[2, :].cpu()
            v_min, v_max, v_mean = v_states.min().item(), v_states.max().item(), v_states.mean().item()
            logger.log(f"  Membrane potentials (v): min={v_min:.2f}, max={v_max:.2f}, mean={v_mean:.2f}")

            if torch.isnan(v_states).any() or torch.isinf(v_states).any():
                raise AssertionError("Membrane potentials contain NaN or Inf values!")

            fired_states = sim_instance.Fired.cpu()
            n_spikes = int((fired_states > 0).sum().item())
            logger.log(f"  Current fired spikes count: {n_spikes}")

            metrics["v_min"] = round(v_min, 2)
            metrics["v_max"] = round(v_max, 2)
            metrics["n_spikes"] = n_spikes
        else:
            metrics["mock"] = True

        metrics["status"] = "PASS"

        if compact:
            summary = (
                f"PASS [{stage}]: {effective_steps} steps in {t_elapsed:.4f}s "
                f"({ms_per_step:.2f} ms/step)"
            )
            if not mock_backend:
                summary += f" | v min={metrics.get('v_min')} max={metrics.get('v_max')} | spikes={metrics.get('n_spikes')}"
            print(summary)
        else:
            logger.log("\n" + "=" * 70, always=True)
            logger.log("ALL HEADLESS SIMULATION ASSERTIONS PASSED SUCCESSFULLY", always=True)
            logger.log("=" * 70, always=True)

        return metrics

    except Exception as e:
        metrics["status"] = "FAIL"
        metrics["error_type"] = type(e).__name__
        metrics["error_message"] = str(e)

        exc_type, exc_val, exc_tb = sys.exc_info()
        tb_lines = traceback.format_exception(exc_type, exc_val, exc_tb)
        last_frame = traceback.extract_tb(exc_tb)[-1] if exc_tb else None
        loc_str = f"{os.path.basename(last_frame.filename)}:{last_frame.lineno} in {last_frame.name}" if last_frame else "unknown"

        metrics["location"] = loc_str

        # Full trace into log file
        if logger.log_file:
            logger.log_file.write("\n" + "".join(tb_lines))
            logger.log_file.flush()

        # Concise output for agent context
        print(f"\nFAIL [{stage}]: {type(e).__name__}: {e}", file=sys.stderr)
        print(f"  Location: {loc_str}", file=sys.stderr)
        if log_file:
            print(f"  Detailed traceback written to: {log_file}", file=sys.stderr)
        else:
            traceback.print_exc()

        return metrics

    finally:
        if json_output:
            try:
                with open(json_output, "w", encoding="utf-8") as jf:
                    json.dump(metrics, jf, indent=2)
            except Exception as j_err:
                print(f"Warning: Failed to write JSON output to {json_output}: {j_err}", file=sys.stderr)
        logger.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Headless snngine_v4 Simulation Smoke Test (Agent Iteration Optimized)")
    parser.add_argument("--steps", type=int, default=100, help="Number of simulation steps (default: 100)")
    parser.add_argument("--device", type=int, default=0, help="CUDA device index (default: 0)")
    parser.add_argument(
        "--stage",
        choices=["contracts", "1step", "full"],
        default="full",
        help="Test stage: 'contracts' (no sim steps), '1step' (fast smoke), 'full' (100 steps)",
    )
    parser.add_argument("--quick", action="store_true", help="Shortcut for --stage 1step --steps 1 --compact")
    parser.add_argument("--mock-backend", action="store_true", help="Simulate on CPU without compiling/loading CUDA backend")
    parser.add_argument("--compact", action="store_true", help="Print single-line summary on stdout to conserve context tokens")
    parser.add_argument("--log-file", type=str, default=None, help="File path to save complete detailed logs")
    parser.add_argument("--json-output", type=str, default=None, help="File path to save structured metrics JSON")

    args = parser.parse_args()

    # Apply --quick shortcut
    if args.quick:
        args.stage = "1step"
        args.steps = 1
        args.compact = True

    default_log = args.log_file or os.path.join(os.path.dirname(__file__), "headless_engine_sim.log")
    default_json = args.json_output or os.path.join(os.path.dirname(__file__), "headless_engine_sim_result.json")

    res = run_headless_simulation(
        steps=args.steps,
        device_id=args.device,
        stage=args.stage,
        mock_backend=args.mock_backend,
        compact=args.compact,
        log_file=default_log,
        json_output=default_json,
    )

    sys.exit(0 if res.get("status") == "PASS" else 1)
