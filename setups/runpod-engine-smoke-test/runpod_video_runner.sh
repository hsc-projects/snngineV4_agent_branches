#!/usr/bin/env bash
# ==============================================================================
# Runpod SNNgine_v4 Simulation Video Generation Runner
# Bootstraps video dependencies, sets up EGL/OpenGL headless environment,
# and executes the offscreen simulation video generator.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
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

export PATH="/usr/local/cuda/bin:${PATH:-}"
export LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}"
export PYOPENGL_PLATFORM="egl"
export QT_QPA_PLATFORM="offscreen"
export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"

CMD="${1:-all}"
shift || true

run_bootstrap() {
    info "Bootstrapping video encoding and rendering dependencies..."
    
    # 1. System packages: ffmpeg, EGL libraries
    if ! command -v ffmpeg &>/dev/null; then
        info "Installing system ffmpeg and OpenGL libraries via apt..."
        apt-get update -qq && apt-get install -y -qq ffmpeg libegl1-mesa libgl1-mesa-glx libgles2-mesa
    fi

    # 2. Python packages: imageio, imageio-ffmpeg
    info "Installing Python video packages via pip..."
    pip install --break-system-packages --no-cache-dir imageio imageio-ffmpeg vispy || true

    pass "Video dependencies bootstrapped successfully."
}

run_generate() {
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
    else
        fail "Video generation finished without producing a valid MP4 artifact in $OUTPUT_DIR"
    fi
}

case "$CMD" in
    bootstrap)
        run_bootstrap
        ;;
    generate)
        run_generate "$@"
        ;;
    all)
        run_bootstrap
        run_generate "$@"
        ;;
    *)
        echo "Usage: $0 {bootstrap|generate|all} [generator arguments...]"
        exit 1
        ;;
esac
