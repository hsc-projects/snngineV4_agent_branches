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

## Step 1: build audit (2026-10-30)

Passed. The harness's builds on the volume (7^3, 9^3 and 11^3, the last added by the user; each unrewired and
rewired at lambda 0.4; seed 0) satisfy every invariant of `snngine_v4/tests/network_invariants.py`: every
excitatory neuron has 1600 synapses onto excitatory and 400 onto inhibitory neurons, every inhibitory neuron 2000
onto excitatory and none onto inhibitory neurons; no autapses; every delay follows round((D - 1) d / d_max)
(exact x.5 ties may round either way); E -> E synapses per group pair fall with distance. 11^3 can be used in
step 6. Details and the per-build table: `engine-fix-rerun-log.md`, step 1.

For step 2: the engine's own wiring at 7^3 gives 515, 336 and 119 E -> E synapses per group pair at 1, 3 and 6
cells (the figures of A1), but only 8 to 13 E -> E synapses per excitatory neuron within its own group, against
810 to 860 with rewiring. In the unrewired 9^3 and 11^3 builds the corner-to-corner pairs hold more synapses
than the next distance (not explained).

Cost: about $0.09 (one pod, about 9 minutes at $0.57/h, estimated).
