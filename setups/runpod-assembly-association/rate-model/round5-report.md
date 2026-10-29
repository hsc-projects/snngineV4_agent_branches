# Round 5: why the round-4 models over-propagate on the larger lattice

Raw results are in `output-round5/` (gitignored): per-round traces (`trace_*.json`, `A_trace_*.json`, `A2` to `A4`), single-group calibrations (`small_results_podB.tgz`), cross-check dumps and tests (`xchk_*`), fit and admission outputs (`adm_*`, `final_*`), and the extracted spiking reference (`spiking_s73_g9_d4_rounds.json`). New code: `round5_diag_spiking.py`, `round5_diag_popdensity.py`, `round5_cross_check.py` (plus options `delay_offset`, `exc_r`, `inh_r`, `trace` in `spiking_group_model.py` and `ei_inter_scale`, `commit_rule` in `popdensity_model.py`; defaults reproduce round 4).

**Summary.**
(1) Setup parity: no difference in the 9 x 9 x 9 protocol explains the over-propagation (table below).
(2) First diverging quantity, in both models: the response to a single injected group (A-alone test before any learning). The spiking runs give a median of 415 spikes (48 tests, 308 to 554) and no excitatory neuron outside the group; both models, run with derived weights, give about 950 to 1090, almost all of the excess being inhibitory neurons in neighbouring groups.
(3) Model B: the reduction to 250 synapses per neuron is not the main cause. The full network (2000 synapses per neuron, derived weights, no fitted factor) behaves differently from the fitted reduced one: it does not over-propagate (0 of 72 transfers on 9^3), because it is too stable, and the 9^3 drop is reproduced at a single value of the inter-group excitatory -> inhibitory factor. The over-propagation of round 4 came from compensating the neighbour-inhibition excess by fitted factors (0.7 and 1.1) on the reduced network, which has stronger, lumpier early learning.
(4) Model A: with the same realization and the same group-level learned weights as model B, model A responds 2 to 4 times more strongly in neighbouring groups from the third learning round on; its plasticity update itself matches (mean |w_fast| after round 1 within 1.3 times of the spiking value). The fitted `plast_scale` 0.31 therefore compensates a dynamical over-response of the population model, not the plasticity law. Cause localized, not removed.
(5) Verdicts: **neither model is admitted.** Model B (full network, ei 0.5, w 1.1) passes the 7^3 class
fractions and the uniform-C2 check but fails the 9^3 check (ignitions 0.34 against at most 0.14); no
setting tried meets both. Model A: no fix found. Total pod cost of round 5 about $2.6 (estimated).

## Setup parity (both models)

Differences between the round-4 9 x 9 x 9 runs and the spiking runs (`../params/session73-g9-*.json`), found by comparing code and parameter files:

| item | spiking s73 g9 | round-4 model runs | action |
|---|---|---|---|
| neurons | N 42,500 (58.30 per group) | `neurons_per_group` 20000/343 gave N 42,507 | set 42500/729 (negligible) |
| delay count, grid | D 16, 9^3, delay round((D-1) d / d_max), d_max 8 sqrt 3 (1.08 steps per cell) | identical rule | none needed (checked in `rate_model.Spec.D`, `assoc_engine.rewire_by_distance`) |
| stray limit | `max_active_frac` 0.0467 x 729 = 34 | 34/729 x 729 = 34 (checked) | none |
| pair positions | the engine's pairs (distance nearest 4, margin 2, seeds 0 and 1, 12 each) | `pick_pairs(seed 0)` | replaced by the 24 spiking pair positions (`s73_g9_d4_pairs.json`); the group index x 81 + y 9 + z reproduces the engine's A-B distance for all 24 pairs |
| protocol | 30 rounds, 50 injection + 50 gap steps, test 100 steps, k 12, +20, clamp +-100, runaway stop 0.5 N, c1 gain 0 | same (model A has no runaway stop; no spiking job ran away) | none |
| other job parameters | s73 differs from session69a only in `controls`, `max_active_frac`, `pair_margin` | read from session69a | none |
| connectivity | direct A -> B synapses at 4 cells: 56 observed in 24 pairs | 55.8 expected from the sampling rule (lam 0.4) | none; intra-group E -> E synapses per neuron 867 / 851 (engine) against 833 (rule, sizes equal), consistent with size variation |
| weights, neuron model | built weights {-0.44, 0.45, 0.47}, no deleted synapses (s0-harness) | same | none |
| first-transfer classes of the spiking 9^3 runs | recomputed from the job JSONs: 4 contained, 1 ignition (36 strays, s0 pair 6), 19 none | iteration 61 and task: 5 transfers, 0 ignitions | the admission bounds of the task are kept (0.42 transfers, 0.14 ignitions) |
| model B reduction, fitted factors | 2000 synapses, derived weights | 250 synapses, `ei_inter_scale` 0.7, `w_inter_scale` 1.1 | tested below |
| model A | derived | `plast_scale` 0.31 | tested below |

Kernel check (`snn_simulation.cu`, update_current_): delivery with `atomicAdd` (no lost updates), weights, delays and delivery bucket as modelled. Delivery offset by one or two extra steps changes the single-group response by under 10 % (7^3, `delay_offset`), so it is not the cause below.

## Spiking reference (24 pairs, medians, rounds counted from 1)

| round | 1 | 2 | 3 | 5 | 10 | 20 | 30 |
|---|---|---|---|---|---|---|---|
| joint-round spikes | 1134 | 1254 | 2558 | 3650 | 5388 | 10,700 | 11,620 |
| A-alone test spikes | 593 | 949 | 1501 | 1857 | 2651 | 4584 | 4780 |
| groups active outside A, B, route | 0 | 0 | 0 | 0 | 2.5 | 11 | 11 |
| mean abs w_fast per synapse | 2.6e-4 | 4.8e-4 | 1.2e-3 | 2.6e-3 | 6.8e-3 | 2.3e-2 | 3.1e-2 |

(Before learning: A-alone test 415.5 spikes, no neighbour excitatory neuron active in any of 48 tests.) First transfers in rounds 14 to 22, strays 8 to 36.

## Model B (reduced spiking network)

### Where it diverges, and what it is not

Settings: 9^3, the 24 spiking pair positions, 2 to 3 realizations (48 to 72 simulations); `syn_scale` is the synapse number relative to 2000.

| setting | simulations | contained / ignition / none | transfers | A-alone test spikes before learning (median) |
|---|---|---|---|---|
| spiking (reference) | 24 | 4 / 1 / 19 | 0.21 | 415 |
| reduced (250), ei 0.7, w 1.1 (round 4) | 48 | 9 / 38 / 1 | 0.98 | 833 |
| reduced (250), ei 1, w 1 | 56 | 1 / 0 / 55 | 0.02 | 1005 |
| reduced (250), ei 0.3 | 48 | 0 / 27 / 21 | 0.56 | 512 |
| reduced (1000), ei 0.3 | 24 | 0 / 12 / 12 | 0.50 | 480 |
| full (2000), ei 1 | 72 | 0 / 0 / 72 | 0.00 | 993 |
| full (2000), ei 0.3 | 72 | 0 / 59 / 13 | 0.82 | 512 |
| full (2000), ei 0.4 | 48 | 0 / 12 / 36 | 0.25 | |
| full (2000), ei 0.5 | 48 | 2 / 5 / 41 | 0.15 | |

(ei = factor on the weight of E -> I synapses between groups; the intra-group E -> I weight is untouched.)

1. **First diverging quantity: the single-group response.** Derived models give 950 to 1090 spikes against 415; excitatory spikes in the group (about 120) agree, the excess is 500 to 700 inhibitory spikes in neighbouring groups (inhibitory spikes outside the group: 704 at 9^3 full scale, 560 at 7^3 against 217 in the engine survey s57 at 7^3). Not caused by: the reduction (full network 945 spikes against 998 to 1000 for 250 and 500 synapses at 7^3 and 993 against 1005 at 9^3), the inhibitory neurons' parameters (fixing r of all inhibitory neurons at 0, 0.5 or 1 gives 840 to 420 outside spikes, still above 217), the excitatory neurons' parameters (r fixed at 0 to 1: 580 to 700), a delivery delay offset of 1 or 2 steps, or the connectivity (direct synapse counts and intra-group counts match the engine). Not found: a code-level reason in the engine's neuron update, delivery, weights or wiring (all re-read).
2. **The excess is a pure weight factor on inter-group E -> I synapses.** At 7^3 (`s57` survey: gain_ei 0.05, 0.1, 0.2, 0.5, 1; total spikes 171, 196, 226, 336, 438; inhibitory spikes outside 0.5, 1.5, 23, 117, 217), the model with inter-group E -> I factor 0.3 gives total 202, 202, 224, 338, 476 and outside 5, 5, 26, 107, 215 (`output-round5/small_results_podB.tgz`, `calib7d_f0.3_*`). One factor reproduces the whole dependence on gain_ei (derived: 0.3; origin in the engine not found). This is the calibration "0.3 from single-group calibration" of round 4.
3. **With that factor the early rounds agree, the later ones do not.** Full network, ei 0.3: round 1 and 2 joint spikes 1211 and 1630 (spiking 1134, 1254), A-alone test 666 and 1500 (593, 949), w_fast 2.8e-4 and 5.4e-4 (2.6e-4, 4.8e-4); from round 3 the spread runs away (groups outside A at round 10: 148, spiking 2.5; ignition in 82 % of the simulations). With ei 1 the full network is too stable (round 10: 0 groups outside, w_fast 4.6e-3 against 6.8e-3, no transfer in 72). The spiking network lies between: this is a sharp threshold in the inter-group inhibition (none -> ignition within ei 0.3 to 0.5), with a narrow band of contained transfers.
4. **The reduction matters for the early learning, but is not the cause of the failure of the 9^3 check.** At the same factors the reduced network has stronger early growth than the full one (ei 1: round 2 joint spikes 8507 against 3199, A-alone test 5472 against 2003; mean |w_fast| 1.1e-3 against 5.2e-4), because few large synapses make the input lumpier. It does not decide between transfer and no transfer: at ei 1 both end with no transfer, at ei 0.3 both ignite (56 % and 82 %).
5. **What the round-4 fit compensated.** The fitted pair (0.7, 1.1) on the reduced network sits just above the none -> ignition threshold: at 9^3 it ignites in 79 % of the simulations (98 % transfers), because the threshold is the same for 7^3 and 9^3 in that model and the 7^3 pairs near the surface do not lower it enough.

### Fix and repeated admission test

Fix: remove the reduction (`syn_scale` 1, 2000 synapses per neuron, derived weights; 35 s per simulation when nothing ignites, 100 to 300 s for ignitions) and fit the two remaining inter-group factors on the 12 seed-0 pair positions x realizations 0 to 4 at 7^3 (60 simulations per setting; contained / ignition / none; L1 distance from 0.50 / 0.33 / 0.17):

| ei | w | contained | ignition | none | L1 |
|---|---|---|---|---|---|
| 0.35 | 1 | 0.08 | 0.50 | 0.42 | 0.833 |
| 0.4 | 1 | 0.07 | 0.35 | 0.58 | 0.867 |
| 0.45 | 1 | 0.13 | 0.30 | 0.57 | 0.800 |
| 0.5 | 1 | 0.25 | 0.12 | 0.63 | 0.933 |
| 0.7 | 1 | 0.23 | 0.00 | 0.77 | 1.200 |
| 0.85 | 1 | 0.08 | 0.00 | 0.92 | 1.500 |
| 0.5 | 0.9 | 0.12 | 0.00 | 0.88 | 1.433 |
| **0.5** | **1.1** | **0.22** | **0.53** | **0.25** | **0.567** |
| 0.5 | 1.25 | 0.12 | 0.80 | 0.08 | 0.933 |
| 0.45 | 1.1 | 0.17 | 0.57 | 0.27 | 0.667 |
| 0.45 | 1.25 | 0.07 | 0.83 | 0.10 | 1.000 |

Chosen (lowest L1): `ei_inter_scale` 0.5, `w_inter_scale` 1.1, `learn_scale` 1 (2 free parameters, 1 of them, ei, with an independent single-group calibration at 0.3 that it does not reproduce: 0.5 against 0.3). Because the fit leaves a band in which the 9^3 result depends strongly on the setting, the 9^3 result for the unfitted w = 1 (ei 0.5) is also given.

Repeated admission test at the chosen setting (ei 0.5, w 1.1, full network; fresh realizations 5 to 9,
all 24 pair positions; `output-round5/round5/final_*`):

| check | model B | spiking reference / bound | result |
|---|---|---|---|
| class fractions, 7^3 (120 simulations) | contained 0.225, ignition 0.508, none 0.267 | 7/24, 10/24, 7/24, each within its 95 % binomial interval | pass |
| 9^3 (120 simulations) | transfers 0.383, ignitions 0.342 (contained 5, ignition 41, none 74) | transfers at most 0.42 (5 of 24), ignitions at most 0.14 (0 of 24) | **fail** (ignitions) |
| uniform C2, 7^3 (48 paired simulations, realizations 5, 6) | associations 10 (activity-dependent C2) against 12 (C2 held at 1.2); paired difference 0.04, 95 % CI -0.04 to 0.12 | same associations | pass |
| per-pair kappa, 7^3 (information only) | -0.06 | | |

Round by round on 9^3 (the 24 spiking pair positions, seeds 0 and 1, 48 simulations; medians, same
quantities as the spiking reference above):

| round | 1 | 2 | 3 | 5 | 10 | 20 | 30 |
|---|---|---|---|---|---|---|---|
| joint-round spikes | 1612 | 2115 | 4212 | 6872 | 20,859 | 42,646 | 50,086 |
| A-alone test spikes | 904 | 1675 | 2327 | 3449 | 11,218 | 21,648 | 21,698 |
| groups active outside A, B, route | 0 | 0 | 0 | 0 | 26 | 63 | 66 |
| mean abs w_fast per synapse | 2.8e-4 | 5.3e-4 | 1.7e-3 | 3.6e-3 | 2.1e-2 | 7.9e-2 | 9.9e-2 |

22 of 48 transfer, all as ignitions (first transfer in rounds 12 to 29, strays 40 to 222; spiking: rounds
14 to 22, strays 8 to 36); 26 end without transfer. The first-round weight change agrees with the
spiking runs (2.8e-4 against 2.6e-4); from round 3 the spread grows faster (round 10: 26 groups outside
against 2.5).

The unfitted w 1 (ei 0.5) gives on 9^3 transfers 0.15 and ignitions 0.10 (table above, 48 simulations),
within both bounds, but on 7^3 (fit positions, realizations 0 to 4) none 0.63, outside the interval of
7/24; it was not run as a formal admission test. No setting tried meets the 7^3 and the 9^3 check
together: the 7^3 classes need a setting above the none -> ignition threshold, at which the 9^3
lattice ignites too.

### Verdict (model B)

Not admitted: it passes the class fractions and the uniform-C2 check but fails the 9^3 check
(ignitions 0.34 against at most 0.14). The cause of round 4's failure is identified (fitted factors on
a reduced network compensating an excess of neighbour inhibition, near a sharp none -> ignition
threshold in the inter-group E -> I weight); removing the reduction narrows the gap (9^3 ignitions 0.79 at
the round-4 setting, same pair positions, -> 0.34) but does not close it. Two free parameters (ei, w). The final runs were collected by the
parent session after the round-5 agent had stopped; they are the runs it had started (`final1.sh`).

Cost and speed (pod `yz1r4af896r1ne`, `cpu3g`, 16 vCPU, 64 GB, EU-RO-1, $0.64/h, created 08:42 UTC, terminated about 12:25 UTC after the final results were downloaded; `list-pods`
empty): about 3.7 h, about $2.4 (estimated from the lifetime; billing not read). Its last runs finished at 12:16 UTC. A full-network simulation takes 35 s (no transfer) to 300 s (ignition) on one vCPU, about $0.0004 to $0.005, against about $0.017 for a GPU spiking job (iteration 65): 3 to 40 times cheaper. The reduced network (18 to 34 s) is not much faster.

## Model A (population density)

### Where it diverges

9^3, the 24 spiking pair positions, realizations 0 and 1 (48 simulations each):

| setting | contained / ignition / none | transfers | ignitions |
|---|---|---|---|
| spiking | 4 / 1 / 19 | 0.21 | 0.04 |
| `plast_scale` 0.31 (round 4) | 5 / 32 / 11 | 0.77 | 0.67 |
| `plast_scale` 1 (derived) | 4 / 43 / 1 | 0.98 | 0.90 |
| `plast_scale` 1, ei 0.3 | 0 / 48 / 0 | 1.00 | 1.00 |
| `plast_scale` 0.31, ei 0.3 | 0 / 48 / 0 | 1.00 | 1.00 |

Per round (medians): joint-round spikes with `plast_scale` 1 are 3306, 6872, 9876, 22,500 in rounds 1, 2, 3, 5 (spiking 1134, 1254, 2558, 3650); with 0.31: 3030, 3372, 3890, 6834. Before learning the A-alone test gives 1088 spikes (spiking 415, model B full 993): the same neighbour-inhibition excess as in model B. Mean |w_fast| per synapse after round 1: 3.2e-4 (spiking 2.6e-4, B full 2.9e-4), so the plasticity update with the derived amplitude gives the right first-round change; from round 2 it runs ahead (1.3e-3 against 4.8e-4), because the activity is higher.

### Causes tested

1. **Plasticity law (rule split, 4 pairs, 6 rounds, mean |w_fast| per synapse; model B full network for comparison).** pre-only: A 2.5e-4, 8.1e-4, 1.8e-3, 6.6e-3 against B 2.0e-4, 4.6e-4, 8.8e-4, 1.9e-3; STDP-only: A 6e-5 to 1.1e-4 against B 1.6e-4 to 2.1e-4. The presynaptic rule drives the growth in both; model A grows faster from round 2 (round 5: 3.4 times B).
2. **Same realization, same learned weights (decisive).** Model B (full network, derived) learns for 1, 2, 3 and 5 rounds on four pairs; its group-level mean weight changes (E -> E between groups, E -> I) and its sampled network are given to model A (`round5_cross_check.py`), and both run the A-alone test. Round 1: E / I spikes A 124 / 1188 against B 122 / 1193 (agree). Round 3: out-of-group excitatory spikes A 578 against B 193 (median of 4), inhibitory spikes 3481 against 2204, 6 groups active in both. Round 5: 708 against 216, 8 against 6 groups. With these weights model A therefore fires 2 to 4 times more than model B. The time course of a neighbouring group at 1 cell: B excitatory 38, 5, 0 spikes per 5 steps, A 53, 53, 0: in A the neurons fire a second synchronous volley that the inhibition prevents in B. Hence `plast_scale` 0.31 compensates this over-response, not the plasticity law.
3. **Options of the model, same test (round 3 / round 5 out-of-group excitatory spikes, B 193 / 216):** base 578 / 708; 24 classes 578 / 414; 48 classes 578 / 344; input fluctuation x 0.25: 580 / 740; x 0.5: 571 / 590; x 1: 596 / 644 (round 2 already 123 to 699); extra voltage spread 2 mV: 576 / 504; 5 mV: ignition; age bins 120 or latency cap 20: unchanged. None removes the over-response; resolution is not the cause. `commit_rule` "peak" (a neuron fires when v > 30 as in the engine, so that inhibition arriving during the upswing can stop it; the round-4 rule commits a neuron irrevocably at the separatrix, and in the monitored group all 102 committed excitatory spikes had an inhibitory spike of the group before their firing step) changes the timing (round 3: 0 against 193; round 5: 578 / 216) but not the excess per group (about 96 spikes per active group against 36 in B).
4. **Neighbour inhibition (ei 0.3):** gives ignition in all simulations, as in model B (the threshold is crossed); not a remedy.
5. **w_fast decay, runaway stop:** the decay acts as in the spiking network (only during learning steps; `tau_fast` 2000 steps = 5 % per round); the runaway stop is not needed (no spiking job ran away, and model A ignites with far fewer than 0.5 N spikes per step).

### Verdict (model A)

Not admitted; no fix found. The 9^3 test is repeated with the exact pair set above: 77 % transfers and 67 % ignitions at the round-4 setting (bounds 42 % and 14 %). Located: the over-response of a neighbouring group in the population model (second volley, more than one spike per neuron; the irrevocable commitment and the mean-field inhibition are the suspects, only partly tested), plus the neighbour-inhibition excess shared with model B. Cost: pod `8an6yab6kczlzz` (`cpu3c`, 8 vCPU, 16 GB, EU-RO-1, $0.24/h), created 09:21 UTC, terminated about 09:57 UTC (about 0.6 h, about $0.15); model A simulations take 5 to 25 s each.

## Open

- Origin of the factor 0.3 (inter-group E -> I) in the engine: not found; single-group, 7^3 survey s57 reproduced over four gain_ei values.
- Model A: a remedy for the second synchronous volley (abortable commitment together with a graded, non-mean-field inhibition) is not implemented.
