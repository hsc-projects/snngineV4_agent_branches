#!/usr/bin/env bash
# Round 6, steps 1 and 2 on the fixed engine (round6-report.md, "After the engine fixes"). Run on a GPU pod after
# setups/runpod-engine-tests/run_on_pod.py (e.g. --configs small) has unpacked a pack_tree.sh copy and built its
# backend in /root/engine-tests/tree. RATE.tgz: this folder and archive-pre-engine-fix/params and
# archive-pre-engine-fix/rate-model/*.json, packed from the repository root (without output-round* and .venv).
#   round6_fixed_pod.sh RATE.tgz
# Results (small files) in /workspace/output/rate-model-round6-fixed/ with a finished marker; exports on local disk.
set -uo pipefail
W=/root/engine-tests/tree
OUT=/workspace/output/rate-model-round6-fixed
X=/root/r6x
rm -f "$OUT/finished"; mkdir -p "$OUT" "$X"
T0=$(date +%s)
log() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$OUT/session.log"; }
finish() { log "done in $(( $(date +%s) - T0 )) s, exit $1"
  for d in "$X"/g*; do mkdir -p "$OUT/$(basename "$d")"; cp "$d"/*.json "$d"/group_cell.npy "$OUT/$(basename "$d")/" 2>/dev/null; done
  tar -czf "$OUT/results.tgz" -C "$OUT" --exclude=results.tgz . ; echo "$1" > "$OUT/finished"; exit "$1"; }

tar --no-same-owner -xzf "$1" -C "$W" || { log "unpacking failed"; finish 2; }
source /workspace/venv/bin/activate
BACKEND="$W/snngine_v4/nn/cuda_backend"
export PATH="/usr/local/cuda/bin:$PATH" LD_LIBRARY_PATH="$BACKEND/build:/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}"
export PYOPENGL_PLATFORM=egl QT_QPA_PLATFORM=offscreen PYTHONPATH="$W" PYTHONUNBUFFERED=1
cd /workspace
A="$W/setups/runpod-assembly-association"
RM="$A/rate-model"; P="$A/archive-pre-engine-fix/params"
log "PACK_INFO: $(tr '\n' ';' < "$W/PACK_INFO")"

log "module checks of model B and the rate model"
python -m unittest discover -s "$RM" -p "test_spiking_group_model.py" -v > "$OUT/test_spiking_group_model.log" 2>&1; log "test_spiking_group_model rc=$?: $(grep -E '^(Ran|OK|FAILED)' "$OUT/test_spiking_group_model.log" | tr '\n' ' ')"
python -m unittest discover -s "$RM" -p "test_rate_model.py" > "$OUT/test_rate_model.log" 2>&1; log "test_rate_model rc=$?: $(grep -E '^(Ran|OK|FAILED)' "$OUT/test_rate_model.log" | tr '\n' ' ')"

exp() {  # tag, params...; skipped when an earlier run finished it
  local t=$1; shift
  if [ -f "$X/$t/meta.json" ] && grep -q "EXPORT DONE" "$OUT/export_$t.log" 2>/dev/null; then log "export $t exists"; return; fi
  python "$RM/round6_export_engine.py" --params "$@" --suffix E0 --out "$X" --tag "$t" > "$OUT/export_$t.log" 2>&1
}
log "exports (7^3 two in parallel, 9^3 one at a time: four builds at once exceed the GPU memory)"
exp g7-s0 "$P"/session71-d4-s0-p*.json &
exp g7-s1 "$P"/session71-d4-s1-p*.json &
wait
exp g9-s0 "$P"/session73-g9-d4-s0-a.json "$P"/session73-g9-d4-s0-b.json
exp g9-s1 "$P"/session73-g9-d4-s1-a.json "$P"/session73-g9-d4-s1-b.json
for t in g7-s0 g7-s1 g9-s0 g9-s1; do
  grep -q "EXPORT DONE" "$OUT/export_$t.log" || { log "export $t failed"; tail -20 "$OUT/export_$t.log" | tee -a "$OUT/session.log"; finish 3; }
  log "export $t: $(grep -E 'audit E->I' "$OUT/export_$t.log")"
done

log "step 2 again: model B on each exported network (trace)"
for t in g7-s0 g7-s1 g9-s0 g9-s1; do
  python "$RM/round6_compare.py" trace --export "$X/$t" --out "$X/$t/trace.json" > "$OUT/trace_$t.log" 2>&1 &
done
wait
for t in g7-s0 g7-s1 g9-s0 g9-s1; do
  python - "$X/$t/trace.json" <<'EOF' | tee -a "$OUT/session.log"
import json, sys
r = json.load(open(sys.argv[1]))
rows = [j[k] for j in r["jobs"] for k in ("AB", "BA")]
print(sys.argv[1].split("/")[-2], "tests", len(rows), "pass", sum(x["pass"] for x in rows),
      "totals equal", sum(x["engine"]["total"] == x["model"]["total"] for x in rows),
      "largest input diff", max(max((p["input_max_abs_diff"] for p in x["per_step"]), default=0) for x in rows),
      "first spike diff steps", sorted({x["first_spike_diff_step"] for x in rows if x["first_spike_diff_step"] is not None}))
EOF
done

log "audit of model B's own network (configured composition) against each export"
for t in g7-s0 g9-s0; do
  python "$RM/round6_compare.py" audit --export "$X/$t" --out "$X/$t/audit_model_b.json" >> "$OUT/audit.log" 2>&1
done
cat "$OUT/audit.log" >> "$OUT/session.log"

log "single-group response, model B's own networks (configured composition, no fitted factor), seeds 0 to 3"
python "$RM/round6_compare.py" single --exports "$X/g9-s0" "$X/g9-s1" --out "$OUT/single_g9_configured.json" --seeds 0 1 2 3 --workers 6 2>&1 | tee -a "$OUT/session.log"
python "$RM/round6_compare.py" single --exports "$X/g7-s0" "$X/g7-s1" --out "$OUT/single_g7_configured.json" --seeds 0 1 2 3 --workers 6 2>&1 | tee -a "$OUT/session.log"
log "SESSION DONE"
finish 0
