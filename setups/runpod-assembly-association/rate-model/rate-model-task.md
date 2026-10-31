# Task: Rate Model for Screening the Assembly-Association Parameters

> [!IMPORTANT]
> **Status (2026-10-31): round 6 step 3 done, model B admitted** with one fitted parameter, the C2
> consolidation rate `kappa` 0.045 (the protocol's 0.05 x 0.9): on the rerun's own networks it reproduces the
> associations at 7 x 7 x 7 and 9 x 9 x 9 within the spiking intervals (17 and 8 against 15 and 11 of 24; held-out
> pairs: Cohen's kappa 0.83 and 0.82) and the uniform-C2 control (0 against 0) (`round6-report.md`, "Step 3",
> "Fit"). Without the fit it is not admitted (9 x 9 x 9: 1 to 2 associations against 11). Covered: d 4, rewiring at
> lambda 0.4; not covered: 11 x 11 x 11, the engine's own wiring. Next: round 6 step 4 (check on the sparse
> substrate) before the model narrows any range. Round 6 has spent about $6.17 (user's limit about $8).

> [!NOTE]
> **Status (2026-10-30): on hold until the engine-fix rerun.** Round 6 found that the engine's synapse table was
> transposed (`round6-report.md`), so the spiking ground truth of rounds 1 to 5 (s71, s73) came from scrambled
> networks; their reports and ground-truth files are archived in `../archive-pre-engine-fix/rate-model/`. On the
> fixed engine, round 6 steps 1 and 2 were repeated: model B with the configured composition and no fitted
> factor reproduces the single-group response at 7 x 7 x 7 and 9 x 9 x 9 (within 3.8 % and 1.6 %; report,
> "After the engine fixes"). Round 6 step 3 resumes with the new ground truth from `../engine-fix-rerun-task.md`
> (its step 8). The history below is unchanged except where it names the faulty engine's references.

> [!NOTE]
> **Status (2026-10-29): rounds 1 to 5 finished, no model admitted.** Rounds 1 to 3 (smooth rate models: generic
> sigmoid, derived couplings, then transfer functions derived from the engine's Izhikevich neurons)
> all failed the admission test with no transfer in any setting (report, rounds 1 to 3). Round 3's
> diagnosis: recruiting a group from its 12 injected neurons is a spike-synchrony effect a smooth
> rate curve cannot reproduce, and noise smoothing gives inhibition a baseline the silent network
> lacks. **Round 4 tries two group models that keep spikes or their statistics, side by side: model A
> (population density) and model B (reduced spiking network)**; see "Round 4" below. The smooth rate
> model is no longer a candidate for screening; its code is kept. **Round 4 finished (2026-10-29):
> neither model is admitted**; both keep transferring and igniting on 9 x 9 x 9, where the spiking
> network does not (`../archive-pre-engine-fix/rate-model/round4-popdensity-report.md`, `../archive-pre-engine-fix/rate-model/round4-spiking-report.md`). **Round 5 finished
> (2026-10-29): neither model is admitted** (`../archive-pre-engine-fix/rate-model/round5-report.md`): model B at full size passes the 7 x 7 x 7
> classes and the uniform-C2 check but still ignites too often on 9 x 9 x 9; model A has no fix. **Round 6 started (2026-10-30)**; see "Round 6" below. Raw
> results of rounds 2 to 4 were left in the writing sessions' scratchpads, not in the repository; the
> reports hold the numbers. **[default]** marks a starting value the agent may change (log the reason).

## Why

Every decision in the sparse task (`../sparse-assemblies-task.md`) costs pod time (about $2.4 per
full decision of 144 jobs). Many choices are ranges to scan: the connection length lambda, the
diffusion length and threshold of the C1 field, `lam_sup`, the C2 gate. A model with one rate per
location group, the same lattice, wiring statistics, fields and protocol, runs on CPU in seconds and
can discard settings that cannot work before any pod session. It is only useful if it reproduces
what the spiking network did. It never decides a variant on its own: the project uses spiking
networks by choice, and the rate model is a tool, not a version of the concept (user decision,
2026-10-29). The same model is later meant to be extended for standalone use, so keep its code
general (forms and parameters as options).

## Read first

1. `agents/common.md` (shared rules, including the Python rule).
2. `../sparse-assemblies-task.md`: Terms, Setup, Variants, Method (the vocabulary used here).
3. `../archive-pre-engine-fix/runpod-assembly-association-report.md`: "The protocol that passes" and "What is established".
4. `../archive-pre-engine-fix/tuning-log.md`, iterations 56, 59, 61, 63 and 64 (the runs rounds 1 to 5 compared against).
   Items 3 and 4 came from the faulty engine: read them for the protocol and the measures, not for numbers;
   the reference numbers now come from `../engine-fix-rerun-task.md` (its steps 5 and 6).
5. `../archive-pre-engine-fix/rate-model/rate-model-report.md` (rounds 1 to 3, and "Review 2026-10-29"), `../archive-pre-engine-fix/rate-model/round4-popdensity-report.md`,
   `../archive-pre-engine-fix/rate-model/round4-spiking-report.md`, `../archive-pre-engine-fix/rate-model/round5-report.md`
   and `round6-report.md`.
6. Code: `../assoc_build.py` and `../assoc_engine.py` (network construction: neuron counts per type,
   synapses per neuron, weights, gains, intra-group input, `rewire_by_distance`), `../assoc_fields.py`
   (`ChemicalField`, `FuelField`), `../assoc_protocol.py` (protocol, tests, strays). Per-pair outcomes of
   spiking sessions: `python ../assoc_sweep_summary.py <output folder> "<session>*" -v`; the archived sessions'
   results are in `../archive-pre-engine-fix/output/`, new ones in `../output/` (both gitignored; local only).

## Model

- One excitatory and one inhibitory rate unit per location group (343 on 7 x 7 x 7), sigmoid
  transfer function, time constant **[default]** 10 steps (1 step = 1 ms).
- **Coupling derived from the spiking network:** for each pair of groups, the number of synapses of
  each type (E -> E, E -> I, I -> E) times their mean weight and the protocol's gains (`gain`,
  `gain_ee_inter`, `gain_ie`, intra-group input of assemblies), divided by the group's neuron
  count. Every constant is either derived this way (with the code location it comes from) or one of
  the fitted parameters below. No constants without a stated origin; parameters that are accepted
  must be used.
- **Sampled connectivity:** the synapse counts between groups are drawn from the spiking network's
  rule (`rewire_by_distance`: each synapse lands in a group with probability proportional to the
  target type's neurons there times exp(-d / lambda), own group included), once per realization
  (seed), not set to their expected values. This gives pairs at the same distance different
  couplings, as in the spiking network. The model cannot reproduce the spiking network's exact
  realization, so per-pair agreement is not expected. The rule follows the harness's wiring: rewiring
  (revision 1 of `../runpod-assembly-association-task.md`) until `../engine-fix-rerun-task.md`, step 2,
  decides it again; if the engine's own wiring is chosen, the models need its distance profile (new code,
  or exported networks as in round 6).
- **Transfer functions (round 3):** each population's rate as a function of its input is derived from
  its neuron model in the engine, in the same current units as the derived couplings: the
  steady-state firing rate of the excitatory and of the inhibitory Izhikevich neuron (the engine's
  parameters for each type, 1 ms steps, the input clamp of +-100) as a function of constant input
  current, computed numerically, then smoothed by Gaussian input noise. Excitatory and inhibitory
  units get their own curves; no shared generic sigmoid. Fitted parameters (at most three, as
  before): **[default]** the noise width, the time constant, and one common input scale only if the
  derived scale demonstrably misses (state why). Record the curves (rate against input) in the report.
- Fields C1, C2, C3 with the update of `ChemicalField` / `FuelField`, released from the group rates.
- Plasticity on the group-to-group couplings: rule `both` approximated as rate products, `w_fast` and
  `w_perm` as in the protocol.
- Protocol, tests and measures as in the sparse task (transfer, ignition, strays, `R_off`).

## Substeps

**1. Build** (round 1, checks corrected in the review): the coupling and field checks compare with
the spiking network's code, not with the model's own formulas. Add checks for the derived
constants (each against the value computed from the spiking code) and for the sampled connectivity
(mean over realizations within 5 % of the expected counts).

**2. Sanity checks** before any fitting, recorded in the report: an injected assembly activates and
stays active as in the predecessor's Substep 1; ordinary groups stay quiet without injection; under
joint injection of a pair at d 4, activity spreads beyond A and B in at least some realizations. If
the model never transfers under the protocol for any reasonable setting of the fitted parameters,
stop and report why before Substep 3.

**3. Admission test** against the spiking runs, decided before use. Each pair is classified by its
**first transfer in the joint rounds**: *contained* (at most 34 strays), *ignition* (more than 34)
or *none* (no transfer); a pair that later loses the association keeps its first-transfer class.
Spiking reference: the rerun's protocol and grid comparison (`../engine-fix-rerun-task.md`, steps 5 and 6;
their report names the ground-truth files). The references of rounds 1 to 5 (s71 E0: 7 contained, 10
ignition, 7 none; iterations 61 and 64; `../archive-pre-engine-fix/rate-model/s71_ground_truth.json`) came
from the faulty engine and are not used. Requirements:
- **Class fractions:** over **[default]** 5 realizations x 24 pairs at d 4 on 7 x 7 x 7, each class's
  fraction lies within the 95 % binomial interval of the spiking fraction.
- **Grid size:** the difference between 7 x 7 x 7 and 9 x 9 x 9 (pairs at least 2 cells from the surface)
  that the rerun's step 6 finds, if any, is reproduced (on the faulty engine: ignitions fell to zero and
  transfers dropped on 9 x 9 x 9, iteration 61).
- **Uniform C2:** holding C2 uniform where released has the effect the rerun's step 5 finds (on the faulty
  engine: the same associations as activity-dependent C2, iteration 64).
Fit only the model's free parameters (at most three, named in the report), using the 12 pair
positions of seed 0 and realizations 0 to 4; evaluate on all 24 pair positions with fresh realizations
(5 to 9). Report, as information only, per-pair kappa against the
ground truth. Record every result with the settings it was run with, whether the test passes or
fails. If it fails, stop and report; the model is not used for screening, and its code is kept.

**4. Screening runs** (only after admission): scans requested by the sparse task, such as lambda
against d / lambda, C1 diffusion length and L4's starting threshold. Each scan reports the settings
it excludes and why; the sparse task tests the remaining ones on pods.

## Round 4: two group models

Both reuse round 3's derived couplings, sampled connectivity, fields, plasticity, protocol, measures,
module-check style and admission test (Substeps 2 and 3 unchanged). Each is built and tested by its
own agent, in its own files, so both can run at the same time.

- **Model A, population density** (files `popdensity_model.py`, `test_popdensity_model.py`,
  `admission_popdensity.py`, report `../archive-pre-engine-fix/rate-model/round4-popdensity-report.md`). Intent: a group-level model that
  keeps what the smooth curves lost: the finite number of neurons per group (about 58, of them 12
  injected), the resulting fluctuations, refractoriness and synchronous recruitment.
  **[default]** form: a finite-size stochastic population model per group and type, in which a density
  of membrane states (refractory density or Fokker-Planck, from the engine's Izhikevich parameters)
  gives a firing hazard and the number of spiking neurons per step is drawn binomially from it. Other
  population-density forms are allowed if they serve the intent (log the reason).
- **Model B, reduced spiking network** (files `spiking_group_model.py`, `test_spiking_group_model.py`,
  `admission_spiking_group.py`, report `../archive-pre-engine-fix/rate-model/round4-spiking-report.md`). Intent: keep spikes and synchrony at
  a cost far below the GPU runs. **[default]** form: the engine's Izhikevich neurons, update and input
  clamp, with fewer neurons per group and synapses per neuron, weights scaled so that each neuron's
  mean input and the injected group's drive match the full network, connectivity drawn with
  `rewire_by_distance`'s rule, numpy on the pod. Only useful if one simulation costs clearly less than a
  GPU spiking job (about $0.017 in iteration 65); report the cost per simulation.

Each model gets its own pod and its own **[default]** limit of $3. A model that passes admission is
reported with its speed and cost; screening (Substep 4) waits for the user.

## Round 5: why the models over-propagate on the larger lattice

Intent: find why both round-4 models keep transferring and igniting on 9 x 9 x 9, where the spiking
network does not (iteration 61: 5 of 24 transfers, no ignition; activity from A levels off at 10 to
16 groups around it after about 20 rounds), then fix the cause and repeat the admission test. The
order below is a starting point; follow the evidence.

1. **Setup parity.** Compare each model's 9 x 9 x 9 runs with the spiking ones
   (`../archive-pre-engine-fix/params/session73-*.json`, `../archive-pre-engine-fix/tuning-log.md` iteration 61): about 58 neurons per group
   (N 42,500), delay count D 16 (about 1.1 steps per cell), `pair_margin` 2, stray limit 34 groups,
   30 rounds, injection, test duration, runaway check (round 2 noted that the runaway stop is not
   modelled). List every difference and remove it before anything else.
2. **Where they diverge.** Compare the models with the spiking 9 x 9 x 9 runs round by round, using
   the spiking outputs in `../output/s73-*` (job JSON and NPZ files; gitignored, local only): number
   of active groups around A, A-alone strays, round of the first transfer. Find the first quantity
   that differs.
3. **Causes to test, one at a time** (hypotheses, not limits): the reduction itself (model B's 250
   synapses per neuron make fewer, larger weights; test more synapses on a few pairs); what the
   fitted factors compensate for (model A's plasticity amplitude 0.31; model B's inter-group E -> I
   factor, 0.7 in the fit against 0.3 from single-group calibration, and its unexplained excess of
   inhibitory firing in neighbouring groups); `w_fast` decay; inhibition between groups; the runaway
   stop.
4. **Fix and re-test.** Prefer a cause that is derived or explained over a new fitted factor; at most
   three free parameters per model, as before. Repeat the admission test (Substep 3) with the fix.

Model B first (closest to the spiking network, so its divergence is the most informative), then
model A. Each model: own pod, **[default]** at most $3. Report in `../archive-pre-engine-fix/rate-model/round5-report.md` (one file, a
section per model), with every result and its settings, the cause found or the causes ruled out, the
verdict per model and the cost.

## Round 6: the engine's own network in model B

Intent: remove the one unexplained difference that round 5 found and that every later difference
builds on. Model B at full size (2000 synapses per neuron) needs a fitted factor on inter-group
E -> I weights (0.3 to match a single injected group, 0.5 in the fit), because without it a single
injected group drives 2 to 3 times too many inhibitory spikes in neighbouring groups (about 1000
spikes against 415). No origin was found in the engine code. With the factor, the 7 x 7 x 7 and the
9 x 9 x 9 check cannot both be met: a sharp none -> ignition threshold lies between them. If model B
reproduces the single-group response without a factor, the fitted factors and the conflict may
disappear. Model B at full size is already 3 to 40 times cheaper than a GPU job (35 to 300 s per
simulation on one vCPU). The cause may also lie in the engine itself (for example fewer E -> I
synapses built than the configuration specifies); a cause of that kind changes how the spiking
results are read and is also reported to the sparse task (`../sparse-assemblies-task.md`).

Outcome (`round6-report.md`): the cause was in the engine, a transposed synapse table that gave every built
network the wrong composition; fixed on 2026-10-30, with the other engine fixes of that day
(`../engine-fix-rerun-task.md`). Steps 1 and 2 were then repeated on the fixed engine ("After the engine
fixes" in the report). The fitted factors and the `frac_I_to_I` option of rounds 5 and 6 described the
faulty networks; model B uses the configured composition (its defaults). Step 3 (report, "Step 3"): not
admitted at the rerun's settings without fitted parameters (9 x 9 x 9 associations 1 against 11); admitted
with the consolidation rate `kappa` fitted to 0.045. The admission ran with new scripts on the rerun's summaries
(`round6_regime_precheck.py`, `round6_admission_compare.py`); the constants of `admission_test.py` and the
other round 4 and 5 scripts listed in step 3 still hold the faulty engine's references.

1. **Export and structure audit.** On a GPU pod, build the engine's network as the spiking runs did
   (7 x 7 x 7: N 20,000, S 2000, `rewire` lam 0.4, seeds 0 and 1, s71 parameters; 9 x 9 x 9:
   N 42,500, D 16, s73 parameters) and export what the engine simulates: postsynaptic targets, the
   weights as written into the engine (gains included) and the normalized weights, delay buckets,
   each neuron's parameters (a, b, c, d), type, model flag (`N_flags` row 3), group and post-warm-up
   state, the group cells, and the pair positions and injected neurons of each job. Before any
   dynamics, compare the export with model B's own construction, per neuron type pair, within and
   between groups: synapses per presynaptic neuron (model B assumes 400 E -> I of 2000, read from
   the configuration code, not counted in the built network), inhibitory in-degree of neighbouring
   groups, weights, delays, neuron parameters. Correct any difference in model B's construction;
   prefer a derived correction, a fitted factor only with a stated reason. Add an option to model B
   that loads the exported network instead of drawing its own.
2. **Single-group response, step by step.** Run the A-alone test before learning in the engine and in
   model B on the same exported network, with background input off. Compare, in this order, each
   neuron's summed input current over the first steps (before float rounding can flip a spike: the
   engine sums with `atomicAdd` in float32, so spike trains can diverge later for reasons unrelated
   to the cause), then spikes per step, per group and per type. **[default]** pass: input currents
   equal within float32 tolerance over the first steps; total spikes within 5 % and the same groups
   active. The first differing quantity localizes the cause (neuron update, delivery order or timing,
   input clamp, injection); fix it in model B.
3. **Learning, then admission** (waits for the rerun's steps 5 and 6, which give the spiking reference;
   `../engine-fix-rerun-task.md`, step 8). With the single-group response right and no inter-group E -> I
   factor, compare the first rounds of learning with the spiking 9 x 9 x 9 reference of the rerun (the
   archived one, `../archive-pre-engine-fix/rate-model/round5-report.md`, "Spiking reference", came from the
   faulty engine), then repeat the admission test (Substep 3) with at most
   three free parameters, all named. Report per-pair kappa on the exported networks: they are the
   same realizations as the spiking runs, so per-pair agreement is possible, though not guaranteed
   (float rounding, step 2). First point the admission code at the rerun's results; today it holds the
   faulty engine's as constants: `SESSION` (protocol parameters, `session69a-stage2.json`) and
   `REFERENCE_COUNTS` (7 / 10 / 7) in `admission_test.py`, `load_ground_truth` (`s71_ground_truth.json`),
   the grid-size and uniform-C2 thresholds of its docstring and code (from 0 / 24 ignitions, 5 / 24
   transfers, 6 and 7 of 24 associations), and the same names in `admission_spiking_group.py`,
   `admission_popdensity.py`, `round5_*.py`, `round6_compare.py` (`spec_for`) and the module checks.
4. **Check on the sparse substrate.** Admission covers the predecessor setup (every group an
   assembly, the wiring chosen in the rerun's step 2). Before the model narrows any range for a family of the sparse task (S, L, K,
   E), compare it with that family's first GPU screening run of its baseline (24 pairs): the classes
   must lie within the binomial intervals of the spiking fractions.

Model A is not part of this round; it stays parked unless the user asks.

Each session needs the user's go. Compute: the export on one GPU pod (RTX 4090, EU-RO-1; minutes; the round
ran on RTX PRO 4000 Blackwell pods instead; on the fixed engine, four builds at once (two 7 x 7 x 7, two
9 x 9 x 9) exceeded its 24 GB, so the 9 x 9 x 9 builds run one at a time),
written to the network volume (about 3 GB, not downloaded); model B on a CPU pod in EU-RO-1 as in
round 5, reading the exports from the volume (to verify that a CPU pod can attach it; otherwise copy
the exports there); **[default]** at most $3 for the round. Report in `round6-report.md`.

## Backlog (after round 6)

- An analytic propagation bound from neural-field theory: whether A-to-B spread exists for a given
  lambda, synapse count, weights and noise, so that part of the wiring sweeps need no pod. If model B
  falls short of admission, a mean-field reduction that keeps fluctuations (round 3's diagnosis: smooth
  rate curves miss the spike-synchrony recruitment). Read first: Krüger and Stannat 2014 (front
  propagation in stochastic neural fields), Farkhooi and Stannat 2017 (complete mean-field theory for
  binary recurrent networks), Löcherbach 2017 (Hawkes-process mean-field limits), Lagzi, Atay and
  Rotter 2018 (bifurcations of interacting spiking populations), Roxin, Brunel and Hansel 2005 (delays
  and spatiotemporal dynamics). PDFs are in the Mendeley library (`E:\MEGA\Mendeley Library`); none
  has a Markdown version in `archive/` yet (checked 2026-10-30). Decided with the user on 2026-10-31
  as a backlog item, not a task of its own.

## Rules

- **Only with the user's explicit go for each session.**
- **Compute (user decision 2026-10-29): simulation runs go to a Runpod CPU pod** (no GPU), in
  EU-RO-1 or, when it has no CPU capacity, EU-CZ-1, EUR-IS-1 or US-NE-1 (user decisions 2026-10-29,
  round 4), terminated as soon as the results are downloaded; read the price before creating it and
  note pod type, region and cost in the report (**[default]** at most $3 for this round without asking). The
  host is weak: use it only for editing and short checks, one process at a time.
- Python: on the host, standard library only or a `.venv` in this folder (`agents/common.md`); on the
  pod, a virtual environment there.
- Work only in this folder; import from the parent folder, do not change its files.
- No commits without the user's go.
- **Files:** this file, `../archive-pre-engine-fix/rate-model/rate-model-report.md`, `rate_model.py`, `test_rate_model.py`,
  `admission_test.py`, `../archive-pre-engine-fix/rate-model/s71_ground_truth.json`, the round 4 files named above, and for round 5
  `../archive-pre-engine-fix/rate-model/round5-report.md`, `round5_cross_check.py`, `round5_diag_popdensity.py`, `round5_diag_spiking.py`,
  `../archive-pre-engine-fix/rate-model/s73_g9_d4_pairs.json` and the gitignored `../archive-pre-engine-fix/rate-model/output-round5/` (round 5 changes the round 4 model files
  as needed); for round 6 `round6-report.md`, `round6_export_engine.py` (export and structure
  audit), `round6_compare.py` (the step-2 comparison), the option of `spiking_group_model.py` that
  loads an exported network, and the gitignored `output-round6/`; after the engine fixes `round6_fixed_pod.sh`
  (the repeat of steps 1 and 2 on a pod) and the gitignored `output-round6-fixed/`; for step 3
  `round6_regime_precheck.py`, `round6_admission_compare.py`, `round6_precheck_pod.sh`, `round6_grid_pod.sh`,
  `round6_strays_pod.sh`, `round6_fit_pod.sh`, `round6_fit_summary.py` and the gitignored
  `output-round6-precheck/`, `output-round6-grid/`, `output-round6-strays/` and `output-round6-fit/`. A round 4 agent
  changes only its own model's files; shared files (`rate_model.py`, `../archive-pre-engine-fix/rate-model/s71_ground_truth.json`) are read,
  not changed.
