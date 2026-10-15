#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/cuda/bin:${PATH}"
export LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}"

echo "[*] Updating git submodules in /tmp/pycuda..."
cd /tmp/pycuda
git submodule update --init --recursive

echo "[*] Verifying siteconf.py..."
if [ ! -f siteconf.py ]; then
    python3 ./configure.py --cuda-root=/usr/local/cuda
    echo "CUDA_ENABLE_GL = True" >> siteconf.py
fi

echo "[*] Building and installing PyCUDA via pip..."
pip install --break-system-packages --no-cache-dir --no-build-isolation .

echo "[*] Verifying PyCUDA and PyCUDA GL interop..."
cd /root
python3 -c "import pycuda, pycuda.driver as cuda, pycuda.gl as cudagl; cuda.init(); print(f'SUCCESS: PyCUDA {pycuda.VERSION_TEXT} with OpenGL interop initialized successfully on {cuda.Device.count()} device(s).')"
