#!/usr/bin/env bash
# Step 1 of engine-fix-rerun-task.md on a GPU pod: build each network of the params files with the volume's
# harness and engine (rate-model/round6_export_engine.py, with arrays, on the pod's own disk), then check it with
# rerun_build_audit.py. 7^3 builds two at a time; 9^3 and 11^3 one at a time (GPU memory).
#   rerun1_audit_pod.sh DIR      DIR holds the params files (rerun1*.json) and rerun_build_audit.py
# Results (small files) in /workspace/output/engine-fix-rerun/step1/ with a finished marker.
set -uo pipefail
R=/workspace/snngineV4_cloud/snngineV4_agent_branches
IN=$1
OUT=/workspace/output/engine-fix-rerun/step1
X=/root/rerun1-exports
rm -f "$OUT/finished"; mkdir -p "$OUT" "$X"
T0=$(date +%s)
log() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$OUT/session.log"; }
finish() { log "done in $(( $(date +%s) - T0 )) s, exit $1"; echo "$1" > "$OUT/finished"; exit "$1"; }

source /workspace/venv/bin/activate
export PATH="/usr/local/cuda/bin:$PATH" LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}"
export PYOPENGL_PLATFORM=egl QT_QPA_PLATFORM=offscreen PYTHONPATH="$R" PYTHONUNBUFFERED=1 SNN_REPO="$R"
cd /workspace
log "checkout: $(git -C "$R" log --oneline -1); status lines: $(git -C "$R" status --short | wc -l)"
EXPORT="$R/setups/runpod-assembly-association/rate-model/round6_export_engine.py"

run() {  # params stem: export, then audit (the audit runs in the background while the next build runs)
  local t=$1
  python "$EXPORT" --params "$IN/$t.json" --suffix E0 --out "$X" --tag "$t" > "$OUT/export_$t.log" 2>&1
  if ! grep -q "EXPORT DONE" "$OUT/export_$t.log"; then log "export $t failed"; tail -20 "$OUT/export_$t.log" | tee -a "$OUT/session.log"; return 1; fi
  cp "$X/$t/meta.json" "$OUT/meta_$t.json"
  log "export $t: $(grep -E '^\[\*\] engine|^\[\+\] s4' "$OUT/export_$t.log" | tr '\n' ' ')"
  ( python "$IN/rerun_build_audit.py" "$X/$t" --out "$OUT/audit_$t.json" > "$OUT/audit_$t.log" 2>&1
    log "audit $t: $(grep -vE '^AUDIT DONE' "$OUT/audit_$t.log" | tail -3 | tr '\n' ' ')"
    grep -q "AUDIT DONE" "$OUT/audit_$t.log" && rm -f "$X/$t"/{post,w_engine,w_norm,bnd}.npy ) &
}

log "7^3"
run rerun1a-audit-g7-unrewired & run rerun1b-audit-g7-rewired & wait
log "9^3"
run rerun1c-audit-g9-unrewired; run rerun1d-audit-g9-rewired
log "11^3"
run rerun1e-audit-g11-unrewired; run rerun1f-audit-g11-rewired
wait
while pgrep -f rerun_build_audit.py > /dev/null; do sleep 5; done   # audits started inside background runs
n_pass=$(grep -l '"passed": true' "$OUT"/audit_*.json 2>/dev/null | wc -l)
log "audits passed: $n_pass of 6"
tar -czf "$OUT/results.tgz" -C "$OUT" --exclude=results.tgz --exclude=finished .
[ "$n_pass" = 6 ] && finish 0 || finish 1
