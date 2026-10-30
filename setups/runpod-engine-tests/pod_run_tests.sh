#!/usr/bin/env bash
# Engine tests on a Runpod pod (setups/runpod-engine-tests/README.md); started detached by run_on_pod.py.
#   pod_run_tests.sh TREE.tgz RUN [LEVEL] [CONFIGS]
# LEVEL quick (default: the small configurations) or full (all); CONFIGS, e.g. "small,odd", overrides the level's
# configurations. Unpacks TREE.tgz to /root/engine-tests/tree (local disk, a fixed path: the compiled libraries
# link to each other by absolute path, so a cached build stays valid), takes the CUDA backend from the build cache
# on the volume or builds it inside the copy and caches it, compiles and runs snngine_v4/tests, and writes to
# /workspace/output/engine-tests/RUN: build.log, tests.log, summary.txt, results.tgz, and finished (exit code).
# The code and the backend build on the shared volume are not touched; the caches are in their own folder.
set -uo pipefail

TGZ="${1:?tree .tgz}"
RUN="${2:?run name}"
LEVEL="${3:-quick}"
CONFIGS="${4:-}"
case "$LEVEL" in
    quick) [ -n "$CONFIGS" ] || CONFIGS="small,odd" ;;
    full) ;;
    *) echo "level must be quick or full" >&2; exit 2 ;;
esac
W="/root/engine-tests/tree"
OUT="/workspace/output/engine-tests/$RUN"
CACHE="/workspace/engine-tests-cache"
rm -rf "$W"
mkdir -p "$W" "$OUT" "$CACHE/builds" "$CACHE/apt"
rm -f "$OUT/finished"
T0=$(date +%s)
: > "$OUT/summary.txt"
log() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$OUT/summary.txt"; }
finish() { log "done in $(( $(date +%s) - T0 )) s, exit $1"; tar -czf "$OUT/results.tgz" -C "$OUT" --exclude=results.tgz . ; echo "$1" > "$OUT/finished"; exit "$1"; }

tar --no-same-owner -xzf "$TGZ" -C "$W" || { log "unpacking failed"; finish 2; }   # packed on Windows: foreign uids
find "$W" -name '*.sh' -exec sed -i 's/\r$//' {} +   # a Windows checkout may carry CRLF line endings
cat "$W/PACK_INFO" >> "$OUT/summary.txt" 2>/dev/null
log "level $LEVEL${CONFIGS:+, configurations $CONFIGS}"
log "GPU: $(nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader)"

source /workspace/venv/bin/activate
export PATH="/usr/local/cuda/bin:${PATH:-}" LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}"
export PYOPENGL_PLATFORM=egl QT_QPA_PLATFORM=offscreen PYTHONPATH="$W" PYTHONUNBUFFERED=1
cd /workspace                       # never run Python from a source tree (PyCUDA import shadowing)

# ---- build tools (container, not volume); the package files are cached on the volume
if ! command -v cmake > /dev/null || [ ! -e /usr/include/GL/gl.h ] || [ ! -e /usr/include/EGL/egl.h ] \
        || [ ! -e /usr/include/python3.12/Python.h ]; then
    log "installing build packages (cmake, Mesa/EGL headers, Python headers)"
    # apt cannot lock a folder on the network volume: it works in its local cache, and the package files are
    # copied from and to the volume cache around it (download-only first, before the image's clean-up hook runs)
    PKGS=(cmake ninja-build libgl1-mesa-dev libegl1-mesa-dev libgles2-mesa-dev libglvnd-dev python3.12-dev)
    cp -n "$CACHE"/apt/*.deb /var/cache/apt/archives/ 2>/dev/null
    { apt-get update -qq \
        && apt-get install -y -qq --no-install-recommends --download-only "${PKGS[@]}" \
        && { cp -n /var/cache/apt/archives/*.deb "$CACHE/apt/" 2>/dev/null; true; } \
        && apt-get install -y -qq --no-install-recommends "${PKGS[@]}"; } > "$OUT/apt.log" 2>&1 \
        || { log "installing build packages failed (apt.log)"; finish 3; }
fi

# ---- CUDA backend: cached by a hash of its sources, the build setup and the GPU architecture
BACKEND="$W/snngine_v4/nn/cuda_backend"
ARCH=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -1 | tr -d '. ')
KEY=$( { find "$BACKEND" "$W/setups/runpod-engine-smoke-test/CMakeLists.txt" -type f \
           \( -name '*.cu' -o -name '*.cuh' -o -name '*.h' -o -name '*.hpp' -o -name '*.cpp' -o -name 'CMakeLists.txt' \) \
           -not -path '*/build/*' -print0 | sort -z | xargs -0 sha256sum | cut -d' ' -f1;
         nvcc --version | tail -1; python -V; } | sha256sum | cut -c1-16)
CACHED="$CACHE/builds/$KEY-sm$ARCH"
if [ -f "$CACHED/.complete" ]; then
    log "CUDA backend from the cache ($KEY, SM $ARCH)"
    cp -a "$CACHED" "$BACKEND/build"
    rm -f "$BACKEND/build/.complete"
else
    log "building the CUDA backend in the copy (no cached build for $KEY, SM $ARCH)"
    if ! bash "$W/setups/runpod-engine-smoke-test/runpod_engine_test_runner.sh" build > "$OUT/build.log" 2>&1; then
        log "build failed (build.log, build_cuda.log)"
        cp "$W/setups/runpod-engine-smoke-test/logs/build_cuda.log" "$OUT/" 2>/dev/null
        finish 3
    fi
    TMPC="$CACHE/builds/.tmp-$KEY-sm$ARCH-$$"
    rm -rf "$TMPC" && cp -a "$BACKEND/build" "$TMPC" && touch "$TMPC/.complete" \
        && { [ -d "$CACHED" ] && rm -rf "$TMPC" || mv "$TMPC" "$CACHED"; }
    log "cached the build as $KEY-sm$ARCH"
fi
export LD_LIBRARY_PATH="$BACKEND/build:$LD_LIBRARY_PATH"
LOC=$(python -c "import snngine_v4.nn.cuda_backend as b; print(b.__file__)" 2>> "$OUT/build.log") \
    || { log "backend not importable from the copy (build.log)"; finish 3; }
case "$LOC" in "$W"/*) ;; *) log "backend imported from outside the copy: $LOC"; finish 3 ;; esac

# ---- tests
log "compiling the tests"
python -m py_compile "$W"/snngine_v4/tests/*.py >> "$OUT/tests.log" 2>&1 || { log "test files do not compile"; finish 4; }

log "running the tests"
SNN_ENGINE_TESTS=1 SNN_ENGINE_CONFIGS="$CONFIGS" SNN_ENGINE_EXPORT_DIR="$W/exports" \
    python -m unittest discover -s "$W/snngine_v4/tests" -p "test_*.py" -v >> "$OUT/tests.log" 2>&1
RC=$?
grep -E "^(FAIL|ERROR):" "$OUT/tests.log" | sort -u >> "$OUT/summary.txt"
grep -E "^Ran [0-9]+ tests|^OK|^FAILED" "$OUT/tests.log" | tail -2 >> "$OUT/summary.txt"
finish "$RC"
