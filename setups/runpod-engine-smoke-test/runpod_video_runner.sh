#!/usr/bin/env bash
# ==============================================================================
# Runpod SNNgine_v4 Simulation Video Generation Runner
# Bootstraps video dependencies, sets up EGL/OpenGL headless environment,
# and executes the offscreen simulation video generator.
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

OUTPUT_DIR="${OUTPUT_DIR:-/workspace/output}"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$OUTPUT_DIR" "$LOG_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[*] $1${NC}"; }
pass()  { echo -e "${GREEN}[+] $1${NC}"; }
warn()  { echo -e "${YELLOW}[!] $1${NC}"; }
fail()  { echo -e "${RED}[-] $1${NC}"; exit 1; }

VENV_DIR="/workspace/venv"
if [ ! -d "$VENV_DIR" ]; then
    info "Initializing persistent virtual environment at $VENV_DIR on the network volume..."
    python3 -m venv --system-site-packages "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

export PATH="/usr/local/cuda/bin:${PATH:-}"
export LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}"
export PYOPENGL_PLATFORM="egl"
export QT_QPA_PLATFORM="offscreen"
export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"

CMD="${1:-all}"
shift || true

run_bootstrap() {
    info "Bootstrapping video encoding, rendering, and PyCUDA GL interop dependencies into persistent /workspace/venv..."
    
    # 1. System packages: ffmpeg, EGL libraries, and OpenGL development headers
    if command -v apt-get &>/dev/null; then
        info "Verifying system packages via apt..."
        apt-get update -qq && apt-get install -y -qq \
            ffmpeg libgl1-mesa-dev libegl1-mesa-dev libgles2-mesa-dev libglvnd-dev cmake ninja-build
    fi

    # 2. Python engine dependencies inside persistent venv
    info "Installing Python dependencies into persistent /workspace/venv..."
    pip install --no-cache-dir \
        "pydantic>=2.9" "numpydantic" "pydantic-settings" "pydantic-extra-types" \
        "scipy" "pandas" "deepdiff" "lxml" "numba" "tables" \
        imageio imageio-ffmpeg vispy "mako" "pytools" || true

    # 3. PyCUDA with OpenGL interop
    if python3 -c "import pycuda.gl" &>/dev/null; then
        pass "PyCUDA with OpenGL interop already installed and verified."
    else
        WHEEL_DIR="/workspace/wheels"
        mkdir -p "$WHEEL_DIR"
        local cached_wheel
        cached_wheel=$(find "$WHEEL_DIR" -name "pycuda*.whl" 2>/dev/null | head -n 1 || true)
        if [ -n "$cached_wheel" ]; then
            info "Installing cached PyCUDA wheel from $cached_wheel into persistent venv..."
            pip install --no-cache-dir "$cached_wheel"
        else
            info "Building PyCUDA with OpenGL interop from source..."
            if [ ! -d "/tmp/pycuda" ]; then
                git clone --recurse-submodules https://github.com/inducer/pycuda.git /tmp/pycuda
            fi
            cd /tmp/pycuda
            rm -f siteconf.py
            python3 ./configure.py --cuda-root=/usr/local/cuda
            echo "CUDA_ENABLE_GL = True" >> siteconf.py
            
            # Bridge NumPy 2.x include path for PyCUDA C++ compilation
            local np_inc
            np_inc=$(python3 -c "import numpy; print(numpy.get_include())")
            echo "CXXFLAGS = ['-I$np_inc']" >> siteconf.py
            mkdir -p /usr/local/lib/python3.12/dist-packages/numpy/core
            ln -sfn "$np_inc" /usr/local/lib/python3.12/dist-packages/numpy/core/include
            mkdir -p "$VENV_DIR/lib/python3.12/site-packages/numpy/core" 2>/dev/null || true
            ln -sfn "$np_inc" "$VENV_DIR/lib/python3.12/site-packages/numpy/core/include" 2>/dev/null || true

            pip install --no-cache-dir --no-build-isolation .
            # Cache the wheel on the persistent volume so future pods install in seconds
            pip wheel --no-deps -w "$WHEEL_DIR" --no-build-isolation . || true
        fi
        # Verification
        cd /root
        python3 -c "import pycuda, pycuda.driver as cuda, pycuda.gl as cudagl; cuda.init(); print(f'[+] PyCUDA {pycuda.VERSION_TEXT} with OpenGL interop verified on {cuda.Device.count()} device(s).')"
    fi

    pass "Video, engine, and PyCUDA GL dependencies bootstrapped successfully."
}

ensure_system_packages() {
    if ! ldconfig -p | grep -q "libEGL.so" 2>/dev/null; then
        info "Mesa/EGL libraries missing from ephemeral container; installing via apt..."
        apt-get update -qq && apt-get install -y -qq \
            ffmpeg libgl1-mesa-dev libegl1-mesa-dev libgles2-mesa-dev libglvnd-dev
    fi
}

run_generate() {
    ensure_system_packages
    info "Launching headless simulation video generation..."
    info "Output directory: $OUTPUT_DIR"
    
    python3 "$SCRIPT_DIR/generate_simulation_video.py" \
        --output-dir "$OUTPUT_DIR" \
        "$@" 2>&1 | tee "$LOG_DIR/video_generation.log"
    
    local latest_video
    latest_video=$(find "$OUTPUT_DIR" -maxdepth 1 -name "simulation_*.mp4" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -f2- -d" ")
    
    if [ -n "$latest_video" ] && [ -s "$latest_video" ]; then
        local sz
        sz=$(stat -c%s "$latest_video")
        pass "Video generated successfully: $latest_video ($sz bytes)"
        prune_output_retention
    else
        fail "Video generation finished without producing a valid MP4 artifact in $OUTPUT_DIR"
    fi
}

run_composite() {
    ensure_system_packages
    info "Launching headless unified composite video generation (3D + Raster + Voltage)..."
    info "Output directory: $OUTPUT_DIR"
    
    python3 "$SCRIPT_DIR/generate_composite_video.py" \
        --output-dir "$OUTPUT_DIR" \
        "$@" 2>&1 | tee "$LOG_DIR/video_generation.log"
    
    local latest_video
    latest_video=$(find "$OUTPUT_DIR" -maxdepth 1 -name "simulation_composite_*.mp4" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -f2- -d" ")
    
    if [ -n "$latest_video" ] && [ -s "$latest_video" ]; then
        local sz
        sz=$(stat -c%s "$latest_video")
        pass "Composite video generated successfully: $latest_video ($sz bytes)"
        prune_output_retention
    else
        fail "Composite video generation finished without producing a valid MP4 artifact in $OUTPUT_DIR"
    fi
}

prune_output_retention() {
    local max_videos=5
    local min_free_gb=2

    info "Evaluating rolling retention policy on $OUTPUT_DIR (baseline: $max_videos videos)..."

    # 1. Capacity check on persistent volume (throttle if approaching 20GB limit)
    if command -v df &>/dev/null; then
        local avail_gb
        avail_gb=$(df -BG "$OUTPUT_DIR" 2>/dev/null | awk 'NR==2 {gsub("G","",$4); print $4}')
        if [[ -n "$avail_gb" && "$avail_gb" =~ ^[0-9]+$ ]]; then
            if (( avail_gb < 1 )); then
                warn "Critical volume space (${avail_gb}GB free). Throttling retention to 1 video."
                max_videos=1
            elif (( avail_gb < min_free_gb )); then
                warn "Low volume space (${avail_gb}GB free < ${min_free_gb}GB threshold). Throttling retention to 2 videos."
                max_videos=2
            fi
        fi
    fi

    # 2. Enforce retention limit (oldest first)
    local mp4_files=()
    while IFS= read -r f; do
        [[ -n "$f" ]] && mp4_files+=("$f")
    done < <(find "$OUTPUT_DIR" -maxdepth 1 -name "simulation_*.mp4" -type f -printf '%T@ %p\n' | sort -n | cut -f2- -d" ")

    local count="${#mp4_files[@]}"
    if (( count > max_videos )); then
        local to_delete=$(( count - max_videos ))
        info "Found $count video(s) on volume (max: $max_videos). Pruning $to_delete oldest video(s)..."
        for (( i=0; i<to_delete; i++ )); do
            local vid="${mp4_files[i]}"
            local meta="${vid%.mp4}.json"
            info "Pruned: $(basename "$vid")"
            rm -f "$vid" "$meta"
        done
    fi
    local remaining
    remaining=$(find "$OUTPUT_DIR" -maxdepth 1 -name "simulation_*.mp4" -type f | wc -l)
    pass "Rolling retention complete: $remaining video(s) retained on persistent volume."
}

case "$CMD" in
    bootstrap)
        run_bootstrap
        ;;
    generate)
        run_generate "$@"
        ;;
    composite)
        run_composite "$@"
        ;;
    all)
        run_bootstrap
        run_composite "$@"
        ;;
    *)
        echo "Usage: $0 {bootstrap|generate|composite|all} [generator arguments...]"
        exit 1
        ;;
esac
