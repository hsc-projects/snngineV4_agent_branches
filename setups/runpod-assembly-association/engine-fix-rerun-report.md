# Report: assembly association on the corrected engine

Report of `engine-fix-rerun-task.md`: one section per step; the sessions are in `engine-fix-rerun-log.md`. At the
end, conclusions A1 to A8 of the task, each as holds, changes or falls.

## Step 0: corrected engine on the network volume (2026-10-30)

Done. The volume's checkout `/workspace/snngineV4_cloud/snngineV4_agent_branches` is now a git clone of
`docs/runpod-pi-setup` at f051b62 (from a bundle; `git status` clean). It replaced an uploaded, non-git copy
with engine files from 2026-09-29, kept as `snngineV4_agent_branches.pre-f051b62` without its backend builds.

| check | result |
|---|---|
| engine tests on f051b62 (`full`, run `rerun0-f051b62-full`) | 51 tests OK |
| backend build on the volume (`runpod_assembly_runner.sh env`) | SM 120, built afresh in 81 s; imported from the clone |
| module checks (`test_assoc_modules.py`) | 73 / 73 on CPU, 73 / 73 on CUDA |

The volume holds a backend build for SM 120 (Blackwell) only. The first session on another architecture
(RTX 4090 or L4, SM 89) builds its own, so such a batch starts with one pod, not several (parallel first
builds race over `build`).

Cost: about $0.10 (one pod, about 10 minutes at $0.57/h, estimated).
