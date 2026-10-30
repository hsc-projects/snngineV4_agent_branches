# Task: Re-establish the Assembly-Association Results on the Corrected Engine

**Goal:** rerun the experiments whose results came from engine bugs fixed on 2026-10-30, in order of
dependence, so that every conclusion of the assembly-association work again rests on a correctly built
network; correct or withdraw the conclusions that do not survive.

> [!NOTE]
> **Status: proposed (2026-10-30); waits for the user's go.** Steps 0 and 1 change what other sessions
> import from the network volume and need the user's explicit approval. The rules, requirements and
> "Revisions agreed with the user" of `runpod-assembly-association-task.md` apply; `sparse-assemblies-task.md`
> applies to step 6.

## Read first

1. `setups/runpod-engine-tests/engine-tests-report.md`: what was wrong in the engine and what the tests now
   guarantee.
2. `rate-model/round6-report.md`: how the synapse-table transpose was found, and the size of the error at 7^3.
3. `agents/mapping/synapse-construction.md`: the construction pipeline and the invariants of a correct build.
4. `runpod-assembly-association-report.md` ("Handoff for the next agent") and `tuning-log.md`, iterations 38
   to 65, for the experiments named below.

## What was wrong, and what reached the harness

The engine fixes are in commit f56ccf8 and the commit after it (empty-delay autapse search, chemistry kernel
memory layout). What the harness (`assoc_engine.py`, `assoc_protocol.py`) takes from the engine decides which of
them matter:

| engine bug | reaches the harness? | evidence |
|---|---|---|
| 1. Synapse table transposed whenever N != S: each neuron's synapse list came from other neurons' rows (target types per neuron, delays, distance profile wrong; I -> I synapses present; autapses) | **yes, every build** | rewiring (`rewire_by_distance`, from s47) redraws each target but keeps its type (`tgt_exc`) and its built weight, so the per-neuron composition survives |
| 2. Initial weights set by slot range before the final sort: wrong for excitatory sources (their slots hold both target types), right for inhibitory ones (one connection over all slots) | **yes**: E -> I weights (mean 0.466 for 0.45, round 6), and E -> E where `w_ee` is None (s47 survey) | `typed_weights` keeps the built value where a weight is None; `w_ei` is never set |
| 3. Synapse-count correction produced negative delay buckets | **yes, 9^3** (N 42 500, D 16); 11^3 not established | `test_engine.py` `asm9` |
| 4. Spike ring buffer with D > 13 | not triggered in the recorded sessions (argued from `runaway_frac` 0.5 and `i_max` 100, not checked per step) | |
| 5. Engine STDP bounds, presynaptic index, synapse removal | no | `step()` calls `backend.update(False, ...)` (`b_stdp` off); removal never called |
| 6. Chemistry kernel race | no: the harness's fields C1 and C2 are its own (`assoc_fields.py`); C0 is zeroed; the one comparison with the engine's kernel (`substep2_chemistry`, Substep 2) runs at grid 32, where the old kernel was correct | |
| 7. Autapse search (elongated reservoirs refused; misplaced exclusion) | no: every reservoir was cubic, and rewiring removes autapses | |

Size of bug 1 at 7^3 (round 6): an excitatory neuron had about 318 inhibitory targets instead of 400, and
about one neuron in five (whole location groups) none; an inhibitory neuron had about 326 synapses onto
inhibitory neurons (none configured) and 1674 instead of 2000 onto excitatory ones. On the corrected network
one injected group drives a median of about 870 spikes instead of about 470.

## Affected results

| experiments | status |
|---|---|
| s1 checks (Substeps 0 to 3 on synthetic input) | unaffected |
| s1 to s46 (engine wiring, N 5000 to 40 000) | invalid; superseded by the rewired line, not rerun |
| s47 to s72, s74-inh, s75 to s77 (rewired 7^3) | quantitatively invalid; whether the conclusions hold is open |
| s73-g9, s74-reach (9^3); s73-g11 (11^3) | invalid (bugs 1 to 3; bug 3 at 11^3 not established) |
| rate model, rounds 1 to 5 | their targets (s71, s73) are invalid; not rerun (step 7) |
| rate model, round 6 | diagnosis valid; its 9^3 numbers and 7^3 E -> I weights predate fixes 2 and 3 |
| sparse SP0 (field geometry) | unaffected |
| sparse SP1 to SP3 (7^3, rewired) | invalid, except probably the single-synapse threshold (isolated-neuron scan) |
| chem-diffusion videos | plume telemetry wrong (grids of 100 and more cells, bug 6); demo only, rerun only if the numbers are used |
| engine smoke tests | unaffected (stability and timing claims) |

Conclusions that rest on affected results (to be corrected or re-established):

1. "The engine's connectivity is practically flat in space" (tuning log, iteration 39; report Summary, History
   "38 to 40", Substep 6; task revision): produced by bug 1. The corrected engine at 7^3 gives about 516, 336, 119
   and 54 excitatory -> excitatory synapses per group pair at 1, 3 and 6 cells and the largest distance.
   Iteration 38 ("direct synapses do not fall with distance") and iteration 30 likewise.
2. Iteration 25, intra-group density varying about threefold (the reason for `w_intra_ee_total`): probably
   bug 1; not verified.
3. Every regime tuning (gain 4, `gain_ie` 2, `gain_ee_inter` 0.6, intra total 40; iterations 40 and 41): tuned on
   a network that responds at about half strength.
4. Report, "What is established": all-or-none propagation with pair-dependent thresholds (item 1; pairs 3 and 5
   never transfer, 1, 8 and 10 easily; item 8; iteration 45): candidates for an artifact of the groups without
   inhibitory targets.
5. Item 9, ignitions as a finite-size effect (iteration 61): confounded (7^3 had the bimodal composition, 9^3
   did not, and 9^3 had bug 3).
6. Items 2, 3, 6, 7, 10 to 13 (6 of 24 pairs; C2 carries no spatial information, iteration 64; reach against
   containment): quantitatively invalid.
7. Sparse report, Substep 2: "60 to 100 times more inhibition than excitation", no substrate showing
   summation, the stop rule: depend directly on the E/I composition.
8. Rate model, round 5 ("over-propagates", neither model admitted): the models were closer to the correct network
   than the engine (model B with the configured composition predicted 954.5 spikes at 9^3; the corrected engine
   gives 961.5); the fitted factors (`ei_inter`, `w_inter`, `plast_scale`) compensated for bug 1.

Not explained by the fixes: the SP3 crash (illegal address at D 13, hysteresis job); keep the `runaway_frac`
and `i_max` safeguards until its cause is found.

## Steps (in order of dependence)

Each step has a session in the tuning log's format and ends with an entry in a report for this task
(`engine-fix-rerun-report.md`).

0. **Deploy (needs the user's approval).** Put the corrected engine on the network volume (code and a fresh
   backend build per architecture), then run the engine tests there (`setups/runpod-engine-tests/`, `full`)
   and the harness's module checks (`test_assoc_modules.py`). No session may run during the upload.
1. **Build audit**, 7^3 (N 20 000, S 2000) and 9^3 (N 42 500, D 16), unrewired and after
   `rewire_by_distance` (lambda 0.4): per neuron, the synapses onto each type equal the configuration
   (excitatory 400 onto inhibitory, inhibitory none onto inhibitory), no autapses, the delays follow the rule;
   excitatory -> excitatory synapses per group pair fall with distance. Done when the audit passes on both
   sizes; a failure stops the task.
2. **Connectivity survey** (equivalent of s46, s47): distance profile of the unrewired engine at 7^3 and 9^3
   against the rewired one. Decides whether rewiring is still needed (the user decides).
3. **Operating regime** (equivalent of s47regime, s48): Substep 1 on 100 groups plus the saturation diagnostic,
   over `gain`, `gain_ie`, `gain_ee_inter` and the intra-group total. Also decide whether I -> I weights get
   their own gain (`set_gains` scales them by `gain` only).
4. **Propagation survey** (s53, s54): retest all-or-none propagation and pair-dependent thresholds in the new
   regime (conclusion 4).
5. **Protocol** (s69a, 24 pairs or more, with controls) and the uniform-C2 control (s76): the pass rate and
   items 2, 3 and 13.
6. **Grid comparison**: 7^3 (s71 E0, distances 4 and 6) against 9^3 (s73), and 11^3 once bug 3 is ruled out
   there (count-table audit): conclusion 5 and item 12.
7. **Sparse substrate SP1 to SP3** (about $0.65; `sparse-assemblies-task.md` already lists it as pending):
   decides the stop rule (conclusion 7).
8. **Rate model**: no rerun of rounds 1 to 5; steps 5 and 6 are the new ground truth for round 6 step 3
   (model B with the configured composition).

Can be dropped as superseded: s1 to s46 (only their conclusions in the documents need correcting, item 1 and
2 above); iterations 41 to 44, 46 to 52, 54, 55, 57, 59, 60, 62, 63 and 65; the s37 and s76 videos (re-render
after step 5 if wanted).

## Documents to correct once the steps have answered

`runpod-assembly-association-report.md` (Summary, History, "What is established", "The protocol that passes"),
`tuning-log.md` (a note at iterations 25, 30, 38, 39), `runpod-assembly-association-task.md` (the revision that
cites flat connectivity), `sparse-assemblies-report.md` (Substep 2), `rate-model/round5-report.md` and the round 5 status in
`rate-model/rate-model-task.md`.
Correct each with the step that re-established or refuted it; until then, mark the conclusion "pending
re-establishment on the corrected engine (engine-fix-rerun-task.md)".
