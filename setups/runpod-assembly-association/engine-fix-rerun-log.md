# Rerun log: assembly association on the corrected engine

One entry per session of `engine-fix-rerun-task.md`: hypothesis, change, result, decision (as in the archived
`archive-pre-engine-fix/tuning-log.md`). Each step's outcome goes to `engine-fix-rerun-report.md`.

## Step 0 (pod `nf30u221xzjwmt`, 2026-10-30): corrected engine on the network volume

- **Goal:** the volume's checkout at the branch's latest commit (f051b62, which contains the engine fixes of
  f56ccf8 and cc94dde), the old backend builds gone, a fresh build, the module checks passing.
- **Found:** `/workspace/snngineV4_cloud/snngineV4_agent_branches` was not a git clone but an uploaded copy
  (engine files dated 2026-09-29) with backend builds `build` and `build_sm120`.
- **Decision (the user's):** replace it with a clone of the branch from a git bundle; keep the old copy.
- **Change:**
  - Bundle of `docs/runpod-pi-setup` at f051b62 (MD5 d65ff149..., checked on the pod) cloned to the same path;
    `origin` set to the GitHub URL; `git status` clean. The old copy is kept as
    `snngineV4_agent_branches.pre-f051b62`, its builds deleted (compiled from the old CUDA code).
  - Engine tests (`setups/runpod-engine-tests/`, pack `head` at f051b62, run `rerun0-f051b62-full`):
    `full`, 51 tests OK (162 s; CUDA build in the copy, no cached build for its source hash).
  - `runpod_assembly_runner.sh env`: found no build (SM none), built the backend for SM 120 through the
    smoke-test runner (staged CMakeLists fallback, as before) in 81 s; import from the clone confirmed.
- **Result:** module checks (`test_assoc_modules.py`) 73 / 73 on CPU and 73 / 73 on CUDA; `git status` still
  clean after the build. Logs: `output/rerun0/`.
- **Cost:** 1 pod, RTX PRO 4000 Blackwell, $0.57/h, 10:16 to about 10:26 UTC, about $0.10 (estimated from the
  lifetime); terminated (delete 204, `get-pod` 404).
- **Note:** a pod not created by this task, `s9o38cl9s4qvny` ("r6-fixed-engine", same volume), was created at
  10:20:42 UTC, during the deploy: the rate model's round 6 repeat on the fixed engine
  (`rate-model/round6_fixed_pod.sh`). It ran from its own copy of the repository and wrote only the build cache
  and its results on the volume, not the checkout; terminated by its session.
- **Decision:** step 0 done; step 1 waits for the user's go and cost cap.
