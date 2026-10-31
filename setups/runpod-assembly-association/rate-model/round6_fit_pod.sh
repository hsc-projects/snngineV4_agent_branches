#!/usr/bin/env bash
# Round 6 step 3, fit (round6-report.md, "Step 3"): model B with the C2 stage on exports of the engine-fix rerun's
# networks (7^3: step 5, lambda 0.4; 9^3 and 11^3: step 6, d 4) at the steps' settings plus extra settings per job (the
# fitted parameter, e.g. kappa; c2_uniform for the uniform-C2 check), final strays recorded per pair.
# Run on a GPU pod after setups/runpod-engine-tests/run_on_pod.py (e.g. --configs small) has unpacked a
# pack_tree.sh copy and built its backend in /root/engine-tests/tree:
#   round6_fit_pod.sh RATE.tgz NAME JOB [JOB ...]
#   JOB = SIZE:SEEDS:SETTINGS, e.g. 9:0:kappa=0.035 or 7:0,1:kappa=0.035,c2_uniform=1.2 (all jobs run at once)
# RATE.tgz: the rate-model folder, the rerun's params files and archive-pre-engine-fix/params/session69a-stage2.json.
# Results in /workspace/output/rate-model-round6-fit-NAME/ with a finished marker; the host terminates the pod.
set -uo pipefail
W=/root/engine-tests/tree
OUT=/workspace/output/rate-model-round6-fit-$2
X=/root/r6xf
rm -f "$OUT/finished"; mkdir -p "$OUT" "$X"
T0=$(date +%s)
log() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$OUT/session.log"; }
finish() { log "done in $(( $(date +%s) - T0 )) s, exit $1"
  for d in "$X"/g*; do mkdir -p "$OUT/$(basename "$d")"; cp "$d"/meta.json "$OUT/$(basename "$d")/" 2>/dev/null; done
  tar -czf "$OUT/results.tgz" -C "$OUT" --exclude=results.tgz . ; echo "$1" > "$OUT/finished"; exit "$1"; }

tar --no-same-owner -xzf "$1" -C "$W" || { log "unpacking failed"; finish 2; }
shift 2
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
log "PACK_INFO: $(tr '\n' ';' < "$W/PACK_INFO"); $NCPU CPUs, $MEMG GB; jobs: $*"

declare -A PARAMS=([7:0]=rerun5e-proto-lam0.4-s0:proto [7:1]=rerun5g-proto-lam0.4-s1:proto
                   [9:0]=rerun6c-grid-g9-d4-s0:E0 [9:1]=rerun6d-grid-g9-d4-s1:E0
                   [11:0]=rerun6g-grid-g11-d4-s0:E0 [11:1]=rerun6h-grid-g11-d4-s1:E0)
log "exports (one at a time: two 9^3 builds exceed the GPU memory)"
for k in $(for j in "$@"; do IFS=: read -r size seeds _ <<< "$j"; for s in ${seeds//,/ }; do echo "$size:$s"; done; done | sort -u); do
  tag="g${k%%:*}-lam0.4-s${k##*:}"; IFS=: read -r params suffix <<< "${PARAMS[$k]}"
  python "$RM/round6_export_engine.py" --params "$P/$params.json" --suffix "$suffix" --out "$X" --tag "$tag" > "$OUT/export_$tag.log" 2>&1
  grep -q "EXPORT DONE" "$OUT/export_$tag.log" && log "export $tag: $(grep 'audit E->I' "$OUT/export_$tag.log")" \
    || { log "export $tag failed"; tail -5 "$OUT/export_$tag.log" >> "$OUT/session.log"; finish 3; }
done

# workers: memory per full-size model B process, upper bounds 11^3 8.5 GB, 9^3 4.5 GB, 7^3 2.5 GB (in tenths); 90 % of the
# container's memory shared in proportion to each job's need, at most one worker per simulation, at most NCPU in all
need=0; for j in "$@"; do IFS=: read -r size seeds _ <<< "$j"; n=$(( 12 * $(echo "${seeds//,/ }" | wc -w) ))
  need=$(( need + n * ( size == 11 ? 85 : size == 9 ? 45 : 25 ) )); done
pids=(); labels=()
for j in "$@"; do
  IFS=: read -r size seeds sets <<< "$j"; n=$(( 12 * $(echo "${seeds//,/ }" | wc -w) )); m=$(( size == 11 ? 85 : size == 9 ? 45 : 25 ))
  wk=$(( MEMG * 9 * n * m / need / m )); cpu=$(( NCPU * n * m / need )); [ "$cpu" -lt "$wk" ] && wk=$cpu
  [ "$wk" -gt "$n" ] && wk=$n; [ "$wk" -lt 1 ] && wk=1
  ex=(); for s in ${seeds//,/ }; do ex+=("$X/g$size-lam0.4-s$s"); done
  label="g${size}-s${seeds//,/}-${sets//[=,]/_}"
  log "job $label: $n simulations, $wk workers, --set gain_ee_inter=2.4 gain_ie=2.0 ${sets//,/ }"
  python "$RM/round6_regime_precheck.py" export --c2 --exports "${ex[@]}" --set gain_ee_inter=2.4 gain_ie=2.0 ${sets//,/ } \
    --workers "$wk" --out "$OUT/$label.json" > "$OUT/$label.log" 2>&1 &
  pids+=($!); labels+=("$label")
done
for i in "${!pids[@]}"; do wait "${pids[$i]}"; log "${labels[$i]}: $(tail -1 "$OUT/${labels[$i]}.log" | cut -c1-600)"; done
log "SESSION DONE"
finish 0
