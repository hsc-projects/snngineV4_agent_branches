# Tuning log: sparse assemblies

One entry per step of `sparse-assemblies-task.md` (hypothesis, change, result, decision). The
predecessor's iterations are in `tuning-log.md`.

## Entry 1 (Substep 0, 2026-10-29): field-geometry check
- **Question:** at which C1 diffusion length does the field from A and B single out the route middle
  (C in M against the off-route shell Sh), and does the region {C >= theta} around A first reach B
  along the segment A-B?
- **Change (code):** `sparse_field_geometry.py` (new; `ChemicalField` only, no neurons; host smoke test
  on one case, 3 s).
- **Choice (agent):** sources axis-aligned and centred in the grid (A and B in the same row of cells);
  release one unit per step per injected group, spread over its 64 voxels, 50 steps of injection and 50
  of gap per round, as the joint rounds. All quantities are relative to C at A (the field is linear in the
  release rate).
- **Runs:** two CPU pods (cpu3c, 16 vCPU, EU-RO-1, $0.48/h; about 7 and 5 minutes); 20 cases (grids 7
  and 11, d 4 and 6, L 1, 1.5, 2, 3, 4 cells, k 0.16), rounds 1, 5, 10, 30; second run adds the gated
  readout. `output/sp0-field-geometry/`, `output/sp0-field-geometry-2/`.
- **Result, linear field:** (i) C in M against Sh stays below 2 everywhere: at most 1.51 (11^3, d 4, after
  one round), falling with length and with rounds (11^3 d 4, round 30: 1.49 at L 1 to 1.30 at L 4; 7^3
  d 4: 1.34 to 1.09; d 6 at 7^3, A and B on the surface: 1.02 to 1.06). (ii) The region around A first
  reaches B along the segment in every case (axis-aligned pairs, so symmetric; diagonal pairs not
  tested), at theta_c = 0.03 to 0.30 of C at A. (iii) At that threshold the region around A has a radius
  of about d / 2 - 0.3 cells (1.5 to 1.7 at d 4, 2.2 to 2.6 at d 6): the regions grow as spheres and meet
  at the midpoint. **Stop rule triggered** for the linear field.
- **Result, gated readout** (the other form tried first, since L2 to L4 read C1 through a threshold):
  fraction of M against Sh voxels with C >= f theta_c. At steady state (round 30), f 1: 11^3 d 4: 2.4
  (L 1), 2.6 (1.5), 2.8 (2), **3.3 (3; M 0.56 open, Sh 0.17)**, 3.1 (4); 11^3 d 6: 1.6 to 2.2; 7^3 d 4:
  1.9 to 2.0; 7^3 d 6: 1.3 to 1.5. After one round only 1.7 to 1.9. Higher thresholds do not raise the
  ratio much and close M.
- **C2 marker:** k 0.02, decay 0.01: C at 1 cell from an injected group is 1.1 % of the centre, at 2 cells
  3e-6: a marker (0.36 cells).
- **Decision:** the gated C1 passes the stop rule (ratio above 2) away from the surface, at steady state,
  with long lengths; L4 is kept. C1 default for L2 to L5: **L 3 cells (k 0.16, decay 0.0011, about 900
  steps to settle, about 9 joint rounds)**, gate threshold starting at theta_c of the field after the
  rounds run so far. The contrast needs several rounds and is weak near the surface (7^3), so L2 to L5
  are screened on 9^3 or 11^3 with `pair_margin` 2 as well as on 7^3. Cost about $0.10.

## Entry 2 (Substep 0, 2026-10-30): single-synapse threshold (prediction), S3 forms
- **Calculation (host, the engine's Izhikevich update as in `rate-model/rate_model.py`):** a one-step
  current of 16.3 fires a resting excitatory neuron (every r); inhibitory neurons 5.6 to 16.5. At the
  passing protocol's gains (4 x `gain_ee_inter` 0.6) that is a normalized inter-group E -> E weight of
  6.8; the baseline 0.05 carries 0.7 % of it. Substep 1 measures it in the engine.
- **Consequence for S3:** with S0's mean the strongest synapse of a neuron reaches about 13 % of the
  threshold at sigma 1 and at most about 37 % at any sigma (about 400 inter-group synapses per neuron),
  against about half in Teramae et al. 2012, whose mean weight is about 4.5 % of the threshold.
- **User decision:** run both, S3a (S0's mean) and S3b (Teramae's ratio, mean about 0.31).

## Entry 3 (Substep 0, 2026-10-30): options for Substeps 1 and 2, field options
- **Order (agent's choice):** the options Substeps 1 and 2 need first (S2 to S5, hysteresis test,
  single-synapse threshold) and the two field options; the L and K options follow before Substeps 3
  and 4, so that substrate results can shape them.
- **Change (code, all default off; module checks 72, of which 71 pass on the host's CPU; the
  assessment check needs Pillow, which only the pod has):**
  - `weights.inter_ee` (`AssocEngine.draw_inter_ee`, `inter_ee_mask`): lognormal (S3) or power-law
    (S2) initial inter-group E -> E weights with a given mean, normalized per presynaptic neuron; the
    plasticity bounds widen per synapse to the initial weight (bounds act on changes only). S2's form
    differs from a single Pareto, which cannot put one synapse per neuron above 6.8 at mean 0.05: a
    Pareto tail above the threshold (exponent 2) holding `lam_sup` synapses per neuron, plus a lognormal
    bulk carrying the rest of the mean; the normalization scales the bulk only.
  - `transmission` (S4) and `silent` (S5): a per-step factor on the weights written to the engine
    (`AssocRun.transmission_factor`, as `std` writes depressed weights; restored after each call);
    S5's unsilencing in plastic phases. `prop_survey` and `input_survey` release C1 when S4 is on.
  - `c1.uniform` (control for S4 and L2 to L5); `c2.no_injected` (K5).
  - Jobs `single_synapse_threshold` (one-step current scan on isolated ordinary excitatory neurons) and
    `hysteresis` (background current to ordinary neurons ramped up and down without reset).

## Entry 4 (Substeps 1 and 2, sessions sp1 and sp2, 2026-10-30): baseline and substrate S0 to S5
- **Pod:** RTX 4090 and L4 had no capacity in EU-RO-1; one RTX PRO 4500 Blackwell (SM 120, $0.72/h,
  15:11 to 15:49 UTC, about $0.45). The harness runs from its own folder on the volume
  (`setups/runpod-sparse/`), so the predecessor's folder stays untouched. First start failed: the
  backend had to be built for SM 120 and the fresh container lacked the OpenGL headers; installed in the
  container (apt), the empty failed build removed, rebuilt (the SM 89 build stays parked in
  `build_sm89`). Module checks 72 / 72 on CPU and GPU.
- **Substep 1** (lattice spacing 2, 7^3, N 20,000, S 2000; `output/sp1-substrate/`): injected
  assemblies reach A_g 1.0 at every lambda; no spikes without injection; one of 5 assemblies (group 4)
  spills into a neighbour at lambda 0.4 to 1.0, none at 1.5. **Single-synapse threshold, measured:** a
  one-step current of 19.5 for every one of 200 ordinary excitatory neurons, a normalized inter-group
  E -> E weight of **8.1** (prediction 6.8; used from here on).
- **Substep 2** (12 pairs at d 4 per setting; spikes per excitatory neuron per round; input per step to
  excitatory neurons in M; `output/sp1-substrate/`, `output/sp2-substrate/`):

  | Substrate | lambda | M joint | M A + B | Sh joint | E in M joint / A | Inh in M joint | loop max |
  |---|---|---|---|---|---|---|---|
  | S0 / S1 | 0.4, 0.6, 1.0, 1.5 | 0 | 0 | 0 | 0.17 to 0.29 / 0.10 to 0.16 | -18 to -23 | 0.003 to 0.008 |
  | S2, `lam_sup` 0.5 / 1 / 2 | 0.4 | 0 / 0.004 / 0.030 | 0.002 / 0.009 / 0.076 | 0.003 / 0.006 / 0.046 | 0.17 to 0.22 | -17 to -22 | 0.002 to 0.003 |
  | S2, `lam_sup` 0.5 / 1 / 2 | 1.0 | 0.002 / 0.012 / 0.053 | 0.003 / 0.014 / 0.108 | 0.004 / 0.009 / 0.050 | 0.26 to 0.36 | -23 to -26 | 0.006 |
  | S3a, sigma 1 and 0.51 | 0.4, 1.0 | 0 | 0 | 0 | as S0 | as S0 | 0.003 to 0.008 |
  | S3b, sigma 1, mean 0.37 | 0.4 | 3.8 | 3.5 | 3.7 | 4.0 / 3.5 | -33 | 0.034 (off-route assemblies ignite) |
  | S3b, sigma 1, mean 0.37 | 1.0 | 0.023 | 0.018 | 0.014 | 2.3 / 1.1 | -24 | 0.005 |
  | S4 (gain 1), S5 (half silent) | 0.4, 1.0 | 0 | 0 | 0 | as S0 | as S0 | 0.003 to 0.008 |

  - The ordinary substrate itself responds gradedly: under a background ramp the loop is small
    (0.002 to 0.008 spikes per step against rates up to 0.02); propagation is not all-or-none there.
  - What keeps the route middle silent is inhibition: the input to its excitatory neurons is 60 to 100
    times more inhibitory than excitatory at every lambda; excitation from A and B adds linearly (joint
    about twice A alone) but stays far below threshold.
  - **No substrate shows summation:** where the route middle fires at all (S2, S3b at lambda 1.0), it
    fires as much or more under A or B alone; S3b at lambda 0.4 activates the whole reservoir. S4 and S5
    cannot act against inhibition 60 to 100 times larger than the excitation they scale.
- **Decision:** the stop rule of Substep 2 applies (no substrate kept); reported to the user before
  trying alternative forms. Cost of Substeps 1 and 2 about $0.45.

## Entry 5 (Substep 2, session sp3, 2026-10-30): S6, weaker inhibition between groups
- **User decision:** try an inhibition variant before stopping. **Change (code):** `gain_ei_inter`,
  `gain_ie_inter` (`AssocEngine.set_gains`: E -> I and I -> E synapses between different groups times
  these; default 1); module check `inter_group_inhibition_gains_only_between_groups` (73 / 73 on CPU and
  GPU).
- **Session** (`params/sparse-sp3-inhibition.json`, `output/sp3-inhibition/`): S0, S2 (`lam_sup` 1) and
  S3b, each with inter-group E -> I or I -> E at 0.5 / 0.2 / 0.05 or both at 0.2 (S3b: three settings),
  lambda 0.4 and 1.0; 102 jobs on one RTX 4090 ($0.89/h, about 13 minutes, about $0.20). One job crashed
  (S3b, both 0.2, lambda 1.0, hysteresis: CUDA illegal address, presumably the engine's spike buffer under
  runaway).
- **Result:**
  - **S0:** weaker inter-group inhibition lowers the inhibition onto the route middle from -18 to -23 down
    to -1 to -12 per step, but its excitation stays 0.2 to 0.34 per step: no excitatory neuron there fires
    under any setting. A single synapse needs a current of 19.5; the route middle receives under 2 % of it
    per step from A and B together.
  - **S2:** the route middle fires a little (0.015 to 0.08 spikes per neuron and round), but as much under A
    or B alone (joint 0.0 to 0.9 times A + B) and as much off the route (Sh 0.7 to 1.0 times M).
  - **S3b:** every setting activates the reservoir (off-route assemblies at A_g 1, runaways at lambda 1.0).
- **Conclusion:** across S0 to S6 the input from A and B to the route middle adds linearly; where it is
  strong enough to fire neurons there, it fires them under one assembly alone and off the route as well.
  No substrate shows summation. **Stop rule of Substep 2 confirmed** after the alternative form.
- **Note:** a pod of the rate-model round-6 agent (`rm6-export`, RTX PRO 4000 Blackwell, SM 120) was
  created on the same volume at 23:18 UTC, three minutes before this session's RTX 4090 (SM 89); the
  runner swaps the backend build per architecture, so the two must not run at the same time. This
  session finished at about 23:31 and its pod is terminated.
