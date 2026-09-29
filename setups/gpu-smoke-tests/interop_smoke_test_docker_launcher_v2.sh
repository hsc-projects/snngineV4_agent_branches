#!/usr/bin/env bash
# ==============================================================================
# Host launcher for containerized GPU interop smoke test v2 (Frontier)
# Supports:
#   Default (no args): Phase 1 & 2 Automated Headless EGL test + offscreen snapshot
#   --gui:             Phase 3 Interactive GUI test (PySide6 + VisPy) on host display with safety guards
#   --web:             Phase 4 Containerized Web Bridge (EGL + WebSocket:6080) for cloud readiness
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PARENT_DIR="$(cd "${WORKSPACE_ROOT}/.." && pwd)"

IMAGE_NAME="snngine-gpu-smoke:v2"
DOCKERFILE="${SCRIPT_DIR}/Dockerfile.docker-smoke-v2"

echo "======================================================================"
echo "SNNgineV4 - Docker GPU Interop Smoke Test Launcher v2 (Frontier)"
echo "======================================================================"

# Check if image exists locally; if missing, build it
if ! docker image inspect "${IMAGE_NAME}" >/dev/null 2>&1; then
    echo "[Launcher] Docker image '${IMAGE_NAME}' not found locally."
    echo "[Launcher] Building '${IMAGE_NAME}' using ${DOCKERFILE}..."
    docker build -t "${IMAGE_NAME}" -f "${DOCKERFILE}" "${SCRIPT_DIR}"
    echo "[Launcher] Docker image build complete."
else
    echo "[Launcher] Docker image '${IMAGE_NAME}' found."
fi

if [[ "${1:-}" == "--web" ]]; then
    echo "======================================================================"
    echo "[Launcher] Mode: Category 3 Containerized Web Bridge (EGL + WebSocket:6080)"
    echo "======================================================================"
    echo "[Launcher] Open http://localhost:6080 in your web browser to interact."
    docker run --rm --gpus all \
        --name snngine-gpu-smoke-web-v2 \
        -p 6080:6080 \
        -e PYTHONUNBUFFERED=1 \
        -v "${PARENT_DIR}:/workspace/snngineV4_cloud:ro" \
        -w "/workspace/snngineV4_cloud/snngineV4_agent_branches" \
        -e PYTHONPATH="/workspace/snngineV4_cloud/snngineV4_agent_branches:/workspace/snngineV4_cloud/SNNgine3D_agent_branches/notebooks/simulation_demo" \
        "${IMAGE_NAME}" \
        python3 setups/gpu-smoke-tests/interop_smoke_test_web_gui.py "${@:2}"
elif [[ "${1:-}" == "--gui" ]]; then
    echo "======================================================================"
    echo "[Launcher] Mode: Category 2 Interactive GUI (PySide6 standalone VisPy double torus)"
    echo "======================================================================"
    
    # Apply host GNOME Shell extension safety guard to prevent Mutter assertion crash
    echo "[Launcher] Applying host GNOME Shell extension safety guard..."
    gnome-extensions disable tiling-assistant@ubuntu.com >/dev/null 2>&1 || true
    trap 'echo "[Launcher] Restoring tiling-assistant extension..."; gnome-extensions enable tiling-assistant@ubuntu.com >/dev/null 2>&1 || true' EXIT INT TERM
    
    # Authorize local container connections to X server
    xhost +local:root >/dev/null 2>&1 || true

    echo "[Launcher] Launching GUI container on DISPLAY=${DISPLAY:-:1}..."
    docker run --rm --gpus all \
        -e DISPLAY="${DISPLAY:-:1}" \
        -e QT_XCB_GL_INTEGRATION=glx \
        -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
        -v "${PARENT_DIR}:/workspace/snngineV4_cloud:ro" \
        -w "/workspace/snngineV4_cloud/snngineV4_agent_branches" \
        -e PYTHONPATH="/workspace/snngineV4_cloud/snngineV4_agent_branches:/workspace/snngineV4_cloud/SNNgine3D_agent_branches/notebooks/simulation_demo" \
        "${IMAGE_NAME}" \
        python3 setups/gpu-smoke-tests/interop_smoke_test_standalone_gui.py "${@:2}"
else
    echo "======================================================================"
    echo "[Launcher] Mode: Category 1 Automated Headless EGL + Offscreen Snapshot"
    echo "======================================================================"
    OUTPUT_FILE="${SCRIPT_DIR}/rendered_frame_docker_v2.png"
    docker run --rm --gpus all \
        --user "$(id -u):$(id -g)" \
        -e HOME=/tmp \
        -v "${PARENT_DIR}:/workspace/snngineV4_cloud:ro" \
        -v "${SCRIPT_DIR}:/output:rw" \
        -w "/workspace/snngineV4_cloud/snngineV4_agent_branches" \
        -e PYTHONPATH="/workspace/snngineV4_cloud/snngineV4_agent_branches:/workspace/snngineV4_cloud/SNNgine3D_agent_branches/notebooks/simulation_demo" \
        "${IMAGE_NAME}" \
        python3 setups/gpu-smoke-tests/interop_smoke_test_auto.py --snapshot /output/rendered_frame_docker_v2.png "$@"
    
    # Fix ownership if root created the file
    if [ -f "${OUTPUT_FILE}" ]; then
        chown "$(id -u):$(id -g)" "${OUTPUT_FILE}" 2>/dev/null || true
        chmod 664 "${OUTPUT_FILE}" 2>/dev/null || true
        echo "[Launcher] Verified output snapshot: ${OUTPUT_FILE}"
    fi
fi

EXIT_CODE=$?
echo "======================================================================"
echo "[Launcher] Test container exited with code: ${EXIT_CODE}"
echo "======================================================================"
exit ${EXIT_CODE}
