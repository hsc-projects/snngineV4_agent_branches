# Assembly association (minimal main feature): report

## Summary

**Status (2026-10-26, iteration 58): the minimal version passes in 6 of 24 pairs at distance 4 with
all controls; the task's goal (any pair, larger distances) is not reached yet.** Substeps 0 to 3
pass. On a distance-dependent wiring (the engine's own wiring is flat in space), two assemblies
injected together become associated over multi-hop routes: joint rounds with learning wherever there
is activity, then a short circuit stage in which C2, released by every active neuron in proportion to
its activity, makes the changes permanent. Under the user's revised criterion (a few strays allowed),
6 of 24 pairs pass with control 0, control 1 (no C2) and a joint-activation control (seed 0: 5 of 12,
seed 1: 1 of 12). C1 is skipped (the user's provisional decision); energy as local fatigue does not
focus the short circuit; the user's C3 fuel is implemented but not yet run. Cost about $56.7 of a $90
cap. Start with "Handoff for the next agent"; "History of approaches" summarizes why earlier
approaches failed.

**Terms.** *Route:* the neurons and synapses between A and B that carry an association (in the code:
`path_groups`, the groups whose cell lies within 1 cell of segment A-B). *Strays:* groups active
(A_g >= 0.5) in a test outside A, B and the route, C included. *Stray limit:* 34 strays (10 % of the
343 groups); a test with more strays, or with a runaway, fails (the user's "whole-network activation
is bad", made measurable). *M / Sh:* the middle of the route and an off-path shell at the same
distance from A and B, compared in the selectivity telemetry.

## Handoff for the next agent

This section replaces every earlier handoff (written 2026-10-26, after s70). It is written for an
agent that starts cold.

### Read first, in this order
1. This section.
2. `tuning-log.md`, iterations 53 to 58 (the current line of work), then 38 to 52 for why the earlier
   approaches failed; iterations 1 to 37 are in `tuning-log-1-37.md`. Italic notes mark conclusions
   that later iterations superseded.
3. The task file `runpod-assembly-association-task.md` (requirements, protocol, rules). Several of its
   points were revised later by the user; "Decisions taken by the user" below takes precedence.
4. `agents/main_feature/main-feature-readme-reconstruction.md` (the concept).

### State
- **No pods running** (`list-pods` returned `[]` after s70). All results up to s70 are in `output/`.
- **Cost:** about $56.7 of the user's **$90** cap ($20.36 billed through s48; later sessions estimated
  from pod lifetimes x $0.89/h, s64 x $0.59/h). Check `list-pod-billing` before the next session.
- **The volume holds the C3 fuel code** (57 module checks pass on CPU and GPU); it has not been run
  in a session yet. `assoc_protocol.py` changed afterwards in a comment only: upload it with the next
  session and compare MD5 sums as usual.
- **Nothing committed.** The user decides about commits.
- **Autonomy:** the user said "continue as you see fit" within the $90 cap (choose sessions, report).

### Open problems (from s69, 24 pairs at d 4)
- **Pass rate:** 6 of 24; 9 pairs transfer but exceed the stray limit; 9 end without association
  (7 never transfer, 2 lose the transfer in consolidation).
- **Seed dependence:** seed 0 5 of 12, seed 1 1 of 12.
- **Distance 6, sparse layouts and the Substep 7 video:** not yet tried with this protocol.

### The protocol that passes (iteration 56; `params/session69a-stage2.json`)
- **Network:** N 20,000, S 2000, 7 x 7 x 7 location groups, every group an assembly (shortcut 1:
  normalized intra-group input, total 40), distance-dependent rewiring `rewire: {"lam": 0.4}`, gain 4,
  `gain_ee_inter` 0.6, `gain_ie` 2, injection k 12 neurons at I 20, runaway check 0.5, input clamp
  +-100.
- **Joint rounds:** A and B injected together (50 steps + 50 gap); C1 skipped (gate open everywhere,
  `theta1` -1, `soft1` 0, C1 gain 0), so learning happens wherever there is activity (rule "both",
  a_pre 0.5), temporary (`w_fast`, tau 2000); after each round a test with A alone on `w_fast`;
  up to 30 rounds.
- **Short circuit stage** once A alone activates B (spread accepted, `accept_uncontained`): A and B
  injected together for 5 to 10 rounds, C2 released by every neuron in proportion to its spikes (gain
  1, no saturation, k 0.02, decay 0.01), `w_fast` moved into `w_perm` at kappa 0.05 per step times a
  C2 gate that rises from 0 at C2 0.6 to 1 at 1.2 (`theta2` 0.6, `soft2` 0.6), no new learning
  (`learn_in_c2` false), no energy.
- **Final test:** A alone (and B alone) on `w_perm` only; pass = B >= 0.5 within 100 steps, no runaway,
  at most 34 of 343 groups active outside A, B and the route (`criterion` "bounded").

### What is established (with the iteration that shows it)
1. **Activity-proportional chemistry cannot select a route that is silent before learning**
   (iterations 41 to 52): the neurons between A and B do not fire under joint injection, and no
   regime of gains, balance, background input or layout makes them fire in a graded way; propagation
   is all-or-none, with pair-dependent thresholds.
2. **Growth plus consolidation finds a route without chemical selection** (iterations 53 and 56):
   learning wherever there is activity, made permanent by capture on transfer (iteration 53) or by the
   C2 short circuit stage (iteration 56), forms associations in about a quarter to a third of the
   pairs; whether C1 gates the learning makes no difference (iteration 53, gating-off control).
3. **The associations need joint activation** (iteration 56).
4. **Energy as local fatigue defocuses** (iterations 55 and 57): the route fires most and loses the most
   excitability, with or without wide spread. It does not change the outcome.
5. **C2 favours the route only weakly:** proportional release 1.4 to 1.5 times higher on the route than
   in the off-path shell (saturating release 1.2 to 1.4), against a firing ratio of about 2.
6. **Measurement notes:** with background input, every condition is a single trial; judge effects
   across pairs (mean against standard error), not by counting pairs above a threshold (iteration 52).
   Pairs 3 and 5 of seed 0 never transfer; pairs 1, 8 and 10 of seed 0 transfer easily.

### Next step (prepared, not run): the C3 fuel sweep (iteration 58)
- **Idea (the user's):** energy depletion is global and usage increases local availability, modelled
  as a third chemical C3 ("fuel"): a fixed total supply per step, delivered in proportion to recent
  local use, consumed by spikes. It should concentrate excitability on A, B and the route during the
  short circuit and starve weaker activity around them, and lower everyone's excitability when
  activity spreads over the whole reservoir.
- **Code:** `assoc_fields.FuelField`, selected with `energy: {"mode": "fuel", ...}` (see its docstring);
  use it in the short circuit stage only (`in_c1` false, `in_c2` true, `in_test` false).
- **Suggested sweep:** the s69 setting (copy a job of `params/session69a-stage2.json`, controls off),
  energy `{"mode": "fuel", "supply": 0.01, "decay": 0.01, "tau": 50, "floor": 0.05, "cap": 2, "k": 0.02}`
  with `consume` 0.5 / 1 / 2 x `beta` 1 / 2, plus energy off as reference; seed 0, the 10 pairs that
  transfer (0, 1, 2, 4, 6 to 11); about 70 jobs, 5 pods, about $1.5. Rough scale: route neurons fire
  about 0.012 spikes per step during injection, with about one neuron per voxel, so the trace there
  reaches about 0.6 against a floor of 0.05, and the route's share of the supply should be several
  times the mean.
- **Measure:** strays in the final test, associations, transfers beyond the limit, and in the last
  short-circuit round `sel_inject_end` (`E`, `spikes_per_exc` and `C2` for the route M against the
  shell Sh): C3 should now be higher on the route than in the shell.
- **If it helps:** confirm with controls (`control_modes` ["no_chemistry", "separate"]) on 2 seeds; the
  energy-off result of the same pairs is control 3. Then distance 6, more seeds, and the Substep 7
  assessment video.

### How to run a session
The general pod workflow (stock, one GPU architecture per batch, upload once, module checks, detached
sessions, one collector per pod, terminating and verifying, cost) is in
[`setups/runpod-technical.md`](../runpod-technical.md), section "Running pod sessions". Specific to
this task:
- **Pod body:** `{"name", "image": "runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404", "dataCenterIds": ["EU-RO-1"], "cloud": "SECURE", "gpu": {"id": "NVIDIA GeForce RTX 4090", "count": 1, "minCudaVersion": "12.8"}, "ports": ["22/tcp"], "startSsh": true, "mounts": {"network": [{"volumeId": "qze81dpw7q", "path": "/workspace"}]}, "disk": 20}`
  (RTX 4090 at $0.89/h; the L4 at $0.59/h runs the same SM 89 build).
- **Upload** from PowerShell: `scp -O -F NUL -i setups/.secrets/id_ed25519 -P PORT -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL <files> root@HOST:/workspace/snngineV4_cloud/snngineV4_agent_branches/setups/runpod-assembly-association/`
  (parameter files to `params/`).
- **Module checks:** `source /workspace/venv/bin/activate; cd /workspace; PYTHONPATH=/workspace/snngineV4_cloud/snngineV4_agent_branches python <dir>/test_assoc_modules.py --device cpu`, then `--device cuda`.
  A failing check aborts every session's preflight.
- **Parameter files:** generate them with short Python snippets from an earlier file (s69 for the
  current protocol); one pair per file keeps sessions short (about 10 to 30 minutes).
- **Start:** `bash <dir>/runpod_assembly_runner.sh start <dir>/params/<file>.json --session-limit-min 60`;
  results go to `/workspace/output/assembly-association/<session>/`, marker `<params stem>.finished`.
- **Collect:** `python collect_pod_sessions.py <pods.csv> output params`, one per pod.
- **Analyse** on the host (weak: standard library only, keep it light):
  `assoc_sweep_summary.py output "<session glob>"` (one line per configuration),
  `assoc_controls_summary.py output "<session glob>"` (one line per pair with controls),
  `assoc_selectivity.py` (surveys: `--propclass`, `--bridge`, `--input`).
- Keep `runpod_assembly_runner.sh` with LF line endings. In module checks, region boundaries must not
  coincide with neuron positions (GPU rounding differs).

### Code: options added in this work (all module-checked, 57 checks)
- **Protocol:** `criterion` ("bounded", default, or "contained"), `max_active_frac` 0.1;
  `control_modes` ("no_chemistry", "gating_off", "separate"); `inject_mode` ("joint" or "alternate",
  used by "separate"); `capture`; `accept_uncontained`; `oracle` (diagnostic); `bridges`; energy per
  phase (`energy.in_c1` / `in_c2` / `in_test`); `energy.mode` "fuel" (C3); `bg` with `targets`
  "ordinary"; `inter_norm`.
- **Plasticity:** `norm_factor`, `weight_dep`, `ltp_events` / `capture`.
- **Tests record:** `n_active_outside` / `active_outside` / `bounded` per test; selectivity telemetry
  (`regions`, `selectivity`, `weight_selectivity`; M = middle of the route, Sh = off-path shell at the
  same distance from A and B).
- **Jobs:** `substep4` (protocol with controls), `prop_survey` (with `bridge_max`, `off_asm_max`),
  `input_survey`, `conn_survey`, `diag_saturated_path`.

### Decisions taken by the user
Earlier: gains and intra-group weights above 1, explicit S, background input, separate inhibitory
gains, the presynaptic C1 rule, excitatory-only `A_g`, the runaway check, self-limiting release,
larger reservoirs, parallel pods, the Substep 7 video, safeguards, module checks on the pod, the
global Substep 1 retune, Substep 8, distance-dependent wiring, bridge assemblies may be active in the
test, at most one free cell between assemblies, the within-group boost is a free parameter, distance
relative to the connection range, synaptic normalization and capture as allowed rule revisions,
speed and data over cost, keep local work small (weak host). On 2026-10-26:
- **pass criterion revised:** an association passes if A -> B (or the reverse) >= 0.5 in the strict
  final test, no runaway, at most 10 % of all groups (34 of 343) active outside A, B and the route,
  control 0 and control 1. A few stray groups are acceptable; whole-network activation is not. C is
  recorded but no longer a pass condition (control 2 dropped);
- **provisional:** C1 may be skipped in the minimal version (the user's intuition: C1 privileges
  short-term-memory assemblies against the dream state's random activations, which the minimal
  version does not have). C2 is released by every active neuron in proportion to its activity during
  the short circuit state, not by B alone. Energy is to focus the short circuit on the real route;
  the user's form: global depletion, usage increases local availability, possibly a third chemical
  C3 (fuel). Control 1 then concerns C2; the joint-activation control is added;
- **cost cap $90** (raised from $50 / $60), "continue as you see fit".
These decisions are also listed in the task file ("Revisions agreed with the user"), and the user's
statements on C1, C2, energy and strays in the README reconstruction.

### Choices made by the agent (tell the user if you change them)
Normalized intra-group input; `gain_ee_inter`; `learn_in_c2` false; the rewiring rule; the final test
on `w_perm`; RTX 4090 (L4 as fallback); the oracle as a diagnostic; the M / Sh regions (`sel_radius`
1); the stray limit counted as groups with A_g >= 0.5 outside A, B and the route (path radius 1 cell),
C included; the C3 form (trace, floor, beta, cap, decay) in `FuelField`.

### Repository state
Nothing committed. Untracked in this folder: `assoc_*.py` (new: `assoc_sweep_summary.py`,
`assoc_controls_summary.py`), `collect_pod_sessions.py`, `test_assoc_modules.py`,
`runpod_assembly_runner.sh`, `wait_pod_session.py`, `params/`, this report, `tuning-log.md`,
`tuning-log-1-37.md`, `output/.gitignore` (results under `output/` are gitignored). Modified (the
documentation pass of 2026-10-26, applied with the user's go): the task file (status note,
"Revisions agreed with the user"), `agents/feature-todos.md` (status line),
`agents/main_feature/main-feature-readme-reconstruction.md` ("Later statements of the user"),
`setups/README.md` (index rows), `setups/runpod-technical.md` ("Running pod sessions").

## History of approaches

Details and numbers are in the tuning log under the iterations named. Iterations 1 to 37
(`tuning-log-1-37.md`) built the harness, found a working regime of gains and numerical safeguards,
retuned for N = 20,000, passed the protocol on the engine's own wiring at distance 2 (10 of 12 pairs,
s36), extended it to longer distances and sparse layouts, and examined why transfers were lost in
consolidation.

| Iterations | Approach | Result |
|---|---|---|
| 38 to 40 | mechanism check; engine wiring against distance-dependent rewiring | associations ran over direct A <-> B synapses; the engine's wiring is flat in space; rewiring with λ 0.4 |
| 41 to 44 | C1-gated learning on the rewired network; oracle diagnostic (chemistry fixed along A-B) | 0 of 60 with real chemistry; oracle 6 of 12 at d 4, 0 of 24 at d 6; the route is silent before learning |
| 45, 46, 50, 52 | propagation regime: layout, gains, excitation / inhibition balance, background input | all-or-none propagation with pair-dependent thresholds; no graded regime |
| 47, 51 | coincidence detection by single neurons or by bridge assemblies | no usable two-sided signal |
| 48, 49, 53 | capture on successful transfer, synaptic normalization; revised pass criterion | 8 of 24 pairs associate; the gating-off control reproduces 6 of the 7 in seed 0 (independent of the chemistry) |
| 54, 55, 57 | C1 skipped; C2 short circuit stage; energy as local fatigue | 3 to 6 associations in 10 to 12 pairs; fatigue defocuses |
| 56 | the best setting without energy, with controls on 2 seeds | 6 of 24 pass; the associations need joint activation |
| 58 | C3 fuel (global supply delivered where it is used) | implemented and module-checked, not run |

## Implementation

| File | Role |
|---|---|
| `assoc_engine.py` | headless network (built through the sibling chem-diffusion builder, imported), per-step hooks, gains (option `inter_norm`), intra-group normalization, **`rewire_by_distance`** |
| `assoc_build.py` | builder with explicit S |
| `assoc_fields.py` | voxel mapping, C1 / C2 fields (release, 7-point zero-flux diffusion, decay), local energy field, **`FuelField`** (C3 fuel), group activity `A_g` |
| `assoc_plasticity.py` | chemical-gated plasticity on the fixed N × S synapses: `w_fast` (decays), `w_perm` (permanent), rule `stdp` / `pre_c1` / `both`, options `consolidate_ee_only`, `weight_dep` ("mult" / "upper") |
| `assoc_protocol.py` | Substeps 0 to 4 as jobs with controls (`control_modes`, joint-activation control, pass `criterion`); `diag_saturated_path`, `conn_survey`, `prop_survey`, `input_survey`; telemetry `split` (E / I, along A-B), `gate_profile`, `direct_stats`, stray counts per test, route selectivity (`regions`, `selectivity`, `weight_selectivity`); diagnostics `freeze_direct_AB`, `oracle` |
| `assoc_queue.py`, `runpod_assembly_runner.sh` | pod-side queue (preflight, one child process per engine, resumable jobs, wall-clock limits) |
| `assoc_summarize.py`, `assoc_selectivity.py`, `wait_pod_session.py` | host-side summaries (selectivity: M / Sh ratios per variant); background waiting for a detached session |
| `assoc_sweep_summary.py`, `assoc_controls_summary.py` | host-side summaries of protocol sessions: one line per configuration, or one line per pair with controls |
| `test_assoc_modules.py` | 57 analytic checks on CPU and GPU (stub engine) |
| `collect_pod_sessions.py` | host-side collector: waits for every pod's session marker, downloads and extracts; exits 1 if a session is still pending |
| `assoc_video.py` | `A_g` heat-map video with C1 / C2 projections |

Engine facts: one `update()` is 1 ms (two Izhikevich half-steps). Current added to row 7 of
`N_states` between steps is read by the next step. The kernel delivers synapse bucket d of
`N_delays` d steps after the spike, and reads only `N_rep`, `N_weights` and `N_delays`; the
pre-synaptic reverse indices matter only to the engine's STDP, which stays off. Inhibitory
neurons project only onto excitatory ones. Weight bounds: excitatory [0.05, 1], inhibitory
[−1, −0.05].

## Substep 0: Harness

**Summary:** passes (s1). Python-side current injection works, weights written between steps
are delivered exactly, the voxel mapping puts every neuron in its group's cell, and an
unstimulated run stays silent. Thalamic noise is off by default, and a step is 1 ms. Telemetry
and video are produced.

## Substep 1: Assembly activation

**Summary:** passes on nearly all groups after a global retune.
- **Engine wiring, N = 20,000, S = 2000:** 332 to 338 of 343 groups (s34). This needed intra-group
  input normalized per neuron (total 30, i.e. current 120 when the whole group fires), k = 12,
  I = 20, g 4, `gain_ie` 4.
- **Rewired, λ 0.4, `gain_ie` 2, intra total 40:** 86 to 91 of 100 groups (s48). The failures
  are spill into neighbours, which rises with `gain_ee_inter`.
- **Sparse layouts, old wiring, total 160:** lattice 52 to 59 of 64, random 27 of 30 (s41).

Early sessions (s1 to s6) found the structural cause of the first failures: too few
intra-group synapses at small S, and weights bounded at 1. Tuning-log iterations 1 to 5 and
25 to 27.

## Substep 2: Chemical release, diffusion, optional energy

**Summary:** passes (s1). Release is proportional to spikes, diffusion matches the engine's C0
kernel (relative error 1e-6), and the plume forms and fades. Energy consumption and recovery
work; the suppression check passed only trivially. In the protocol, energy as local fatigue does not
focus the short circuit (iterations 54, 55, 57); the C3 fuel is prepared (iteration 58).

## Substep 3: Chemical-gated plasticity (isolated)

**Summary:** passes (s1) on the real synapse tensors with synthetic spikes and chemistry:
changes occur only where the gates are on, `w_fast` decays, `w_perm` persists, and the bounds
hold. Module checks: 57 / 57 (iteration 58).

## Substep 4: Full protocol

**Summary:** passes in 6 of 24 pairs at d 4 on the rewired network (iteration 56, s69), under the
user's revised criterion and with C1 skipped (provisional): control 0, control 1 (no C2) and the
joint-activation control hold in all six (seed 0: 5 of 12, seed 1: 1 of 12). Setting:
`params/session69a-stage2.json`; protocol in "Handoff for the next agent". Earlier results:
- **Rewired, C1 skipped, C2 short circuit stage** (s67, s68, s70): 3 to 6 associations in 10 to 12
  pairs in every configuration of C2 reach, threshold and energy.
- **Rewired, capture on transfer** (s66): associations in 8 of 24 pairs; the gating-off control
  reproduces 6 of the 7 in seed 0.
- **Engine wiring, d 2** (s36): 10 of 12 random pairs, 1 to 3 C1 rounds, strict transfer 0.51 to
  1.00. Setting: `params/session36-seed{0,1}-learnc2off-N20k-pairs.json`.
- **Mechanism** (s44, s45; iterations 37, 38):
  - the gates open only at A and B;
  - learning sits on synapses linking A and B directly (about 340 direct E→E synapses per pair,
    at every distance);
  - with those synapses frozen, 6 / 28 pairs pass instead of 20 / 28.
- **Rewired, C1-gated, λ 0.4 / 0.5** (s48 to s50): 0 / 60. Longer chemical reach opens the gate
  along the route but also everywhere else (the C1 profile along A-B is flat, iteration 43).
- **Rewired, decoupled chemistry** (s51, ten variants, 6 pairs each): no contained association
  except the two easy pairs; the gate never prefers the route (M / Sh 0.35 to 1.4).
- **Rewired, oracle chemistry** (diagnostic, s51 / s52): d 4 up to 6 / 12 (a_pre 0.5 or 1), d 6
  0 / 24. The route is silent before learning (iteration 44).
- Control 0 has held throughout. Control 2 (C) is recorded but no longer a pass condition
  (iteration 53). Two fixes for transfers lost in consolidation did not help (s44): consolidating
  onto excitatory neurons only, and a higher C2 threshold.

## Substep 5: Tuning loop

**Summary:** 58 iterations in `tuning-log.md` (index at its top). The main milestones were:
- a working regime (gains, s17 to s19);
- a numerical safeguard (input clamp at −100 and +100) and a runaway detector, which removed a
  kernel crash (s29 to s31);
- the N = 20,000 retune (s32 to s36);
- runaway control at long range (s40, s41);
- the mechanism check and the flat-wiring finding (s44 to s46);
- distance-dependent wiring (s47 onward);
- the oracle split into plasticity and chemistry, and the finding that the route is silent under
  joint activation (s51, s52);
- surveys of the propagation regime, coincidence detection and background input, all negative (s53
  to s65);
- the user's revised criterion and the recheck with controls (s66);
- C1 skipped, the C2 short circuit stage, energy variants, and the first passes with all controls
  (s67 to s70);
- the C3 fuel, prepared (iteration 58).

## Substep 6: Scale-up and any-pair test

**Summary:** not passed.
- **Engine wiring, N = 20,000, d 3 to 6:** best about 55 to 70 % of random pairs (s41, s44),
  but distant pairs are directly connected.
- **Larger N:** does not create distance in this engine (s46).
- **Rewired network:** the current protocol has been run at d 4 only (Substep 4); d 6 is not yet
  tried with it (the C1-gated rule gave 0 of 24 at d 6 even with oracle chemistry, iteration 44).

## Substep 7: Assessment video

**Summary:** specified (task file), not built. The line approach is settled: VisPy
`LineVisual`, `method='gl'`, `connect='segments'`, two vertices per synapse, `antialias=False`,
width 1. A milestone `A_g` video of a passing pair on the old wiring is in
`output/s37-N20k-milestone-video/`.

## Substep 8: Sparse assemblies

**Summary:** tested on the old (flat) wiring only. Total intra current 160 with runaway control:
- `a_pre` 0.25: lattice 22 / 24, random 17 / 24 (d 2 and 4) (s41);
- `a_pre` 0.5: 53 / 72 with about 2 C1 rounds, d 6 18 / 24 (s43).

Not checked for direct synapses. On the rewired network only surveys so far: propagation
(iteration 45, all-or-none) and the bridge threshold diagnostic (iteration 51, no usable
coincidence window). The current protocol (Substep 4) treats every group as an assembly; sparse
layouts are not yet tried with it. Layouts:
`assemblies: {"layout": "lattice", "spacing": 2}` or
`{"layout": "random", "count": 30, "min_gap": 1, "seed": 0}`.

## Pod sessions and cost

| Sessions | GPUs | Notes | Cost |
|---|---|---|---|
| s1 to s23 | RTX 2000 Ada, L4, one RTX 4090 | N ≤ 5000, 1 pod each, 3 to 14 min | about $1.7 |
| s24 to s40 | RTX 4090 (some L4) | N = 20,000 / 40,000, up to 4 pods in parallel | about $8.1 |
| s41 to s45 | 2 to 6 × RTX 4090 | long range, sparse, mechanism check | about $9.8 |
| s46 to s50 | 1 to 8 × RTX 4090 | connectivity survey, rewiring, regime, chemistry reach | about $6.5 (s46 to s48 billed $1.49; s49e / s50 about $5 estimated) |
| s51 | 16 × RTX 4090 | oracle and decoupled chemistry, 6 pairs per variant, 4 to 10 min sessions | about $4.6 (estimated) |
| s52 | 13 × RTX 4090 | oracle learning speed, 12 pairs per variant, 10 to 23 min sessions | about $4.6 (estimated) |
| s53, s54 | 16 + 6 × RTX 4090 | propagation surveys 1 and 2 (no learning, about 1 min sessions) | about $3.5 (estimated) |
| s55, s57, s58 | 8 × RTX 4090, reused | propagation surveys 3 to 5 | about $3.1 (estimated) |
| s59 | 8 × RTX 4090 | balanced background survey | about $1.3 (estimated) |
| s60 | 2 × RTX 4090 | two-sided input survey | about $0.4 (estimated) |
| s61 | 9 × RTX 4090 | convergence range, normalization, capture | about $3.3 (estimated) |
| s62 | 2 × RTX 4090 | capture plus normalization, real chemistry | about $0.8 (estimated) |
| s63 | 10 × RTX 4090 | E / I rebalancing survey (120 jobs, sessions 49 to 80 s, pods about 8 min) | about $1.2 (estimated) |
| s64 | 4 × L4 (RTX 4090 out of capacity) | bridge threshold diagnostic (84 jobs, six sessions, two chained; pods about 10 min) | about $0.4 (estimated) |
| s65 | 5 × RTX 4090 (no further capacity) | background on ordinary neurons (216 jobs, eight sessions, three chained; pods about 15 min) | about $1.1 (estimated) |
| s66 | 5 × RTX 4090 | recheck under the revised criterion (24 protocol jobs with controls, one session chained; pods 20 to 29 min, partly idle) | about $1.6 (estimated) |
| s67 | 3 × RTX 4090 (+ 1 Blackwell that never started) | C2 + energy sweep, stage 1 (192 jobs, 12 sessions, two chains per pod; pods 33 to 64 min) | about $2.4 (estimated) |
| s68 | 5 × RTX 4090 | stage 1b: depleting energy, proportional C2 (90 jobs, two sessions per pod; pods 12 to 23 min) | about $1.2 (estimated) |
| s69, s70 | 5 × RTX 4090 | stage 2 with controls (24 jobs) and shared-pool energy (50 jobs); C3 module checks on the last pod (pods 16 to 36 min) | about $1.8 (estimated) |

Billing (`list-pod-billing`, day buckets 2026-10-25 and 2026-10-26) totals $20.36, which
covers everything up to s48 and may include a few pods of other tasks on 2026-10-25. Later pods
are estimated from pod lifetime × $0.89/h (s51 and s52 were not yet posted when last read).
Read again before s63 (buckets 2026-10-24 to 2026-10-26): $41.78 billed over 180 pods, below the
running estimate, so the estimates are conservative. Total about $56.7 of the $90 cap. The per-session group costs above are approximate sums of the
earlier per-session estimates. Per-pod costs are in `list-pod-billing` (by pod id).

Hiccups:
- `exec_pod.py` from Git Bash rewrites remote paths; PowerShell works.
- A dropped long SSH connection once left a pod idle for 31 minutes, hence detached sessions
  with markers.
- An L4 hit the 45-minute session limit on protocol runs; RTX 4090 only since then.
- `pkill -f` matched its own SSH shell; use the bracket pattern.
