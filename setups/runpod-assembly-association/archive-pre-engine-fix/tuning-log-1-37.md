# Tuning log, iterations 1 to 37: assembly association

Archived verbatim from `tuning-log.md` on 2026-10-26; the index of all iterations is at the top of
`tuning-log.md`. *Italic notes in parentheses* were added later and mark conclusions that a later
iteration superseded, refuted or confirmed.

## Iteration 1 (session s2, 2026-10-25): Substep 1, S and background noise
- **Hypothesis:** groups cannot be recruited because an excitatory neuron has only 0.79
  synapses onto excitatory neurons of its own group (S = 100, session s1). More synapses per
  neuron (S) and background (thalamic) input that keeps neurons closer to threshold should
  let a few injected neurons recruit their group.
- **Change:** own builder (`assoc_build.py`) with S as a parameter; background input
  `pt` (per-step probability of a uniform [0, 15] excitatory / [0, 25] inhibitory current);
  grid S in {100, 300, 1000}, k in {3, 10}, pt in {0, 0.2, 0.4}; I = 20, intra-group weight 1.0.
- **Result:** only S = 300 ran (rebuilding the engine in one process failed:
  `ExtensionByDuplicateError` from the sibling's array-interface patch).
  S = 300 gives 2.17 intra-group excitatory synapses per excitatory neuron (scales with S).
  pt = 0: `A_A` 0.07 to 0.10 (k = 3) and 0.19 to 0.33 (k = 10), only the injected
  neurons; no recruitment. pt = 0.2: network-wide activity without stimulation (baseline
  max `A_g` 0.95 to 1.0, 15 Hz mean rate); pt = 0.4: 25 Hz, everything active.
- **Decision:** one process per engine configuration (queue change); next sweep
  S in {300, 1000} with much weaker noise, pt in {0, 0.02, 0.05, 0.1}.

## Iteration 2 (session s3, 2026-10-25): Substep 1, S = 300 and 1000, weak noise
- **Hypothesis:** with S = 1000 (more intra-group synapses) and weak background input,
  injected neurons recruit their group.
- **Change:** S in {300, 1000}, k in {3, 10}, pt in {0, 0.02, 0.05, 0.1}; I = 20,
  intra-group weight 1.0 (the upper weight bound).
- **Result:** no recruitment in any setting. S = 1000 gives 7.18 intra-group excitatory
  synapses per excitatory neuron, yet with pt = 0 `A_A` equals the injected fraction
  (0.07 to 0.10 for k = 3, 0.19 to 0.33 for k = 10) and nothing else fires. Background
  input makes unstimulated groups exceed `A_g` = 0.1 already at pt = 0.02 (1.5 Hz mean rate,
  baseline max `A_g` 0.19 to 0.20) without helping recruitment; S = 1000, k = 3, pt = 0.1
  ran away (139 Hz).
- **Diagnosis:** a scale mismatch, not a tuning problem. A synaptic spike adds w <= 1 to the
  target's input current for one step; at rest an Izhikevich neuron needs roughly 15 to 20
  coincident units (estimate from the equations, not measured). 7 intra-group synapses at
  w = 1 deliver at most 7. The same limit blocks transfer between groups.
- **Decision:** stopped; needs the user's decision on how weights map to current
  (see report, Substep 1).

## Iteration 3 (session s4, 2026-10-25): global current gain vs intra-group weights above 1
- **User decision:** use a global synaptic current gain g (plasticity keeps normalized weights
  in [0.05, 1], the engine receives g * w), and also try the alternative: intra-group
  excitatory weights above 1, non-plastic (`fixed` mask in `assoc_plasticity.py`), gain 1.
- **Change:** option 1: g in {2, 5, 10, 20, 40}, intra-group weight 1.0 or the built 0.47;
  option 2: intra-group weight in {2, 5, 10, 20, 40}, g = 1; both at S in {300, 1000}, k = 3,
  I = 20, no background input.
- **Result:**
  - Option 1: a hard switch between g = 5 (no recruitment, others <= 0.10) and g = 10
    (S = 1000) or g = 20 (S = 300): the whole network becomes active and stays active
    (`A_g` = 1 everywhere at the end of the gap). No regime with one active group.
  - Option 2, S = 300: intra-group weight 20 gives `A_A` = 0.78, 0.77, 0.73, 0.83 in 4 of
    5 groups, others <= 0.03, activity ends after the gap; weight 40 is similar (others
    <= 0.08). The fifth group (group 4) stays at the injected fraction (0.07, 13 spikes) in
    every setting.
  - Option 2, S = 1000: weight 10 gives partial recruitment (0.80, 0.73, 0.50 in 3 groups);
    weights 20 and 40 run away into the whole network.
- **Decision:** refine both. Option 2: S = 300, intra weights 15 to 30, k in {3, 5}, 10 groups,
  and record why a group fails. Option 1: g between 5 and 10, with stronger inhibition
  (inhibitory weights -1.0), and g combined with a moderate intra-group boost.

## Iteration 4 (session s5, 2026-10-25): refinement on 10 groups, S = 300
- **Hypothesis:** option 2 with intra weights 15 to 30 and k = 5 recruits reliably; option 1
  has a working window between g = 5 and g = 10, possibly with stronger inhibition.
- **Change:** as decided in iteration 3; per-group diagnostics added (group size,
  intra-group excitatory synapses leaving the injected neurons).
- **Result:**
  - Option 2: 0 to 2 of 10 groups pass (best: weight 30, k = 5: 2/10). Session s4's 4/5 was
    a lucky draw. Recruitment tracks the intra-group synapses leaving the injected neurons
    (0 to 21 here): groups with about 9 or more recruit (`A_A` 0.55 to 0.68), groups with
    0 to 2 stay at the injected fraction. Others stay <= 0.05: no spread.
  - Option 1: g = 6 to 9 runs away in every group (`A_g` = 1 network-wide), also with
    inhibitory weights at the bound (-1.0). g = 2 or 3 with intra-group weights 5 to 10: the
    same split (one group recruits, runaway at g = 3, weight 7).
- **Decision:** two further levers within the requirements: (a) intermediate S (500, 700),
  where intra-group synapses are denser than at 300 but inter-group spread is weaker than at
  1000, with intra weights 10 to 20 and k = 5; (b) the energy shortcut, which is meant to
  concentrate activity, to quench the runaway of option 1 (g = 6 and 8).

## Iteration 5 (session s6, 2026-10-25): intermediate S, and energy against the runaway
- **Change:** option 2 at S in {500, 700}, intra weights {10, 15, 20}, k = 5; option 1 at
  S = 300, g in {6, 8} with energy on (consumption 0.2 or 0.5 per spike, recovery 0.01 or
  0.005, spread k = 0.1, excitability = energy squared); 10 groups each.
- **Result:**
  - **Option 2, S = 700, intra weight 20, k = 5: 9 of 10 groups pass** (`A_A` 0.66 to 0.83,
    every other group <= 0.08, activity ends after the gap). Weight 15: 8/10. S = 500: at
    most 5/10 (weight 20, with one runaway into the whole network).
  - The failing group (4) is internally sparse: 1.42 intra-group excitatory synapses per
    excitatory neuron (passing groups 3.3 to 6.4), and its injected neurons have 2.
  - Option 1 with energy: the runaway is gone, but so is recruitment (`A_A` 0.11 to 0.20),
    and unstimulated groups reach 0.22 > 0.1: energy suppresses everything evenly here.
- **Decision:** continue with option 2 at S = 700 to 850, intra weight 15 to 20, k in {5, 8},
  on 20 groups, to find a setting that passes for every group (the "any pair" requirement).
  Keep option 1 in mind for transfer between groups (Substep 4), where the intra-group
  boost does not help.

## Iteration 6 (session s7, 2026-10-25): 20 groups, S 700 to 850; first protocol probes
- **Change:** option 2, S in {700, 775, 850}, intra weight {15, 20}, k in {5, 8}, 20 groups;
  gain g in {2, 3, 4} combined with the intra boost (same intra current 20); four Substep 4
  probes at S = 700, intra current 20, k = 5, g in {1, 3}, gate thresholds 0.5 and 2.
- **Result:**
  - **S = 775, intra weight 15, k = 8: 20 of 20 groups pass** (others <= 0.10, at the
    limit). S = 775 weight 15 k 5 and weight 20 k 5: 19/20. S = 700: at most 11/20 (this
    network has two internally sparse groups, 1.1 and 1.4 intra synapses per excitatory
    neuron, and several groups whose activation spreads to the whole network);
    S = 850: at most 16/20. Each S is a different random network, so the S = 775 result
    has to be confirmed on another seed.
  - Gain g >= 2 combined with the intra boost runs away in every group.
  - Protocol probes are invalid: group A (90) of the S = 700, weight 20 network activates the
    whole network on its own (control 0 already gives `A_B` = 1.0), so C1 is high
    everywhere (about 13 along A-B), the gate opens everywhere and 2.78 of 3.5 million
    synapses change. They do show that release, gating, `w_fast`, consolidation and both
    controls run end to end.
- **Decision:** protocol on the S = 775, weight 15, k = 8 setting, A and B adjacent (1 cell)
  and 2 cells apart, gate thresholds {1, 3, 6}; in the same session Substep 1 on all 125
  groups of that network and on a second seed.

## Iteration 7 (session s8, 2026-10-25): protocol on the passing Substep 1 setting
- **Change:** S = 775, intra weight 15, k = 8, g = 1; Substep 1 on all 125 groups (seed 0)
  and 20 groups (seed 1); protocol with A-B distance 1 and 2 cells, gate thresholds
  {1, 3, 6} (C1/C2 release gain 1 per spike), up to 15 C1 rounds and 15 C2 rounds.
- **Result:**
  - Substep 1: **121/125 groups pass on seed 0** (3 groups spill into neighbours: others
    0.10 to 0.16; one weak group, 3.23 intra synapses per excitatory neuron, `A_A` 0.39);
    **20/20 on seed 1** (others <= 0.09).
  - Protocol: no association in any setting; controls 0, 1 and 2 behave as required.
    Two causes: (1) C1 reaches only 0.17 to 0.35 (gate thresholds 1 to 6), so the gate stays
    shut (0 to 14 permanent changes); (2) the neurons between A and B do not fire
    (others <= 0.09 during joint activation), so STDP has no postsynaptic spikes to work with:
    even with gating off only 470 (d = 1) and 1,022 (d = 2) synapses changed.
- **Decision:** raise the C1/C2 release gain to 20 per spike and lower the thresholds to the
  measured range; give synapses between groups more drive with a modest global gain
  g in {1.5, 2} while keeping the intra-group current at 15 (intra weight 15 / g), so that
  activity can spill into the neurons between A and B; check Substep 1 at these settings
  for runaway; a_plus 0.1.

## Iteration 8 (session s9, 2026-10-25): release gain 20, global gain 1 to 2
- **Change:** as decided in iteration 7 (S = 775, intra current 15, k = 8, C1/C2 release gain
  20, a_plus = a_minus = 0.1, thresholds {1, 3}, g in {1, 1.5, 2}, A-B distance 1 and 2).
- **Result:**
  - Substep 1 at g = 1.5 / 2: 17/20 and 16/20 groups pass (others up to 0.11 / 0.12).
  - C1 now reaches 5.5 to 9.2 near A and B, so the gate opens there, but `w_fast` stays at
    about 1e-4 and only 300 to 1,500 synapses change permanently: no transfer in any
    setting (final `A_B` <= 0.16). Activity between A and B stays low (others <= 0.13).
  - g = 2, d = 2 reports `association: true`, but it is a runaway: during the C2 stage the
    whole network became active (others up to 1.0; 1.6 to 3.1 million synapses changed), and
    control 2 fails. Not a success.
- **Diagnosis:** STDP needs postsynaptic spikes; the neurons between A and B hardly fire
  during joint activation, so the only plastic synapses with both pre and post spikes are
  the few direct ones between A and B.
- **Tooling incident:** the SSH session carrying the run went silent (buffered child output)
  and was most likely dropped without either end noticing, so the pod idled about 31 minutes
  after the run finished (05:01 UTC) until it was found and terminated (about $0.30).
  Fix: sessions now run detached on the pod and are awaited by short polls for a
  completion marker (`wait_pod_session.py`).

## Iteration 9 (session s10, 2026-10-25): activity on the A-B path
- **Hypothesis:** background input during training only (not in any test) brings the neurons
  between A and B close enough to threshold that convergent input from A and B makes them
  fire, so STDP gets postsynaptic spikes there.
- **Change:** path tracking (14 groups within 1 cell of segment A-B, pair 90 to 92);
  `train_noise` pt in {0, 0.01, 0.03}; g in {1, 1.5}; a_plus = a_minus in {0.1, 0.5};
  S = 775, intra current 15, k = 8, release gain 20, thresholds 2.
- **Result:** a sharp switch, no stable regime in between.
  - pt = 0: path groups stay at <= 0.08; about 1,000 to 1,400 synapses change; no transfer.
  - pt = 0.01 at g = 1: path groups up to 0.11, 12,000 to 29,000 synapses change; no transfer.
  - pt = 0.03, or pt = 0.01 at g = 1.5: path groups do fire in the first rounds (up to 0.71),
    then a positive feedback loop takes over: C1 rises everywhere to the 2,000 cap (decay
    0.002 per step is too slow, so C1 spreads over the whole grid), the gate opens
    everywhere, all 3.08 million plastic synapses are potentiated and the network stays
    active. The four "association" results come from this runaway (control 2 fails).
- **Diagnosis:** C1 has no spatial selectivity at this decay rate, and nothing limits the
  feedback between activity, C1 and potentiation.
- **Decision:** make C1 local (decay 0.02 or 0.05 per step: diffusion length about 2.8 or
  1.8 voxels, below one group cell); shorter `w_fast` (tau 500 steps); test the energy
  shortcut against the runaway (its stated purpose); pt = 0.01 during training, a_plus 0.5,
  g in {1, 1.5}.

## Iteration 10 (session s11, 2026-10-25): local C1, energy, shorter w_fast
- **Change:** as decided in iteration 9 (C1/C2 decay 0.02 or 0.05 per step, tau_fast 500,
  energy on or off, train_noise pt = 0.01, a_plus 0.5, g in {1, 1.5}); 8 jobs.
- **Result:** no transfer in any job; each run ends in one of two states.
  - Quiet: C1 stays local (0.1 to 1.9 along A-B, mean 0.2 to 0.8), path groups mostly
    silent (round maxima 0.08 to 0.46), 4,000 to 12,000 synapses change in `w_fast`, final
    `A_B` <= 0.06.
  - Runaway: the network ignites during training (path and others 1.0), C1 rises
    everywhere, all 3.08 million plastic synapses are potentiated. The two "association"
    results (g = 1.5, energy off) are runaways again (control 2 fails).
  - Energy on always ends quiet: it suppresses the runaway and the path activity alike.
- **Diagnosis:** with the intra-group boost the network is bistable: a group is either
  silent or (once boosted neighbours ignite each other) everything is active. The graded
  regime the concept needs (A and B active, the neurons between them firing sparsely,
  the rest quiet) does not exist with the current excitation/inhibition balance:
  inhibitory weights are bounded at -1 and scaled by the same gain as excitatory ones, and
  inhibitory neurons are only 20 % of the network.
- **Decision:** stopped for the user. Proposed next lever (within "weights by neuron type",
  identical for every pair): a separate, larger gain for inhibitory synapses (and/or for
  excitatory-to-inhibitory ones) so that spreading activity recruits inhibition before it
  ignites neighbouring groups.

## Iteration 11 (session s12, 2026-10-25): separate inhibitory gains
- **User decision:** add a separate gain for inhibitory and excitatory-to-inhibitory synapses.
- **Change:** `gain_ie` (inhibitory-to-excitatory, times g) in {2, 4, 8}, `gain_ei`
  (excitatory-to-inhibitory, times g) in {1, 2}, g in {1, 1.5}; otherwise as iteration 10
  (C1 decay 0.02, tau_fast 500, train_noise 0.01, a_plus 0.5, energy off).
- **Result:**
  - **No runaway in any of the 12 protocol runs** (iterations 8 to 10 ran away whenever
    activity spread). Unstimulated groups still reach 0.2 to 0.9 in single training rounds
    (background input), but never lock into network-wide activity.
  - Path groups fire sparsely (round maxima 0.08 to 0.44, mostly 0.1 to 0.2), `w_fast`
    stays about 1e-4, 3,300 to 26,000 synapses change permanently; no transfer (final
    `A_B` <= 0.09); all controls behave.
  - Substep 1 at g = 1.5, gain_ie 4 or 8, gain_ei 2: only 8/20 groups recruited (`A_A`
    0.49 to 0.71 in the failing ones): the stronger inhibition also limits recruitment.
- **Decision:** with runaway under control, drive learning harder in the stable setting
  (g = 1.5, gain_ie {4, 8}, gain_ei 2): training background input pt {0.02, 0.04}, a_plus
  {0.5, 1.0}, up to 30 C1 rounds, tau_fast 2000.

## Iteration 12 (session s13, 2026-10-25): driving learning in the stable setting
- **Change:** as decided in iteration 11 (intra weight 10 at g = 1.5, i.e. intra current 15).
- **Result:** stable in all 8 runs (no runaway; unstimulated groups at most 0.23 to 0.8 in
  single training rounds). **First learning trend:** in the C1-phase tests, `A_B` under
  A-alone stimulation rises over the rounds from 0.00 to 0.05 to 0.08 in every run;
  final strict tests 0.05 to 0.08 (control 0 before training: 0.00 to 0.03). 3,700 to
  53,000 synapses change permanently. Far below the 0.5 criterion; path groups stay at
  0.11 to 0.24.
- **Diagnosis:** learning now acts in the right place, but a fully potentiated plastic
  synapse still delivers at most g * 1 = 1.5 units, so even a potentiated path drives only a
  few of B's neurons. Inhibition now bounds the network, so the excitatory gain on the
  plastic (inter-group) synapses can probably be raised further without runaway.
- **Decision:** reported to the user. Proposed next: raise g (2 to 3) together with the
  inhibitory gains (gain_ie 8 to 16), keeping the intra current at 15.

## Iteration 13 (session s14, 2026-10-25): higher excitatory gain with stronger inhibition
- **User decision:** raise g (2 to 3) together with the inhibitory gains (8 to 16), intra
  current 15.
- **Change:** g in {2, 2.5, 3}, gain_ie in {8, 16}, gain_ei 2, train_noise 0.02, a_plus 0.5,
  tau_fast 2000, 30 C1 rounds; Substep 1 at g = 2 and 3 with gain_ie 16.
- **Result:**
  - No improvement in learning: B under A-alone stimulation reaches 0.03 to 0.12 (session
    s13: 0.05 to 0.08); control 0 before training 0.00 to 0.06; path groups 0.10 to 0.21.
  - g = 3, gain_ie 16: runaway even before training (control 0 `B -> A` = 1.0), so its
    "association" result is invalid. g = 2.5, gain_ie 16: the gating-off control runs away.
  - Substep 1 collapses: 4/20 groups at g = 2, 0/20 at g = 3 (gain_ie 16).
- **Diagnosis:** the gains trade recruitment against stability without increasing what the
  plasticity learns. The limiting factor is the learning rule itself: STDP needs the
  neurons between A and B to fire, and in the stable regime they fire only sparsely
  (about 10 to 20 % of a path group per round), so only a few synapses are ever potentiated.
- **Decision:** stopped for the user (13 iterations; Substep 4 has made only marginal progress
  over 7 iterations). Proposal: revise the gating rule (the task allows it within the
  requirements) so that C1 itself marks the synapses to strengthen, e.g. potentiate
  synapses whose presynaptic neuron fires inside a high-C1 region, without requiring a
  postsynaptic spike (closer to the pheromone-trail inspiration than Hebbian coincidence).

## Iteration 14 (sessions s15, s16, 2026-10-25): presynaptic C1-gated rule, saturation diagnostic
- **User decision:** revise the gating rule so that synapses whose presynaptic neuron fires
  inside a high-C1 region are potentiated without requiring a postsynaptic spike.
- **Change:** `rule="pre_c1"` in `assoc_plasticity.py` (alone or together with STDP), with an
  option `pre_post_gate` (also require the target in a high-C1 region); module check added
  (21/21 pass). s15: a_pre in {0.05, 0.2}, post gate on/off, in the stable setting of
  iteration 12. s16: a_pre in {1, 3}, kappa 0.05; plus a new diagnostic
  `diag_saturated_path` that sets every plastic synapse among A, B and the path groups to
  the upper bound and tests A alone.
- **Result:**
  - The rule works mechanically and is spatially selective: up to 250,000 synapses change
    permanently, and with the post gate the summed change falls from about 513 at the A-B
    line to 0.8 at 3.5 cells. But B under A-alone stimulation stays at 0.03 to 0.08,
    the same as the gating-off control.
  - **Saturation diagnostic: even with all 48,000 (path radius 1) or 204,000 (radius 1.5)
    plastic synapses among A, B and the path at the upper bound, A alone activates B to only
    0.05 to 0.12 at g = 1 to 3** (before: 0.00 to 0.03).
- **Conclusion:** within the current weight bounds, gains and connectivity, no plasticity
  rule can produce the association: even perfect learning stays far below 0.5. The limit is
  the maximum current a learned path can carry, not the learning rule. *(Superseded: higher
  gains with matching inhibition give a working regime, iterations 15 and 16.)*
- **Decision:** stopped for the user. Proposed next: use the saturation diagnostic (cheap,
  about 20 s per setting) to search for a regime in which the untrained network does not
  transmit A to B but the saturated path does (higher g with matching inhibition, larger
  plastic upper bound, k, intra current), before running the protocol again.

## Iteration 15 (sessions s17, s18, 2026-10-25): regime search with the saturation diagnostic
- **User decision:** search with the saturation diagnostic for a regime in which the untrained
  network does not transmit A to B but a saturated path does.
- **Change (s17):** g in {4, 8, 12}, initial excitatory-to-excitatory weight between groups
  `w_ee` in {0.05, 0.15, 0.47} (inside the bounds; lower start, same upper bound, so a
  larger dynamic range), gain_ie in {4, 16}, gain_ei 2, intra current 15, k = 8.
- **Result (s17):** no regime: either no transfer even when saturated (g = 4, gain_ie 4) or
  network-wide activity before training. Paradoxically, stronger inhibition (gain_ie 16)
  made things run away. **Cause found: a numerical artefact of the engine's integration.**
  `update_N_state_` integrates v in two 0.5 ms half-steps; a large negative input drives v
  so far down in the first half-step that the quadratic term overshoots past threshold in
  the second one (v = -65, I = -500: v -> -316 -> +717, a spurious spike). Strong inhibition
  therefore produces spikes. This may also have affected iterations 11 to 13 at
  gain_ie 8 / 16 with g >= 2.
- **Fix:** `i_min`: the summed input current is clamped from below (`AssocEngine.clamp_current`),
  a numerical safeguard, default off. Worked by hand from rest: inputs down to about -200
  stay below threshold, -300 produces a spurious spike; -100 is used.
- **Result (s18, i_min = -100):** g in {4, 6, 8}, gain_ie in {1, 4, 16}, w_ee in {0.05, 0.2}.
  - Untrained: no transfer in any setting (B <= 0.09, C <= 0.06).
  - Saturated path: g = 6, gain_ie 16: B -> A = **0.50**, C 0.10; g = 6 / 8, gain_ie 4:
    0.44 / 0.47 (C <= 0.06); g = 4: at most 0.28; gain_ie 1 at g >= 4 and gain_ie 16 at
    g = 8: runaway once saturated.
  - `w_ee` has no effect on the untrained test (identical spike counts): the untrained
    spread from A is too weak to depend on it. "Others" up to 0.2 to 0.5 in the tests are
    mostly inhibitory neurons next to A (strong excitatory-to-inhibitory gain).
- **Decision:** a narrow working window exists around g = 6 to 8, gain_ie 4 to 16. Refine it
  (g {6, 7, 8}, gain_ie {6, 8, 12}, gain_ei {1, 2}) before running the protocol there.

## Iteration 16 (session s19, 2026-10-25): regime refinement
- **Change:** g in {6, 7, 8}, gain_ie in {6, 8, 12}, gain_ei in {1, 2}, w_ee 0.2, i_min -100,
  intra current 15, k = 8, pair 90 to 92 (2 cells), path radius 1.
- **Result:** **a working regime exists** (all four diagnostic checks pass):
  - **g = 6, gain_ie 6, gain_ei 1:** untrained A -> B 0.00, B -> A 0.03; saturated path
    **A -> B 0.73, B -> A 0.53**; C <= 0.08.
  - g = 6, gain_ie 8, gain_ei 1: untrained 0.00 / 0.03; saturated 0.30 / 0.50; C <= 0.08.
  - g = 7, gain_ie 6 or 8, gain_ei 1: saturated 0.55 to 0.98, but C 0.10 to 0.16 (just over).
  - gain_ei 2 everywhere: saturated transfer at most 0.44 (stronger feedback inhibition).
  - After saturation, other groups reach 0.5 to 0.85 (the saturated path groups and
    inhibitory neurons next to A and B), while the far group C stays quiet.
- **Decision:** reported to the user. Next: run the protocol in this regime (g = 6,
  gain_ie 6, gain_ei 1, i_min -100), with the presynaptic C1 rule at high rates so that the
  learned path approaches saturation; check Substep 1 in this regime.

## Iteration 17 (session s20, 2026-10-25): protocol in the found regime
- **User decision:** run the protocol in the found regime (g 6, gain_ie 6, gain_ei 1,
  i_min -100) with the presynaptic C1 rule at high rates, and check Substep 1 there.
- **Change:** rule pre_c1 or both, a_pre in {1, 3}, kappa 0.05, train_noise off or 0.01,
  release gain 20, C1 decay 0.02, thresholds 2, up to 30 C1 rounds; Substep 1 on all 125
  groups.
- **Result:**
  - **Without training background input, a path forms and then tips over:** path-group
    activity grows over the rounds (e.g. 0.12 -> 0.25 -> 0.44 -> 0.56 -> 0.67; *largely
    inhibitory neurons, iteration 18*), and B under
    A-alone stimulation rises with it (0.08 -> 0.20 -> **0.47** at best). A few rounds later
    learning feeds on itself: the network ignites, all 3.08 million synapses are
    potentiated, and the "association" (C1 test passes after 10 to 28 rounds) is a runaway
    (control 2 fails).
  - **With training background input 0.01: stable, best result so far:** final B under
    A-alone stimulation 0.17 to 0.34 (session s13: 0.08), C <= 0.04, controls 0 and 2 pass.
    The gating-off control runs away, i.e. the chemical gate is what keeps learning local
    (formally control 1 is marked failed).
  - Substep 1: only 3/125 groups pass, because other groups reach 0.11 to 0.22 (mostly
    inhibitory neurons next to A, driven by the high gain); A reaches >= 0.5 in 113 groups
    and >= 0.42 in all.
- **Diagnosis:** the mechanism now produces a trail (path activity and transfer grow with
  training), but nothing stops it before it spreads everywhere; and `A_g` counts inhibitory
  neurons, which in this regime respond to neighbouring activity without being part of an
  assembly (the engine's own `G_firing_count_hist` counts only excitatory neurons).
- **Decision:** reported to the user (measurement definition and a stopping mechanism are
  both decisions).

## Iteration 18 (session s21, 2026-10-25): excitatory-only A_g, runaway check, saturating release
- **User decision:** count only excitatory neurons in `A_g` (as the engine's
  `G_firing_count_hist`), add a runaway check, and make C1 release self-limiting.
- **Change:** `activity_exc_only` (default now True); `test(..., exclude=path)` reports
  `contained` (C and every group outside A, B and the path <= 0.1; this definition of the
  runaway check is the agent's, not the user's); a C1-phase test that
  transfers without being contained stops training without consolidation (`runaway_round`);
  the new check `association_contained`; `ChemicalField.release(..., saturation)`:
  gain * (1 - c / saturation) per spike, never above `saturation` (module check added, 22/22
  pass). Protocol in the regime of iteration 16 with saturation 4 or 8, rule pre_c1 or
  both, a_pre 1 or 3, train_noise off or 0.01, thresholds 2 (soft 2).
- **Result:**
  - **Substep 1 passes on all 125 groups** (`A_A` >= 0.58, others 0.00, baseline 0 spikes).
  - Protocol: no learning. C1 at the end of each round reaches only 0.1 to 2.9, below the
    gate (threshold 2, fully open at 4), so at most 650 synapses change; B <= 0.12. The
    saturation level was set too close to the gate threshold.
  - With excitatory-only `A_g`, path-group activity is 0.00 to 0.09: the "path activity"
    of 0.12 to 0.67 reported in iteration 17 was largely inhibitory neurons.
- **Decision:** scale the gate to the saturation level (threshold well below saturation),
  and re-run.

## Iteration 19 (session s22, 2026-10-25): gate scaled to the saturation level
- **User decision:** rerun with the gate threshold scaled well below the C1 saturation level.
- **Change:** saturation 8 or 16, thresholds and soft widths 0.15 * saturation (gate fully
  open at 0.3 * saturation); rule pre_c1 or both, a_pre 1, train_noise off or 0.01;
  regime of iteration 16; `A_g` over excitatory neurons.
- **Result:**
  - All 8 runs contained (no runaway; C 0.00, other groups <= 0.05); controls 0 and 2 pass;
    the gating-off control still runs away (formally control 1 fails).
  - Learning is spatially selective: summed `w_fast` change about 433 at the A-B line, 215 at
    1 cell, 48 at 2 cells, 0 at 3 cells (pre_c1, sat 8, no background input).
  - **Best transfer: B alone activates A to 0.25 to 0.29** (both rules, final strict test),
    A -> B <= 0.06; B under A in the C1-phase tests plateaus at 0.06 after about 6 rounds.
  - C1 at the end of a round is 0.2 to 0.9 along A-B, below the thresholds (1.2 / 2.4), so
    the gate opens near A and B but not in the middle of the path: only 6,000 to 11,000
    synapses change (the saturation diagnostic saturated about 48,000).
- **Next (proposed):** let the gate open along the whole path: lower thresholds (e.g.
  0.05 * saturation), slower C1 decay (0.01) so C1 reaches the middle, more C1 rounds.

## Iteration 20 (session s23, 2026-10-25): low gate, slow C1 decay
- **User decision:** lower the gate thresholds, slow the C1 decay so C1 reaches the middle of
  the path, use more C1 rounds.
- **Change:** thresholds and soft widths 0.05 * saturation (saturation 8 or 16), C1/C2 decay
  0.01 or 0.005, up to 50 C1 rounds, rule both or pre_c1, no background input.
- **Result:** the opposite extreme. C1 fills the whole reservoir almost uniformly (mean =
  max, e.g. 10.7 everywhere at saturation 16, decay 0.005): the reservoir is small (5 x 5 x 5
  groups, 20 voxels per axis, zero-flux boundaries), so a slowly decaying chemical fills the
  box. The gate opens everywhere and the network runs away in round 3 or 4 of every run.
  **The runaway check worked**: it stopped every run before consolidation (`runaway_round`
  3 or 4, no permanent change), and the final tests show no spread (C and others 0).
- **Diagnosis:** decay 0.02 keeps C1 too local (gate shut in the middle of the path), 0.01 and
  slower fill the whole box. Spatial selectivity of C1 needs a diffusion length of the order
  of the A-B distance but well below the reservoir size; with A and B 2 of 5 cells apart,
  that window is narrow, and boundary effects matter. *(On the engine's spatially flat wiring.
  On the rewired network, slow decay opens the gate along the path, but also far from it, and
  goes with ignitions; iteration 42.)*
- **Decision:** reported to the user.

## Iteration 21 (session s24, 2026-10-25): larger reservoir, N = 20,000
- **User decision:** move to a larger reservoir so that C1 can be selective between A and B
  without filling the box; the user also allowed running pods in parallel (session s25,
  N = 40,000, runs alongside).
- **Change:** N = 20,000 (D = 13, segmentation 7 x 7 x 7 = 343 groups, 58 neurons per group),
  S in {775, 1000}; regime of iteration 16 unchanged (g 6, gain_ie 6, gain_ei 1, i_min -100,
  intra current 15, k = 8); Substep 1 on 20 groups; saturation diagnostic at A-B distance
  2 and 3; protocol (rule both, saturation 8, thresholds 1.2) at C1 decay 0.01, 0.015, 0.02.
- **Result:** the regime does not carry over.
  - Substep 1: 4/20 (S = 775) and 9/20 (S = 1000) groups recruited; intra-group excitatory
    synapses per excitatory neuron 1.93 / 2.56 (about 5 at N = 5000, S = 775).
  - Saturation diagnostic: no transmission even with the path saturated (0.00 to 0.02).
  - Protocol: contained (no runaway; C1 stays local, 0.1 to 0.2 along A-B), 330 to 964
    synapses change, B 0.00 to 0.02.
- **Diagnosis:** the working regime depends on the group-internal synapse density; at the
  same S, larger groups are internally sparser. S has to grow with the group size (about
  2000 at N = 20,000 to match N = 5000, S = 775), and the regime has to be re-derived with
  the saturation diagnostic for each network size. *(On the engine's wiring, S = 2000 also made
  every pair of groups densely and directly connected, iterations 38 and 39.)*
- **Session s25 (parallel), N = 40,000, S = 1000** (8 x 8 x 8 = 512 groups, 78 neurons per
  group): 1.72 intra-group excitatory synapses per excitatory neuron; Substep 1 1/20;
  saturated path transmits at most 0.14; protocol learns almost nothing (71 to 82 synapses),
  B 0.00. Confirms the scaling diagnosis. GPU utilization 96 %, 8.6 GB VRAM, about 5 minutes
  per protocol run on an RTX 4090.

## Iteration 22 (sessions s26 to s28, 2026-10-25): N = 20,000 with larger S, two pods in parallel
- **User decision:** at N = 20,000, run Substep 1 and the saturation diagnostic with S = 1500
  and S = 2000 on two pods in parallel, then the protocol in whichever regime works.
- **Regime search (s26a/b):** g in {4, 6, 8} (intra current 15), gain_ie in {4, 6, 8},
  gain_ei 1, i_min -100.
  - S = 1500 (3.83 intra-group synapses per excitatory neuron): no regime; Substep 1 at most
    4/20, saturated path at most 0.23.
  - **S = 2000 (5.06): a regime at g = 4** (gain_ie 4, 6 or 8): untrained no transfer;
    saturated path **B -> A 1.00**, A -> B 0.19 to 0.35, C <= 0.02; Substep 1 15/20 (g = 4).
    B alone already excites neighbouring groups (others about 0.5) before training. g = 6 / 8
    transfer B -> A even untrained (0.55 to 0.98).
- **Protocol (s27a/b, s28):** g = 4, gain_ie 4 or 6, C1 decay 0.01 / 0.015 / 0.02.
  **Every run crashed in its first protocol job with `cudaErrorIllegalAddress` at
  `snn_simulation.cu:1011`** (the synchronization after `update_current_`). The regime search
  on the same network (including near-global firing for 100 steps) did not crash.
  Hypothesis tested in s28: the spike ring buffer (`buffer_size_factor` 15, pointer reset at
  13 * N spikes, D = 13) overruns; raising the buffer to 40 * N (runtime default of
  `Simulation.__init__`, `assoc_build.py`) with `CUDA_LAUNCH_BLOCKING=1` crashed identically,
  so that hypothesis is refuted. The cause is inside the engine kernel and not yet known.
  *(Diagnosed in iteration 23, removed by the safeguards of iteration 24.)*
- **Decision:** stopped for the user (engine-level fault; the task forbids debugging on the
  pod and modifying `snngine_v4/`).

## Iteration 23 (session s29, 2026-10-25): crash diagnostic
- **User decision:** one diagnostic run that logs spike counts and kernel inputs per step from
  Python until the crash, then diagnose locally from the logs.
- **Change:** `AssocEngine.start_diag` writes one flushed line before and one after every
  `update()` (step, engine t, phase, spikes, weight finiteness and range, v / u / input range);
  enabled by the job parameter `diag_log`. Same job as s27a, `CUDA_LAUNCH_BLOCKING=1`.
  Log: `output/s29-crash-diagnostic/crashdiag-S2000-g4-ie4-dec0.01_steps.csv`.
- **Result:** crash at engine step 3266, in the 13th C1-phase test. In the steps before, about
  **19,900 of 20,000 neurons fired in every step**, input currents reached about 7,800 and
  membrane potentials about 60,000 (numerical explosion; weights finite, in [-7.04, 15]).
- **Diagnosis (from the code, consistent with every observation; not proven by a test; *the
  safeguards built on it removed the crash, iteration 24*):**
  the engine rewinds its spike write pointer after 13 * N spikes (`snn_simulation.cu:414`,
  hard-coded), while the spikes of the last D steps are still being read. With D = 13
  (N = 20,000) and nearly all N neurons firing every step, the spikes in the read window
  (about 13 * N) reach that threshold; the read-side bookkeeping (`n_fired_m1_to_end` etc. in
  `_update_sim_pointers`) then goes wrong and `update_current_` reads invalid spike indices.
  At N = 5000 (D = 10) even total firing stays below 13 * N, which is why only the large
  network crashed; the larger buffer did not help because the threshold is fixed in CUDA,
  not derived from the buffer size.
- **Trigger:** total, numerically exploding runaway (all neurons, every step), i.e. a state the
  protocol should never reach. Suggested mitigations (not implemented): an upper clamp on the
  summed input current (e.g. `i_max` 100) next to `i_min`, and a runaway detector in
  `AssocRun.run` that aborts a phase when more than e.g. 50 % of the neurons fire in one step;
  alternatively keep D <= 12.

## Iteration 24 (sessions s30a to s30c in parallel, s31, 2026-10-25): safeguards, rerun of s27
- **User decision:** add the upper clamp on the input current and the per-step runaway detector,
  check them, then rerun s27 at N = 20,000 (pods in parallel allowed; module checks on the pod,
  not on the host).
- **Change:** `i_max` (upper clamp next to `i_min`, `AssocEngine.clamp_current`) and
  `runaway_frac` (`AssocRun.run` stops a phase in the first step in which more than that
  fraction of all neurons fires; a stop in a C1 round ends training without consolidation, a
  stop in a C2 round ends consolidation, a stopped test is not contained); both default off.
  Three module checks on a stub engine (25/25 pass on the pod, CPU and GPU). s30a / s30b: s27a /
  s27b (gain_ie 4 / 6, C1 decay 0.01 / 0.015 / 0.02) with `i_max` 100, `runaway_frac` 0.5;
  s30c: Substep 1 and the saturation diagnostic of s26 with the safeguards, plus gain_ie 8 at
  decay 0.015. All N = 20,000, S = 2000, g = 4, seed 0, pair 249 -> 263 (2 cells).
- **Result:**
  - **No crash** in 9 protocol runs (27 with controls), including the s27a / s29 crash job
    (s30a, decay 0.01): the detector stopped it in C1 round 14 at 63 % of neurons firing. The
    detector fired in 3 main runs and in every gating-off control.
  - **The safeguards do not change the regime (s31):** the same jobs without safeguards, twice,
    with `i_max` alone and with both give identical Substep 1 results (15/20) and identical
    saturation diagnostics (one untrained value 0.02 vs 0.00). Within one process the engine is
    deterministic; between processes or GPUs it is not (s26 15/20, s30c 13/20, same jobs), so a
    single run carries noise of a few groups or tenths of `A_g`.
  - Protocol: B -> A transfers in the strict final test in 4 runs (0.84 to 1.00; ie4 dec 0.02,
    ie6 dec 0.015 and 0.02, ie8 dec 0.015), A -> B at most 0.21. C stays <= 0.02, control 0 and
    control 1 (no chemistry) pass in all runs; gating off passes in all but ie4 dec 0.02.
    **None is contained**, but B alone already drives other groups to 0.39 to 0.59 before any
    training (control 0, B -> A), so the containment check fails for this pair independently of
    learning.
  - The C1-phase test (A -> B, `w_fast` included) passes contained after 2 rounds (ie4 dec 0.02,
    0.62) and 6 rounds (ie8 dec 0.015, 0.77), but consolidation keeps little of it (strict A -> B
    0.21 and 0.15).
  - Decay 0.01 and ie4 dec 0.015 ignite gradually over 14 to 24 rounds (others 0.1 -> 0.9) and
    are stopped before consolidation.
- **Decision:** reported to the user. Open: the containment check for a pair whose B spills
  untrained; consolidation of the A -> B direction; more pairs and seeds.

## Iteration 25 (sessions s32a to s32d in parallel, 2026-10-25): Substep 1 on all 343 groups
- **User decision:** follow the agent's recommendation: retune the N = 20,000 regime globally
  until Substep 1 passes on (nearly) all groups, then the protocol on random pairs and seeds;
  containment relative to control 0 as telemetry only.
- **Hypothesis:** the pair 249 -> 263 of s30 violates Substep 1 (A under-recruited at 0.41,
  B spilling to 0.39 to 0.59); Substep 1 so far tested 20 of 343 groups and missed such groups.
- **Change:** Substep 1 on all 343 groups with counts (pass, under-recruited, spilling,
  runaway); `diag_saturated_path(n_pairs)`; `others_excess_over_control0` /
  `contained_rel_control0` in every test after control 0 (telemetry); grid over intra-group
  current {15, 20, 25}, k {8, 12}, gain_ie {4, 6, 8}, gain_ei {1, 2}, w_ee {0.1, 0.2} (72
  settings, g = 4, seed 0, safeguards on), each with the saturation diagnostic on 5 pairs at
  distance 2 and 5 at distance 3.
- **Result:** no setting passes more than **251 of 343 groups (73 %)**. Recruitment and spill
  trade off: intra current 15, k 8: 190 under-recruited, 6 spilling; intra current 25, k 12:
  60 under-recruited, 40 spilling; inhibition only moves groups between the two. w_ee 0.1 spills
  much less than 0.2 (23 to 40 vs 83 to 175 groups); intra current 25 with w_ee 0.2 runs away
  (stopped by the detector; this exposed an indexing bug in Substep 1 on a truncated run, fixed).
  **Cause:** intra-group density varies about threefold between groups: under-recruited groups
  have a median of 3.0 intra-group excitatory synapses per excitatory neuron, spilling groups
  8.1 (saturating at `A_g` = 1), passing groups 4.8. A uniform intra-group weight cannot serve
  both ends.
- **Decision:** parameters cannot fix this; normalize the intra-group input per neuron
  (iteration 26).

## Iteration 26 (sessions s33a / s33b, seeds 0 and 1, 4 pods in parallel, 2026-10-25): normalized intra-group input
- **Change (code, within shortcut 1, agent's choice):** `w_intra_ee_total`: every excitatory
  neuron's incoming intra-group excitatory weights are the total divided by its number of such
  synapses, so its summed intra-group input when its whole group fires is the same for every
  neuron (one global rule, nothing per group or pair); optional `w_intra_ee_cap` per synapse;
  intra-group synapses stay non-plastic. Module check added (27/27 pass). Grid: total intra
  current {40, 60, 80, 120}, cap {none, 30}, k {8, 12}, (gain_ie, gain_ei) in {(4, 1), (6, 2)},
  w_ee 0.1, g = 4, plus the uniform intra current 25 as reference on the same pod.
- **Result:**
  - **Substep 1: 331 / 343 (seed 0) and 318 / 343 (seed 1)** at total 120, no cap, k = 12,
    gain_ie 4, gain_ei 1 (uniform reference on the same pods: 298 and 279); spilling groups fall
    from about 30 to 0 to 5; recruitment still rises with the total; (6, 2) is worse on both
    seeds (<= 296).
  - Saturation diagnostic (5 pairs): untrained transfer and spill 0 in every pair; transfer at
    saturation 5/5 (d = 2) and 3/5 (d = 3) on seed 0, 1/5 and 4/5 on seed 1.
  - Results vary between pods of different GPUs more than s31 suggested (uniform reference:
    246 on a 4090 in s32a, 298 on an L4 in s33a, same seed and setting), so settings are
    compared only within one pod.
- **Decision:** push recruitment and transfer together: total {120, 160, 200, 240}, k {12, 16},
  g {4, 5}, 10 pairs per distance, both seeds (s34).

## Iteration 27 (session s34, seeds 0 and 1, 2 pods, 2026-10-25): recruitment vs transfer
- **Change:** total intra current {120, 160, 200, 240}, k {12, 16}, g {4, 5} (total kept in
  current units), gain_ie 4, gain_ei 1, w_ee 0.1; saturation diagnostic on 10 pairs per
  distance; one pod per seed so that settings are compared on the same GPU.
- **Result:** **total 120, k 12, g 4: Substep 1 338 / 343 (seed 0) and 332 / 343 (seed 1)**,
  2 to 3 spilling groups; but a saturated path transfers for only 5 to 6 of 10 pairs. Totals of
  160 and more, or g = 5, raise transfer to 9 to 10 of 10 but make 22 to 84 groups spill, and
  the diagnostic pairs then spill before training. One gain sets both the untrained drive
  between groups (spill) and what a fully learned path can carry (transfer).
- **Decision:** separate the two with a gain on excitatory synapses between groups only,
  `gain_ee_inter`, with w_ee lowered so that the untrained current stays the same (s35).

## Iteration 28 (session s35, 4 pods, 2026-10-25): gain between groups; protocol on random pairs
- **Change (code):** `gain_ee_inter` (excitatory-to-excitatory synapses between different
  groups, times g; module check added, 28/28); `pair_draw` (the protocol on the (k + 1)-th
  random pair). Regime total 120, k 12, g 4, gain_ie 4, gain_ei 1 with (gain_ee_inter, w_ee) in
  {(1, 0.1), (1.5, 0.067), (2, 0.05), (3, 0.05)}; protocol (s30a parameters, C1 decay 0.02, at
  most 30 C1 rounds) on pairs 0 to 2 at distance 2 for gain_ee_inter 2 and 3, both seeds.
- **Result:**
  - Regime: 1.5 and 2 leave Substep 1 unchanged (untrained current unchanged) and raise
    saturated transfer to 9 to 10 of 10 pairs (both seeds, both distances); 3 raises the
    untrained current and makes 91 to 126 groups spill.
  - **Substep 4 passes, all checks, on seed 1, pair 277 -> 275 (gain 2)**: after 2 C1 rounds
    the strict final test gives A -> B 0.51 and B -> A 0.61, contained (others <= 0.05,
    C 0.00), controls 0, 1 (both) and 2 pass. Seed 0, pair 332 -> 234 (gain 2): A -> B 0.72,
    contained, all checks except control 1 gating off.
  - The C1-phase test passes contained after 1 to 2 rounds in 7 of 12 runs, but the C2 stage
    (learning on, C1 still released, 5 rounds) over-strengthens: final tests then spread
    (others up to 1.0, C up to 0.67) in most of them. Other runs ignite during C1 (stopped by
    the runaway check, no consolidation).
  - Control 1 gating off: whenever it transfers, it is a network-wide runaway (16 to 32
    million synapses changed, C 0.4 to 0.8, others 1.0), never contained; the formal check
    counts it as an association.
- **Decision:** option `learn_in_c2` (False: the C2 stage only consolidates what the C1 rounds
  learned); gain 2 on 6 pairs per seed with it on and off (s36).

## Iteration 29 (session s36, 4 pods, 2026-10-25): consolidation only in the C2 stage
- **Change (code):** `learn_in_c2` (default True, the earlier behaviour); with False the C2
  rounds release C2 (and C1) and move `w_fast` into `w_perm` where both gates are on, without
  new C1-gated learning. Regime of iteration 28 with gain_ee_inter 2; protocol on random pairs
  0 to 5 at distance 2, seeds 0 and 1, `learn_in_c2` on and off (24 runs).
- **Result:**
  - *(Iterations 29 to 37: these associations run mainly over direct A <-> B synapses, not a
    multi-hop path, iteration 38.)*
  - **`learn_in_c2` off: 8 of 12 pairs pass Substep 4 with every check** (seed 0: 4 / 6,
    seed 1: 4 / 6), after 1 to 3 C1 rounds; strict final transfer 0.51 to 1.00, other groups
    <= 0.09, C 0.00; 7,700 to 38,000 of 40 million synapses changed permanently. Of the other
    four: two fail only control 1 gating off (a network-wide runaway, never contained), one
    never transfers within 30 rounds (B -> A 0.35), one ignites during C1 (stopped).
  - `learn_in_c2` on: 0 of 12 pass; 6 of the 8 associations spread (others 0.10 to 1.00).
  - The C1 phase is identical in both variants, yet some pairs ignite on one pod and pass on
    another (e.g. seed 0, 208 -> 206): outcomes per pair vary across GPUs.
- **Decision:** `learn_in_c2` off. Milestone video of two passing pairs (s37); then report.
- **s37 (milestone video, fresh pod):** seed 1, pair 15 -> 1 passes again with every check
  (B -> A 1.00, others 0.00, 2 C1 rounds; `output/s37-N20k-milestone-video/
  s4-ee2-lic0-pair5-seed1-video_main.mp4`); seed 0, pair 59 -> 73, which passed in s36, ignites
  in C1 round 5 this time (stopped, no consolidation): per-pair outcomes are not reproducible
  across pods, so pass rates are the meaningful measure.

## Iteration 30 (session s38, 4 pods, 2026-10-25): control 1 rule; Substep 6, distance
- **User decisions:** control 1 fails only on a contained association; a network-wide
  ignition (B active because everything is) counts as no association. Every grid cell being an
  assembly is not the intended setup; continue on that basis for now and note sparse
  assemblies (separated by at least one non-assembly cell, C one of them) as the last task
  (Substep 8 in the task file, not fully formulated).
- **Change:** control-1 checks in `substep4_protocol` accordingly; s36 re-scored: **10 of 12
  pairs pass** (the two gating-off-only failures were ignitions). s38: setting of s36
  (`learn_in_c2` off), saturation diagnostic on 10 pairs at distances 3 to 6 cells, protocol on
  6 random pairs each at distances 3, 4, 5, 6, seeds 0 and 1.
- **Result (full passes, 6 pairs per seed):** distance 2 (s36, re-scored) 10 / 12; **3: 7 / 12;
  4: 5 / 12; 5: 5 / 12; 6: 5 / 12** (6 cells spans most of the 7-cell reservoir). Passing runs
  need 1 to 4 C1 rounds, transfer 0.52 to 1.00, other groups <= 0.09, C 0.00. The saturation
  diagnostic transfers for 10 / 10 pairs at every distance (C stays inactive in 7 to 10 of 10).
  Nearly every failure beyond 2 cells is ignition during the C1 rounds (stopped by the runaway
  check, no consolidation); a few pass the C1 test but lose it in consolidation (0.08 to 0.19).
  No distance threshold within the reservoir; the limit is runaway control, not reach.
  *(Distance was not really tested: every pair of groups is directly connected on the engine's
  wiring, iterations 38 and 39.)* Caveat:
  every cell is still an assembly, so paths run through boosted cells (Substep 8).
- **Decision:** start Substep 8 in parallel (user request): assembly layouts (iteration 31).

## Iteration 31 (session s39, 4 pods, 2026-10-25): sparse assemblies (Substep 8, first pass)
- **User request:** work on isolated assemblies in parallel with the all-groups path.
- **Change (code):** `assemblies` parameter (`assembly_layout`): "all" (default, unchanged),
  "lattice" (every `spacing`-th cell per axis; spacing 2 gives 64 of 343 cells, one
  non-assembly cell between neighbours), "random" (`count` cells at Chebyshev distance > min_gap,
  seeded). Shortcut 1 (intra boost, normalization, non-plastic mask) only inside assemblies;
  `gain_ee_inter` on every excitatory synapse that is not inside an assembly; A, B, C drawn from
  assemblies only; Substep 1 tests assemblies only; with sparse layouts only non-assembly cells
  count as path, so any other assembly that activates breaks containment (agent's choice).
  Module checks for layouts, masked boost, gains and pair/path selection (31/31; one wrong test
  expectation caught by the preflight, fixed, sessions restarted). s39: s36 setting unchanged,
  lattice and random (30) layouts, seeds 0 and 1; Substep 1, saturation diagnostic and the
  protocol on 6 random pairs at distances 2 and 4.
- **Result:** **29 of 48 pairs pass every check.** Lattice: Substep 1 62 / 64 and 57 / 64,
  distance 2 6 / 12, **distance 4 11 / 12** (the assembly halfway between A and B stays silent).
  Random: Substep 1 29 / 30 and 15 / 30 (seed 1: half the assemblies peak at 0.25 to 0.47),
  distance 2 9 / 12, distance 4 3 / 12. No assembly spills in any run. Failures are mostly
  ignitions during C1, as on the all-groups path. The association forms through ordinary
  (unboosted) neurons. *(Not checked for direct A <-> B synapses, which on the engine's wiring
  connect every pair densely, iteration 39.)*
- **Decision:** raise the total intra current for sparse layouts (spill no longer limits it) and
  apply the runaway controls of iteration 32 (s41).

## Iteration 32 (session s40, 4 pods, 2026-10-25): runaway control on the all-groups path
- **Hypothesis:** beyond 2 cells the failures are ignitions during C1, so slowing or localizing
  learning should raise the pass rate.
- **Change:** setting of s38 at distances 3 and 4 (6 pairs, seeds 0 and 1), one variable at a
  time: `a_pre` 0.5 or 0.25 (presynaptic C1 learning rate, 1 before), gain_ee_inter 1.5 (w_ee
  0.067), C1 decay 0.03 (0.02 before).
- **Result (24 runs each; s38 baseline 12 / 24 pass, 9 ignitions):** **C1 decay 0.03: 17 / 24**,
  5 ignitions; **`a_pre` 0.25: 16 / 24, 2 ignitions**; gain_ee_inter 1.5: 15 / 24, 4 ignitions;
  `a_pre` 0.5: 4 / 9 (incomplete: the L4 pod reached the 45-minute session limit; L4 is several
  times slower than an RTX 4090 on protocol runs, so L4 is avoided for them from now on).
- **Decision:** combine C1 decay 0.03 and `a_pre` 0.25 on both paths (s41).

## Iteration 33 (session s41, 6 pods, 2026-10-25): combined runaway control on both paths
- **Change:** C1 decay 0.03 and `a_pre` 0.25 together. All groups: distances 3 to 6, 6 pairs,
  seeds 0 and 1 (`session41X/Y-seed1-...`, seed 0 merged into `session41XY-seed0-...` because a
  4090 was out of stock). Sparse: lattice and random (30) layouts, distances 2 and 4, 6 pairs,
  total intra current 120 and 160 (`session41-{lattice,random30}-seed0-...`; seed 1 merged into
  `session41-latrnd-seed1-...`, random-layout jobs suffixed `-rnd`).
- **Result so far (seed 1, all groups):** d 3 to 4 **10 / 12** (s38: 7 / 12), 2 ignitions;
  d 5 to 6 6 / 12 (s38: 7 / 12) with **0 ignitions** but 6 pairs not transferring within 30
  C1 rounds; passing pairs need 3 to 11 C1 rounds on average (s38: about 2). The combination
  removes ignitions but over-damps learning at long range.
- **Result so far (lattice, seed 0, sparse):** 19 / 24; total intra current 120: d 2 5 / 6,
  d 4 3 / 6; 160: d 2 5 / 6, d 4 6 / 6; Substep 1 62 / 64 (120), 59 / 64 with 3 spilling (160).
- **Result (seed 0, all groups):** d 3 4 / 6, d 4 2 / 6, d 5 3 / 6, d 6 4 / 6 = 13 / 24 (s38:
  8 / 24), 3 ignitions (s38: 14). **Both seeds, all groups: 29 / 48 (s38: 22 / 48)**, 5
  ignitions (s38: 21).
  Of the d 5 to 6 failures, 9 of 11 are pairs not transferring within 30 C1 rounds.
- **Result, sparse (complete, seeds 0 and 1, 6 pairs per cell):**

  | Layout | Intra current | d 2 | d 4 | Total |
  |---|---|---|---|---|
  | lattice | 120 | 9 / 12 | 9 / 12 | 18 / 24 |
  | lattice | 160 | 10 / 12 | **12 / 12** | **22 / 24** |
  | random (30) | 120 | 5 / 12 | 7 / 12 | 12 / 24 |
  | random (30) | 160 | 8 / 12 | 9 / 12 | 17 / 24 |

  Overall 69 / 96 (s39, current 120 without runaway control: 29 / 48). Failures: 6 ignitions,
  14 no transfer, 4 other. Passing random-layout pairs need 12 to 14 C1 rounds on average.
  Substep 1 (assemblies passing / total, current 120 / 160): lattice seed 0 62 / 64, 59 / 64
  (3 spilling); lattice seed 1 52 / 64, 52 / 64 (1 spilling); random seed 0 25 / 30, 27 / 30;
  random seed 1 26 / 30, 27 / 30. Random seed 1 at 120 is 26 / 30 here but was 15 / 30 in s39
  with the same intra-group setting, and lattice seed 1 dropped from 57 / 64 to 52 / 64: the
  variation between pods (iteration 29) affects Substep 1 too.
- **Decision:** total intra current 160 for sparse layouts from now on. As on the all-groups
  path, the remaining failures are mostly no transfer, so the runaway control over-damps
  learning on both paths. Next: a_pre 0.5 with C1 decay 0.03, and up to 60 C1 rounds at long
  range (all groups prepared as s42, iteration 34); for sparse layouts the same a_pre 0.5
  variant, plus lattice and random at d 6.

## Iteration 34 (session s42, 4 pods, 2026-10-25): long-range learning, all groups
- **Hypothesis:** at d 5 to 6 the runaway control of s41 slows learning too much (most
  failures are no transfer, not ignition), so faster presynaptic learning or more C1 rounds
  should raise the pass rate without bringing back the ignitions.
- **Change:** `params/session42-seed{0,1}-N20k-all-longrange.json`, 36 jobs per seed: variant
  `apre05` (a_pre 0.5, C1 decay 0.03, d 3 to 6, 6 pairs each) and variant `r60` (s41 setting,
  `max_c1_rounds` 60, d 5 to 6). A first start on two pods was terminated after about 5
  minutes at the user's request (no results); the rerun split each seed over two pods
  (`session42{a,b}-seed{0,1}-...`, 18 jobs each, 17 to 42 minutes).
- **Result (seeds 0 and 1, 6 pairs each):**

  | Variant | d 3 | d 4 | d 5 | d 6 | Ignitions |
  |---|---|---|---|---|---|
  | s41 (a_pre 0.25, 30 rounds), for comparison | 9 / 12 | 7 / 12 | 5 / 12 | 8 / 12 | 5 / 48 |
  | `apre05` (a_pre 0.5) | 8 / 12 | 7 / 12 | 6 / 12 | 4 / 12 | 11 / 48 |
  | `r60` (a_pre 0.25, 60 rounds) | | | 7 / 12 | 7 / 12 | 3 / 24 |

  `apre05`: 25 / 48 (s41: 29 / 48); the ignitions return (11, mostly within the first 1 to 18
  C1 rounds), and passing pairs need 1 to 11 rounds. `r60`: d 5 to 6 14 / 24 (s41: 13 / 24);
  of the 10 failures, 5 end at the 60-round limit without transferring, the others ignite or
  transfer without containment. Over both variants, the failed checks are: no association 19,
  association not contained 11, both 7. Several pairs pass the C1-phase test but lose the
  transfer in consolidation (final transfer 0.04 to 0.33).
- **Decision:** neither variant beats the s41 setting at long range; s41 stays the best known
  setting for all groups. The remaining failures are spread over three modes (ignition,
  no transfer, loss in consolidation), so a single learning-rate or round-count change does not
  address them. Pass rates at d 3 to 6 sit around 50 to 60 % with this regime.

## Iteration 35 (session s43, 2 pods, 2026-10-25): sparse assemblies with a_pre 0.5, distance 6
- **Hypothesis:** in s41 the sparse runs, especially the random layout, failed mostly by no
  transfer and needed 12 to 14 C1 rounds, so a_pre 0.5 should speed up learning there; distance
  6 is untested.
- **Change:** `params/session43-seed{0,1}-N20k-sparse-apre05.json`: s41 sparse setting with
  total intra current 160 (`w_intra_ee_total` 40), C1 decay 0.03, **a_pre 0.5**; lattice and
  random (30, layout seed 0, as in s41) layouts, d 2, 4, 6, 6 pairs each.
- **Result (seeds 0 and 1):**

  | Layout | d 2 | d 4 | d 6 | s41 at 160 (d 2 / d 4) |
  |---|---|---|---|---|
  | lattice | 7 / 12 | 10 / 12 | 8 / 12 | 10 / 12, 12 / 12 |
  | random (30) | 10 / 12 | 8 / 12 | **10 / 12** | 8 / 12, 9 / 12 |

  Total 53 / 72; at d 2 and 4, 35 / 48 (s41 at 160: 39 / 48). **Passing pairs need 1.2 to 2.4
  C1 rounds on average** (s41: 4 to 14). Ignitions 6 of 72. Distance 6 passes 18 of 24.
- **Decision:** on the sparse path a_pre 0.5 cuts the rounds to about 2 (the task prefers fewer
  rounds) at a similar pass rate: better for the random layout, slightly worse for the lattice.
  The association forms at distance 6 (almost across the reservoir) through ordinary neurons.
  *(Not checked for direct A <-> B synapses; see iterations 38 and 39.)*
  Keep a_pre 0.5 for sparse layouts; the per-pair spread between pods (iteration 29) is of the
  same order as the differences here, so more pairs would be needed to separate 22 / 24 from
  17 / 24.

## Iteration 36 (no session, 2026-10-26): why C1-phase transfers are lost in consolidation
- **Question:** on the all-groups path, why do pairs that pass the C1-phase test fail the
  final test (iteration 34)? Analysis of the saved telemetry only (s41 and s42, all-groups
  runs; host-side, no pods).
- **Data:** 80 runs passed the C1-phase test without a runaway; in 50 the final strict A -> B
  test passes ("kept"), in 30 it does not ("lost"; final transfer median 0.20, C1-phase test
  median 0.68). No C2-stage runaway in either group, and extra C2 rounds (up to 10) do not
  rescue lost runs.
- **How the two tests differ (code):** the C1-phase test is non-strict (`w_perm + w_fast`) and
  A -> B only; the final test is strict (`w_perm` only). `w_fast` moves into `w_perm` at
  `kappa * g1 * g2` per step (gates linear from 1.2 to 2.4, evaluated at the postsynaptic
  neuron) and decays with tau 2000 steps; with `learn_in_c2` off nothing new is learned.
- **Results:**
  - The overall consolidated fraction (`w_perm` change / `w_fast` after C1) is the same in
    both groups (median 0.43 kept, 0.44 lost), so not too little consolidation overall.
  - On the A-B line (synapse midpoint within 0.5 cells) consolidation works equally in both
    groups: 84 % of `w_fast` reaches `w_perm`.
  - **Lost runs learned and consolidated more away from the line:** at 1 to 3 cells from the
    line they hold about twice the `w_fast` and 1.5 to 3 times the `w_perm` change of kept
    runs, and they needed more C1 rounds (median 4 against 2). The ratio of consolidated
    change at >= 1 cell from the line to that on the line separates the groups best (median
    0.35 kept, 0.59 lost; one threshold at 0.47 classifies 74 % of runs, base rate 62.5 %), at
    every distance (d 3: 0.29 / 0.49, d 4: 0.45 / 0.83, d 5: 0.34 / 0.64, d 6: 0.37 / 0.53).
    Number of C1 rounds, distance, C1-test margin and spike counts separate worse (64 to 66 %).
  - The saved C1 / C2 profiles and snapshots are taken after each round's 50-step gap, when
    the fields have decayed (about 7 voxels above the gate threshold); they show the gates
    closed along the whole line in kept and lost runs alike, so they say nothing about the
    gates during injection.
- **Interpretation (correlational, not proven; *the inhibition part is refuted in iteration
  37: consolidating only onto excitatory neurons does not keep the transfers*):** a transfer
  is lost when the trail learned in
    the C1 rounds is spatially broad and consolidation keeps a large off-path part. C2 is
    released mostly by A and B (the most active groups in the C2 stage), so both gates are high
    around the assemblies in every direction, not only along the path. Off-path excitatory
    potentiation, including onto inhibitory neurons (the excitatory-to-inhibitory synapses are
    plastic), would raise the inhibition that A's activity recruits and divert current; the
    non-strict C1-phase test still passes because there the full `w_fast` on the line adds to
    it. Which of the two (inhibition or diversion) dominates cannot be decided from the saved
    data: the weights are not saved, and the weight statistics do not split by target type.
- **Decision (proposals, nothing run):**
  1. Telemetry first (cheap, makes the next run decisive): split `weight_change_stats` by
     target type (E / I) and by position along the line (near A, middle, near B, beyond the
     ends); record C1 / C2 along the line at the end of injection, not after the gap; add a
     strict A -> B test right after the C1-phase test, to measure how much of the transfer rests
     on `w_fast` before consolidation starts.
  2. Candidate fixes, all global: a higher C2 threshold (`theta2`) so that only the strongest
     co-activation consolidates; consolidating only excitatory-to-excitatory synapses (if the
     E / I split confirms the inhibition reading). (A strict test right after the C1-phase test,
     also proposed here, is pointless: `w_perm` changes only in the C2 stage, so before it a
     strict test equals control 0.)

## Iteration 37 (session s44, 6 pods, 2026-10-26): consolidation telemetry and two global fixes
- **Hypothesis (iteration 36):** transfers are lost because the off-path part of the trail is
  consolidated, through C2 high around A and B, possibly feeding inhibition.
- **Change (code):** `weight_change_stats` gains `split` (on / off the line, by target type
  E / I, by position along A-B: behind A, near A, middle, near B, beyond B); `gate_profile`
  records the mean C1 gate, C2 gate and product at the end of every injection (C1 and C2
  rounds) for A and B, the path and all other groups (`gates_inject_end` in the round logs);
  plasticity option `consolidate_ee_only` (consolidate only synapses onto excitatory neurons);
  module checks for each (35 in total). Sessions (s41 all-groups setting, d 4 to 6, 6 pairs,
  seeds 0 and 1, one pod each): `diag` (unchanged, telemetry), `ee` (`consolidate_ee_only`),
  `th2` (`theta2` 1.8 instead of 1.2).
- **Result:** module checks 35 / 35 on CPU and GPU.

  | Variant | d 4 | d 5 | d 6 | Total | Ignitions | Kept / C1-phase passes |
  |---|---|---|---|---|---|---|
  | `diag` (s41 setting) | 8 / 12 | 9 / 12 | 8 / 12 | **25 / 36** | 4 | 21 / 25 |
  | `ee` | 9 / 12 | 8 / 12 | 5 / 12 | 22 / 36 | 3 | 17 / 26 |
  | `th2` | 6 / 12 | 5 / 12 | 6 / 12 | 17 / 36 | 5 | 13 / 22 |

  The same setting passed 20 / 36 at these distances in s41: the spread between pods is
  about 5 pairs in 36. Telemetry (`diag`):
  - **The C1 / C2 gates open only at the neurons of A and B.** At the end of injection the
    mean C1 gate is 0.12 to 0.17 at A and B, 0.001 to 0.002 on the path and 0 elsewhere,
    in the C1 and in the C2 rounds; the product g1 * g2 is about 0.001 on the path. The
    chemical plume does not reach the threshold (1.2) between A and B.
  - **Learning and consolidation sit on synapses whose midpoint is in the middle third of
    A-B:** `w_fast` after C1 on the line 315 of about 480, `w_perm` change 204 of about 273.
    With the gate open only at A and B (rule `both` with `pre_post_gate` needs C1 at both
    ends, the STDP part at the target), these are synapses from A (or its surroundings) onto
    B and back, i.e. **direct long-range A <-> B synapses, not multi-hop paths** *(confirmed
    in iteration 38)*.
  - About a third of the consolidated change on the line, and nearly all of it off the line,
    goes onto inhibitory targets (`diag` kept: on-line E 121 / I 70, off-line E 2 / I 55).
    `ee` removes it, but transfers are still lost (17 of 26 kept), so the inhibition reading of
    iteration 36 is wrong; lost runs simply learned more of everything (about twice the change
    in every category). The lower gate at A and B during the C2 rounds in lost runs (g1 * g2
    0.07 against 0.12; open fraction 0.19 against 0.39, in all three variants) fits fewer
    consolidated synapses per learned one.
- **Decision:** neither fix helps; keep the s41 setting. The telemetry raises a question about the
  mechanism itself: if the association runs over direct A <-> B synapses, it does not use the
  multi-hop path the task describes. Diagnostic s45 (iteration 38): the same pairs with the
  direct A <-> B synapses made non-plastic.
