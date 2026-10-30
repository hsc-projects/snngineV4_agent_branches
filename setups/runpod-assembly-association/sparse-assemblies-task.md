# Task: Sparse Assemblies on Distance-Dependent Wiring

**Goal:** associate distant cell assemblies in a spatially extended spiking network, so that
activating one activates the other.
**Approach:** co-activate them, while chemicals that diffuse and decay in 3D space serve as an
additional information store outside the neuron and synapse models. So far they are released
depending on activity, storing where and when it occurred. What is stored, and how it is used
(gating plasticity, distributing a limited global fuel supply, or otherwise), is a design choice,
ideally biologically or physically plausible.

> [!NOTE]
> Successor of `runpod-assembly-association-task.md` (the minimal version, "the predecessor"): its
> requirements, rules and "Revisions agreed with the user" apply unless stated here. Approved by the
> user; **not started, waits for the user's go.** **[default]** marks a starting value the agent may
> change (log the reason). Formulas, functional forms and numbers in the variants are starting points, not
> definitions: a variant is defined by its intent, and the agent may use other forms, or propose variants not
> listed here, when they serve the goal better (log the reason and tell the user).

## Read first

1. The predecessor's report, `runpod-assembly-association-report.md`: "Handoff for the next agent"
   (above all "The protocol that passes", "What is established", "Review after iteration 63", "How to
   run a session", "Code: options added in this work").
2. `tuning-log.md`, iterations 53 to 65 (the current line of work), then 38 to 52.
3. The concept: `agents/main_feature/main-feature-readme-reconstruction.md`.
4. The papers cited below, in `archive/primary_literature/` (PDF, and a folder with the Markdown
   version); their findings as read are in the two sections "Added 2026-10-28" (entries N40 to N46
   added 2026-10-29) of `archive/unsorted_literature/assembly_association_papers_ranking.md`;
   conversion defects of some Markdown versions are listed at the top of
   `archive/primary_literature/primary_literature_index.md`. The literature search
   reports in that folder are leads only; several of their numbers are wrong.

## Terms

Established equivalents and their sources: `assembly-association-glossary.md`.

- **Network:** N Izhikevich neurons (one step = 1 ms), S fixed synapses each, grouped by position
  into location groups on a cubic grid. An **assembly** is a group whose intra-group input is boosted
  ("shortcut 1"); neurons in other groups are **ordinary neurons**.
- **Chemicals:** fields on a voxel grid (4 voxels per location-group cell along each axis,
  `vox_per_cell`) that diffuse and decay; an additional information store
  outside the neuron and synapse models. So far they are released depending on activity (linearly in
  the predecessor). The variants below try particular uses (C1 so far as a long-range bridge read by
  L2 to L5 and S4, C2 as a short-range marker for consolidation, C3 as fuel with a fixed global
  supply delivered where it was used, `FuelField` in `assoc_fields.py`); these are current ideas, not
  fixed roles. Other sources of release, other uses and further fields are open.
- **Weights:** `w_fast` (temporary, decays) and `w_perm` (permanent); normalized to [0.05, 1].
- **Rules** (`assoc_plasticity.py`): `stdp`; `pre_c1` (a firing neuron in high C1 strengthens its
  outgoing synapses, no postsynaptic spike needed); `both` (the two together).
- **Joint round:** A and B injected together, then a test with A alone on `w_fast`. **Transfer:**
  that test activates B (activity >= 0.5). **Ignition:** a transfer with more strays than the limit.
- **Short circuit stage:** after the first transfer, joint rounds in which C2 moves `w_fast` into
  `w_perm`.
- **Route:** the groups within 1 cell of the segment A-B. **Strays:** groups active (>= 0.5) in a
  test outside A, B and the route; the limit is 10 % of all groups.
- **Controls:** control 0 (A alone before training does not activate B); control 1 (C2 off; fails by
  construction, recorded only); joint-activation control (A and B in alternating rounds, never
  together, must not associate); uniform-C1 and uniform-C2 controls (the field held uniform
  wherever it is released).
- **Single-synapse threshold:** the smallest normalized weight that alone fires a resting ordinary
  neuron.

## Why and goal

In the predecessor every group is an assembly, so each group is an on/off unit: activity either
stays near A or sweeps the reservoir (iterations 45 to 63), 6 of 24 pairs associate at distance 4,
and the uniform-C2 control associates the same pairs plus one (iteration 64): the chemistry selects
nothing. Both fields were released where neurons fired and read where `w_fast` already was, so they
carried no information the synapses lacked; the route middle stays silent before learning. The
concept has sparse assemblies with ordinary neurons between them; on distance-dependent wiring these
were only surveyed without learning (iterations 45 and 51).

**Goal:** associations between sparse assemblies A and B over multi-hop routes, with the permanent
strengthening of ordinary neurons confined to the route, and the chemical fields contributing to it.

## Setup [default start]

- **Layout:** lattice with spacing 2 (64 of 343 cells are assemblies); later spacing 3 (27) and
  random (about 30, at least one free cell between assemblies).
- **Grid:** 7 x 7 x 7, N 20,000 (58 neurons per group), S 2000; later 9 x 9 x 9 (N 20,000 or 42,500).
- **Connection range:** lambda 0.4 cells (`rewire: {"lam": 0.4}`).
- **Protocol:** the predecessor's passing protocol (iteration 56, `params/session69a-stage2.json`),
  with the boost on assembly cells only: joint rounds with rule `both` and C1 skipped, short circuit
  stage with C2, final test A alone on `w_perm`.

## Pass criteria

1. **Association:** A -> B (or the reverse) >= 0.5 in the final test, no runaway, strays within the
   limit (bridge assemblies on the route may be active).
2. **Controls:** control 0 and the joint-activation control hold.
3. **Route selectivity:** `R_off` = mean permanent change per E -> E synapse onto ordinary neurons in
   an off-route shell, divided by the same in the route middle (the M / Sh regions of the
   predecessor's telemetry). 1 is an even spread, 0 the route only. Target: median <= 0.25 over
   associated pairs (predecessor: 0.18 to 0.42 in passing pairs); a pair above 0.5 is unselective.
4. **Chemical contribution:** the result differs from the uniform control of each field it uses
   (more associations or lower `R_off`, beyond the uncertainty). Otherwise it is reported as
   association without chemical selection, as in the predecessor.

## Method

- Paired comparisons on the same pairs, at least 48 pairs (two seeds) per decision, counts with
  binomial uncertainty, decision threshold fixed before the run.
- **Screening:** each variant first runs on 24 pairs (one seed) without controls; only the best one or
  two per family (S, L, K, E) get a full decision (48 pairs, all controls). The baselines S0, L0, K0
  and E0 are one shared run. (Iteration 65: 48 jobs cost about $0.8, so a full decision with two
  controls, about 144 jobs, costs about $2.4.) The rate model of `rate-model/` has not passed its
  admission test (rounds 1 to 5); it may narrow parameter ranges before screening only if a later
  round passes.
- **Distance relative to the connection range** (predecessor decision): distances are stated in
  units of lambda (d 4 at lambda 0.4 is 10 lambda), and each pair's number of direct A -> B synapses
  is recorded. Associations at different lambda are compared at equal d / lambda; 11 x 11 x 11
  (used in iteration 61) holds d 10 along a diagonal with `pair_margin` 2, enough for 10 lambda up
  to lambda 1.0. At lambda 1.5, d 4 is 2.7 lambda, so passes there do not show multi-hop
  association; use lambda 1.5 for the substrate diagnostics of Substep 2 only.
- Every run records strays, `R_off`, the distance profile of the permanent changes and, where C1 is
  used, C1 in the route middle.
- Each variant changes one thing and gets its own decision; only kept variants are combined (Substep 6).

## Variants

| Variant | Change | Basis |
|---|---|---|
| S0 | baseline weights | predecessor |
| S1 | lambda 0.6, 1.0, 1.5, compared at equal d / lambda (see Method) | one-hop estimate: input to the route middle from A and B together exceeds the input next to A from A alone only for lambda > 1 / ln 2 (about 1.44) |
| S2 | power-law tail on inter-group E -> E weights, set by `lam_sup` | Kuśmierz et al. 2020 |
| S3 | lognormal inter-group E -> E weights, sigma 1 and sigma 0.51 | Teramae et al. 2012; Teramae & Fukai 2014; Hiratani et al. 2013; Chambers & MacLean 2016; Omura et al. 2015 |
| S4 | transient transmission gain where C1 is high, with a brake where local firing is high | Egelman, King, Montague 1998 (NO raises transmitter release nearby; depletion of external calcium as the brake) |
| S5 | voltage-gated ("silent") inter-group E -> E synapses that transmit only while the postsynaptic neuron is depolarized, so input from A and B together can cross threshold where either alone does not | Wang et al. 2018 (silent synapses respond at -35 mV, not at -70 mV; conditioning, not pseudo-conditioning, makes them transmit) |
| S6 | weaker inhibition between location groups: inter-group E -> I and / or I -> E gains lowered (`gain_ei_inter`, `gain_ie_inter`), intra-group inhibition unchanged | agent's proposal after Substep 2 (user decision, 2026-10-30): the route middle receives 60 to 100 times more inhibition than excitation under joint injection |
| L0 | rule `both`, C1 skipped | predecessor |
| L1 | BTSP-like rule gated by random plateau events | Bittner et al. 2017; Wu & Maass 2025; Milstein et al. 2021; Cone & Shouval 2021 |
| L2 | BTSP-like rule gated by C1 | as L1; Gally et al. 1990 |
| L3 | `pre_c1` with a sign set by the presynaptic rate | Krekelberg & Taylor 1997; Zhuo et al. 1993 (NO with weak tetanus: potentiation); Zhuo, Kandel & Hawkins 1994 (NO with 0.25 Hz stimulation: depression; with 50 Hz: potentiation); Krekelberg & Taylor 1996 (a diffusive rule that only potentiates, as in Gally et al. 1990 and Montague et al. 1991, gives uniform weights in most circumstances; the depression at low presynaptic rates supplies the competition) |
| L4 | the better of L2 and L3 with a C1 threshold that falls each round until the first transfer | Montague 1996 (stringency); Steinbock et al. 1995 (fronts from two points first meet on the shortest path between them); field-geometry check (Substep 0) |
| L5 | C1 is also released by synapses whose temporary weight (`w_fast`) has just increased, so the C1 bridge extends itself as learning proceeds | Montague et al. 1991 (strengthened synapses become sources of the substance, so changes in synaptic strength move through tissue faster than the substance diffuses) |
| L6 | learned, local disinhibition (user decision, 2026-10-30): inhibitory synapses onto excitatory neurons weaken where C1 is high and the neuron receives excitation, together with L0's excitatory potentiation | Stöber, Lehr et al. 2020 (where feed-forward inhibition dominates, as in Substep 2, the excitatory route is unlocked by inhibitory LTD and neuromodulator-gated potentiation, each roughly doubling the postsynaptic potential) |
| K0 | C2 as in the predecessor | predecessor |
| K1 | lower C2 level, or C2 falling during the stage | Lehr et al. 2022; Montague 1996; Krekelberg & Taylor 1997 |
| K2 | tags plus a per-neuron consolidation threshold | Clopath et al. 2008; Lehr et al. 2022; Frey & Morris 1997 (a weak tetanus gives lasting LTP when another input to the same neurons was strongly tetanized about 1 h before; the tag decays within 3 h); Nunes et al. 2024 (two weakly potentiated inputs cooperate: both are maintained, neither alone) |
| K3 | short-lived C2 with a steep gate | Trapani et al. 2021, 2025; Wood et al. 2011 (NO inactivation about 150 per second); Ogasawara et al. 2007 |
| K4 | depression of non-transmitting synapses where C2 is high, plus caps on summed weights | Gally et al. 1990; Montague et al. 1991; Fiete et al. 2010; Miller & MacKay 1994; Miller & Jin 2013 (a limit on the number of strong outgoing synapses, pruning the weak ones) |
| K5 | no C2 release by neurons receiving injected current (C1 unchanged) | Ogasawara et al. 2007 |
| K6 | K2 with a consolidation budget per neuron, shared out subtractively | Lehr et al. 2022; Triesch et al. 2018; Miller & MacKay 1994 |
| K7 | cooperation and competition: a neuron's tags consolidate when its summed change lies within a band; above it, all its tags decay | Nunes et al. 2024 (a third potentiated input makes all inputs decay, the strong one included; later inputs decay more the more the earlier ones were potentiated; blocking Cdc42 turns competition into cooperation) |
| E0 | no energy | predecessor |
| E1 | C3 fuel, supply share proportional to (recent use + floor) to the power `beta`; `beta` 3, little diffusion | Montague 1996 (conceptual); Devor et al. 2007 |
| E2 | E1 with injected neurons excluded from the fuel demand, and demand reduced by local inhibitory activity | predecessor (A and B drew most of the supply); Boas et al. 2008; Reichold et al. 2009 (in a vascular model, neighbours lose much less flow than the dilated vessel gains: a fixed global supply is a design choice, not a passive vascular property) |

## Substeps

**0. Field geometry and new options**, on a CPU pod before any GPU session (the host is used only for
editing and short checks; user decision, 2026-10-29).

- **Field-geometry check** (`ChemicalField` only, no neurons): static sources at A and B, releasing
  at the rate of injected assemblies, on 7 x 7 x 7 and 11 x 11 x 11, d 4 and 6, diffusion lengths 1
  to 4 cells (4 to 16 voxels; at k 0.16, the stable maximum being 1/6, decay about 0.01 / 0.0025 /
  0.0011 / 0.0006, i.e. 100 to 1600 steps to settle, longer than one 100-step joint round: record
  the field after one round and in steady state). Record (i) C1 in the route middle against the
  off-route shell (M / Sh regions); (ii)
  the threshold at which the regions above it around A and B first connect, and whether that
  connection lies on the segment A-B; (iii) the radius of those regions around A and B at that
  threshold. Set C1's k and decay to the length with the highest (i) whose first connection lies on
  the segment. Check that C2's length keeps it a marker (about 1.4 voxels = 0.36 cells in the
  passing protocol: k 0.02, decay 0.01; diffusion length about sqrt(k / decay) voxels,
  `ChemicalField` in `assoc_fields.py`; the passing protocol's C1 settings, k 0.16, decay 0.003,
  would reach about 7.3 voxels = 1.8 cells, but its release gain was 0). **Stop rule:** if (i) stays
  below 2 at every
  length, first try other field setups (nonlinear release, a second field, other decay forms) and
  report; drop L4 only if none gives a neck, and keep the bridge C1 for L2 and L3 only if their
  screens beat L0.
- **S4:** intent: raise transmission where C1 is high, less so where firing is already high.
  **[default]** form: E -> E synapses onto a neuron transmit with a factor 1 + g x C1 / (C1 + C1_half) x (1 - u),
  where C1 is the bridge field at that neuron's group and u (0 to 1) a trace of its group's recent firing
  (**[default]** g 1, C1_half the route-middle C1 of the field-geometry check, u reaching 1 at the
  firing rate of an assembly under injection). No lasting change: the factor follows C1 and u.
  Module checks: the factor is 1 where C1 is 0 and where u is 1.
- **S5:** intent: supralinear summation of converging inputs in the route middle. **[default]** form:
  half of the inter-group E -> E synapses transmit with a factor rising sigmoidally with the
  postsynaptic membrane potential, from 0 at rest to 1 halfway to threshold, set each step through the
  per-synapse gain (`gain_map`, `assoc_engine.py`); the other synapses are scaled so that a neuron's
  summed input at threshold equals S0's. (a) the gate stays fixed; (b) a synapse strengthened above
  **[default]** 0.5 loses its gate (unsilencing, Wang et al. 2018). Module checks: the factor is 0 at
  rest and 1 above the set potential; check that the engine reads the gain when the spike is
  delivered, and report if it does not.
- **Fields:** K5 masks the injected neurons in C2's release only (both fields are released from the
  same spike counts in `assoc_protocol.py`); `c1.uniform` as the control for L2 to L5, like
  `c2.uniform`. Module checks: with K5 on, C1's release is unchanged; `c1.uniform` holds every voxel
  while C1 is released.
- **S2, S3 initial weights:** mean input per neuron as in S0; each neuron's summed outgoing weight
  normalized so that none becomes a hub (as Hiratani et al. 2013 did); the bounds [0.05, 1] apply to
  plastic changes only, not to the initial weights (user decision). S2: weights above the
  single-synapse threshold number `lam_sup` per neuron on average; the transition is critical at
  `lam_sup` 1. S3: sigma 1.0 and mu - sigma^2 = log 0.2, weights above the single-synapse threshold
  redrawn (Teramae et al. 2012: EPSPs above 20 mV, the distance from rest to threshold, redrawn; the
  strongest per neuron then about 10 mV);
  and sigma 0.51, mu -0.64 (Chambers & MacLean 2016). Strong synapses transmit on top of the noise
  of the weak ones, so S3 needs background activity (Teramae & Fukai 2014). With S0's mean (0.05) a
  neuron's strongest synapse stays far below half the single-synapse threshold (6.8 predicted for an
  ordinary excitatory neuron at the passing protocol's gains; at sigma 1 about 13 %, at most about 37 %
  at any sigma), so S3 runs in two forms (user decision, 2026-10-30): **S3a** with S0's mean input;
  **S3b** with Teramae's ratio of mean weight to threshold (about 4.5 %, mean about 0.31), inhibition
  unchanged.
- **L1, L2 (BTSP-like rule):** a gate event in a neuron (L1: a random plateau at a low rate; L2: C1
  above a threshold) opens a window; only synapses onto that neuron with presynaptic activity in the
  window change, weak ones up and strong ones down; no postsynaptic spike needed. The measured window
  is asymmetric (decay constants about 1.3 s before the plateau, 0.7 s after; Bittner et al. 2017);
  here **[default]** 200 steps, two thirds before the event. Two variants: (a) binary weights
  flipping with probability 0.5 (Wu & Maass 2025), at most one gate event per neuron per training
  (**[default]**), since a second one can reverse the first; (b) continuous: each gate event moves a
  weight toward Ip / (Ip + Id), the overlaps of a potentiation and a depression trace with the gate
  signal (Milstein et al. 2021; Cone & Shouval 2021). (b) needs no event limit, but selects only if
  the depression trace is longer than the potentiation trace (**[default]** twice as long); in
  Milstein's fit, traces under 50 ms did not reproduce the depression.
- **L3:** change = f(presynaptic rate) x (C1 - threshold) where C1 exceeds the threshold; f negative
  below a rate threshold (**[default]** the mean rate of ordinary neurons under joint injection),
  positive above; the C1 threshold above the background level.
- **L4:** the C1 threshold starts at a value taken from the field-geometry check, the same for all
  pairs (no knowledge of where A and B are), and falls by **[default]** 10 % per round until the first
  transfer, then stays.
- **L5:** intent: let learning itself extend the C1 bridge. A synapse that is strengthened releases
  C1, which can gate the next synapses further along, so the region of change can move towards the
  route middle faster than diffusion alone carries C1. **[default]** form: per step, each synapse's
  increase in `w_fast` adds release at its postsynaptic neuron's group, scaled by a gain
  (**[default]** so that a full strengthening from 0.05 to 1 releases as much as one spike), on top of
  the activity-dependent release, combined with the better of L2 and L3. A limit on release per group
  and step (**[default]** that of an injected assembly at full activity) guards against runaway. Below
  a threshold near C1's background level, release from strengthening has no effect (Montague et al.
  1991: fluctuations near the background cause no lasting change). The combined rule must keep a
  depression term: potentiation alone, spread by a diffusing messenger, tends to uniform weights
  (Krekelberg & Taylor 1996), and too much release gives no stable structure; scan the gain against
  the release limit.
- **L6** (approved by the user, 2026-10-30): intent: lower the feed-forward inhibition only where the route is
  to form, by learning, instead of everywhere (S6). **[default]** form: during the joint rounds the
  I -> E synapses onto an excitatory neuron (plastic for this rule only) are depressed by `a_inh`
  (**[default]** equal to `a_pre`) per step, times the C1 gate at that neuron (C1 released as for L2
  to L5) and times its excitatory input relative to its mean (a coincidence proxy: input from A and B
  together raises it), down to a floor of **[default]** half the initial weight (an analogue chosen by
  the agent, not derived; Stöber, Lehr et al. 2020 report about a doubling of the postsynaptic
  potential); the excitatory potentiation of L0 runs alongside. The inhibitory changes are temporary
  like `w_fast` and become permanent under C2 like the excitatory ones. Controls: uniform C1, and the
  same depression without the coincidence factor. Substep 2 found the route middle's excitation far
  below threshold even with inhibition cut to 5 % (S6), so L6 can only help together with excitatory
  growth; it belongs to Substep 3, which under the present stop rule of Substep 2 does not run
  (whether Substep 2 is rerun after the core-code fixes is pending).
- **K1 to K7:** K2 tags a synapse when its `w_fast` change exceeds a threshold and consolidates a
  neuron's tags only if its summed change exceeds a threshold proportional to 1 / (C2 + epsilon).
  K3: C2 decays within a few steps and gates consolidation through a steep sigmoid, one threshold
  for all pairs. K4: where C2 is high, synapses that did not transmit are depressed; when a neuron's
  summed incoming or outgoing weight exceeds a cap, all of them are reduced by the same amount. K6:
  each consolidation uses up a per-neuron budget, taken equally from every tag, so small tags fall
  below the threshold (a pool shared in proportion would only scale the weights, Triesch et al.
  2018). K7: intent: a neuron recruited by many potentiated inputs (as in an ignition) consolidates
  none of them, one with a few does. **[default]** band from the K2 threshold to three times it;
  above it, every tag of the neuron decays at the `w_fast` rate. Nunes et al. 2024 found competition
  to be an active destabilization rather than the division of a limited pool (K6's premise); K7
  tries that form.
- **E2** as in the table.
- **Hysteresis test:** ramp a background current to ordinary neurons up and down and record the
  mean rate; a loop means all-or-none propagation (Kuśmierz et al. 2020).

**1. Baseline.** Per layout and lambda: assemblies activate (predecessor's Substep 1), ordinary
neurons stay quiet without injection; measure the single-synapse threshold.

**2. Substrate, S0 to S5, no learning.** Per substrate record: (a) summation: do ordinary neurons
in the route middle fire under joint injection when they do not under A or B alone (input currents
always add; the question is whether the sum crosses threshold); (b) the ratio of their input under
joint injection to the input of ordinary neurons next to A under A alone; (c) the hysteresis test;
(d) the spread under joint injection against A alone. S2 and S3 at the best lambda of S1; S2 with
`lam_sup` 0.5, 1 and 2; S4 on S0 and on the best of S1 to S3, with C1 released as in Substep 0,
and with a uniform-C1 control (the same mean gain everywhere); S5 on S0 and on the best of S1 to
S3. The papers behind S2 and S3 used networks without spatial structure. **Keep** substrates with summation and a narrower hysteresis
loop than S0. S4 is kept if it adds summation to its base substrate, the uniform-C1 control does
not, its loop is no wider than the base's, and strays do not rise. If none qualifies, stop and
report: the substrate then needs a change outside these variants, such as conductance-based
synapses with slower excitation than inhibition (Chambers & MacLean 2016: tau_e 10 ms, tau_i 5 ms,
inhibitory reversal -90 mV; needs new kernels).

**3. Learning rule, L0 to L6.** On each kept substrate, d 4, all controls in the full decision;
record whether each pair's first transfer is contained or an ignition. **Keep** a rule that raises
transfers over L0 without more strays; L2 to L6 must also do worse under the uniform-C1 control.
If L5 ignites (strays rise) at every gain tried, report it and try a lower limit or a higher threshold
before dropping it.

**4. Consolidation, K0 to K7.** On the best substrate and rule. **Keep** a variant that lowers median
`R_off` against K0, keeps the pass rate within its uncertainty, and does worse under the uniform-C2
control than with its own C2, and keeps the joint-activation control (a later strong event can create an
association without pairing; Faress et al. 2024). Report K5 separately: it uses knowledge of which
neurons are injected.

**5. Energy, E1 and E2.** Only if strays or `R_off` still fail (the C3 fuel changed nothing in the
predecessor, iteration 59). **Keep** if strays fall without fewer associations.

**6. Combinations** of kept variants, at most two new ones per comparison (**[default]** S x L, then
+ K, then + E), each against its best component. When two kept variants need
incompatible settings of the same field, give them separate fields rather than combining them on
one. S4 and L2 to L5 read
the same C1 and may be combined. With E1 or E2 and S4 or L2 to L5, check C1 in the route middle:
less firing of A and B weakens the bridge.

**7. Distance and grids:** the best combination at d 6 and beyond, and at 9 x 9 x 9; record where
associations stop.

**8. Assessment video** of the best run (`assoc_assessment.py`), sampling all changed synapses, not
only the largest.

**9. Directionality** (optional, only with the user's go). On the best combination with C1: inject
A, then B after a delay shorter than C1's lifetime (**[default]** half of it); lingering messenger
links stimuli presented in succession, but only above a minimum interval and within a band of
thresholds (Krekelberg & Taylor 1997, both papers). Compare A -> B with B -> A in the
final test. Control: the same delay with C1's lifetime shorter than the delay; the asymmetry must
disappear.

## Rules

As in the predecessor (work only in this folder, no changes to `snngine_v4/`, pods in EU-RO-1,
terminate pods after download, no commits without the user's go), plus:
- **User decisions (2026-10-28):** K5, the BTSP-like rule and initial weights above the plasticity
  bound may all be tried.
- **Cost:** own cap **$25** (preliminary; the user raises it when needed), standing approval within
  it. Spend only on runs that decide something; report the cost at the end of each substep and
  before the cap would be exceeded.
- **Files:** this file, `sparse-assemblies-report.md`, `sparse-tuning-log.md`,
  `params/sparse-*.json`, `output/sp*`, and the harness code the new options need (`assoc_*.py`,
  `test_assoc_modules.py`, `runpod_assembly_runner.sh`; user decision, 2026-10-29). New options default
  to off, so earlier parameter files reproduce their runs; every new option gets a module check.
