#!/usr/bin/env bash
# ==============================================================================
# Runpod Headless 3D Chemical Diffusion Video Runner (snngine_v4)
# Task specification: setups/runpod-chem-diffusion/runpod-chem-diffusion-task.md
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

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

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${BLUE}[*] $1${NC}"; }
pass()  { echo -e "${GREEN}[+] $1${NC}"; }
warn()  { echo -e "${YELLOW}[!] $1${NC}"; }
fail()  { echo -e "${RED}[-] $1${NC}"; exit 1; }

VENV_DIR="/workspace/venv"
if [ ! -d "$VENV_DIR" ]; then
    info "Initializing persistent virtual environment at $VENV_DIR..."
    python3 -m venv --system-site-packages "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

export PATH="/usr/local/cuda/bin:${PATH:-}"
export LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}"
export PYOPENGL_PLATFORM="egl"
export QT_QPA_PLATFORM="offscreen"
export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"

CMD="${1:-generate}"
shift || true

ensure_system_packages() {
    if ! ldconfig -p | grep -q "libEGL.so" 2>/dev/null || ! command -v ffmpeg &>/dev/null; then
        info "Installing Mesa/EGL and ffmpeg packages in ephemeral container..."
        apt-get update -qq && apt-get install -y -qq \
            ffmpeg libgl1-mesa-dev libegl1-mesa-dev libgles2-mesa-dev libglvnd-dev
    fi
    if ! python3 -c "import OpenGL.GL" &>/dev/null; then
        info "Installing PyOpenGL into persistent venv for 3D texture support (VolumeVisual)..."
        pip install -q PyOpenGL
    fi
}

prune_output_retention() {
    local max_videos=5
    local min_free_gb=2

    info "Evaluating rolling retention policy on $OUTPUT_DIR (baseline: $max_videos videos)..."
    if command -v df &>/dev/null; then
        local avail_gb
        avail_gb=$(df -BG "$OUTPUT_DIR" 2>/dev/null | awk 'NR==2 {gsub("G","",$4); print $4}')
        if [[ -n "$avail_gb" && "$avail_gb" =~ ^[0-9]+$ ]]; then
            if (( avail_gb < 1 )); then
                warn "Critical volume space (${avail_gb}GB free). Throttling retention to 1 video."
                max_videos=1
            elif (( avail_gb < min_free_gb )); then
                warn "Low volume space (${avail_gb}GB free). Throttling retention to 2 videos."
                max_videos=2
            fi
        fi
    fi

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

run_generate() {
    ensure_system_packages
    info "Launching headless 3D chemical diffusion composite video generator..."
    info "Output directory: $OUTPUT_DIR"

    python3 "$SCRIPT_DIR/generate_chem_diffusion_video.py" \
        --output-dir "$OUTPUT_DIR" \
        "$@" 2>&1 | tee "$LOG_DIR/chem_video_generation.log"

    local latest_video
    latest_video=$(find "$OUTPUT_DIR" -maxdepth 1 -name "simulation_chem_*.mp4" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -f2- -d" ")

    if [ -n "$latest_video" ] && [ -s "$latest_video" ]; then
        local sz
        sz=$(stat -c%s "$latest_video")
        pass "Chemical diffusion video generated successfully: $latest_video ($sz bytes)"
        prune_output_retention
    else
        fail "Chemical diffusion video generation finished without producing a valid MP4 artifact in $OUTPUT_DIR"
    fi
}

case "$CMD" in
    generate|all)
        run_generate "$@"
        ;;
    *)
        echo "Usage: $0 {generate|all} [generator arguments...]"
        exit 1
        ;;
esac
