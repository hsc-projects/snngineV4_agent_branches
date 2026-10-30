# Task: Engine Correctness and Performance Benchmark on Runpod

> [!NOTE]
> **Proposed (2026-10-30), not yet approved by the user.** **[default]** marks a starting value the
> agent may change (log the reason).

## Goal

Measure the simulation engine (`snngine_v4/`, the CUDA kernels behind `AssocEngine`) and the
assembly-association harness that drives it, so that every change to the kernels, whether a bug fix or
an optimization, can be checked for correctness first and for speed second, on comparable hardware.

## Why

The core code has had fundamental errors, which another agent is fixing (2026-10-30). Until now nothing
checked the engine against an independent reference, and no timing was recorded except the harness's
loop time per job. Those loop times already suggest where time goes: with plasticity the harness runs
at about 87 steps per second at N 20,000 (s71) and 21 at N 77,600 (s73), both on an RTX 4090; without
plasticity about 2,200 steps per second at N 20,000 (sparse-task sp1, Substep 1, on an RTX PRO 4500,
so not directly comparable). Network construction took 12 to 20 s (N 20,000 to 77,600, S 2000, on the
same two cards). Without measurements per phase on one card, an optimization could target a phase
that takes little of the time.

## Rules

- **Correctness before speed:** a timing result counts only for a build that passed the correctness
  check of the same commit. Exception: the pre-fix commit's timings, kept only as the speed reference
  for the fixes and labelled as such.
- **Scope:** what the harness uses: network construction (with `rewire_by_distance`), the neuron
  update, the input clamp and spike delivery. The engine's own STDP and chemistry kernels, which the
  harness does not use, are out of scope unless the bug list touches them.
- **Pods only:** the host is used for editing; every run, check and analysis script runs on a pod.
- **Core code:** this task reads `snngine_v4/` and does not change it; whether a pod-based correctness
  check satisfies the rule in `agents/common.md` (no core edits without a local GPU for regression
  testing) is the user's decision, not this task's.
- Pods in EU-RO-1 with the network volume; the backend build is per GPU architecture (see
  `setups/runpod-technical.md`, "Running pod sessions"); never two GPU families on the volume at once.
- **Cost:** own cap **[default] $5**; report the cost after each session.
- No commits without the user's go.
- **Files:** this file, `runpod-engine-benchmark-report.md`, scripts and parameter files in this
  folder, results in `output/` (gitignored by `output/.gitignore`).
- **Order with the core fixes:** the fixing agent's commit and bug list are the input of Substeps 1
  and 3; the volume's code copy is synced to each commit before it is measured, and the backend builds
  parked on the volume (`build_sm<arch>`) are deleted after a core change, or the runner restores a
  stale build.

## Method

### 1. Correctness check

Intent: a kernel change must not change what the network computes, beyond float rounding.

- **Construction checks** (on the built networks of Method 2): S synapses per neuron, counts per
  neuron type as built, no autapses after rewiring (`rewire_by_distance` excludes them; for the
  engine's own construction, whether it allows them is read from the code and recorded), delay
  buckets monotone and ending at S, each synapse's delay equal to the engine's rule for its distance,
  and the synapse counts per group pair against the connection rule (the engine's delay-dependent
  probability, or `rewire_by_distance`'s exp(-d / lambda), within the sampling spread). Construction
  has been a source of past bugs (`agents/common.md`).
- **Analytic micro-cases** (no reference implementation needed): one neuron under a constant or
  one-step current (spike times from the Izhikevich update computed in float32 with the kernel's
  order of operations, so an exact match is expected; float64 only as a sanity check); one synapse
  with a known weight and delay (the current arrives at the step the kernel's delay convention
  implies, read from the code and stated in the script, with size gain x w); a chain of neurons
  (arrival times add up); a neuron with many convergent synapses (the summed input equals the sum of
  the weights that fired). These localize an error to the neuron update, the delay buckets or the
  delivery.
- **Reference for whole networks:** an independent CPU implementation of one step (neuron update,
  input clamp, delivery with delays), written from the kernel code with its line references (reading
  kernel internals is this task's purpose, an exception to the mapping rule in `agents/common.md`).
  Model B of the rate model (`../runpod-assembly-association/rate-model/spiking_group_model.py`) is a
  candidate, but its parity with the engine is itself open (rate-model round 6); it is used only once
  that round has shown step-by-step agreement.
- **Network cases [default]:** three small networks (N 500 to 2,000, S 50 to 200, one with
  distance-dependent rewiring), background input off, a fixed injection schedule, 200 steps; the
  engine's built network (targets, weights, delays, neuron parameters) is exported and fed to the
  reference.
- **Determinism:** each case runs twice on the GPU. `atomicAdd` adds inputs in no fixed order, so even
  two GPU runs may differ in the last bits; that run-to-run spread is the tolerance for the comparison
  with the reference.
- **Pass:** construction checks exact (counts, delays) or within the sampling spread (counts per group
  pair); the micro-cases exact; in the network cases the reference's spike raster equals the GPU's for
  every step before the first step at which the two GPU runs differ from each other (all 200 steps if
  they never differ); after that step, the reference's spike count per location group and step
  differs from the GPU's by no more than the two GPU runs differ from each other.
- The harness itself keeps its own module checks (`test_assoc_modules.py`); this task covers the
  engine below it.
- **Test of the test:** on the pre-fix commit the check must fail wherever a known bug touches the
  cases (bug list from the fixing agent); a check that passes the pre-fix code there is too weak.

### 2. Benchmark matrix

| Axis | Values [default] |
|---|---|
| Network size | N 20,000 (7^3, the engine's default D), 42,500 (9^3, D 16), 77,600 (11^3, D 20) |
| Synapses per neuron | S 200, 2000 |
| Activity | silent (no input); moderate (mean 0.005 spikes per neuron and step, about 5 Hz); high (0.05, about 50 Hz) |
| Phase | network construction; engine steps alone; harness step without plasticity; harness step with plasticity (rule `both`, the passing protocol's settings) |

- **Network:** built as the assembly harness builds it, with the sparse task's setup (lattice of
  assemblies, spacing 2; `rewire` lambda 0.4; the passing protocol's weights and gains), so that the
  numbers apply to the runs that matter; the engine's default construction without rewiring is
  measured once per size as a reference.
- **Construction** depends only on the network: measured for the 6 networks (3 sizes x 2 synapse
  counts), **[default]** 3 builds each.
- **Engine steps** for all 18 configurations (6 networks x 3 activity levels).
- **Harness steps** (without and with plasticity) only at moderate activity (6 configurations): they
  are slow (about 21 steps per second with plasticity at N 77,600) and their cost does not depend
  much on the activity.
- **Activity** comes from the engine's own background input (`set_noise`, probability `pt` per step),
  so that the engine-only phase has no harness work per step; `pt` is calibrated once per network on
  the reference GPU to the target rate and then held fixed. In the predecessor `pt` up to 0.05 gave
  only 0.000 to 0.005 spikes per neuron and round of 100 steps in the route middle (iteration 45,
  survey 5), far below the targets, and the harness's fluctuating background current (`bg`) ignited the
  boosted assemblies (iterations 46 and 52). If `pt` cannot reach a target as a steady state, `bg` is
  used instead (its per-step cost is then part of the engine phase and recorded), or the nearest
  steady rate below a jump is used and recorded.

### 3. Measures

- Per phase: wall time with CUDA synchronization (`torch.cuda.Event` around the Python-level call):
  construction time; steps per second over **[default]** 1,000 steps (harness with plasticity: 300)
  after 200 warm-up steps (50); **[default]** 5 repeats (construction 3), reported as median and
  interquartile range.
- Peak GPU memory: `nvidia-smi` for the whole process (the engine allocates through PyCUDA, which
  `torch.cuda.max_memory_allocated` does not see), plus the torch figure for the harness's tensors.
- Time per kernel only from Nsight Systems runs (point 5): the engine times only a whole update, in
  whole milliseconds on the host (`update_duration`, `snn_simulation.cu` around line 996), and
  per-kernel timers would change the core code. `update_duration` is recorded alongside as a
  cross-check.
- Every result as JSON with the `snngine_v4` commit, the build's architecture, GPU type, driver and CUDA
  version.

### 4. Baseline and regression rule

- **Reference GPU:** RTX 4090 (SM 89). Results on other cards are recorded but compared only with the
  same card. If no RTX 4090 is free in EU-RO-1, the baselines wait rather than switch cards (the sparse
  task met that on 2026-10-29, session sp1); the correctness check may run on any card.
- **Baselines:** the last commit before the core fixes, then the fixed commit (named by their hashes in
  the report).
- **Regression:** a configuration is flagged when its median time exceeds the baseline's by more than
  the larger of **[default]** 10 % of the baseline and three times the larger interquartile range of
  the two runs.
- **Same conditions:** baselines and comparisons on the same GPU type, driver and image, one job at a
  time on the pod (no parallel sessions), after the warm-up.

### 5. Profiling (on demand)

Nsight Systems (timeline: synchronizations, transfers, idle gaps) and, for a flagged or targeted
kernel, Nsight Compute (occupancy, memory throughput, warp divergence). Whether the pod image provides
`nsys` and `ncu` is checked in Substep 0. Known suspects: the warp divergence of the connectivity search
during construction; `atomicAdd` contention in spike delivery; in the harness, the Python loop and the
full (S, N) weight rewrites per step (plasticity, `std`, S4, S5).

## Substeps

0. **Setup:** scripts and parameter files; check that `nsys` / `ncu` exist in the image (install
   otherwise, in the container only); a short smoke run of every script on one configuration.
1. **Correctness check** (Method 1) on the pre-fix commit, then on the fixed commit.
2. **Calibrate the activity levels** per network (Method 2).
3. **Baseline:** the full matrix on the pre-fix commit and on the fixed commit (Method 3, 4).
4. **Profiling** of the two slowest phases (Method 5); a short report of where the time goes.

## Cost estimate

From past runs (`../runpod-assembly-association/output/`): construction 12 to 20 s (N 20,000 to
77,600, S 2000; RTX 4090 and RTX PRO 4500); the harness without plasticity about 2,200 steps per second
at N 20,000 (sp1, RTX PRO 4500; the engine alone is at least that fast); with plasticity 87, 37 and 21
steps per second at N 20,000, 42,500 and 77,600 (s71, s73, RTX 4090). Per commit, at S 2000 (S 200 is
faster):
- construction: (6 networks x 3 builds + 3 default builds) x up to 20 s: about 7 minutes;
- engine steps: 18 configurations x 6,000 steps (warm-up included); at 2,200 steps per second
  (N 20,000) and, assumed, about half and a quarter of that at N 42,500 and 77,600: about 1 to 2
  minutes;
- harness without plasticity: 6 x 6,000 steps: about 1 minute;
- harness with plasticity: 6 x 1,750 steps at 87, 37 and 21 steps per second: about 3 minutes at
  S 2000, less at S 200;
- pod start, backend check and module checks: about 5 minutes; margin for loading and writing.
About 20 minutes per commit, about $0.30 at $0.89/h. Further pod time: Substep 0 (setup, `nsys`
install, smoke runs) about 15 minutes; correctness checks about 10 minutes per commit; calibration
about 10 minutes; profiling about 15 minutes per session. All substeps for two commits, with one
profiling session: about 1.5 to 2 pod-hours, **about $1.3 to $1.8** (cap $5). Writing the reference
and the scripts costs no pod time. The rates at N 42,500 and 77,600 without plasticity are not measured
yet (assumption above); Substep 0's smoke run replaces the estimate before the full matrix.
