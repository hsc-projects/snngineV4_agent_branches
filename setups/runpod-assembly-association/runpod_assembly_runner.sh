#!/usr/bin/env bash
# ==============================================================================
# Pod-side runner for the assembly association task (snngine_v4).
# Task specification: setups/runpod-assembly-association/runpod-assembly-association-task.md
#
# Usage: runpod_assembly_runner.sh run <params.json> [assoc_queue.py arguments...]
#        runpod_assembly_runner.sh env
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [[ ! -d "$REPO_ROOT/snngine_v4" ]]; then
    for c in /workspace/snngineV4_cloud/snngineV4_agent_branches /workspace/snngineV4_agent_branches; do
        if [[ -d "$c/snngine_v4" ]]; then REPO_ROOT="$c"; break; fi
    done
fi

OUTPUT_DIR="${OUTPUT_DIR:-/workspace/output/assembly-association}"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$OUTPUT_DIR" "$LOG_DIR"

info() { echo -e "\033[0;34m[*] $*\033[0m"; }
pass() { echo -e "\033[0;32m[+] $*\033[0m"; }
fail() { echo -e "\033[0;31m[-] $*\033[0m" >&2; exit 1; }

T_START=$(date +%s)
source /workspace/venv/bin/activate
export PATH="/usr/local/cuda/bin:${PATH:-}"
export LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}"
export PYOPENGL_PLATFORM="egl"
export QT_QPA_PLATFORM="offscreen"
export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"
cd /workspace  # never run Python from a source tree (PyCUDA import shadowing)

CMD="${1:-run}"
shift || true

ensure_backend() {
    # The backend build is architecture-specific. Builds are kept per architecture on the
    # volume (build_sm<arch>) so switching GPU families back and forth needs no rebuild.
    local backend="$REPO_ROOT/snngine_v4/nn/cuda_backend"
    local arch cached
    arch=$(python3 -c "import torch; c = torch.cuda.get_device_capability(0); print(f'{c[0]}{c[1]}')")
    cached=$(grep -oP 'CMAKE_CUDA_ARCHITECTURES:\w+=\K\w+' "$backend/build/CMakeCache.txt" 2>/dev/null || echo none)
    info "GPU architecture SM $arch, backend build on volume: SM $cached"
    if [[ "$cached" != "$arch" ]]; then
        if [[ -d "$backend/build" ]]; then
            rm -rf "$backend/build_sm$cached"
            mv "$backend/build" "$backend/build_sm$cached"
            info "Parked build for SM $cached in build_sm$cached"
        fi
        if [[ -d "$backend/build_sm$arch" ]]; then
            mv "$backend/build_sm$arch" "$backend/build"
            pass "Restored cached build for SM $arch"
        else
            info "No cached build for SM $arch: building through the smoke-test runner"
            bash "$REPO_ROOT/setups/runpod-engine-smoke-test/runpod_engine_test_runner.sh" build
        fi
    fi
    python3 -c "from snngine_v4.nn.cuda_backend import snn_simulation_gpu" || fail "backend import failed"
    pass "Backend importable for SM $arch"
}

ensure_python_packages() {
    python3 -c "import imageio_ffmpeg" 2>/dev/null || { info "Installing imageio-ffmpeg into the venv"; pip install -q imageio-ffmpeg; }
    python3 -c "import PIL" 2>/dev/null || { info "Installing Pillow into the venv"; pip install -q pillow; }
    if ! python3 -c "import vispy.scene" 2>/dev/null; then
        info "vispy.scene not importable: installing Mesa/EGL packages"
        apt-get update -qq && apt-get install -y -qq libgl1-mesa-dev libegl1-mesa-dev libgles2-mesa-dev libglvnd-dev
    fi
}

case "$CMD" in
    env)
        nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
        ensure_backend
        ensure_python_packages
        ;;
    run)
        PARAMS="${1:?params file required}"
        shift || true
        nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
        ensure_backend
        ensure_python_packages
        T_SETUP=$(date +%s)
        info "Setup took $((T_SETUP - T_START)) s"
        python3 "$SCRIPT_DIR/assoc_queue.py" --params "$PARAMS" --output-dir "$OUTPUT_DIR" \
            --setup-seconds "$((T_SETUP - T_START))" "$@" 2>&1 | tee "$LOG_DIR/assoc_queue_$(date +%Y-%m-%d_%H-%M-%S).log"
        ;;
    start)
        # detached run: survives a dropped SSH connection; the host waits for the marker
        # $OUTPUT_DIR/<params stem>.finished (exit code inside) with wait_pod_session.py
        PARAMS="${1:?params file required}"
        shift || true
        MARKER="$OUTPUT_DIR/$(basename "$PARAMS" .json).finished"
        rm -f "$MARKER"
        nohup bash -c "PYTHONUNBUFFERED=1 bash '$SCRIPT_DIR/runpod_assembly_runner.sh' run '$PARAMS' $*; echo \$? > '$MARKER'" \
            > "$LOG_DIR/session_$(basename "$PARAMS" .json).log" 2>&1 < /dev/null &
        disown
        pass "Started detached session (marker: $MARKER)"
        ;;
    *)
        echo "Usage: $0 {run <params.json> [args...]|start <params.json> [args...]|env}"
        exit 1
        ;;
esac
