# Task: Rate Model for Screening the Assembly-Association Parameters

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
> network does not (`round4-popdensity-report.md`, `round4-spiking-report.md`). **Round 5 finished
> (2026-10-29): neither model is admitted** (`round5-report.md`): model B at full size passes the 7 x 7 x 7
> classes and the uniform-C2 check but still ignites too often on 9 x 9 x 9; model A has no fix. Raw
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
3. `../runpod-assembly-association-report.md`: "The protocol that passes" and "What is established".
4. `../tuning-log.md`, iterations 56, 59, 61, 63 and 64 (the runs to compare against).
5. `rate-model-report.md` (rounds 1 to 3, and "Review 2026-10-29"), `round4-popdensity-report.md`,
   `round4-spiking-report.md` and `round5-report.md`.
6. Code: `../assoc_build.py` and `../assoc_engine.py` (network construction: neuron counts per type,
   synapses per neuron, weights, gains, intra-group input, `rewire_by_distance`), `../assoc_fields.py`
   (`ChemicalField`, `FuelField`), `../assoc_protocol.py` (protocol, tests, strays), and the per-pair
   outcomes of `python ../assoc_sweep_summary.py ../output "s71*" -v`. Results are in `../output/`
   (gitignored; local only).

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
  realization, so per-pair agreement is not expected.
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
Spiking reference (s71 E0, d 4, 24 pairs, `s71_ground_truth.json`): 7 contained, 10 ignition,
7 none. Requirements:
- **Class fractions:** over **[default]** 5 realizations x 24 pairs at d 4 on 7 x 7 x 7, each class's
  fraction lies within the 95 % binomial interval of the spiking fraction (7/24, 10/24, 7/24).
- **Grid size** (iteration 61): on 9 x 9 x 9 with pairs at least 2 cells from the surface, ignitions
  fall to (nearly) zero and transfers drop clearly (spiking: 17 of 24 transfers on 7 x 7 x 7, 5 on
  9 x 9 x 9; 9 and 0 ignitions).
- **Uniform C2** (iteration 64): holding C2 uniform where released gives the same associations as
  activity-dependent C2, within the uncertainty.
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
  `admission_popdensity.py`, report `round4-popdensity-report.md`). Intent: a group-level model that
  keeps what the smooth curves lost: the finite number of neurons per group (about 58, of them 12
  injected), the resulting fluctuations, refractoriness and synchronous recruitment.
  **[default]** form: a finite-size stochastic population model per group and type, in which a density
  of membrane states (refractory density or Fokker-Planck, from the engine's Izhikevich parameters)
  gives a firing hazard and the number of spiking neurons per step is drawn binomially from it. Other
  population-density forms are allowed if they serve the intent (log the reason).
- **Model B, reduced spiking network** (files `spiking_group_model.py`, `test_spiking_group_model.py`,
  `admission_spiking_group.py`, report `round4-spiking-report.md`). Intent: keep spikes and synchrony at
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
   (`../params/session73-*.json`, `../tuning-log.md` iteration 61): about 58 neurons per group
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
model A. Each model: own pod, **[default]** at most $3. Report in `round5-report.md` (one file, a
section per model), with every result and its settings, the cause found or the causes ruled out, the
verdict per model and the cost.

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
- **Files:** this file, `rate-model-report.md`, `rate_model.py`, `test_rate_model.py`,
  `admission_test.py`, `s71_ground_truth.json`, the round 4 files named above, and for round 5
  `round5-report.md`, `round5_cross_check.py`, `round5_diag_popdensity.py`, `round5_diag_spiking.py`,
  `s73_g9_d4_pairs.json` and the gitignored `output-round5/` (round 5 changes the round 4 model files
  as needed). A round 4 agent
  changes only its own model's files; shared files (`rate_model.py`, `s71_ground_truth.json`) are read,
  not changed.
