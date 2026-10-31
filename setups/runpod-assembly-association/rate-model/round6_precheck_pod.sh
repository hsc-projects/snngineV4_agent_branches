#!/usr/bin/env bash
# Round 6 on the fixed engine, before the admission test (rate-model-task.md, round 6 step 3; round6-report.md):
#  (a) model B pre-check: outcome classes of the archived protocol (session69a-stage2.json settings, rewiring at
#      lambda 0.4, configured composition, no fitted factor, full size) on 7^3 (the 24 s71 pair positions) and
#      9^3 (24 pairs >= 2 cells from the surface), realizations 0 and 1: do the settings give mixed classes?
#  (b) steps 1 and 2 again at lambda 1.0 (exports of the s71 / s73 networks rewired at lambda 1.0, trace, audit,
#      single-group response of model B's own networks).
# Run on a GPU pod after setups/runpod-engine-tests/run_on_pod.py (e.g. --configs small) has unpacked a
# pack_tree.sh copy and built its backend in /root/engine-tests/tree. RATE.tgz as for round6_fixed_pod.sh.
#   round6_precheck_pod.sh RATE.tgz
# Results (small files) in /workspace/output/rate-model-round6-precheck/ with a finished marker.
set -uo pipefail
W=/root/engine-tests/tree
OUT=/workspace/output/rate-model-round6-precheck
X=/root/r6x10
rm -f "$OUT/finished"; mkdir -p "$OUT" "$X" /root/p10
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
NCPU=$(nproc)
log "PACK_INFO: $(tr '\n' ';' < "$W/PACK_INFO"); $NCPU CPUs"

# (a) model B pre-check in the background (numpy, CPU)
WB=$(( NCPU > 12 ? NCPU - 8 : NCPU / 2 ))
( python "$RM/admission_spiking_group.py" eval --realizations 0,1 --syn-scale 1 --workers "$WB" --out "$OUT/pre_eval_g7.json" > "$OUT/pre_eval_g7.log" 2>&1
  log "pre-check 7^3 rc=$?: $(tail -1 "$OUT/pre_eval_g7.log")"
  python "$RM/admission_spiking_group.py" grid --realizations 0,1 --n-pairs 24 --syn-scale 1 --workers "$WB" --out "$OUT/pre_grid_g9.json" > "$OUT/pre_grid_g9.log" 2>&1
  log "pre-check 9^3 rc=$?: $(tail -1 "$OUT/pre_grid_g9.log")" ) &
PRE=$!

# (b) lambda 1.0: params files of the s71 / s73 networks with the rewiring at lambda 1.0
python - "$P" /root/p10 <<'EOF'
import glob, json, os, sys
src, dst = sys.argv[1], sys.argv[2]
for f in glob.glob(os.path.join(src, "session71-d4-s[01]-p*.json")) + glob.glob(os.path.join(src, "session73-g9-d4-s[01]-[ab].json")):
    d = json.load(open(f))
    for e in [d["engine"]] + [j["engine"] for j in d["jobs"] if "engine" in j]:
        if "rewire" in e:
            e["rewire"]["lam"] = 1.0
    json.dump(d, open(os.path.join(dst, os.path.basename(f).replace(".json", "-lam1.0.json")), "w"), indent=1)
EOF
exp() {  # tag, params...
  local t=$1; shift
  python "$RM/round6_export_engine.py" --params "$@" --suffix E0 --out "$X" --tag "$t" > "$OUT/export_$t.log" 2>&1
  grep -q "EXPORT DONE" "$OUT/export_$t.log" && log "export $t: $(grep 'audit E->I' "$OUT/export_$t.log")" || { log "export $t failed"; tail -5 "$OUT/export_$t.log" >> "$OUT/session.log"; }
}
log "lambda 1.0 exports (7^3 two in parallel, 9^3 one at a time)"
exp g7-s0-lam1.0 /root/p10/session71-d4-s0-p*-lam1.0.json & E1=$!
exp g7-s1-lam1.0 /root/p10/session71-d4-s1-p*-lam1.0.json & E2=$!
wait "$E1" "$E2"
exp g9-s0-lam1.0 /root/p10/session73-g9-d4-s0-a-lam1.0.json /root/p10/session73-g9-d4-s0-b-lam1.0.json
exp g9-s1-lam1.0 /root/p10/session73-g9-d4-s1-a-lam1.0.json /root/p10/session73-g9-d4-s1-b-lam1.0.json

log "lambda 1.0: model B on the exported networks (trace)"
for t in g7-s0 g7-s1 g9-s0 g9-s1; do
  [ -f "$X/$t-lam1.0/meta.json" ] && python "$RM/round6_compare.py" trace --export "$X/$t-lam1.0" --out "$X/$t-lam1.0/trace.json" > "$OUT/trace_$t.log" 2>&1
  python - "$X/$t-lam1.0/trace.json" <<'EOF' | tee -a "$OUT/session.log"
import json, sys
try:
    r = json.load(open(sys.argv[1]))
except OSError:
    print(sys.argv[1], "missing"); sys.exit()
rows = [j[k] for j in r["jobs"] for k in ("AB", "BA")]
print(sys.argv[1].split("/")[-2], "tests", len(rows), "pass", sum(x["pass"] for x in rows),
      "totals equal", sum(x["engine"]["total"] == x["model"]["total"] for x in rows),
      "largest input diff", max(max((p["input_max_abs_diff"] for p in x["per_step"]), default=0) for x in rows))
EOF
done
log "lambda 1.0: audit of model B's own network against the exports"
for t in g7-s0 g9-s0; do
  python "$RM/round6_compare.py" audit --export "$X/$t-lam1.0" --out "$X/$t-lam1.0/audit_model_b.json" >> "$OUT/audit.log" 2>&1
done
cat "$OUT/audit.log" >> "$OUT/session.log"
log "lambda 1.0: single-group response of model B's own networks, seeds 0 to 3"
python "$RM/round6_compare.py" single --exports "$X/g9-s0-lam1.0" "$X/g9-s1-lam1.0" --out "$OUT/single_g9_lam1.0.json" --seeds 0 1 2 3 --workers 6 2>&1 | tee -a "$OUT/session.log"
python "$RM/round6_compare.py" single --exports "$X/g7-s0-lam1.0" "$X/g7-s1-lam1.0" --out "$OUT/single_g7_lam1.0.json" --seeds 0 1 2 3 --workers 6 2>&1 | tee -a "$OUT/session.log"

log "waiting for the pre-check"
wait "$PRE"
log "SESSION DONE"
finish 0
