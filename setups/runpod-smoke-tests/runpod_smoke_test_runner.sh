#!/usr/bin/env bash
# Pod-side smoke test execution runner for RunPod GPU deployments.
# Executes either automated headless zero-copy interop assertions (--headless)
# or the containerized native EGL web bridge server (--web) on port 6080.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUPS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
GPU_SMOKE_DIR="${SETUPS_DIR}/gpu-smoke-tests"
WORKSPACE_ROOT="$(cd "${SETUPS_DIR}/.." && pwd)"
PARENT_DIR="$(cd "${WORKSPACE_ROOT}/.." && pwd)"

SNAPSHOT_PATH="${SCRIPT_DIR}/rendered_frame.png"
MODE="headless"
PORT="6080"
HOST="0.0.0.0"

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Modes:
  --headless        Run automated headless zero-copy interop assertions and offscreen EGL snapshot (default)
  --web             Run native EGL web bridge server on port ${PORT} for remote browser verification
  --check           Inspect GPU, driver, and Python environment without running tests

Options:
  --port <port>     Web server port (default: 6080)
  --host <host>     Web server host address (default: 0.0.0.0)
  --snapshot <path> Output path for offscreen EGL snapshot
  -h, --help        Show this help message
EOF
    exit 0
}

# Parse CLI options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --headless)
            MODE="headless"
            shift
            ;;
        --web)
            MODE="web"
            shift
            ;;
        --check)
            MODE="check"
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --snapshot)
            SNAPSHOT_PATH="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage
            ;;
    esac
done

echo "======================================================================"
echo "SNNgineV4 - RunPod GPU Smoke Test Runner"
echo "======================================================================"
echo "Execution time: $(date -u '+%Y-%m-%d %H:%M:%SZ')"
echo "Host / Pod:     $(hostname)"
echo "Directory:      ${SCRIPT_DIR}"
echo "Mode:           ${MODE}"
echo "======================================================================"

# Step 1: Inspect GPU and driver environment
echo "[Step 1/3] Inspecting GPU and driver environment..."
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name,driver_version,memory.total,compute_cap --format=csv,noheader || true
else
    echo "ERROR: nvidia-smi not found. This runner requires an NVIDIA GPU pod." >&2
    exit 1
fi

# Step 2: Resolve Python executable and environment
echo "[Step 2/3] Resolving Python environment..."
if [[ -f "/opt/venv/bin/python3" ]]; then
    PYTHON_BIN="/opt/venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
else
    echo "ERROR: No suitable python3 executable found." >&2
    exit 1
fi
echo "Using Python: ${PYTHON_BIN} ($("${PYTHON_BIN}" --version 2>&1))"

# Configure search paths and EGL platform
SNNGINE_BRANCHES="${WORKSPACE_ROOT}"
SNNGINE3D_BRANCHES="${PARENT_DIR}/SNNgine3D_agent_branches"

export PATH="/usr/local/cuda/bin:${PATH:-}"
export LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}"
export PYTHONPATH="${SNNGINE_BRANCHES}:${SNNGINE3D_BRANCHES}/notebooks/simulation_demo:${PYTHONPATH:-}"
export PYOPENGL_PLATFORM="egl"

# Step 3: Execute chosen mode
echo "[Step 3/3] Executing mode: ${MODE}..."
case "${MODE}" in
    check)
        echo "Performing environment diagnostics..."
        "${PYTHON_BIN}" -c "
import sys, torch
print(f'Python: {sys.version}')
print(f'PyTorch: {torch.__version__}, CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'Device 0: {torch.cuda.get_device_name(0)}')
try:
    import pycuda.driver as cuda
    cuda.init()
    dev = cuda.Device(0)
    print(f'PyCUDA: device={dev.name()}, compute_cap={dev.compute_capability()}')
except Exception as e:
    print(f'PyCUDA check warning/failure: {e}')
try:
    import vispy
    print(f'VisPy version: {vispy.__version__}')
except Exception as e:
    print(f'VisPy check warning/failure: {e}')
"
        echo "Environment diagnostic check completed."
        ;;

    headless)
        AUTO_SCRIPT="${GPU_SMOKE_DIR}/interop_smoke_test_auto.py"
        if [[ ! -f "${AUTO_SCRIPT}" ]]; then
            echo "ERROR: Automated test script not found at ${AUTO_SCRIPT}" >&2
            exit 1
        fi
        echo "Running ${AUTO_SCRIPT} --snapshot ${SNAPSHOT_PATH}..."
        "${PYTHON_BIN}" "${AUTO_SCRIPT}" --snapshot "${SNAPSHOT_PATH}"
        EXIT_CODE=$?
        echo "======================================================================"
        if [[ ${EXIT_CODE} -eq 0 ]]; then
            echo "✓ ALL RUNPOD HEADLESS INTEROP ASSERTIONS PASSED (EXIT CODE 0)"
            if [[ -f "${SNAPSHOT_PATH}" ]]; then
                echo "✓ Offscreen EGL snapshot generated at: ${SNAPSHOT_PATH}"
            fi
        else
            echo "✗ HEADLESS SMOKE TEST FAILED WITH EXIT CODE: ${EXIT_CODE}"
        fi
        echo "======================================================================"
        exit ${EXIT_CODE}
        ;;

    web)
        WEB_SCRIPT="${GPU_SMOKE_DIR}/interop_smoke_test_web_gui.py"
        if [[ ! -f "${WEB_SCRIPT}" ]]; then
            echo "ERROR: Web bridge script not found at ${WEB_SCRIPT}" >&2
            exit 1
        fi
        echo "Starting native EGL web bridge on ${HOST}:${PORT}..."
        echo "Browser access: http://${HOST}:${PORT} (or via RunPod HTTP proxy)"
        exec "${PYTHON_BIN}" "${WEB_SCRIPT}" --host "${HOST}" --port "${PORT}"
        ;;
esac
