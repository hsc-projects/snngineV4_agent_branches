#!/usr/bin/env bash
# Round 6 step 4, survey replay (round6-report.md, "Step 4"): S3b survey exports with the engine's own run of the
# propagation survey's conditions on the exported weights (round6_export_engine.py --survey --replay), model B's
# surveys on the same exports (round6_survey.py run) and the comparison of the two (round6_survey.py replay): does
# model B reproduce the engine's spikes on identical S3b weights, as round 6 step 2 did for the A-alone test?
# On a GPU pod after setups/runpod-engine-tests/run_on_pod.py has built /root/engine-tests/tree:
#   round6_replay_pod.sh RATE.tgz
# Results in /workspace/output/rate-model-round6-replay/ with a finished marker; the host terminates the pod.
set -uo pipefail
W=/root/engine-tests/tree
OUT=/workspace/output/rate-model-round6-replay
X=/root/r6xr
rm -f "$OUT/finished"; mkdir -p "$OUT" "$X"
T0=$(date +%s)
log() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$OUT/session.log"; }
finish() { log "done in $(( $(date +%s) - T0 )) s, exit $1"
  for d in "$X"/*/; do mkdir -p "$OUT/exports/$(basename "$d")"; cp "$d"/meta.json "$OUT/exports/$(basename "$d")/" 2>/dev/null; done
  tar -czf "$OUT/results.tgz" -C "$OUT" --exclude=results.tgz . ; echo "$1" > "$OUT/finished"; exit "$1"; }

tar --no-same-owner -xzf "$1" -C "$W" || { log "unpacking failed"; finish 2; }
source /workspace/venv/bin/activate
BACKEND="$W/snngine_v4/nn/cuda_backend"
export PATH="/usr/local/cuda/bin:$PATH" LD_LIBRARY_PATH="$BACKEND/build:/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}"
export PYOPENGL_PLATFORM=egl QT_QPA_PLATFORM=offscreen PYTHONPATH="$W" PYTHONUNBUFFERED=1
cd /workspace
RM="$W/setups/runpod-assembly-association/rate-model"
P="$W/setups/runpod-assembly-association/params"
MEMG=$(free -g | awk '/^Mem:/{print $2}'); ML=$(cat /sys/fs/cgroup/memory.max 2>/dev/null)
[ -n "$ML" ] && [ "$ML" != max ] && MEMG=$(( ML / 1073741824 ))
WK=$(( MEMG * 9 / 10 * 10 / 25 / 2 ))       # 7^3, the input survey's synapse-sized arrays: about 5 GB per process
log "PACK_INFO: $(tr '\n' ';' < "$W/PACK_INFO"); $MEMG GB, $WK workers"
for t in s3b-ie0.5-s0:rerun7j-s3b-s6ie-lam1.0:sp2-lam1.0-S3b-sig1-ie0.5 \
         s3b-ie0.5-s1:rerun7m-s3b-ie0.5-lam1.0-s1:sp2-lam1.0-S3b-sig1-ie0.5-s1; do
  IFS=: read -r tag params suffix <<< "$t"
  python "$RM/round6_export_engine.py" --params "$P/$params.json" --suffix "$suffix" --out "$X" --tag "$tag" --survey --replay \
    > "$OUT/export_$tag.log" 2>&1
  grep -q "EXPORT DONE" "$OUT/export_$tag.log" && log "export $tag done" \
    || { log "export $tag failed"; tail -8 "$OUT/export_$tag.log" >> "$OUT/session.log"; finish 3; }
done
python "$RM/round6_survey.py" run --exports "$X/s3b-ie0.5-s0" "$X/s3b-ie0.5-s1" --out "$OUT/survey/model-s3b-ie0.5" \
  --workers "$WK" > "$OUT/survey.log" 2>&1
log "surveys: $(tail -1 "$OUT/survey.log")"
python "$RM/round6_survey.py" replay --exports "$X/s3b-ie0.5-s0" "$X/s3b-ie0.5-s1" --model "$OUT/survey/model-s3b-ie0.5" \
  --out "$OUT/replay_compare.json" > "$OUT/replay.log" 2>&1
log "replay: $(tr '\n' ' ' < "$OUT/replay.log" | cut -c1-900)"
log "SESSION DONE"
finish 0
