#!/usr/bin/env bash
# ==============================================================================
# SNNgineV4 - Modern Frontier GPU Environment Bootstrap Helper
# Builds an isolated Conda environment targeting maximum operational versions:
# Python 3.14+, CUDA Toolkit 13.2+, PyTorch 2.15-dev (cu132), Numba, VisPy,
# PySide6, and PyCUDA compiled with OpenGL interop enabled.
# ==============================================================================
set -euo pipefail

ENV_NAME="${1:-snngine-frontier}"
CONDA_EXE="${CONDA_EXE:-/home/htm/anaconda3/bin/conda}"
CONDA_PREFIX_DIR="$(dirname "$(dirname "$CONDA_EXE")")"
TARGET_ENV="$CONDA_PREFIX_DIR/envs/$ENV_NAME"

echo "=== [1/6] Provisioning Conda Environment ($ENV_NAME with Python 3.14) ==="
if [ ! -d "$TARGET_ENV" ]; then
    "$CONDA_EXE" create -n "$ENV_NAME" python=3.14 pip setuptools wheel -c conda-forge -y
else
    echo "Environment $ENV_NAME already exists at $TARGET_ENV, proceeding."
fi

PYTHON_BIN="$TARGET_ENV/bin/python"
PIP_BIN="$TARGET_ENV/bin/pip"

echo "=== [2/6] Installing CUDA Toolkit 13.2, Numba, VisPy, and NumPy via conda-forge ==="
"$CONDA_EXE" install -n "$ENV_NAME" numba "cuda-toolkit=13.2*" vispy -c conda-forge -y

echo "=== [3/6] Installing Bleeding-Edge PyTorch (CUDA 13.2 / cu132 Nightly) ==="
"$PIP_BIN" install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu132

echo "=== [4/6] Installing Supporting Libraries (PySide6, PyOpenGL, QtPy, WebSockets, SciPy, Pillow) ==="
"$PIP_BIN" install pyside6 pillow websockets scipy pyopengl qtpy

echo "=== [5/6] Building and Installing PyCUDA from Source with OpenGL Interop ==="
BUILD_DIR="$(mktemp -d -t pycuda_build_XXXXXX)"
trap 'rm -rf "$BUILD_DIR"' EXIT

git clone --recursive --depth 1 https://github.com/inducer/pycuda.git "$BUILD_DIR"
cd "$BUILD_DIR"

CUDA_ROOT="$TARGET_ENV/targets/x86_64-linux"
"$PYTHON_BIN" ./configure.py \
    --cuda-root="$CUDA_ROOT" \
    --cuda-inc-dir="$CUDA_ROOT/include" \
    --cudadrv-lib-dir="/usr/lib/x86_64-linux-gnu" \
    --cudart-lib-dir="$CUDA_ROOT/lib" \
    --cuda-enable-gl

"$PIP_BIN" install . --no-build-isolation
cd /

echo "=== [6/6] Verifying Environment Import Diagnostics ==="
"$PYTHON_BIN" -c "
import sys, torch, pycuda, pycuda.driver, pycuda.gl, numba, numba.cuda, vispy, PySide6
print(f'Python:  {sys.version.split()[0]}')
print(f'PyTorch: {torch.__version__} (CUDA {torch.version.cuda})')
print(f'PyCUDA:  {pycuda.VERSION_TEXT} (RegisteredBuffer={hasattr(pycuda.gl, \"RegisteredBuffer\")})')
print(f'VisPy:   {vispy.__version__}')
print(f'Numba:   {numba.__version__}')
print(f'PySide6: {PySide6.__version__}')
print(f'CUDA HW: {torch.cuda.get_device_name(0)} CC={torch.cuda.get_device_capability(0)}')
"

echo "=== Bootstrap Complete! Environment: $ENV_NAME ==="
