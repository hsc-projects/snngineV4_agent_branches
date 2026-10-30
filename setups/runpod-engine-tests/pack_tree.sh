#!/usr/bin/env bash
# Pack the code an engine test run uses (setups/runpod-engine-tests/README.md).
#   pack_tree.sh worktree OUT.tgz   the local working tree
#   pack_tree.sh head OUT.tgz       the engine (snngine_v4) as committed at HEAD, with the working tree's tests and
#                                   support files (to run the current tests against the committed engine)
# Packs snngine_v4 (without build directories and caches) and the support files the headless build and the tests
# need: the assembly harness's engine builder, the chemical-diffusion and engine-smoke-test helpers (the backend
# build), and this folder's pod script.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
MODE="${1:?mode: worktree or head}"
OUT="${2:?output .tgz}"
case "$OUT" in /*|?:*) ;; *) OUT="$PWD/$OUT" ;; esac

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
EXCLUDES=(--exclude='build' --exclude='build_sm*' --exclude='__pycache__' --exclude='.venv' --exclude='output'
          --exclude='logs' --exclude='*.mp4' --exclude='*.npz' --exclude='*.tgz')

cd "$REPO"
case "$MODE" in
    worktree)
        tar -cf - "${EXCLUDES[@]}" snngine_v4 | tar -xf - -C "$TMP"
        ;;
    head)
        git archive HEAD snngine_v4 | tar -xf - -C "$TMP"
        rm -rf "$TMP/snngine_v4/tests"
        tar -cf - "${EXCLUDES[@]}" snngine_v4/tests | tar -xf - -C "$TMP"
        git rev-parse HEAD > "$TMP/ENGINE_COMMIT"
        ;;
    *)
        echo "mode must be worktree or head" >&2
        exit 2
        ;;
esac

mkdir -p "$TMP/setups/runpod-assembly-association" "$TMP/setups/runpod-engine-tests"
cp setups/runpod-assembly-association/assoc_*.py "$TMP/setups/runpod-assembly-association/"
tar -cf - "${EXCLUDES[@]}" setups/runpod-chem-diffusion setups/runpod-engine-smoke-test | tar -xf - -C "$TMP"
cp setups/runpod-engine-tests/pod_run_tests.sh "$TMP/setups/runpod-engine-tests/"
{ echo "mode: $MODE"; echo "head: $(git rev-parse HEAD)"; echo "packed: $(date -u +%Y-%m-%dT%H:%M:%SZ)";
  echo "uncommitted changes in snngine_v4: $(git status --porcelain snngine_v4 | wc -l)"; } > "$TMP/PACK_INFO"

mkdir -p "$(dirname "$OUT")"
# --force-local: a drive letter (E:/...) is not a remote host; owner root: the Windows uid means nothing on the pod
tar --force-local --owner=0 --group=0 -czf "$OUT" -C "$TMP" .
echo "packed $MODE -> $OUT ($(du -h "$OUT" | cut -f1))"
