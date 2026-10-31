#!/usr/bin/env bash
# Round 6, checks after the review of 2026-10-31 (round6-report.md, "Checks after the review"): module checks
# (test_spiking_group_model.py), exports of the engine's networks (round6_export_engine.py), model B with the C2 stage
# on them (round6_regime_precheck.py export --c2) and the comparison with the spiking runs (round6_fit_summary.py).
# On a GPU pod after setups/runpod-engine-tests/run_on_pod.py (e.g. --configs small) has unpacked a pack_tree.sh copy
# and built its backend in /root/engine-tests/tree:
#   round6_review_pod.sh RATE.tgz NAME SPEC [SPEC ...]
#   SPEC = export:TAG:PARAMS[+PARAMS...]:SUFFIX[,SUFFIX...]   one engine build per export, one at a time
#        | run:LABEL:SIZE:TAG[+TAG...]:SETTINGS:SPIKING[+SPIKING...]
#          model B on those exports with SETTINGS (k=v,k=v; - none), all runs at once; SPIKING: folders of spiking
#          per-job results under output/ to compare with (- none)
# RATE.tgz: the rate-model folder, the params files named, archive-pre-engine-fix/params/session69a-stage2.json and
# the spiking per-job result files (output/<folder>/*.json).
# Results in /workspace/output/rate-model-round6-review-NAME/ with a finished marker; the host terminates the pod.
set -uo pipefail
W=/root/engine-tests/tree
OUT=/workspace/output/rate-model-round6-review-$2
X=/root/r6xv
rm -f "$OUT/finished"; mkdir -p "$OUT" "$X"
T0=$(date +%s)
log() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$OUT/session.log"; }
finish() { log "done in $(( $(date +%s) - T0 )) s, exit $1"
  for d in "$X"/*/; do mkdir -p "$OUT/exports/$(basename "$d")"; cp "$d"/meta.json "$OUT/exports/$(basename "$d")/" 2>/dev/null; done
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
SP="$W/setups/runpod-assembly-association/output"
# the container's limits (cgroup v2), not the host's that nproc and free report
NCPU=$(nproc); CQ=$(awk '{print $1, $2}' /sys/fs/cgroup/cpu.max 2>/dev/null)
[ -n "$CQ" ] && [ "${CQ%% *}" != max ] && NCPU=$(( ${CQ%% *} / ${CQ##* } ))
MEMG=$(free -g | awk '/^Mem:/{print $2}'); ML=$(cat /sys/fs/cgroup/memory.max 2>/dev/null)
[ -n "$ML" ] && [ "$ML" != max ] && MEMG=$(( ML / 1073741824 ))
log "PACK_INFO: $(tr '\n' ';' < "$W/PACK_INFO"); $NCPU CPUs, $MEMG GB; specs: $*"

log "module checks"
(cd "$RM" && python -m unittest test_spiking_group_model > "$OUT/module_checks.log" 2>&1)
log "test_spiking_group_model: $(tail -1 "$OUT/module_checks.log")"
grep -q "^OK" "$OUT/module_checks.log" || { tail -40 "$OUT/module_checks.log" >> "$OUT/session.log"; finish 4; }

runs=()
for s in "$@"; do
  IFS=: read -r kind a b c d e <<< "$s"
  if [ "$kind" = export ]; then
    pf=(); for p in ${b//+/ }; do pf+=("$P/$p.json"); done
    python "$RM/round6_export_engine.py" --params "${pf[@]}" --suffix "$c" --out "$X" --tag "$a" > "$OUT/export_$a.log" 2>&1
    grep -q "EXPORT DONE" "$OUT/export_$a.log" && log "export $a: $(grep -c '^\[+\] .*pair' "$OUT/export_$a.log") jobs; $(grep 'audit E->I' "$OUT/export_$a.log")" \
      || { log "export $a failed"; tail -8 "$OUT/export_$a.log" >> "$OUT/session.log"; finish 3; }
  else
    runs+=("$s")
  fi
done

# workers: memory per full-size model B process, upper bounds 11^3 8.5 GB, 9^3 4.5 GB, 7^3 2.5 GB (in tenths); 90 % of the
# container's memory shared in proportion to each run's need, at most one worker per simulation, at most NCPU in all
nsim() { python -c "import json, sys; print(sum(len(json.load(open(f'$X/{t}/meta.json'))['jobs']) for t in sys.argv[1:]))" ${1//+/ }; }
mem() { case $1 in 11) echo 85;; 9) echo 45;; *) echo 25;; esac; }
need=0
for s in "${runs[@]}"; do IFS=: read -r _ label size tags _ _ <<< "$s"; need=$(( need + $(nsim "$tags") * $(mem "$size") )); done
pids=(); labels=(); models=()
for s in "${runs[@]}"; do
  IFS=: read -r _ label size tags sets spk <<< "$s"
  n=$(nsim "$tags"); m=$(mem "$size")
  wk=$(( MEMG * 9 * n * m / need / m )); cpu=$(( NCPU * n * m / need )); [ "$cpu" -lt "$wk" ] && wk=$cpu
  [ "$wk" -gt "$n" ] && wk=$n; [ "$wk" -lt 1 ] && wk=1
  ex=(); for t in ${tags//+/ }; do ex+=("$X/$t"); done
  st=(); [ "$sets" != - ] && st=(--set ${sets//,/ })
  log "run $label: $n simulations, $wk workers, ${st[*]:-no --set}"
  python "$RM/round6_regime_precheck.py" export --c2 --exports "${ex[@]}" "${st[@]}" \
    --workers "$wk" --out "$OUT/$label.json" > "$OUT/$label.log" 2>&1 &
  pids+=($!); labels+=("$label")
  dirs=""; [ "$spk" != - ] && for f in ${spk//+/ }; do dirs="${dirs:+$dirs,}$SP/$f"; done
  models+=("$label=$OUT/$label.json=$dirs")
done
for i in "${!pids[@]}"; do wait "${pids[$i]}"; log "${labels[$i]}: $(tail -1 "$OUT/${labels[$i]}.log" | cut -c1-500)"; done
python "$RM/round6_fit_summary.py" --model "${models[@]}" --out "$OUT/summary.json" > "$OUT/summary.log" 2>&1
log "summary: $(tr '\n' ' ' < "$OUT/summary.log" | cut -c1-3000)"
log "SESSION DONE"
finish 0
