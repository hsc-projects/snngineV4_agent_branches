#!/usr/bin/env bash
# Round 6, admission at 9^3 (rate-model-task.md, round 6 step 3; round6-report.md): exports of the engine-fix rerun's
# step-6 networks (9^3, d 4, rewired at lambda 0.4, network seeds 0 and 1) and model B with the C2 stage on them,
# at the step's settings, for a pair-by-pair comparison with the spiking runs; also collects the per-pair results
# of the 7^3 runs on step 5's networks (round6_regime_precheck.py, output of the earlier pre-check session).
# Run on a GPU pod after setups/runpod-engine-tests/run_on_pod.py (e.g. --configs small) has unpacked a
# pack_tree.sh copy and built its backend in /root/engine-tests/tree; the step-6 params files in /root/p6.
#   round6_grid_pod.sh RATE.tgz
# Results in /workspace/output/rate-model-round6-grid/ with a finished marker; the host terminates the pod (a
# self-removal from inside the pod would need its API key, which an SSH session does not have and should not read).
set -uo pipefail
W=/root/engine-tests/tree
OUT=/workspace/output/rate-model-round6-grid
PRE=/workspace/output/rate-model-round6-precheck
X=/root/r6x9
rm -f "$OUT/finished"; mkdir -p "$OUT" "$X"
T0=$(date +%s)
log() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$OUT/session.log"; }
finish() { log "done in $(( $(date +%s) - T0 )) s, exit $1"
  for d in "$X"/g*; do mkdir -p "$OUT/$(basename "$d")"; cp "$d"/meta.json "$OUT/$(basename "$d")/" 2>/dev/null; done
  tar -czf "$OUT/results.tgz" -C "$OUT" --exclude=results.tgz . ; echo "$1" > "$OUT/finished"; exit "$1"; }

tar --no-same-owner -xzf "$1" -C "$W" || { log "unpacking failed"; finish 2; }
source /workspace/venv/bin/activate
BACKEND="$W/snngine_v4/nn/cuda_backend"
export PATH="/usr/local/cuda/bin:$PATH" LD_LIBRARY_PATH="$BACKEND/build:/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}"
export PYOPENGL_PLATFORM=egl QT_QPA_PLATFORM=offscreen PYTHONPATH="$W" PYTHONUNBUFFERED=1
cd /workspace
RM="$W/setups/runpod-assembly-association/rate-model"
NCPU=$(nproc); MEMG=$(free -g | awk '/^Mem:/{print $2}')
WK=$(( MEMG / 3 < NCPU ? MEMG / 3 : NCPU ))           # about 3 GB per full-size 9^3 model B process
log "PACK_INFO: $(tr '\n' ';' < "$W/PACK_INFO"); $NCPU CPUs, $MEMG GB, $WK workers"

log "per-pair results of the 7^3 runs on step 5's networks (earlier session)"
mkdir -p "$OUT/step5"
cp "$PRE"/step5b/precheck_own_gee1.2.json "$PRE"/step5b/precheck_lam0.4_gee*.json "$PRE"/step5c/c2_lam0.4_*.json "$OUT/step5/" 2>> "$OUT/session.log"
ls "$OUT/step5" | tee -a "$OUT/session.log"

log "exports of the step-6 9^3 networks (one at a time: two exceed the GPU memory)"
for s in 0 1; do
  f=/root/p6/rerun6$([ $s = 0 ] && echo c || echo d)-grid-g9-d4-s$s.json
  python "$RM/round6_export_engine.py" --params "$f" --suffix E0 --out "$X" --tag g9-lam0.4-s$s > "$OUT/export_s$s.log" 2>&1
  grep -q "EXPORT DONE" "$OUT/export_s$s.log" && log "export s$s: $(grep 'audit E->I' "$OUT/export_s$s.log")" \
    || { log "export s$s failed"; tail -5 "$OUT/export_s$s.log" >> "$OUT/session.log"; finish 3; }
done

log "model B with the C2 stage on the 9^3 exports (gain_ee_inter 2.4, gain_ie 2)"
python "$RM/round6_regime_precheck.py" export --c2 --exports "$X/g9-lam0.4-s0" "$X/g9-lam0.4-s1" \
  --set gain_ee_inter=2.4 gain_ie=2.0 --workers "$WK" --out "$OUT/c2_g9_lam0.4.json" > "$OUT/c2_g9.log" 2>&1
log "9^3: $(tail -1 "$OUT/c2_g9.log" | cut -c1-600)"
log "SESSION DONE"
finish 0
