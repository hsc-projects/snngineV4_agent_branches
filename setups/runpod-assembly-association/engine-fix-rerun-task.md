# Task: Re-establish the Assembly-Association Results on the Corrected Engine

**Goal:** rerun the experiments whose results came from engine bugs fixed on 2026-10-30, in order of
dependence, so that every conclusion of the assembly-association work again rests on a correctly built
network; state for each earlier conclusion whether it holds, changes or falls.

> [!NOTE]
> **Status: proposed (2026-10-30); waits for the user's go.** Step 0 changes the engine that every session
> imports from the network volume and needs the user's explicit approval. The requirements, rules and
> "Revisions agreed with the user" of `runpod-assembly-association-task.md` apply (revision 1, the rewiring,
> rests on a finding of the bug and is decided again in step 2); `sparse-assemblies-task.md` applies to step 7.
> **[default]** marks a starting value the agent may change (log the reason).

## Read first

1. `agents/common.md`: shared rules (no runs on the development host; commits and pod sessions only with the
   user's go).
2. `setups/runpod-engine-tests/engine-tests-report.md`: what was wrong in the engine, and what its test suite
   now guarantees.
3. `rate-model/round6-report.md`: how the transposed synapse table was found, and the size of the error at 7^3.
4. `agents/mapping/synapse-construction.md`: the construction pipeline and the invariants of a correct build.
5. `runpod-assembly-association-task.md` (requirements, protocol, revisions) and `assembly-association-glossary.md`
   (terms).
6. `archive-pre-engine-fix/README.md`, then in that folder `runpod-assembly-association-report.md` ("Handoff
   for the next agent", above all "How to run a session") and `tuning-log.md` for the iterations named below.
   Their numbers come from the faulty engine; read them for the method.
7. `setups/runpod-technical.md`, "Running pod sessions": the pod workflow.

## What was wrong, and what reached the harness

The engine fixes are in commits f56ccf8 and cc94dde. What the harness (`assoc_engine.py`, `assoc_protocol.py`)
takes from the engine decides which of them matter:

| engine bug | reaches the harness? | evidence |
|---|---|---|
| 1. Synapse table transposed whenever N != S: each neuron's synapse list came from other neurons' rows (target types per neuron, delays, distance profile wrong; I -> I synapses present; autapses) | **yes, every build** | rewiring (`rewire_by_distance`, from s47) redraws each target but keeps its type (`tgt_exc`) and its built weight, so the per-neuron composition survives |
| 2. Initial weights set by slot range before the final sort: wrong for excitatory sources (their slots hold both target types), right for inhibitory ones (one connection over all slots) | **yes**: E -> I weights (mean 0.466 for 0.45, round 6), and E -> E where `w_ee` is None (s47 survey) | `typed_weights` keeps the built value where a weight is None; `w_ei` is never set |
| 3. Synapse-count correction produced negative delay buckets | **yes, 9^3** (N 42 500, D 16); 11^3 not established | `snngine_v4/tests/test_engine.py`, configuration `asm9` |
| 4. Spike ring buffer with D > 13 | not triggered in the recorded sessions (argued from `runaway_frac` 0.5 and `i_max` 100, not checked per step) | |
| 5. Engine STDP bounds, presynaptic index, synapse removal | no | `step()` calls `backend.update(False, ...)` (`b_stdp` off); removal never called |
| 6. Chemistry kernel race | no: the harness's fields C1 and C2 are its own (`assoc_fields.py`); C0 is zeroed; the one comparison with the engine's kernel (`substep2_chemistry`, Substep 2) runs at grid 32, where the old kernel was correct | |
| 7. Autapse search (elongated reservoirs refused; misplaced exclusion) | no: every reservoir was cubic, and rewiring removes autapses | |

Size of bug 1 at 7^3 (round 6): an excitatory neuron had about 318 inhibitory targets instead of 400, and
about one neuron in five (whole location groups) none; an inhibitory neuron had about 326 synapses onto
inhibitory neurons (none configured) and 1674 instead of 2000 onto excitatory ones. On the corrected network
one injected group drives a median of about 790 spikes instead of about 470 at 7^3, and about 970 instead of
about 410 at 9^3 (A-alone test before learning, rewired, the archived parameters; `rate-model/round6-report.md`,
"After the engine fixes").

## Affected results

All in `archive-pre-engine-fix/`.

| experiments | status |
|---|---|
| s1 checks (Substeps 0 to 3 on synthetic input) | unaffected |
| s1 to s46 (engine wiring, N 5000 to 40 000) | invalid; superseded by the rewired line, not rerun |
| s47 to s72, s74-inh, s75 to s77 (rewired 7^3) | quantitatively invalid; whether the conclusions hold is open |
| s73-g9, s74-reach (9^3); s73-g11 (11^3) | invalid (bugs 1 to 3; bug 3 at 11^3 not established) |
| rate model, rounds 1 to 5 | their ground truth (s71, s73) is invalid; not rerun (step 8) |
| rate model, round 6 (`rate-model/round6-report.md`, not archived) | diagnosis valid; steps 1 and 2 repeated on the fixed engine (rewired at lambda 0.4): model B with the configured composition matches it ("After the engine fixes") |
| sparse SP0 (field geometry) | unaffected |
| sparse SP1 to SP3 (7^3, rewired) | invalid, except probably the single-synapse threshold (isolated-neuron scan) |
| chem-diffusion videos (`setups/runpod-chem-diffusion/`) | plume telemetry wrong (grids of 100 and more cells, bug 6); demo only, rerun only if the numbers are used |
| engine smoke tests | unaffected (stability and timing claims) |

Conclusions to re-examine (A1 to A8; the rerun report states the outcome of each):

- **A1.** "The engine's connectivity is practically flat in space" (tuning log, iteration 39; report Summary,
  History "38 to 40", Substep 6; revision 1 of the task): produced by bug 1. The corrected engine at 7^3 gives
  about 516, 336, 119 and 54 excitatory -> excitatory synapses per group pair at 1, 3 and 6 cells and the
  largest distance. Iteration 38 ("direct synapses do not fall with distance") and iteration 30 likewise.
- **A2.** Iteration 25, intra-group density varying about threefold (the reason for `w_intra_ee_total`):
  probably bug 1; not verified.
- **A3.** Every regime tuning (gain 4, `gain_ie` 2, `gain_ee_inter` 0.6, intra total 40; iterations 40 and 41):
  tuned on a network that responds at about half strength.
- **A4.** Report, "What is established", items 1 and 8 (iteration 45): all-or-none propagation with
  pair-dependent thresholds (pairs 3 and 5 never transfer, 1, 8 and 10 easily): candidates for an artifact of
  the groups without inhibitory targets.
- **A5.** Item 9, ignitions as a finite-size effect (iteration 61): confounded (7^3 had the bimodal composition,
  9^3 did not, and 9^3 had bug 3).
- **A6.** Items 2, 3, 6, 7, 10 to 13 (6 of 24 pairs; C2 carries no spatial information, iteration 64; reach
  against containment): quantitatively invalid.
- **A7.** Sparse report, Substep 2: "60 to 100 times more inhibition than excitation", no substrate showing
  summation, the stop rule: depend directly on the E/I composition.
- **A8.** Rate model, round 5 ("over-propagates", neither model admitted): the models were closer to the
  correct network than the engine (model B with the configured composition predicted 954.5 spikes at 9^3 and 821
  at 7^3; the fixed engine gives 970.5 and 791); the fitted factors (`ei_inter`, `w_inter`, `plast_scale`)
  compensated for bug 1.

Not explained by the fixes: the SP3 crash (illegal memory access at D 13, hysteresis job); keep the
`runaway_frac` and `i_max` safeguards until its cause is found.

## How to run

- Sessions as in the archived report's "How to run a session" (pod body, upload, module checks, start with
  `runpod_assembly_runner.sh start`, collect with `collect_pod_sessions.py`), with these paths: new parameter
  files go to `params/` (named `rerun<step><letter>-<what>.json`, e.g. `rerun3a-regime.json`), built from the
  archived templates named in each step (`archive-pre-engine-fix/params/`); results to `output/` (gitignored).
- Pods: one GPU architecture per batch (`setups/runpod-technical.md`); the user prefers more parallel pods and
  more data points per parameter over sequential minimal sessions, within the cost cap.
- Cost: the cap is set by the user with the go (**[default]** report the cost after every step and stop
  before a step would exceed the cap).
- Log every session in `engine-fix-rerun-log.md` (hypothesis, change, result, decision, as in the archived
  tuning log); each step ends with a section in `engine-fix-rerun-report.md`. Both are new files of this task.

## Steps (in order of dependence)

0. **Deploy the corrected engine to the volume (needs the user's approval; no session may run meanwhile).** On
   one pod: bring the volume's checkout (`/workspace/snngineV4_cloud/snngineV4_agent_branches`) to the latest
   commit of the branch (`git status` first; if it is not a clean clone of the branch, ask the user), delete
   every backend build there (`snngine_v4/nn/cuda_backend/build` and `build_sm*`: they were compiled from the
   old CUDA code, and `runpod_assembly_runner.sh` would restore them), let the runner build afresh
   (`runpod_assembly_runner.sh env` builds the backend when none is there), and run the module checks (`test_assoc_modules.py`,
   CPU and GPU). The engine itself is tested apart from the volume: `setups/runpod-engine-tests/` (`full`
   level, all tests pass on the commit being deployed). Done when both pass.
1. **Build audit** at 7^3 (N 20 000, S 2000) and 9^3 (N 42 500, S 2000, D 16), unrewired and rewired (lambda
   0.4): per neuron, the synapses onto each type equal the configuration (excitatory neurons 400 onto
   inhibitory, inhibitory neurons none onto inhibitory), no autapses, delays by the rule; excitatory ->
   excitatory synapses per group pair fall with distance. Tool: `rate-model/round6_export_engine.py --params
   <file> --no-arrays` (structure audit of the harness's build), with parameter files from
   `session71-d4-s0-p00.json` (7^3) and `session73-g9-d4-s0-a.json` (9^3), each also without `rewire`. The
   unrewired engine build is also covered by the engine tests (`asm7`, `asm9`). Done when the audit passes on
   both sizes; a failure stops the task and goes to the user.
2. **Wiring decision** (revision 1; A1, A2). Rewiring by distance (lambda 0.4) was adopted because the engine's
   connectivity looked flat in space, which bug 1 produced. Measure the engine's own wiring against rewiring at
   7^3 and 9^3, on the wirings: unrewired, rewired at lambda 0.4, and **[default]** rewired at lambda 1.0.
   - **Connectivity** (`conn_survey`, as s46 and s47: `session46-conn-survey.json`,
     `session47survey-rewired.json`): excitatory -> excitatory synapses per group pair against cell distance;
     fit exp(-d / lambda) to the unrewired profile to give the engine's effective lambda.
   - **Activity spread** (`substep1`, as s47regime: `session47regime{a,b,c}-lam0.4.json`): `substep1_activation`
     reports only the largest activity outside the injected group (`others_max`); add the peak activity of every
     other group, summarized by cell distance from the injected group (a harness change, with a check in
     `test_assoc_modules.py`). The regime is tuned only in step 3, so run each wiring at **[default]** three
     values of `gain` around the archived 4, and compare the wirings where the injected group is recruited
     (`A_max` >= `active`) without runaway. Spread decides more than synapse counts: it says whether assemblies
     stay local and routes can be selective (`sparse-assemblies-task.md`). The same output gives the
     intra-group density per group (`intra_ee_per_exc_neuron`; A2: does it still vary about threefold?).
   - **Report**, per wiring and size: effective lambda, spread (the largest distance at which other groups
     exceed `inactive`, and the activity by distance), intra-group density.
   - **Decision (the user's)**: the engine's own wiring if its activity stays local enough for distinct
     routes; otherwise rewiring, with lambda chosen from these measurements; or, longer term, a
     connection-range parameter in the engine's construction (a core change: its own task, with the user's
     approval and engine tests). Record it as a new revision of `runpod-assembly-association-task.md`
     superseding revision 1. Steps 3 to 7 use the chosen wiring (for the engine's own, drop `rewire` from the
     archived templates).
3. **Operating regime** (as s47regime and s48: `session47regime{a,b,c}-lam0.4.json`,
   `session48regime-lam0.4.json`): Substep 1 on 100 groups plus the saturation diagnostic, over `gain`,
   `gain_ie`, `gain_ee_inter` and the intra-group total (A3). Also decide whether I -> I weights get their own
   gain (`set_gains` scales them by `gain` only).
4. **Propagation survey** (as s53 and s54: `session53*-prop-*.json`, `session54*-prop2.json`): all-or-none
   propagation and pair-dependent thresholds in the new regime (A4).
5. **Protocol** (as s69a: `session69a-stage2.json`, 24 pairs or more, with controls) and the uniform-C2 control
   (as s76: `session76-c2u-*.json`): the pass rate and items 2, 3 and 13 (A6).
6. **Grid comparison**: 7^3 (as s71: `session71-d4-*.json`, `session71-d6-*.json`) against 9^3 (as s73:
   `session73-g9-*.json`), and 11^3 (`session73-g11-*.json`) once the build audit (step 1) passes at 11^3 (A5,
   item 12).
7. **Sparse substrate SP1 to SP3** (about $0.65; `sparse-assemblies-task.md`; generators
   `archive-pre-engine-fix/params/make_sparse_sp{1,2,3}.py`): decides the stop rule (A7).
8. **Rate model**: no rerun of rounds 1 to 5; the results of steps 5 and 6 are the new ground truth for round 6
   step 3 (model B with the configured composition; `rate-model/rate-model-task.md`) (A8). Write the per-pair
   classes of steps 5 and 6 in the format of `archive-pre-engine-fix/rate-model/s71_ground_truth.json` and
   `s73_g9_d4_pairs.json`. Round 6 steps 1 and 2 were repeated on the fixed engine with rewiring at lambda 0.4
   (`rate-model/round6-report.md`, "After the engine fixes"); if step 2 here chooses another wiring, repeat
   them on that wiring before round 6 step 3.

Can be dropped as superseded: s1 to s46; iterations 41 to 44, 46 to 52, 54, 55, 57, 59, 60, 62, 63 and 65;
the s37 and s76 videos (re-render after step 5 if wanted).

## Done when

Every step has its report section, and the report lists A1 to A8, each as holds, changes (with the new
result) or falls, with the step that decided it. The archived documents stay as they are; at the end, update
the status notes at the top of `runpod-assembly-association-task.md`, `sparse-assemblies-task.md` and
`rate-model/rate-model-task.md`, and `agents/feature-todos.md`, to point to the rerun report.
