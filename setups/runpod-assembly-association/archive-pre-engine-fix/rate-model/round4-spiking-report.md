# Round 4, model B (reduced spiking network): report

**Verdict: not admitted.** On 7x7x7 the class fractions of contained and ignition are inside their 95 % intervals, but
"none" is not (0.017 against 0.126 to 0.511); the 9x9x9 check and the uniform-C2 check fail. The model is not used for
screening; Substep 4 was not started. Code and tests are kept.

## Files
`spiking_group_model.py`, `test_spiking_group_model.py`, `admission_spiking_group.py`, this report. Shared files
untouched. Result JSONs (calib, sanity, fit1-4, eval, grid, uniform) are in the session temp folder
(`%TEMP%\modelB_results\res`), not in the repository.

## Model and reduction
Engine's Izhikevich neurons in float32 (snn_simulation.cu update_N_state_, 5-step warm-up state, reset to it before every
phase), input clamp +-100 with injection added after it, delivery by delay bucket as update_current_ (a spike detected at
step k with delay d acts on the target's input at step k+d+1), connectivity drawn with rewire_by_distance's rule (group
by n_target x exp(-d/lambda), neuron uniform within, types kept, no autapses, delay round((D-1) d/d_max), D 13),
weights from assoc_engine (gain 4, gain_ei 1, gain_ie 2, gain_ee_inter 0.6, intra weight w_intra_ee_total 40 / in-degree),
gated plasticity of assoc_plasticity.py (rule "both"; event-based with a lazy decay multiplier), activity A_g over
excitatory neurons (window 20), protocol and classes as rate_model.run_pair_protocol (runaway stop at 0.5 N spikes).
C1 has gain 0, gate open everywhere (theta1 -1), as in the passing protocol; C2 on the cell lattice
(ChemicalFieldLattice), release divided by neuron_scale.
**Reduction chosen: syn_scale 0.125** (250 synapses per neuron instead of 2000: 200 E to E + 50 E to I per excitatory
neuron, 250 I to E), engine weight x S_type/S'_type so the expected summed input per presynaptic volley is unchanged;
intra-group weights keep the engine's in-degree normalisation (not scaled again); **neuron_scale 1** (all 58.3 neurons
per group). Reason: every neuron count reduction multiplies the effect of one spike by 1/scale (an injected 12 of 46 and
a whole-group volley of 160 are unchanged, but each neuron receives larger, rarer kicks), and the synapse reduction was
tested to leave single-group spike counts unchanged between syn_scale 1/16 and 1 (neuron_scale 0.25), so neuron count was
kept at full and only synapses were reduced. Option neuron_scale (k' = round(12 x scale)) is implemented, not used.
Sanity-level speed: see Cost.

## Free parameters (3 named, 2 used)
- `ei_inter_scale` (factor on the engine weight of E to I synapses between groups), **fitted**. Reason: the derived
  model (factor 1) gives 614 inhibitory spikes in other groups after a single-group injection against 212 in the
  spiking prop surveys (s57; total 847 vs 438), while in-group spikes agree (about 230); the cause is not in the code
  (all transliterations agree). Not derived.
- `w_inter_scale` (factor on the engine weight of E to E synapses between groups), **fitted**.
- `learn_scale` (factor on a_pre, a_plus, a_minus): kept at 1.
Fitted on the 12 seed-0 positions x realizations 0 to 4 (60 simulations per setting, C2 stage off), objective L1 distance
of the class fractions from the seed-0 reference (0.50 contained, 0.33 ignition, 0.17 none).

| ei_inter | w_inter | contained | ignition | none | L1 |
|---|---|---|---|---|---|
| 0.2 | 1.0 | 0.00 | 0.88 | 0.12 | 1.100 |
| 0.3 | 1.0 | 0.02 | 0.68 | 0.30 | 0.967 |
| 0.4 | 0.7 | 0.00 | 0.00 | 1.00 | 1.667 |
| 0.4 | 1.0 | 0.05 | 0.25 | 0.70 | 1.067 |
| 0.4 | 1.4 | 0.02 | 0.98 | 0.00 | 1.300 |
| 0.5 | 1.0 | 0.20 | 0.13 | 0.67 | 1.000 |
| 0.5 | 1.2 | 0.00 | 1.00 | 0.00 | 1.333 |
| 0.5 | 1.4 | 0.05 | 0.95 | 0.00 | 1.233 |
| 0.6 | 1.0 | 0.05 | 0.00 | 0.95 | 1.567 |
| 0.6 | 1.1 | 0.27 | 0.73 | 0.00 | 0.800 |
| 0.7 | 1.0 | 0.12 | 0.00 | 0.88 | 1.433 |
| 0.7 | 1.2 | 0.27 | 0.73 | 0.00 | 0.800 |
| 0.7 | 1.4 | 0.12 | 0.88 | 0.00 | 1.100 |
| **0.7** | **1.1** | **0.43** | **0.55** | **0.02** | **0.433** |

The outcome switches sharply between "none" and "ignition" (a threshold in the inter-group coupling); a contained
transfer exists only in a narrow band between them. Chosen: ei_inter 0.7, w_inter 1.1 (neuron_scale 1, syn_scale 0.125).

## Module checks (pod, once, with torch): 21 of 21 pass
Neuron update equals a scalar float32 transliteration of the kernel; `default_init` executed from the engine's source
gives the model's neuron parameters; spike rasters over 120 steps with injection, delays and clamp are identical to a
plain-Python transliteration of the engine's update order; wiring (types, no autapses, E to E shell frequencies within 5 %
of an independent computation, delays and buckets, intra-group in-degree / syn_scale within 6 % of the engine's measured
892.7); engine weights equal a numpy transliteration of typed_weights / set_gains and, with torch, equal the real
`AssocEngine.typed_weights / set_gains / write_weights` (times the reduction factor); summed input invariant between
syn_scale 0.05 and 0.2; event plasticity equals a dense transliteration of GatedPlasticity.step and the real
`GatedPlasticity` (w_fast, w_perm within 3e-6 after STDP, presynaptic term, decay, consolidation); activity equals
`GroupActivity` (transliteration and real class). On the host the first run had 2 test-code bugs, fixed; the whole suite
was run once on the pod after that.

## Substep 2: sanity (run with ei_inter 0.3, syn_scale 0.125, neuron_scale 1, realizations 0 and 1)
- Injected group activates (A_g >= 0.5 and others <= 0.1): 23 of 24 tests (A_max >= 0.9 in 96 %); spill into neighbours
  0 of 24 (spiking: 9 of 48 had neighbours active; 19 %). Spikes in isolated tests: median 493 (spiking 431; 10 to 90 %
  434 to 526 against 260 to 620).
- Quiet network: 0 spikes in 300 steps in both realizations.
- Joint injection of the 24 pairs for 10 rounds with learning: groups other than A, B reach A_g >= 0.5 in 24 of 24 pairs
  in each realization (spread beyond A and B occurs).
(The sanity run used ei_inter 0.3, before the fit; the chosen setting 0.7 was not re-run through the sanity checks.)
Derived model (ei_inter 1, 36 tests): A_max >= 0.9 in 94 %, spikes median 848, inhibitory spikes outside 614;
ei_inter 0.3: median 468, outside 247 (spiking: 431, 212).

## Substep 3: admission test (ei_inter 0.7, w_inter 1.1, neuron_scale 1, syn_scale 0.125, realizations 5 to 9)
- **Class fractions, 7x7x7, 24 positions x 5 realizations = 120 simulations:** contained 49 (0.408), ignition 69
  (0.575), none 2 (0.017). 95 % Clopper-Pearson intervals of the spiking fractions: contained 0.126 to 0.511 (inside),
  ignition 0.221 to 0.634 (inside), none 0.126 to 0.511 (**outside**). **Fails.** Per-realization (contained /
  ignition / none): 6/17/1, 7/17/0, 13/10/1, 11/13/0, 12/12/0. Mean C1 rounds to first transfer or 30: 20.3.
  Per-pair kappa (information): modal class per pair -0.067, all simulations -0.008 (confusion rows ground truth
  contained / ignition / none, columns predicted: [2,5,0], [4,6,0], [2,5,0]).
- **9x9x9** (24 pairs >= 2 cells from the surface x realizations 5 to 9, stray limit 34): contained 31, ignition 88,
  none 1 of 120: transfers 0.99 and ignitions 0.73 against the bounds 0.42 and 0.14 (spiking: 5 of 24 transfers, 0
  ignitions). **Fails**: the model does not reproduce the fall of transfers on the larger grid.
- **Uniform C2 1.2** (7x7x7, same 120 simulations with the C2 stage): associations 30 of 120 with activity-dependent
  C2, 11 of 120 with uniform C2; paired difference -0.158, 95 % interval -0.242 to -0.075, 29 discordant. **Fails**
  (spiking: 6 and 7 of 24). Transfer classes are identical in both arms (the C2 stage comes after the first transfer).

## Cost and speed
Pod `jopm5mdn117bsx` (named modelB-spiking-cpu), cpu3c, 4 vCPU, 8 GB, EU-CZ-1, $0.12/h, created 06:34, terminated
about 08:13 UTC (about 1.65 h, about $0.20); 4 processes in parallel, host shared (load average > 100 on the pod's
machine, so timings are pessimistic). Creation in EU-RO-1 was refused for capacity (cpu3c 32, 16, cpu3g 8); in EU-CZ-1
32, 16 and 8 vCPU cpu3c were refused too and only 4 vCPU was granted (EU-CZ-1 allowed by the user's decision).
Measured per simulation (1 vCPU): 7x7x7 class simulation (C1 stage only) mean 12.1 s, 4067 steps (3.0 ms per step);
9x9x9 24.1 s, 4307 steps (5.6 ms per step); with the C2 stage 33.7 s, 5554 steps. At $0.03 per vCPU-hour: **about
$0.0001 per 7x7x7 simulation, $0.0002 per 9x9x9, $0.0003 with the C2 stage**, against about $0.017 for a GPU spiking job
(iteration 65): about 50 to 150 times cheaper. Total cost of this round-4 work: about $0.20 (no earlier pod). `list-pods`
after termination shows no pod of mine (two other pods, modelA-popdensity-cpu, belong to model A and were not touched).

## Verdict and open problems
Not admitted. The derived model (no fitted parameter) over-inhibits neighbours (614 vs 212 inhibitory spikes outside
the injected group) and is silent or ignites, never in the spiking mix; the inter-group coupling needs two fitted
factors (0.7 on E to I between groups, 1.1 on E to E between groups) to reach a contained/ignition mix, and even then
(i) no "none" class, (ii) transfers do not fall on 9^3, (iii) the C2 gate gives 30 against 11 associations. Remaining
unexplained points: (a) the 2.5 to 3 times excess of out-of-group inhibitory firing in the derived model (candidate: how
the engine delivers E to I input to neighbours; the fitted factors absorb it, and the fit moved from 0.3 (single-group
calibration) to 0.7 (protocol fit), so the two are not consistent); (b) 4 % of injected groups are not recruited
(spiking: 0) and no neighbour spill (spiking: 19 %); (c) only 4 vCPU were available (EU-CZ-1), so the fit grid was small
(14 settings, no learn_scale scan, no neuron_scale scan); a 9^3 and uniform-C2 failure with this model may reflect the
fitted settings rather than the reduced-spiking form. Not tried: scanning learn_scale, neuron_scale 0.5 with fitting,
heterogeneous fitting of E to I only in the neighbourhood of the route.
