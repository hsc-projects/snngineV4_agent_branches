#!/usr/bin/env bash
# Host launcher for containerized GPU interop smoke test
# Checks if the container image exists; if missing, builds it automatically before running.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PARENT_DIR="$(cd "${WORKSPACE_ROOT}/.." && pwd)"

IMAGE_NAME="snngine-gpu-smoke:headless"
DOCKERFILE="${SCRIPT_DIR}/Dockerfile.docker-smoke"

echo "======================================================================"
echo "SNNgineV4 - Docker GPU Interop Smoke Test Launcher"
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

echo "[Launcher] Launching container with --gpus all..."
docker run --rm --gpus all \
    -v "${PARENT_DIR}:/workspace/snngineV4_cloud:ro" \
    -v "${SCRIPT_DIR}:/output:rw" \
    -w "/workspace/snngineV4_cloud/snngineV4_agent_branches" \
    -e PYTHONPATH="/workspace/snngineV4_cloud/snngineV4_agent_branches:/workspace/snngineV4_cloud/SNNgine3D_agent_branches/notebooks/simulation_demo" \
    "${IMAGE_NAME}" \
    python3 setups/gpu-smoke-test/interop_smoke_test_auto.py --snapshot /output/rendered_frame.png "$@"

EXIT_CODE=$?
echo "======================================================================"
echo "[Launcher] Test container exited with code: ${EXIT_CODE}"
echo "======================================================================"
exit ${EXIT_CODE}
