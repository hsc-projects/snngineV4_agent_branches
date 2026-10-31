#!/usr/bin/env bash
# Round 6 step 4 and optional coverage (rate-model-task.md; round6-report.md, "Step 4"), on a GPU pod after
# setups/runpod-engine-tests/run_on_pod.py (e.g. --configs small) has unpacked a pack_tree.sh copy and built its
# backend in /root/engine-tests/tree:
#   1. module checks (test_spiking_group_model.py);
#   2. S3b at lambda 1.0, inter-group I -> E gain 0.5 (the engine-fix rerun's step 7 decision: rerun7j seed 0,
#      rerun7m seed 1): survey exports (round6_export_engine.py --survey) and model B's propagation and input
#      surveys on them (round6_survey.py), compared pair by pair on the host;
#   3. the engine's own wiring at 7^3 (step 5's networks, gain_ee_inter 1.2) with the C2 stage at kappa 0.045;
#   4. repeatability: step 5's lambda 0.4 seed 0 network exported twice (arrays compared), model B with the C2 stage
#      at kappa 0.045 twice on the first export and once on the second.
#   round6_step4_pod.sh RATE.tgz     (RATE.tgz: the rate-model folder, the params files named below and
#                                     archive-pre-engine-fix/params/session69a-stage2.json)
# Results in /workspace/output/rate-model-round6-step4/ with a finished marker; the host terminates the pod.
set -uo pipefail
W=/root/engine-tests/tree
OUT=/workspace/output/rate-model-round6-step4
X=/root/r6x4
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
NCPU=$(nproc); CQ=$(awk '{print $1, $2}' /sys/fs/cgroup/cpu.max 2>/dev/null)
[ -n "$CQ" ] && [ "${CQ%% *}" != max ] && NCPU=$(( ${CQ%% *} / ${CQ##* } ))
MEMG=$(free -g | awk '/^Mem:/{print $2}'); ML=$(cat /sys/fs/cgroup/memory.max 2>/dev/null)
[ -n "$ML" ] && [ "$ML" != max ] && MEMG=$(( ML / 1073741824 ))
WK=$(( MEMG * 9 / 10 * 10 / 25 )); [ "$WK" -gt "$NCPU" ] && WK=$NCPU       # 7^3: at most 2.5 GB per process
log "PACK_INFO: $(tr '\n' ';' < "$W/PACK_INFO"); $NCPU CPUs, $MEMG GB, $WK workers"

log "1. module checks"
(cd "$RM" && python -m unittest test_spiking_group_model > "$OUT/module_checks.log" 2>&1)
log "test_spiking_group_model: $(tail -1 "$OUT/module_checks.log")"
grep -q "^OK" "$OUT/module_checks.log" || { tail -30 "$OUT/module_checks.log" >> "$OUT/session.log"; finish 4; }

export_one() {   # tag params suffix [--survey]
  python "$RM/round6_export_engine.py" --params "$P/$2.json" --suffix "$3" --out "$X" --tag "$1" ${4:-} > "$OUT/export_$1.log" 2>&1
  grep -q "EXPORT DONE" "$OUT/export_$1.log" && log "export $1: $(grep 'audit E->I' "$OUT/export_$1.log")" \
    || { log "export $1 failed"; tail -8 "$OUT/export_$1.log" >> "$OUT/session.log"; finish 3; }
}
log "exports (one at a time)"
export_one s3b-ie0.5-s0 rerun7j-s3b-s6ie-lam1.0 sp2-lam1.0-S3b-sig1-ie0.5 --survey
export_one s3b-ie0.5-s1 rerun7m-s3b-ie0.5-lam1.0-s1 sp2-lam1.0-S3b-sig1-ie0.5-s1 --survey
export_one g7-own-s0 rerun5a-proto-own-s0 proto
export_one g7-own-s1 rerun5c-proto-own-s1 proto
export_one g7-lam0.4-s0-a rerun5e-proto-lam0.4-s0 proto
export_one g7-lam0.4-s0-b rerun5e-proto-lam0.4-s0 proto

log "4a. the two exports of one network, array by array"
python - "$X/g7-lam0.4-s0-a" "$X/g7-lam0.4-s0-b" > "$OUT/repeat_arrays.txt" 2>&1 <<'EOF'
import sys, numpy as np
a, b = sys.argv[1:3]
for k in ("post", "w_engine", "w_norm", "bnd", "abcd", "init_vu", "types", "groups", "group_cell"):
    x, y = np.load(f"{a}/{k}.npy"), np.load(f"{b}/{k}.npy")
    line = f"{k}: identical {bool(np.array_equal(x, y))}"
    if k == "post" and not np.array_equal(x, y):
        # same targets per neuron and delay bucket, in another order?
        line += f"; rows equal as sets {bool(np.array_equal(np.sort(x, axis=1), np.sort(y, axis=1)))}"
    print(line)
EOF
log "$(tr '\n' ';' < "$OUT/repeat_arrays.txt")"

log "2. model B surveys on S3b"
python "$RM/round6_survey.py" run --exports "$X/s3b-ie0.5-s0" "$X/s3b-ie0.5-s1" --out "$OUT/survey/model-s3b-ie0.5" \
  --workers $(( WK / 2 )) > "$OUT/survey.log" 2>&1         # the input survey holds synapse-sized float64 arrays
log "surveys: $(tail -1 "$OUT/survey.log")"

log "3. own wiring and 4b. repeatability, at once (kappa 0.045)"
C2="$RM/round6_regime_precheck.py export --c2"
python $C2 --exports "$X/g7-own-s0" "$X/g7-own-s1" --set gain_ee_inter=1.2 gain_ie=2.0 kappa=0.045 \
  --workers $(( WK * 2 / 5 )) --out "$OUT/own_kappa0.045.json" > "$OUT/own.log" 2>&1 & P1=$!
python $C2 --exports "$X/g7-lam0.4-s0-a" --set gain_ee_inter=2.4 gain_ie=2.0 kappa=0.045 \
  --workers $(( WK / 5 )) --out "$OUT/repeat_a1.json" > "$OUT/repeat_a1.log" 2>&1 & P2=$!
python $C2 --exports "$X/g7-lam0.4-s0-a" --set gain_ee_inter=2.4 gain_ie=2.0 kappa=0.045 \
  --workers $(( WK / 5 )) --out "$OUT/repeat_a2.json" > "$OUT/repeat_a2.log" 2>&1 & P3=$!
python $C2 --exports "$X/g7-lam0.4-s0-b" --set gain_ee_inter=2.4 gain_ie=2.0 kappa=0.045 \
  --workers $(( WK / 5 )) --out "$OUT/repeat_b.json" > "$OUT/repeat_b.log" 2>&1 & P4=$!
wait $P1; log "own wiring: $(tail -1 "$OUT/own.log" | cut -c1-500)"
wait $P2 $P3 $P4
for r in a1 a2 b; do log "repeat $r: $(tail -1 "$OUT/repeat_$r.log" | cut -c1-300)"; done
log "SESSION DONE"
finish 0
