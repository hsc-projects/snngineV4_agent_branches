#!/usr/bin/env bash
# ==============================================================================
# Runpod Engine Headless Simulation Smoke Test Runner
# ==============================================================================
# Designed for low-token, low-compute agent iteration:
# - Granular subcommands: bootstrap, env, build, test, all
# - Dynamic repo root detection across volume path variants
# - Automatic staged CMake fallback with zero-modification git restoration
# - NVCC compiler error pruning: dumps to build_cuda.log, prints top 15 actionable lines
# - Watchdog execution: prevents hung CUDA loops from racking up cloud spend
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Auto-detect whether inside /workspace/snngineV4_cloud/snngineV4_agent_branches or /workspace/snngineV4_agent_branches
if [[ ! -d "$REPO_ROOT/snngine_v4" ]]; then
    if [[ -d "/workspace/snngineV4_cloud/snngineV4_agent_branches/snngine_v4" ]]; then
        REPO_ROOT="/workspace/snngineV4_cloud/snngineV4_agent_branches"
    elif [[ -d "/workspace/snngineV4_agent_branches/snngine_v4" ]]; then
        REPO_ROOT="/workspace/snngineV4_agent_branches"
    fi
fi

LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

export PATH="/usr/local/cuda/bin:${PATH:-}"
export LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}"
export PYOPENGL_PLATFORM="egl"
export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"

CMD="${1:-all}"
shift || true

# Helper for formatted status
info() { echo -e "\033[1;34m[*] $*\033[0m"; }
pass() { echo -e "\033[1;32m[+] $*\033[0m"; }
fail() { echo -e "\033[1;31m[-] $*\033[0m" >&2; }

run_bootstrap() {
    info "Bootstrapping pod environment dependencies..."
    # 1. System OpenGL/EGL and build packages if missing
    if command -v apt-get &> /dev/null; then
        info "Installing Mesa and EGL development headers..."
        apt-get update && apt-get install -y --no-install-recommends \
            libgl1-mesa-dev libegl1-mesa-dev libgles2-mesa-dev libglvnd-dev cmake ninja-build || true
    fi
    # 2. Python dependencies for snngine_v4 headless execution
    info "Installing Python dependencies via pip..."
    pip install --break-system-packages --no-cache-dir \
        "pydantic>=2.9" "numpydantic" "pydantic-settings" "scipy" "pandas" || true
    pass "Bootstrap completed successfully."
}

run_env_check() {
    info "Validating Environment & GPU hardware..."
    if ! command -v nvidia-smi &> /dev/null; then
        fail "nvidia-smi not found. Non-GPU host detected."
        return 1
    fi
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader

    python3 -c "
import torch
print(f'PyTorch: {torch.__version__} | CUDA Available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'Device: {torch.cuda.get_device_name(0)} (SM {torch.cuda.get_device_capability(0)[0]}{torch.cuda.get_device_capability(0)[1]})')
"
    pass "Environment check completed."
}

run_build() {
    info "Verifying / Building C++/CUDA Simulation Backend..."
    BACKEND_DIR="$REPO_ROOT/snngine_v4/nn/cuda_backend"
    BUILD_LOG="$LOG_DIR/build_cuda.log"
    STAGED_CMAKE="$SCRIPT_DIR/CMakeLists.txt"

    if python3 -c "from snngine_v4.nn.cuda_backend import snn_simulation_gpu" &> /dev/null; then
        pass "Backend shared library already built and importable."
        return 0
    fi

    info "Compiling CUDA backend in $BACKEND_DIR (logging to $BUILD_LOG)..."
    cd "$BACKEND_DIR"

    # Auto-detect CUDA architecture capability or default to SM 89 (Ada)
    ARCH=$(python3 -c "import torch; print(f'{torch.cuda.get_device_capability(0)[0]}{torch.cuda.get_device_capability(0)[1]}') if torch.cuda.is_available() else print('89')")
    info "Targeting CUDA architecture SM $ARCH"

    # Setup trap to ensure original CMakeLists.txt is always restored
    SWAPPED=0
    ORIGINAL_BACKUP="$BACKEND_DIR/CMakeLists.original.bak"
    restore_cmake() {
        if [ "$SWAPPED" -eq 1 ] && [ -f "$ORIGINAL_BACKUP" ]; then
            mv "$ORIGINAL_BACKUP" "$BACKEND_DIR/CMakeLists.txt"
            info "Restored original CMakeLists.txt (git tree preserved)."
            SWAPPED=0
        fi
    }
    trap restore_cmake EXIT INT TERM

    # Try original CMakeLists first
    if ! cmake -B build -S . -DCMAKE_CUDA_ARCHITECTURES="$ARCH" -DCMAKE_BUILD_TYPE=Release > "$BUILD_LOG" 2>&1; then
        info "Original CMake configuration failed. Falling back to staged task CMakeLists.txt ($STAGED_CMAKE)..."
        if [ -f "$STAGED_CMAKE" ]; then
            cp "$BACKEND_DIR/CMakeLists.txt" "$ORIGINAL_BACKUP"
            cp "$STAGED_CMAKE" "$BACKEND_DIR/CMakeLists.txt"
            SWAPPED=1
            cmake -B build -S . -DCMAKE_CUDA_ARCHITECTURES="$ARCH" -DCMAKE_BUILD_TYPE=Release >> "$BUILD_LOG" 2>&1 || {
                fail "CMake configuration failed with staged CMakeLists. See $BUILD_LOG"
                tail -n 25 "$BUILD_LOG" >&2
                return 1
            }
        else
            fail "CMake configuration failed and no staged CMakeLists found. See $BUILD_LOG"
            tail -n 25 "$BUILD_LOG" >&2
            return 1
        fi
    fi

    if ! cmake --build build --config Release -j"$(nproc)" >> "$BUILD_LOG" 2>&1; then
        fail "CMake build failed! Pruned compiler errors (from $BUILD_LOG):"
        echo "------------------------------------------------------------------" >&2
        grep -E "(error:|fatal error:|undefined reference)" "$BUILD_LOG" | head -n 15 >&2 || tail -n 15 "$BUILD_LOG" >&2
        echo "------------------------------------------------------------------" >&2
        echo "Full build log available at: $BUILD_LOG" >&2
        return 1
    fi

    # Immediately restore original CMakeLists so the core codebase stays pristine
    restore_cmake

    touch "$BACKEND_DIR/build/__init__.py"
    export PYTHONPATH="$BACKEND_DIR/build:$PYTHONPATH"
    cd "$REPO_ROOT"

    python3 -c "
from snngine_v4.nn.cuda_backend import snn_simulation_gpu, snn_utils
print('CUDA Backend successfully verified in Python.')
"
    pass "Backend compilation and import successful."
}

run_test() {
    TEST_SCRIPT="$SCRIPT_DIR/test_headless_engine_sim.py"
    SIM_LOG="$LOG_DIR/headless_engine_sim.log"
    JSON_OUT="$LOG_DIR/headless_engine_sim_result.json"

    info "Executing headless simulation test..."
    # 60s timeout guard to prevent infinite GPU hang / cost runaway
    if command -v timeout &> /dev/null; then
        timeout --preserve-status 60s python3 "$TEST_SCRIPT" --log-file "$SIM_LOG" --json-output "$JSON_OUT" "$@"
    else
        python3 "$TEST_SCRIPT" --log-file "$SIM_LOG" --json-output "$JSON_OUT" "$@"
    fi
}

case "$CMD" in
    bootstrap)
        run_bootstrap
        ;;
    env)
        run_env_check
        ;;
    build)
        run_build
        ;;
    test)
        run_test "$@"
        ;;
    all)
        run_env_check
        run_build
        run_test "$@"
        ;;
    full-setup)
        run_bootstrap
        run_env_check
        run_build
        run_test "$@"
        ;;
    *)
        echo "Usage: $0 {bootstrap|env|build|test|all|full-setup} [test_args...]"
        echo "  Examples:"
        echo "    $0 bootstrap                  # Install apt OpenGL headers and pip packages"
        echo "    $0 build                      # Compile backend (auto-falls back to staged CMakeLists with clean restore)"
        echo "    $0 test --quick               # Run fast 1-step test with compact output"
        echo "    $0 test --stage contracts     # Test contracts without simulation steps"
        echo "    $0 test --stage full --steps 100"
        echo "    $0 full-setup --compact       # Bootstrap + Env + Build + Test in one command"
        exit 1
        ;;
esac
