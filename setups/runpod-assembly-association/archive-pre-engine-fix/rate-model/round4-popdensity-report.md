# Round 4, model A (population density): report

**Verdict: NOT admitted. The class fractions pass (52 contained / 49 ignition / 19 none of 120, all inside the 95 % intervals) and so does uniform C2, but the 9x9x9 grid-size check fails (68.3 % transfers, 56.7 % ignitions; spiking 5/24 and 0/24) and per-pair kappa is about 0. The model is not used for screening; code kept. Cost about $0.4.**

## Model form
Files: `popdensity_model.py`, `test_popdensity_model.py`, `admission_popdensity.py` (this folder). Reuses `rate_model.py` (sampled sizes and synapse counts, derived coupling matrices, delays, fields C1/C2, plasticity, protocol, measures) by subclassing `RateNetwork`; shared files unchanged.

Age-structured (refractory-density) finite-size population per location group, three populations per group: bulk excitatory, injected excitatory (k = 12, a random subset), inhibitory. Each is split into K = 12 parameter classes (midpoint quantiles of r; class counts multinomial, injected set hypergeometric) and age bins (steps since the last spike, 0..80, the last bin holds all older neurons). A bin has an integer neuron count and one representative membrane state (v, u) advanced with the engine's exact update (snn_simulation.cu:79-86) under the population's input. The hazard of a bin is the probability that a neuron lies beyond the separatrix v_sep(u) of the engine's map (found by bisection on the engine update, zero input); neurons are spread around the representative state by the input fluctuation, derived from the sampled synapse counts (Poisson shot noise: per presynaptic spike the synapses onto a given neuron are Poisson with mean counts/(n_pre n_post)) and passed through the +-100 clamp (moments of the clamped Gaussian). Committing neurons per step are drawn binomially; a committed neuron fires after the latency the engine map needs to exceed v = 30, is reset (v = c, u += d) and enters age 0. Spike counts are integers and feed couplings, delays, fields and plasticity (rate products with per-step spike fractions). Injection (+20) is added after the clamp, as in assoc_protocol.run. Only groups not at rest are simulated (flat bin list).
Why this form: it keeps finite neuron numbers, binomial fluctuations, refractoriness (u and reset) and synchronous recruitment explicitly; no `nu_act` is needed (round 3's measured constant is gone).

Free parameters (three, named): `sigma_scale` (multiplier on the derived input fluctuation, 1 = derived), `sigma_floor` (mV extra voltage spread, 0 = none), `plast_scale` (common multiplier on the plasticity amplitudes a_pre, a_plus, a_minus; 1 = derived value; added because no setting of the first two produced the class `none`). Finalist: sigma_scale 0, sigma_floor 0, plast_scale 0.31 (see fit). Resolution options, not fitted: K = 12 classes (K = 4 gave too synchronous a group; K = 24 equal to 12 within noise), 80 age bins, latency cap 12.

## Module checks (host: 15 of 15 pass, ~110 s; on the pod 13 of 15, the 2 failures are only the missing engine source files, which were not uploaded)
Against independent code: engine source lines; the update against plain-Python floats (300 random states); class parameters; rest state and separatrix against direct plain-Python simulation (fires 0.05 above, not 0.05 below, for E and I classes); latency and spike-time `u` against direct simulation (60 cases); clipped-Gaussian moments against Monte Carlo; the erf approximation; input mean and variance against explicitly sampled synapses (3 % and 15 %); binomial counts; quiet group stays silent for 300 steps; neuron numbers conserved (bins plus in-flight = class counts); determinism. Against a direct explicit-synapse Izhikevich simulation of the 14 groups within 1.5 cells of one injected group (10 samples each; own code in the test file): first 10 steps equal within 10 % (E 72, I 36 spikes in both), 100-step totals of the own group within 30 % (model E 108 vs direct 101, I 126 vs 116), A_own reaches 1 in both. The GPU spiking runs (s71 control0) give 410 to 464 spikes per injected group with no other group's A above 0.

Known deviations (measured): neighbouring inhibitory neurons fire more in the model (478 vs 351 spikes over the 13 neighbours; test tolerance 50 %); a few neighbour excitatory spikes (about 9, direct 0); the model's later activity (steps 20-60) is more clustered than direct (direct: E 12, 9, 6, 2 per 10 steps; model 7, 5, 15, 8).

## Sanity checks (Substep 2)
Host, single group (see module checks): the injected group activates (A_max = 1), quiet groups stay silent (0 spikes in 300 steps).
Pod (`admission_popdensity.py sanity`, sigma_scale 0, sigma_floor 0, plast_scale 0.31, realizations 5 to 9): injected group activates (A_max >= 0.5, all others <= 0.1) in 5 of 5 groups in every realization (25 of 25); quiet max spikes 0; under joint injection of the 24 pairs for 3 training rounds, groups other than A and B reach A >= 0.5 for 13 to 15 of 24 pairs per realization (14, 15, 14, 15, 13), so activity spreads in many realizations. The model transfers (unlike rounds 1 to 3).

## Fit (Substep 3, pods; 12 seed-0 positions; objective: L1 distance of class fractions from 6/4/2 of 12)
Class counts (contained/ignition/none) per setting; seeds in brackets.
- sigma_scale x sigma_floor, plast_scale 1, seed 0 (12 sims): (1,0) 3/9/0; (0.5,0) 1/11/0; (2,0) 0/12/0; (4,0) 0/12/0; (1,3) 4/8/0; (0.5,3) 1/11/0; (2,3) and (4,3) 0/12/0. No `none` anywhere; with plast_scale 1 the model always transfers.
- plast_scale 1, seeds 0 to 2 (36): (0,0) 13/23/0; (0.25,0) 10/26/0; (0.5,0) 8/28/0; (1,0) 7/29/0; (0,2) 8/28/0; (0,5) 0/36/0.
- plast_scale scan, seeds 0 to 2 (36): sigma_scale 0: ps 0.5 16/20/0; 0.4 16/18/2; 0.33 16/14/6 (L1 0.111); 0.25 10/7/19; 0.125 0/0/36. sigma_scale 0.5: ps 0.5 12/24/0; 0.4 17/18/1; 0.33 15/14/7; 0.25 13/7/16; 0.125 0/0/36. sigma_scale 1: ps 0.4 13/23/0; 0.33 16/19/1; 0.25 20/7/9.
- Finalists, seeds 0 to 4 (60): sigma 0, ps 0.33: 25/27/8 (L1 0.233); sigma 0.5, ps 0.33: 22/27/11 (0.267). Refinement sigma 0, seeds 0 to 4: ps 0.28 23/18/19 (0.300); 0.30 25/21/14 (0.167); 0.31 30/18/12 (0.067); 0.36 29/22/9 (0.067). Chosen (lowest L1, first of the tie): sigma_scale 0, sigma_floor 0, plast_scale 0.31. The sharp dependence on plast_scale (0.25 to 0.5 moves `none` from 19 to 0) means the result is sensitive to this parameter. sigma_scale 0 means the hazard is a step at the separatrix; stochasticity then comes from class sampling, binomial draws only matter through the other inputs; sigma_scale 0.5 behaved the same within noise.

## Admission test, evaluation on all 24 positions, realizations 5 to 9 (120 simulations), 7x7x7
| settings | contained | ignition | none | within 95 % intervals (0.126-0.511 / 0.221-0.634 / 0.126-0.511) | kappa (modal per pair) |
|---|---|---|---|---|---|
| sigma 0, floor 0, ps 0.31 (chosen) | 52 (0.433) | 49 (0.408) | 19 (0.158) | yes / yes / yes: **PASS** | -0.125 (all simulations: see json) |
| sigma 0, ps 0.33 | 56 (0.467) | 51 (0.425) | 13 (0.108) | yes / yes / no | 0.104 |
| sigma 0.5, ps 0.33 | 46 (0.383) | 66 (0.550) | 8 (0.067) | yes / yes / no | 0.008 |
Per-pair kappa is information only: no per-pair agreement with the spiking outcomes (as expected for group-level couplings). Mean first-transfer round and strays were recorded in the result files (not copied here).

## Grid size (9x9x9, pairs >= 2 cells from the surface, 24 pairs x realizations 5 to 9 = 120 sims, stray limit 34)
Chosen setting: 14 contained / 68 ignition / 38 none; transfer fraction 0.683, ignition fraction 0.567; bounds 0.422 (transfer) and 0.142 (ignition): **FAIL**. (ps 0.33: 21/69/30, also fails.) The model does not reproduce the drop in transfers and ignitions at larger lattice size.

## Uniform C2 (1.2), chosen setting, 24 pairs x realizations 5 to 9
Associations: 29 of 120 with activity-dependent C2, 28 of 120 with uniform C2; paired difference -0.008, 95 % interval [-0.080, 0.063], 19 discordant of 120: **PASS**.

## Speed and cost
Measured on the pods (cpu5c and cpu3c, 4 vCPU each, 4 processes per pod, full protocol without the C2 stage): 7x7x7 mean 8.5 to 15.7 s per simulation (about 1.2 M group-steps; 10.3 s for the chosen setting, 1.2 M group-steps); 7x7x7 with C2 stage and controls 15.7 s; 9x9x9 31.4 s (2.8 M group-steps). At $0.26/h for both pods (8 vCPU) this is about $0.0002 to 0.0004 per simulation of one core (4 processes per pod share the vCPUs, so about 10 s core time per simulation). The host measurement earlier (120 to 245 s) was an overloaded host and should be ignored. Total about 1.5 h x $0.26/h = about $0.4 (about 1500 simulations in total).

## Compute
Two pods of mine, because 32 vCPU were not available anywhere (cpu3c 32/16/8 and cpu5c 16/8 refused in EU-CZ-1, EU-RO-1 and EUR-IS-1; US-NE-1 refused cpu3c 32): `cs9zbjswa74lyn` (cpu5c, 4 vCPU, EUR-IS-1, $0.14/h) and `9ribx0esaaprgg` (cpu3c, 4 vCPU, EU-RO-1, $0.12/h), both created 06:44 UTC and deleted at about 08:14 UTC after the results were copied (delete status 204). The two were used in parallel (8 vCPU total) to run independent fits and checks; created by one command pair by mistake of retries, but both used. `list-pods` afterwards is empty. Result files are in the session scratchpad (`.../scratchpad/results/pod1`, `pod2`), not in the repository.

## Open problems
- The grid-size check fails: the model has no mechanism that reduces transfer on a larger lattice (in the spiking network, more neighbouring groups absorb activity through inhibition and delays; here ignitions stay at 57 %). Possibly related to the neighbouring-inhibition excess found in the module checks.
- The class fractions hold only for a narrow window of the plasticity amplitude scale (0.28 to 0.36); a plasticity amplitude 3 times smaller than derived is needed, which contradicts "derived" and suggests that the rate-product form of the learning rule overstates drive for discrete spike volleys (not investigated).
- No per-pair prediction (kappa about 0).
- Late-time activity of one group is more clustered than the direct simulation, neighbour inhibitory spikes 36 % high.
