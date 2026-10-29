# Task: Minimal Version of the Main Feature (Assembly Association via Chemical Release and Gated Plasticity)

> [!NOTE]
> **Status: approved by the user; work stopped after iteration 65 at 6 of 24 pairs (see the report);
> continued in `sparse-assemblies-task.md`. Later decisions of
> the user, listed under "Revisions agreed with the user" at the end, take precedence over the text
> below where they differ.** **[default]**
> marks a starting value the user adopted; the agent may change it (see
> "Defaults"). The requirements and the protocol below are not the agent's to
> change.

> [!IMPORTANT]
> **Read first:** the Workflow and "Cloud and infrastructure work" sections of
> [`agents/common.md`](file:///E:/dev/snngineV4_agent_branches/agents/common.md);
> [`agents/main_feature/main-feature-readme-reconstruction.md`](file:///E:/dev/snngineV4_agent_branches/agents/main_feature/main-feature-readme-reconstruction.md)
> (the concept, in full); the sibling task
> [`runpod-chem-diffusion`](file:///E:/dev/snngineV4_agent_branches/setups/runpod-chem-diffusion/runpod-chem-diffusion-task.md)
> (pod lifecycle and exact `exec_pod.py` commands) and
> [`setups/runpod-technical.md`](file:///E:/dev/snngineV4_agent_branches/setups/runpod-technical.md).
> Do not invent claims about the concept; if something is underspecified, ask
> the user.

## Goal

Two assemblies, A and B, anywhere in a reservoir, are activated together by
current injection. Chemicals released in proportion to neuron activity, plus
chemical-gated weight changes, lead to a *short circuit state*. Afterwards,
activating A alone activates B (or the reverse; either counts), an
associative memory in the reservoir. This task implements and tunes only this
**minimal version** of the main feature, not the full system (PL, STMM,
vascular network, sleep cycle).

## Requirements (stated by the user)

- **No cheating:** stay physically and biologically plausible enough. It must
  work between *any chosen pair* of assemblies in a large reservoir, not only
  a tuned pair. Overcoming the distance between A and B is the point. The end
  goal is a large reservoir; use smaller sizes for what is being tested.
- A and B know nothing of each other's positions. The association forms
  through the spatial spread of the chemicals alone, along multi-hop paths
  through *existing* synapses and the neurons between A and B.
- An **assembly** is the set of neurons at one grid location (a location
  group), *active* when the average activity there is above a level. The
  active state must be *obviously visible* in the simulation and the videos.
- Chemicals are released in proportion to neuron activity, at the neuron's
  location. Plasticity only reweights existing synapses (the engine fixes
  N x S).
- Rounds: as many as needed until it works; **fewer is better**. Be
  efficient.
- **Allowed shortcuts** (the first is not cheating; the second "could be
  allowed"):
  1. *Intra-group weights:* raise the weights between neurons within one
     location, so activating a few activates the whole assembly.
  2. *Local energy:* neurons use up local energy, so a short circuit
     concentrates activity around the relevant neurons and passively
     suppresses activity around others, without inhibitory synapses. Its
     purpose is to facilitate the hardening under C2.
- Beyond the shortcuts, nothing may be set per pair (no pair-specific weights,
  direct A-to-B synapses, chemical sources or gains). Global parameters (N, S,
  D, G, connection probabilities, weights by neuron type, chemical,
  plasticity and energy parameters) may be tuned, identically for every pair.

## Protocol (confirmed by the user)

1. **Joint activation rounds (C1 phase).** Inject current into A and B
   together. Active neurons release C1; weight changes are non-permanent.
   Repeat until the test succeeds. C1 builds up where activity repeatedly
   flows between A and B, not around neurons that fired incidentally.
2. **Short circuit stage (C2 phase).** Keep A and B jointly active. C2 is
   released in proportion to activity; weight changes become permanent where
   C1 and C2 are both high.
3. **Test.** Inject current into A alone; check whether B becomes active.

What "non-permanent" means for a weight, the thresholds, the chemical decay
and the exact gating rule are **what this task has to figure out**.

## Defaults

- Activity `A_g(t)` = fraction of group `g`'s neurons that fired within the
  last `W` ms. **[default]** active `A_g >= 0.5`, inactive `A_g <= 0.1`,
  `W = 20 ms` (assuming 1 ms per simulation step; confirm in Substep 0); at
  least 20 neurons per group (choose N and the grid segmentation for it).
- **[default]** `k = 3` neurons injected per assembly; one round = 50 steps of
  injection plus a 50-step gap; success = `A_B >= 0.5` within 100 steps of the
  start of the injection into A.
- **Revising:** if implementation or testing shows another value is needed,
  change it and log it with the reason (`tuning-log.md`, or the report for
  non-tuning changes). Do not weaken a success criterion merely to make a test
  pass; adjust a threshold only when the measurement itself is the problem
  (e.g. a group too small for a stable `A_g`). The exact gating rule may be
  revised within the requirements.

## Rules

1. **Confinement.** Everything lives in `setups/runpod-assembly-association/`.
   Do not modify `snngine_v4/`, `snngine3d/` or sibling task folders; import
   or invoke sibling code (e.g. `runpod-engine-smoke-test/exec_pod.py`).
2. **Kernels.** Start with C1 and C2 (and the optional energy) as PyTorch
   fields stepped between simulation steps, and plasticity applied to the
   weight tensor from Python. The agent may then write improved or new CUDA
   kernels as new or copied files in this folder (build as in
   `runpod-engine-smoke-test/CMakeLists.txt`) and use them *instead of* the
   engine's; originals stay untouched. A replacement kernel must first
   reproduce the original's behaviour with the new feature off.
3. **Pods and cost.** `EU-RO-1`, `SECURE` cloud, volume `qze81dpw7q` at
   `/workspace`, as in the chemical diffusion task. The user delegated the pod
   strategy to the agent, so pod sessions that follow "Cost efficiency" run
   under a **standing approval** with a cumulative cap **[default] $20**;
   record each session's cost in the report and stop and ask when the cap is
   reached. Anything else outside the repository still needs the user's go.
   Terminate immediately after the artifacts are downloaded and verify
   `list-pods` returns `[]`.
4. **VCS.** `output/` is gitignored (`*`, `!.gitignore`); never stage media or
   telemetry. No commits or pushes without the user's go.
5. **Reports** follow [`setups/report-format.md`](file:///E:/dev/snngineV4_agent_branches/setups/report-format.md),
   one top-level section per substep.

## Cost efficiency

GPU prices are about $0.25 to $0.60 per hour and earlier whole runs cost
$0.05 to $0.08, so what to avoid is overhead, idle pods, sessions lost to
avoidable errors, and an oversized GPU. Adapt this strategy as measurements
come in.

1. **Quality before spend.** Build Substeps 0 to 3 as independent,
   self-contained modules. Write the chemistry stencil, release rule, `A_g`
   and plasticity math to run on CPU tensors and test them without a GPU
   against analytic expectations (conservation without decay, proportional
   release, symmetric diffusion, no change when the gate is off, bounds
   respected, `w_fast` decay curve). `agents/common.md` forbids testing the
   *main application* (GPU and PyQt); these checks run only the new,
   engine-independent modules. Reread modules and runner before any pod
   session (shapes, dtypes, device, padding, the kernel's
   `(height, width, depth)` axis order).
2. **Few, full sessions.** Run Substeps 0 to 3 together in one session, each
   as its own test with its own pass/fail line. Batch many parameter sets per
   session in the tuning loop. Start every session with a cheap preflight
   (imports, backend construction, shapes and devices, weight read/write, a
   few steps) that aborts at the first failure.
3. **No debugging on the pod.** On failure, diagnose from the saved logs and
   telemetry, fix and re-review locally, then start a new session. Save
   enough diagnostics in every run (per-test results, snapshots).
4. **One cheap GPU, one architecture.** The backend build is
   architecture-specific (the smoke test builds SM 8.9 by default; the
   chemical diffusion runs also used a Blackwell card, see its report for
   how), so switching families costs a rebuild. Switch only if a faster card
   lowers cost *per result* (price per hour times time per job).
5. **Metrics runs vs. video runs.** Tuning runs record telemetry only and skip
   the EGL/ffmpeg install and encoding. Record videos at milestones (a
   substep passing, final success) and when visibility must be checked.
6. **Keep state on the volume:** venv, built backend, own kernel builds, and
   (if construction time matters; measure it) cached networks keyed by
   `(N, S, D, G, seed)`. Within a session, build the network once and reuse
   it across parameter sets by resetting state, weights and chemicals.
7. **One queue runner per session:** jobs from parameter files, results
   written incrementally with a done marker per job (reruns resume), a per-job
   and a per-session wall-clock limit (**[default]** 45 minutes), one summary
   at the end. If GPU utilization is low (small reservoirs), run independent
   jobs in parallel on the same GPU.
8. **Keep-alive rule:** idle time costs the hourly price and a restart costs
   the measured startup plus setup time at the same rate, so terminate after a
   batch unless the next batch can start sooner than that. With the
   environment on the volume, default to terminating after every batch.
9. **Measure and adapt.** Record per session: GPU and price, startup, setup
   and run time, GPU utilization, steps per second, cost. `SECURE` cloud only
   unless the user agrees to interruptible or community pods.

## Engine facts to build on

Start from
[`generate_chem_diffusion_video.py`](file:///E:/dev/snngineV4_agent_branches/setups/runpod-chem-diffusion/generate_chem_diffusion_video.py)
(headless network build, simulation stepping, chemical buffers, rendering).
Device pointers into the backend are extracted in
`snngine_v4/nn/sim/simulation.py` (`_make_simulator_backend`); synapse tensors
(`N_rep`, `N_weights`) are built in `snngine_v4/nn/synapses.py`; neuron and
group state layouts in `snngine_v4/nn/config_models/`; the kernels are in
`snngine_v4/nn/cuda_backend/src/simulation/snn_simulation.cu`.

Verified in code:
- The runner steps once per step from Python: `sim_backend.update(False,
  False)`, then `sim_backend.update_chemical_concentrations()`. The backend
  exposes a `stdp_active` flag.
- From the chemical diffusion task: pad backing tensors by +2 per axis;
  `k_val <= 1/6` for the 3D stencil; clear the `b_test_init` test values; the
  `b_update_chemical_concentrations` setter bug. The kernel clamps voxels with
  `C_source > 0` and caps concentrations at 2000.

Verified in SNNgine3D's kernel (read in full; snngine_v4's is a port with the
same structure at the same lines, checked by search only):
- **Input current:** row 7 of `N_states`, reset to 0 every step, synaptic
  currents added with `atomicAdd`. Inject into chosen neurons via the built-in
  sensory input (per-neuron flag `b_sensory_input`, per-group currents
  `sensory_input_current0/1`, defaults 65 and 25 in `lgroup_states.py`), or by
  adding to that row from Python (unverified).
- **Thalamic noise:** groups flagged `b_thalamic_input` get random input
  currents (defaults 25 inhibitory, 15 excitatory). Keep off for quiet
  baselines, or set deliberately.
- **Group activity:** `G_firing_count_hist` counts only *excitatory* spikes,
  only in monitored groups, in a rolling history; divide by the group's
  excitatory count to get `A_g`.
- **Weight bounds:** excitatory `[0.05, 1]`, inhibitory `[-1, -0.05]`;
  preserve them.
- **Existing STDP (template for the Python-side rule):** multiplicative,
  soft-bounded `dw *= |w| * (bound - |w|)`, clipped; a downstream update
  (post fired after pre, within the delay) and an upstream update (when a
  neuron fires, pre-synaptic partners that fired within `2D + 1` steps before;
  skipped for sensory groups); sign and size depend on the target's type and
  the group-pair config. The chemical gate replaces that group-pair config.

From the mapping docs (`agents/mapping/`; not re-verified in the kernel):
location groups (`G` grid cells) and `N x S` weights with targets in `N_rep`;
the built-in STDP is gated by a fixed per-group-pair sign, so **keep it off**
(`stdp_active = False`); the kernel's own `C0` field is not needed, keep its
sources at zero.

Unverified (settled first, in Substep 0): reading per-group activity and
writing `N_weights` between steps without disturbing cached device pointers;
whether adding to the input-current row from Python works (else use the
built-in sensory input); the mapping from neuron positions to chemical-grid
voxels.

## Substeps (each independently testable; later ones build on earlier ones)

### Substep 0: Harness
Headless per-step loop with hooks, a parameter file (seeds, sizes, rule
parameters), JSON telemetry (`A_g(t)`, per-round A/B responses, rounds,
weight-change statistics by distance from the A-B line, chemical snapshots),
and a video panel with `A_g(t)` as a heat map over the grid and active
assemblies outlined (reuse the sibling renderers by import).
**Pass:** an unstimulated run shows all groups inactive; telemetry and video
are produced; the unverified facts are settled (weights read and written
between steps; injection method chosen; voxel mapping documented; thalamic
noise state and step length recorded).

### Substep 1: Assembly activation
Inject into `k` neurons of group A and raise intra-group weights (shortcut 1)
until the whole group is active.
**Pass:** `A_A >= 0.5` while all other groups stay `<= 0.1`, for several
randomly chosen groups; obviously visible in the video.

### Substep 2: Chemical release, diffusion, optional energy
C1 and C2 as PyTorch fields: release at each firing neuron's voxel in
proportion to its firing, 7-point diffusion, decay.
**Pass:** release is proportional to activity (scale the stimulus); diffusion
matches the kernel's `C0` on the same input (one identical *clamped* source
through both); a plume forms around active assemblies and fades afterwards.

*Optional energy field (shortcut 2):* firing consumes energy at the neuron's
location, energy recovers toward a baseline (and may spread locally), and
excitability depends on local energy; the coupling is the agent's choice
**[default idea: scale each neuron's input current by local energy]**. Build
and test it independently; use it only if needed for the hardening under C2.
**Pass (energy):** consumption proportional to firing; recovery after activity
stops; sustained concentrated activity lowers the firing (`A_g`) of nearby
neurons outside it compared with energy off, with no inhibitory-synapse
change.

### Substep 3: Chemical-gated plasticity (isolated)
Weight change on existing synapses gated by local concentration and pre/post
timing, with a non-permanent and a permanent part; drive it with synthetic,
clamped activity and chemistry. **[default implementation]:** shadow tensors
`w_perm` and `w_fast`, `w_perm + w_fast` written into `N_weights` each step,
`w_fast` decays and `w_perm` does not. **[default starting rule]:** the
existing STDP's timing windows, soft-bounded form and bounds, with the
group-pair gate replaced by a chemical gate: changes at synapses whose
post-neuron lies in a high-C1 region go into `w_fast` and move into `w_perm`
where C1 and C2 are both above threshold.
**Pass:** weights change only where the gate is on; `w_fast` decays as
specified; `w_perm` persists; nothing outside the gated region changes.

### Substep 4: Full protocol, small reservoir
Run the protocol with A and B close together. During the test, release and
plasticity are frozen, only A is stimulated (same `k` and current as in
Substep 1), B gets no input.
**Pass (success criterion of the minimal version):** `A_B >= 0.5` within the
window after injecting A alone (or the reverse), with
- **control 0:** the same test before the protocol does not activate B;
- **control 1:** with chemistry or gating disabled, no association;
- **control 2:** an unrelated third group C stays `<= 0.1`;
- **control 3 (if energy is used):** also record the result with energy off;
- the result holds for at least two seeds.
Record the number of rounds needed.

### Substep 5: Tuning loop (autonomous)
Iterate until Substep 4 passes with as few rounds as possible, then until
Substep 6 passes.
1. Hypothesize from the last run's telemetry (no activity transfer, chemicals
   too diffuse or weak, weights saturating or decaying too fast, ...).
2. Change parameters first (injection current, `k`, round length and gap,
   release gains, diffusion and decay of C1 and C2, gating thresholds,
   learning rates, `w_fast` decay, weight bounds, intra-group boost, energy
   parameters if used, global network parameters); change code (including own
   kernels) only when parameters cannot address it.
3. Run several settings per session; download results; terminate the pod.
4. Log hypothesis, change, result and decision in `tuning-log.md`.
5. Stop and report to the user on success, when the cost cap is reached, or
   **[default]** after 10 consecutive iterations without progress on the
   failing criterion.

### Substep 6: Scale-up and any-pair test
Grow the reservoir stepwise (**[default]** small, medium, large, then the
largest that fits the GPU) and test randomly chosen pairs at increasing
distance, including far-apart pairs.
**Pass:** the Substep 4 criterion with all controls holds for random pairs,
including distant ones, in the large reservoir, without pair-specific tuning.
Record VRAM use and steps per second. If pairs beyond some distance are
unreachable through existing synapses, report that threshold as a finding.

### Substep 7: Assessment video (last)
Once the minimal version works (or at the end of the work, on the best run so far), render
one video in which the user can judge visually whether the association formed.
- **3D view:** neurons as markers (A, B and C outlined), and the synapses whose permanent
  weight changed (`w_perm` against the initial weights), drawn as lines coloured by the size
  of the change, growing as the protocol runs. Reuse the line approach of the old code
  (SNNgine3D `SynapseLineVisual` / `CudaLineVisual`: VisPy `LineVisual` with
  `method='gl'`, `antialias=False`, width 1); use `connect='segments'` with two vertices per
  synapse so that each synapse gets its own colour.
- **Phase timeline:** a flat horizontal bar along the bottom, in the style of
  `sleep_timeline.png`, with one coloured segment per protocol phase (gap, joint activation
  with C1 release, C1-phase test, C2 stage, final test A alone), and a moving vertical
  playhead showing the current simulation step, like a video player's progress bar.
- Optional side panels: `A_g(t)` for A, B and C, and C1 / C2 along the A-B line.
**Pass:** the user can tell from the video which phase is running, where synapses were
reinforced (between A and B, not elsewhere), and whether B becomes active when A alone is
stimulated in the final test.

### Substep 8: Sparse assemblies (last; not fully formulated yet)
Noted by the user on 2026-10-25; to be formulated with the user later. Substeps 1 to 7 treat
every grid cell as an assembly (the intra-group boost of shortcut 1 is applied to every
location group). In the intended setup only some grid locations are assemblies; the neurons
between them are ordinary reservoir neurons without the boost. Fixed so far:
- assemblies are separated by at least one non-assembly grid cell;
- C is an assembly.

## Artifacts

```text
setups/runpod-assembly-association/
├── runpod-assembly-association-task.md      # this file
├── runpod-assembly-association-report.md    # report, one section per substep (created during the work)
├── tuning-log.md                            # one entry per tuning iteration
├── params/                                  # parameter files (one per run or sweep)
├── *.py, runpod_assembly_runner.sh          # harness, chemistry, plasticity, runner
├── kernels/                                 # own CUDA kernels and build files, if written
└── output/                                  # gitignored videos and telemetry
```

## Revisions agreed with the user (2026-10-26)

1. **Wiring:** the engine's connectivity is practically flat in space, so the harness rewires
   synapses by distance (λ = 0.4 cells); distance is measured relative to the connection range.
2. **Pass criterion of Substep 4:** A -> B (or the reverse) >= 0.5 in the final test, no runaway, at
   most 10 % of all groups active outside A, B and the route; a few stray groups are acceptable,
   whole-network activation is not. Control 2 (C <= 0.1) is recorded but no longer a pass condition.
3. **C1 (provisional):** may be skipped in the minimal version, where current is injected directly
   into A and B.
4. **C2:** released in the short circuit state by every active neuron in proportion to its activity.
5. **Controls:** control 1 concerns C2 while C1 is skipped; a joint-activation control is added (A
   and B trained in alternating rounds must not become associated).
6. **Energy (shortcut 2):** may take the form of a global fuel (C3) delivered where it is used.
7. **Cost cap:** $90.
