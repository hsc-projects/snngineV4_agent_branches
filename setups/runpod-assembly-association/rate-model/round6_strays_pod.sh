#!/usr/bin/env bash
# Round 6 step 3, final strays (round6-report.md, "Step 3"): model B with the C2 stage on exports of the
# engine-fix rerun's networks at both sizes (7^3: step 5, lambda 0.4; 9^3: step 6, d 4), at the steps' settings,
# with the final tests' strays recorded per pair (round6_regime_precheck.py rows, "final"), to tell whether the
# 9^3 associations model B misses end just above the stray limit of 34 or far from it.
# Run on a GPU pod after setups/runpod-engine-tests/run_on_pod.py (e.g. --configs small) has unpacked a
# pack_tree.sh copy and built its backend in /root/engine-tests/tree:
#   round6_strays_pod.sh RATE.tgz     (RATE.tgz: the rate-model folder and the rerun's params files)
# Results in /workspace/output/rate-model-round6-strays/ with a finished marker; the host terminates the pod.
set -uo pipefail
W=/root/engine-tests/tree
OUT=/workspace/output/rate-model-round6-strays
X=/root/r6xs
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
P="$W/setups/runpod-assembly-association/params"
# the container's limits (cgroup v2), not the host's that nproc and free report
NCPU=$(nproc); CQ=$(awk '{print $1, $2}' /sys/fs/cgroup/cpu.max 2>/dev/null)
[ -n "$CQ" ] && [ "${CQ%% *}" != max ] && NCPU=$(( ${CQ%% *} / ${CQ##* } ))
MEMG=$(free -g | awk '/^Mem:/{print $2}'); ML=$(cat /sys/fs/cgroup/memory.max 2>/dev/null)
[ -n "$ML" ] && [ "$ML" != max ] && MEMG=$(( ML / 1073741824 ))
# memory per full-size model B process, upper bounds: 9^3 4.5 GB (12 at once ran in a pod's 61 GB, 32 did not),
# 7^3 2.5 GB (24 at once ran there)
W9=$(( MEMG * 60 * 10 / 100 / 45 )); W7=$(( MEMG * 35 * 10 / 100 / 25 ))
[ "$W9" -gt 24 ] && W9=24; [ "$W7" -gt 24 ] && W7=24
[ $(( W9 + W7 )) -gt "$NCPU" ] && { W9=$(( NCPU * W9 / (W9 + W7) )); W7=$(( NCPU - W9 )); }
log "PACK_INFO: $(tr '\n' ';' < "$W/PACK_INFO"); $NCPU CPUs, $MEMG GB; workers 9^3 $W9, 7^3 $W7"

log "exports (one at a time: two 9^3 builds exceed the GPU memory)"
for t in g7-lam0.4-s0:rerun5e-proto-lam0.4-s0:proto g7-lam0.4-s1:rerun5g-proto-lam0.4-s1:proto \
         g9-lam0.4-s0:rerun6c-grid-g9-d4-s0:E0 g9-lam0.4-s1:rerun6d-grid-g9-d4-s1:E0; do
  IFS=: read -r tag params suffix <<< "$t"
  python "$RM/round6_export_engine.py" --params "$P/$params.json" --suffix "$suffix" --out "$X" --tag "$tag" > "$OUT/export_$tag.log" 2>&1
  grep -q "EXPORT DONE" "$OUT/export_$tag.log" && log "export $tag: $(grep 'audit E->I' "$OUT/export_$tag.log")" \
    || { log "export $tag failed"; tail -5 "$OUT/export_$tag.log" >> "$OUT/session.log"; finish 3; }
done

log "model B with the C2 stage, final strays recorded (gain_ee_inter 2.4, gain_ie 2), both sizes at once"
python "$RM/round6_regime_precheck.py" export --c2 --exports "$X/g9-lam0.4-s0" "$X/g9-lam0.4-s1" \
  --set gain_ee_inter=2.4 gain_ie=2.0 --workers "$W9" --out "$OUT/c2_g9_lam0.4.json" > "$OUT/c2_g9.log" 2>&1 &
P9=$!
python "$RM/round6_regime_precheck.py" export --c2 --exports "$X/g7-lam0.4-s0" "$X/g7-lam0.4-s1" \
  --set gain_ee_inter=2.4 gain_ie=2.0 --workers "$W7" --out "$OUT/c2_g7_lam0.4.json" > "$OUT/c2_g7.log" 2>&1 &
P7=$!
wait "$P7"; log "7^3: $(tail -1 "$OUT/c2_g7.log" | cut -c1-600)"
wait "$P9"; log "9^3: $(tail -1 "$OUT/c2_g9.log" | cut -c1-600)"
log "SESSION DONE"
finish 0
