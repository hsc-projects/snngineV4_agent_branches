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

## Step 2: wiring (2026-10-30; decision pending)

Measured at 7^3 and 9^3, network seeds 0 and 1, on the engine's own wiring and rewired at lambda 0.4 and 1.0
(sessions `rerun2a` to `rerun2d`; numbers in `engine-fix-rerun-log.md`, step 2).

| | engine's own | rewired, lambda 1.0 | rewired, lambda 0.4 |
|---|---|---|---|
| effective lambda (cells) | 3.8 (7^3), 4.0 (9^3) | 1.1 | 0.42 to 0.46 |
| E -> E per group pair at 1 / 4 cells (7^3) | 457 / 222 | 1495 / 95 | 1316 / 2 |
| intra-group E -> E per excitatory neuron, median (min to max) | 10 to 13 (6 to 18) | 103 to 123 (50 to 333) | 809 to 846 (512 to 1277) |
| spread at gain 2 to 8 | 0 | 0 | 0 |
| spread at gain 12 / 16 / 24 (cells) | 0 to 5 / 0 to 7 / 4 to 9 | 0 to 1 / 0 to 2 / 1 to 5 | 0 to 1 / 0 to 1 / 0 to 2 |

The engine's own wiring keeps activity inside the injected group up to gain 8; above that, activity reaches
across much of the grid. No gain run gives it a consistent spread of one or two cells: at gain 12 most injected
groups stay alone and the others reach 1 to 5 cells, at gain 16 most reach 3 to 7. Rewired at lambda 0.4, activity stays within one or two
cells at every gain run; at lambda 1.0 within one to five. The regime itself (inhibitory gains, inter-group
gain, intra-group total) is tuned only in step 3, so these spreads compare the wirings at the archived values
of everything but `gain`.

**A1** ("the engine's connectivity is practically flat in space"): **falls.** The corrected engine's E -> E
synapses per group pair fall with distance, with an effective lambda of about 4 cells (7^3: 457 at 1 cell, 73
at 8 cells). Its reach is still about ten times that of rewiring at lambda 0.4.

**A2** (intra-group density varies about threefold, a candidate artifact of bug 1): **changes.** The density
varies about 2.5-fold between groups in the engine's own wiring (6 to 18 synapses per excitatory neuron) and at
lambda 0.4 (512 to 1277), and 5- to 6.6-fold at lambda 1.0, so the variation is not an artifact of bug 1. In the
engine's own wiring the density is about 80 times lower than with rewiring at lambda 0.4.

**Decision (the user's).** The options of the task: the engine's own wiring, rewiring with a chosen lambda, or
later a connection-range parameter in the engine's construction (a core change, its own task).
Recommendation: keep rewiring, now on its own merits rather than because of bug 1: the engine's own wiring
has no gain at which activity stays within a cell or two, which distinct routes need, and it gives assemblies
almost no recurrent synapses. Keep lambda 0.4 as the baseline of steps 3 to 7 (the archived protocol, its
distances and the rate model's exports use it) and run lambda 1.0 as a variant in step 3, since its wider
reach may let A -> B transfers over 4 cells work at lower gains.

Cost: about $0.29 (one check pod, about $0.05; four session pods, about $0.24; estimated).
