# Tuning log: assembly association

One entry per tuning iteration (Substep 5 of
`runpod-assembly-association-task.md`). Each entry: hypothesis (from the last run's
telemetry), change (parameters first, code only when parameters cannot address it),
result, decision. Default changes that are not tuning go in the report instead.
*Italic notes in parentheses* were added later. They mark conclusions that a later iteration
superseded, refuted or confirmed, and name that iteration. The original text is unchanged.

Iterations 1 to 37 (harness, regime, N = 20,000 retune, engine wiring) are archived verbatim in
`tuning-log-1-37.md`; iterations 38 onward follow the index below. The report's "History of
approaches" groups them by approach.

## Index

| Iteration | Session | Topic | Where |
|---|---|---|---|
| 1 | session s2 | Substep 1, S and background noise | `tuning-log-1-37.md` |
| 2 | session s3 | Substep 1, S = 300 and 1000, weak noise | `tuning-log-1-37.md` |
| 3 | session s4 | global current gain vs intra-group weights above 1 | `tuning-log-1-37.md` |
| 4 | session s5 | refinement on 10 groups, S = 300 | `tuning-log-1-37.md` |
| 5 | session s6 | intermediate S, and energy against the runaway | `tuning-log-1-37.md` |
| 6 | session s7 | 20 groups, S 700 to 850; first protocol probes | `tuning-log-1-37.md` |
| 7 | session s8 | protocol on the passing Substep 1 setting | `tuning-log-1-37.md` |
| 8 | session s9 | release gain 20, global gain 1 to 2 | `tuning-log-1-37.md` |
| 9 | session s10 | activity on the A-B path | `tuning-log-1-37.md` |
| 10 | session s11 | local C1, energy, shorter w_fast | `tuning-log-1-37.md` |
| 11 | session s12 | separate inhibitory gains | `tuning-log-1-37.md` |
| 12 | session s13 | driving learning in the stable setting | `tuning-log-1-37.md` |
| 13 | session s14 | higher excitatory gain with stronger inhibition | `tuning-log-1-37.md` |
| 14 | sessions s15, s16 | presynaptic C1-gated rule, saturation diagnostic | `tuning-log-1-37.md` |
| 15 | sessions s17, s18 | regime search with the saturation diagnostic | `tuning-log-1-37.md` |
| 16 | session s19 | regime refinement | `tuning-log-1-37.md` |
| 17 | session s20 | protocol in the found regime | `tuning-log-1-37.md` |
| 18 | session s21 | excitatory-only A_g, runaway check, saturating release | `tuning-log-1-37.md` |
| 19 | session s22 | gate scaled to the saturation level | `tuning-log-1-37.md` |
| 20 | session s23 | low gate, slow C1 decay | `tuning-log-1-37.md` |
| 21 | session s24 | larger reservoir, N = 20,000 | `tuning-log-1-37.md` |
| 22 | sessions s26 to s28 | N = 20,000 with larger S, two pods in parallel | `tuning-log-1-37.md` |
| 23 | session s29 | crash diagnostic | `tuning-log-1-37.md` |
| 24 | sessions s30a to s30c in parallel, s31 | safeguards, rerun of s27 | `tuning-log-1-37.md` |
| 25 | sessions s32a to s32d in parallel | Substep 1 on all 343 groups | `tuning-log-1-37.md` |
| 26 | sessions s33a / s33b, seeds 0 and 1, 4 pods in parallel | normalized intra-group input | `tuning-log-1-37.md` |
| 27 | session s34, seeds 0 and 1, 2 pods | recruitment vs transfer | `tuning-log-1-37.md` |
| 28 | session s35, 4 pods | gain between groups; protocol on random pairs | `tuning-log-1-37.md` |
| 29 | session s36, 4 pods | consolidation only in the C2 stage | `tuning-log-1-37.md` |
| 30 | session s38, 4 pods | control 1 rule; Substep 6, distance | `tuning-log-1-37.md` |
| 31 | session s39, 4 pods | sparse assemblies (Substep 8, first pass) | `tuning-log-1-37.md` |
| 32 | session s40, 4 pods | runaway control on the all-groups path | `tuning-log-1-37.md` |
| 33 | session s41, 6 pods | combined runaway control on both paths | `tuning-log-1-37.md` |
| 34 | session s42, 4 pods | long-range learning, all groups | `tuning-log-1-37.md` |
| 35 | session s43, 2 pods | sparse assemblies with a_pre 0.5, distance 6 | `tuning-log-1-37.md` |
| 36 | no session | why C1-phase transfers are lost in consolidation | `tuning-log-1-37.md` |
| 37 | session s44, 6 pods | consolidation telemetry and two global fixes | `tuning-log-1-37.md` |
| 38 | session s45, 2 pods | are the associations direct A <-> B synapses? | below |
| 39 | session s46, 1 pod | connectivity survey over N and S | below |
| 40 | session s47, 4 pods | rewired network, survey and regime search | below |
| 41 | sessions s48, s49e | regime bracket and first protocol on the rewired network | below |
| 42 | session s50, 5 pods | chemical reach on the rewired network | below |
| 43 | session s51, 16 pods | oracle chemistry and decoupled chemistry | below |
| 44 | session s52, 13 pods | learning speed with oracle chemistry | below |
| 45 | sessions s53, s54, s55; 30 pods | propagation survey without learning | below |
| 46 | session s59, 8 pods | fluctuation-driven, balanced background | below |
| 47 | session s60, 2 pods | is there a two-sided input signal for a coincidence-gated release? | below |
| 48 | session s61, 9 pods | convergence range (A), normalization (B), capture (D) | below |
| 49 | session s62, 2 pods | capture plus normalization with real chemistry | below |
| 50 | session s63, 10 pods | rebalancing excitation and inhibition | below |
| 51 | session s64, 4 pods | bridge threshold diagnostic | below |
| 52 | session s65, 5 pods | background input on ordinary neurons only (A1) | below |
| 53 | no session yet | pass criterion revised; s61h reread | below |
| 54 | session s67, 3 pods | C1 skipped; C2 short circuit stage with energy, stage 1 | below |
| 55 | session s68, 5 pods | stage 1b, depleting energy and proportional C2 | below |
| 56 | session s69 | stage 2, the joint-activation test | below |
| 57 | session s70 | shared-pool energy | below |
| 58 | no session | C3 fuel prepared | below |
| 59 | session s71, 14 + 3 pods | C3 fuel, slower growth, distance 6 | below |
| 60 | session s72, 6 pods | rollback before ignition | below |
| 61 | session s73, 14 pods | larger grid, pairs away from the surface | below |
| 62 | session s74, 9 pods | more reach in the larger grid; local activity-dependent inhibition | below |
| 63 | session s75, 4 pods | short-term synaptic depression | below |
| 64 | session s76, 3 pods | uniform-C2 control; Substep 7 assessment video | below |
| 65 | session s77, 3 pods | joint rounds without gaps | below |

## Iteration 38 (session s45, 2 pods, 2026-10-26): are the associations direct A <-> B synapses?
- **Hypothesis:** in the all-groups regime the association forms on existing direct long-range
  synapses between A and B, because the chemical gates open only at A and B (iteration 37).
- **Change (code):** `direct_stats` (counts and summed initial weight of the direct A -> B and
  B -> A synapses, now in every result's `pair`), protocol flag `freeze_direct_AB` (diagnostic:
  those synapses are not plastic, in the main run and the controls), module check (36 in total).
  Sessions `session45-seed{0,1}-N20k-freeze-direct.json`: the s44 `diag` jobs (same pairs, d 4 to
  6) with `freeze_direct_AB`.
- **Result:** module checks 36 / 36 on CPU and GPU. 14 of 18 jobs per seed finished within the
  40-minute session limit (frozen runs often go to 30 C1 rounds; d 6 pair 2 hit the deadline in
  a control on both seeds). **On the 28 pairs run both ways: 20 pass with the direct synapses
  plastic (s44 `diag`), 6 with them frozen**; 16 pass only with them, 2 only frozen (pod
  spread), 4 both. Every pair has **hundreds of direct excitatory synapses** from A onto B
  (median 318 at d 4, 359 at d 5, 342 at d 6; range 138 to 554), and the count does not fall
  with distance: with S = 2000 in a 7-cell reservoir, every tested pair is densely and
  directly connected, up to distance 6 (almost across the reservoir).
- **Decision:** in the all-groups regime at N = 20,000, the association rests mainly on the
  existing direct A <-> B synapses, which the chemical gates (open only at A and B, iteration 37)
  select; it is not the multi-hop path through the neurons between A and B that the task
  describes ("A and B ... are not (or only weakly) directly connected", "multi-hop paths through
  existing synapses"). The pass rates of Substeps 4 and 6 at this size therefore do not show
  the intended mechanism. Overcoming distance needs a reservoir in which distant groups have few
  or no direct synapses (larger extent relative to the connection range, or a shorter connection
  range at the same S), and chemistry that opens the gate between A and B. *(A larger extent
  does not help: the engine's connection range scales with the reservoir, iteration 39; the
  wiring was made distance-dependent instead, iteration 40.)* How to proceed is the
  user's decision (requirements); reported. Cost cap essentially reached (about $19.6 of $20),
  so no further pod sessions.
- **User decision (2026-10-26):** redesign the reservoir so that distant groups have few or no
  direct synapses; cap raised to $30.

## Iteration 39 (session s46, 1 pod, 2026-10-26): connectivity survey over N and S
- **Why the reservoir is densely connected (from the engine code, not run):** each group's
  connection probability is a function of the delay, and the delays are the group distance
  scaled to the reservoir's maximum (`spnn_reservoir.py:114-116`, `(D - 1) * dist / max_dist`);
  the profile (sigmoid plus a floor `gamma * (1 - (d / D)^2)`, `snn_representation.cu:130-144`)
  is fitted per group so that its S synapses are spent (`roughly_optimize_connection_probabilities`).
  The grid follows from D (about D / sqrt(3) cells per axis, `generate_segmentation`), so one
  delay step is about one cell. Consequences: enlarging the reservoir alone does not change the
  range in cells; what matters is S against the number of neurons the near delays can hold. The
  engine's own default S at N = 20,000 is sqrt(N) + 50 = 191; S = 2000 (10 % of N) forces the
  surplus onto distant groups.
- **Change (code):** job `conn_survey`: builds the network only and counts the
  excitatory-to-excitatory synapses between every ordered pair of groups, summarized by the
  cell distance (median, mean, maximum, fraction of pairs with none, per target neuron), plus
  D, G, segmentation and excitatory neurons per group. Session
  `params/session46-conn-survey.json`: N 20k (S 200, 500, 1000, 2000), 50k (500, 1000, 2000),
  100k (500, 1000, 2000), 150k (1000, 2000).
- **Result (s46, 1 pod, about 8 minutes):** **the engine's connectivity is practically flat in
  space in every configuration.** Median E -> E synapses per ordered group pair, by cell
  distance: N 20k / S 2000: d 1 214, d 3 228, d 6 198, d 10 117; N 20k / S 200: 18 at d 1 and 16
  at d 6; N 100k / S 500: 61 at d 1 and 59 at d 6; N 150k / S 2000: 348 at d 1 and 345 at d 6.
  Pairs without any synapse: 0 to 7 % even at the largest distances. Larger N or smaller S scale
  every count down alike, near and far; no (N, S) gives distant groups few direct synapses and
  near ones many. Distance in this engine sets the delays, not the connection probability.
- **Decision:** distance-dependent connectivity has to be added in the harness (a global
  connection-probability rule, within the task's latitude; the engine stays unmodified):
  `AssocEngine.rewire_by_distance` (engine option `rewire: {"lam", "seed"}`) redraws every
  synapse's target with probability proportional to (neurons of the target's type in the group)
  times exp(-d / lam), keeps the target type (inhibitory -> excitatory only, per-type counts as
  built), avoids autapses, sets each synapse's delay by the engine's rule from the new distance
  and re-sorts the delay buckets (`N_delays`, read by the simulation kernel); module check
  `rewiring_keeps_types_and_delays` (37 in total). Expected counts (analytic, 7-cell grid,
  N 20k, S 2000): lam 0.4: about 34 E -> E synapses per target neuron from a face neighbour
  (flat engine: about 4.5), about 15 per group pair at d 3, 2 at d 4, 0.2 at d 5; lam 0.5: 9 at
  d 4, 1.5 at d 5. About three quarters of the synapses then lie inside the own group, whose
  input shortcut 1 normalizes per neuron anyway.

## Iteration 40 (session s47, 4 pods, 2026-10-26): rewired network, survey and regime search
- **Change:** `params/session47survey-rewired.json` (conn_survey, N 20k, S 2000 / 1000, lam
  0.4 / 0.5); `params/session47regime{a,b,c}-lam0.4.json` (N 20k, S 2000, lam 0.4, s44 `diag`
  setting otherwise): `gain_ee_inter` 0.15, 0.3, 0.6 (neighbours now carry about 7 times as many
  synapses per target as before, and w_ee cannot go below its bound 0.05) times `gain_ie` 2, 4
  (inhibition is now local as well); per combination Substep 1 on 100 groups and the saturation
  diagnostic on 6 pairs each at d 4 and d 6 (an untrained path must not transmit, a saturated
  one must).
- **Result:** module checks 37 / 37. **The rewiring gives the intended connectivity** (median
  E -> E synapses per group pair; lam 0.4: d 1 1393, d 2 141, d 3 17, d 4 2 (24 % of pairs
  none), d 5 0 (84 % none), d 6 0 (99 % none); lam 0.5: d 3 51, d 4 8, d 5 1 (35 % none), d 6 0
  (84 % none)). Regime (lam 0.4): no untrained transmission in any setting (B 0.00 at d 4 and 6);
  saturated path transmits only at `gain_ee_inter` 0.6: `gain_ie` 2 d 4 6 / 6, d 6 4 / 6;
  `gain_ie` 4 4 / 6, 2 / 6; 0.3: 2 / 6 at d 4 at most; 0.15: none. Substep 1 (100 groups):
  90 / 100 at `gain_ee_inter` 0.15 and 0.3 (no spill; the failures are the larger groups, 48 to
  59 excitatory neurons, A_max 0.20 to 0.48), 76 to 77 / 100 at 0.6 (about 14 groups spill into
  neighbours). A session of 6 such jobs takes about 3 minutes.
- **Decision:** `gain_ie` 2; bracket `gain_ee_inter` between 0.3 and 0.6 and raise the total
  intra current (30 -> 40) for the larger groups (s48), and run the protocol directly at 0.5 and
  0.6 with total 40.

## Iteration 41 (sessions s48, s49e, 2026-10-26): regime bracket and first protocol on the rewired network
- **Change:** lam 0.4, `gain_ie` 2: `gain_ee_inter` 0.4 / 0.5 x intra total 30 / 40 (Substep 1
  on 100 groups, saturation diagnostic d 4 and 6); protocol at `gain_ee_inter` 0.5 and 0.6 with
  intra total 40, d 4 and 6, 6 pairs (`params/session48*`). s49e: lam 0.5, `gain_ee_inter` 0.3,
  0.4, 0.5 (same jobs) plus the protocol at 0.4, d 4.
- **Result:** intra total 40 removes under-recruitment. Spill rises with `gain_ee_inter`:

  | Network | `gain_ee_inter` | Substep 1 pass | Spill |
  |---|---|---|---|
  | lam 0.4 | 0.4 | 91 | 9 |
  | lam 0.4 | 0.5 | 86 | 14 |
  | lam 0.5 | 0.3 | 97 | 3 |
  | lam 0.5 | 0.4 | 89 | 11 |
  | lam 0.5 | 0.5 | 86 | 14 |

  A saturated path transmits at d 4 from 0.5 upward (4 / 6), and at d 6 only partly at 0.6.
  The untrained network never transmits. **Protocol: 0 / 24 (s48) and 0 / 6 (s49e)**: no
  transfer within 30 C1 rounds (3 ignitions). The pairs have 0 to 5 direct synapses. Learned
  change in the middle of A-B: about 50 to 80 units, against about 10,000 near A and B.
- **Decision:** the chemistry's reach is the limit. At C1 decay 0.03 the plume spreads about 0.6
  cells, so the gate stays closed on the path (s50).

## Iteration 42 (session s50, 5 pods, 2026-10-26): chemical reach on the rewired network
- **Change:** lam 0.4, `gain_ee_inter` 0.6, intra total 40, `gain_ie` 2, d 4 (one variant d 6),
  6 pairs. C1 and C2 decay and gate thresholds varied (thresholds and soft widths together):

  | Variant | C1 / C2 decay | Thresholds / soft widths | Distance |
  |---|---|---|---|
  | d | 0.01 | 1.2 | 4 |
  | f | 0.003 | 1.2 | 4 |
  | g | 0.01 | 0.6 | 4 |
  | h | 0.003 | 0.6 | 4 |
  | i | 0.01 | 1.2 | 6 |

  The five pods of the prepared s49 d, f, g, h and i runs were reused for this; those runs would
  have repeated the failing chemistry. The s49 parameter files are kept unrun.
- **Result:** 0 / 6 in each of d, f, g and h (2 to 3 ignitions each); i (d 6, decay 0.01):
  0 / 6, no transfer within 30 rounds, no ignition. But **the
  C1 gate now opens on the path**:
  - path mean g1 at the end of injection grows over the rounds from 0.05 to 0.97 at the start
    to 0.5 to 1.0 at the end;
  - path activity reaches 0.3 to 0.9;
  - the learned change in the middle of A-B rises from about 60 (s48) to 0.5k to 2k (decay
    0.01) and 10k to 114k (decay 0.003 or threshold 0.6).

  Two near misses in h: pair 0 reached C1-phase transfer 0.62, but it was uncontained, so the
  runaway check stopped it in round 29; pair 4 reached 0.35. The learned change is still
  concentrated around A and B (behind / near A and near / beyond B), and about a third of it on
  the line, and most of it off the line, goes onto **inhibitory** targets. With slow decay the
  gate also opens far from the path (other g1 0.3 to 0.9), which goes with the ignitions.
- **Decision (for the next agent):** (1) restrict *learning*, not only consolidation, to
  synapses onto excitatory neurons. E->I potentiation strengthens the local inhibition the
  path must overcome. It needs a small plasticity option, `learn_ee_only`, analogous to
  `consolidate_ee_only`. (2) Keep the reach of h (decay 0.003, thresholds 0.6) but contain it:
  a lower C1 saturation or release gain, so the plume follows activity, not distance. (3) Faster
  learning (`a_pre` 0.5) once the gate opens on the path. Run (1) to (3) as one-change
  variants at d 4, 6 pairs each, then d 6.

## Iteration 43 (session s51, 16 pods, 2026-10-26): oracle chemistry and decoupled chemistry
- **Review (no session):** the C1 field carries no information about the path. In s50h, C1 along
  A-B at the end of the C1 rounds is flat (5.5 to 6.0 at A, in the middle and at B; reservoir
  mean 2.9, maximum 6.3), and the gate is open at 0.7 to 0.88 in groups far from the path. The
  "near misses" of s50h were network-wide spread (others 0.98 to 1.0). Too-local versus
  box-filling chemistry is the same dilemma as iterations 9/10 and 19/20: with path neurons
  silent, C1 comes from A and B only and spreads the same in every direction, so no threshold
  gives a path. Pairs 1 and 2 ignite in every s48 to s50 variant, independently of the chemistry.
  The diffusion coefficient k had never been varied (0.16 throughout), which ties reach
  (sqrt(k / decay)) to memory (1 / decay).
- **Change (code):**
  - `oracle` (diagnostic, pair-specific, never a protocol result): C1 and C2 held fixed with
    gates fully open within `radius` cells of segment A-B and zero elsewhere. No release,
    diffusion or decay; controls off.
  - Selectivity telemetry (`regions`, `selectivity`, `weight_selectivity`): the middle of the
    path (M: within `sel_radius` 1 of line A-B, 0.25 <= t <= 0.75) against an off-path shell at
    the same distance from A and B (Sh). Compared per excitatory neuron (spikes in the injection
    window), per voxel (C1, C2), per neuron (C1 gate) and per plastic synapse (w_fast, w_perm
    change, by target type), at the end of every injection and after the C1 and C2 phases.
  - C1 / C2 profile at the end of injection as well (`chem_inject_end`).
  - Module checks 40 (three new).
- **Sessions** (`params/session51{a..p}-*.json`): s50h setting (lam 0.4, `gain_ee_inter` 0.6,
  intra total 40, `gain_ie` 2, rule both, a_pre 0.25), d 4, pairs 0 to 5, controls off, one
  variant per pod:
  - oracle: rule both, radius 0.5 / 1.0 / 1.5; rule stdp, radius 1.0; rule pre_c1, radius 1.0;
    rule both, radius 1.0 at d 6;
  - decoupled chemistry: k 0.005, decay 0.001 (reach about 0.56 cells, memory 1000 steps),
    release gain 1, saturation 100 (self-limiting, far above the gate). Thresholds (= soft
    widths) 1, 3 and 10; with training background input pt 0.01 at 3 and 10; rule stdp at 1 and
    3, and at 3 with background input; k 0.02 at threshold 3; slower k 0.0015 / decay 0.0003 at
    threshold 3.
- **Result:** module checks 40 / 40 on CPU and GPU. Jobs about 80 s each, sessions 4 to 10 min.

  | Variant | Pass | Ignite | Gate M / Sh | Spikes M / Sh | w_fast E->E M / Sh |
  |---|---|---|---|---|---|
  | oracle both r 0.5 | 1 (pair 1) | 0 | (Sh 0) | 8.7 | 2e4 |
  | **oracle both r 1.0** | **1** (pair 4) | 1 | 61 | 87 | 4.3e3 |
  | oracle both r 1.5 | 0 | 3 | 2.7 | 3.1 | 8.5 |
  | oracle stdp r 1.0 | 1 (pair 1) | 0 | 61 | 6.3 | 81 |
  | oracle pre_c1 r 1.0 | 0 | 1 | 61 | 88 | 5.0e3 |
  | oracle both r 1.0, d 6 | 0 | 1 | 159 | 112 | 2.5e3 |
  | chemistry, 10 variants | 0 to 1 (pair 1) | 0 to 2 | 0.35 to 1.4 (or both ~0) | 0 to 7.9 | 1.2 to 344 (large ratios only where learning is ~0) |

  - **Even with perfect chemistry the rule rarely associates.** Oracle radius 1: pair 4
    passes (A -> B 0.52 after 20 rounds, contained), pair 0 passes the C1-phase test after 26
    rounds (0.52) but keeps 0.44 after consolidation, pair 2 transfers only uncontained, pair 1
    ignites, pairs 3 and 5 do not transfer in 30 rounds. **Learning is confined to the path
    but too weak:** mean w_fast on E->E synapses in M after 30 rounds is 0.05 to 0.2 (bound 1,
    start 0.05), whereas the saturated path (all at 1) transmits for 6 / 6 pairs at d 4 (s47).
    The soft bound w (1 - w) makes potentiation from the floor 0.05 about 20 times slower than
    at mid-range. A wider tube (1.5) ignites; STDP alone learns nothing where the path is
    silent (path maximum 0.00 in 4 of 6 pairs).
  - **No chemistry variant makes the gate prefer the path** (gate M / Sh 0.35 to 1.4 where it is
    open at all). Path neurons fire no more than off-path ones in most variants (spikes M / Sh
    0 to 4.3 under rule both, below 2 in five of seven), so activity-proportional C1 has little
    to select.
  - **Pair 1 (175 -> 179) passes in several variants** (its earlier ignition is gone with graded
    release), but it transfers almost untrained (oracle r 0.5: after one round, w_fast in M
    0.004), so it is not evidence for the mechanism.
- **Decision:** the plasticity side has to work with perfect chemistry first. Next (s52): oracle
  radius 1.0, d 4, 12 pairs per variant, faster learning: a_pre 0.5 / 1 / 2, `tau_fast` 10,000,
  faster consolidation (kappa), and a weight dependence with additive potentiation under a soft
  upper bound (`weight_dep` "upper"), so learning does not stall at the floor.

## Iteration 44 (session s52, 13 pods, 2026-10-26): learning speed with oracle chemistry
- **Hypothesis (iteration 43):** with perfect chemistry the rule learns too slowly (w_fast on the
  path 0.05 to 0.2 after 30 rounds), mainly because the soft bound w (1 - w) stalls
  potentiation at the floor 0.05.
- **Change (code):** plasticity option `weight_dep` "upper": potentiation times (bound - |w|),
  depression times |w| (no stall at the lower bound); module check (41 in total). Sessions
  `params/session52{a..m}-or-*.json`: oracle radius 1.0, rule both, d 4, **12 pairs** (pair_draw 0
  to 11) per variant: reference (a_pre 0.25); a_pre 0.5, 1, 2; `tau_fast` 10,000; kappa 0.2;
  "upper" with a = a_pre = a_plus = a_minus 0.02, 0.05, 0.1; a_pre 1 with tau 10,000 and kappa
  0.2; "upper" 0.05 with tau 10,000 and kappa 0.2; a_pre 1 and "upper" 0.05 at d 6.
- **Result:** module checks 41 / 41 on CPU and GPU. Sessions 10 to 23 minutes.

  | Variant (d 4 unless noted) | Pass / 12 | Ignite | Lost in consolidation | No transfer | Median C1 rounds |
  |---|---|---|---|---|---|
  | reference (a_pre 0.25) | 5 | 2 | 1 | 4 | 24.5 |
  | **a_pre 0.5** | **6** | 2 | 0 | 3 (+1 uncontained) | 12.5 |
  | **a_pre 1** | **6** | 4 | 1 | 1 | 6.5 |
  | a_pre 2 | 4 | 6 | 1 | 1 | 4 |
  | tau_fast 10,000 | 4 | 4 | 0 | 3 (+1 uncontained) | 21 |
  | kappa 0.2 | 5 | 2 | 1 | 4 | 24.5 |
  | upper 0.02 / 0.05 / 0.1 | 1 / 3 / 3 | 1 / 1 / 2 | 0 / 1 / 3 | 10 / 7 / 4 | 30 / 30 / 25 |
  | a_pre 1, tau 10,000, kappa 0.2 | 5 | 6 | 0 | 1 | 6.5 |
  | upper 0.05, tau 10,000, kappa 0.2 | 4 | 1 | 0 | 7 | 30 |
  | a_pre 1, d 6 | 0 | 4 | 0 | 8 | 30 |
  | upper 0.05, d 6 | 0 | 1 | 0 | 11 | 30 |

  - Two of the 12 pairs are easy: pair 10 passes in round 1 in every variant (it transfers
    almost untrained), pair 1 either ignites in rounds 1 to 3 or passes in round 1. On the
    other ten pairs the best variants pass 4 (a_pre 0.5) and 5 (a_pre 1).
  - **Faster presynaptic learning trades rounds against ignitions:** a_pre 0.25 -> 0.5 -> 1 -> 2
    halves the rounds each step (24.5 -> 12.5 -> 6.5 -> 4) and raises ignitions (2, 2, 4, 6).
    Slower `w_fast` decay adds ignitions; kappa 0.2 changes nothing (the C1 phase is
    bit-identical to the reference on a different pod; consolidation is not the bottleneck).
    The "upper" weight dependence is worse than "mult" at every rate tried.
  - **d 6: 0 / 24 even with perfect chemistry** (s47: the saturated path transmits for 4 / 6
    pairs at d 6, so the limit is what the rule learns in 30 rounds, not what the path can carry).
  - **The path is silent before learning.** In round 1 of joint injection, excitatory neurons in
    the middle of the path fire a median of 0 spikes in the 50 injection steps (maximum 1.4 over
    pairs), in the oracle and in the chemistry runs alike. The concept assumes the opposite
    (`short_circuit_current.png`, step 3: "neurons between them start to fire"). Under the
    oracle, the presynaptic C1 rule bootstraps the path by potentiating outgoing synapses from A
    and B without postsynaptic spikes. With real chemistry, activity-proportional C1 has no
    path activity to mark, which explains iteration 43.
- **Decision:** a_pre 0.5 is the best compromise with perfect chemistry (6 / 12 at d 4, about 12
  rounds); faster learning only moves failures from no transfer to ignition. The common
  limit of both halves is the regime: the neurons between A and B do not fire under joint
  activation. Next (proposed, cost cap nearly reached, about $34.6 of $40): a propagation
  survey without learning (cheap): firing in M under joint injection, against A alone + B alone
  (convergence) and against the off-path shell, over `gain_ee_inter` (0.6 to 1.5), the energy
  shortcut (its stated purpose: let concentrated activity suppress its surroundings), and lam
  (0.4, 0.6); then the chemistry variants of iteration 43 in a regime where the path fires
  under joint injection. Reported to the user.

## Iteration 45 (sessions s53, s54, s55; 30 pods, 2026-10-26): propagation survey without learning
- **User decision:** cost cap raised to $50; run the propagation survey, then the chemistry
  variants in the regime it finds.
- **Question (iteration 44):** in which regime do the neurons between A and B fire under joint
  activation, more than off the path and more than under A or B alone, without spreading?
- **Change (code):** job `prop_survey` (no learning, no chemistry): per pair one round each of
  joint, A-only and B-only injection; spikes per excitatory neuron in M and Sh, A_g of A, B, the
  path groups and all others, runaway; module check. Host summary `assoc_selectivity.py --prop` /
  `--propclass` (per job: good = the path fires, M >= 0.2, with nothing beyond A, B and the path
  in any condition; silent = M < 0.05; explosive = spread or runaway).
- **Survey 1 (s53, 16 pods, 160 jobs, 8 pairs each, d 4):** lam 0.4 / 0.6 x `gain_ee_inter` 0.6,
  0.8, 1.0, 1.2, 1.5 x energy off / three settings (consumption 0.05 or 0.2, recovery 0.01 or
  0.002, spread 0.1, exponent 1 or 2) x `gain_ie` 2 / 4 x training background input 0 / 0.01.
  - **No configuration has a graded regime.** Per job at most one pair (pair 1) is good. In
    six of the eight pairs not a single excitatory neuron outside A and B fires, at any gain up to
    1.5 (pairs 0 and 3: identical spike counts at 0.6 and 1.5). Pairs 1 and 2 propagate, and from
    gain 1.0 spread network-wide. Background input 0.01 lowers the assemblies' own activation
    (A_max 0.3 to 0.6) without making the path fire. Energy changes nothing qualitatively.
  - Substep 1 data on the same network (s48) point to group heterogeneity: groups that spill
    have more excitatory neurons (median 51 to 54 against 47) and 35 % more intra-group synapses
    per neuron, many of them on the reservoir boundary, where rewiring concentrates each
    neuron's synapses on fewer neighbouring groups.
- **Survey 2 (s54, 6 pods, 84 jobs, 12 pairs each, lam 0.4):** `gain_ee_inter` 0.6 to 6 x
  `gain_ie` 2 / 4 / 8 x energy off / on x new option `inter_norm` (AssocEngine.set_gains: each
  excitatory neuron's inter-group excitatory gains scaled by mean in-degree / its in-degree, so
  every neuron's summed inter-group gain is equal; module check, 43 in total).
  - **Still bimodal at every gain:** at 0.6, 2 of 12 pairs good (1 and 8), 9 to 10 silent; from
    1.0 upward no pair is good, 4 to 10 stay silent and the rest explode (at 6: 4 to 5 silent, 7 to
    8 explosive). In-degree normalization and inhibition (up to 8) change only which pairs explode.
  - **Interpretation:** with every grid cell an assembly (shortcut 1 applied to all groups), every
    group is a bistable unit that ignites fully once a few of its neurons fire (by design, for
    Substep 1). Propagation is then a chain of all-or-none group ignitions: it dies within one
    cell or takes over. The graded firing between A and B that the concept needs cannot occur in
    this layout. It needs ordinary reservoir neurons between the assemblies, i.e. sparse
    assemblies (Substep 8, the user's intended setup).
- **Survey 3 (s55, 8 pods, 96 jobs, 12 pairs each, lam 0.4):** sparse layouts (lattice spacing 2,
  random 30 with one free cell between) x `gain_ee_inter` 0.6 to 4 x `gain_ie` 2 / 4 x energy off /
  on x `inter_norm` off / on.
  - **Sparse layouts do not help:** lattice 11 / 12 silent up to gain 3, then explosions (gain 4:
    up to 9 / 12); random layout 6 to 12 silent, the rest explosive; at most one good pair per
    job. Most pairs give identical spike counts at gains 1 and 3: no excitatory neuron outside
    the assemblies is near threshold, whatever the E -> E gain.
- **Survey 4 (s57, the same 8 pods reused, 60 jobs):** layout all / lattice x `gain_ei` 0.05 to 1 x
  `gain_ee_inter` 1 / 2 / 4 x `gain_ie` 1 / 2; new telemetry: spikes per neuron outside A and B,
  excitatory and inhibitory (`exc_out`, `inh_out`).
  - **Feedforward inhibition is what silences the surroundings:** at `gain_ei` 1 only inhibitory
    neurons fire outside A and B (0.09 to 0.15 spikes per neuron, excitatory 0.000), at every
    E -> E gain. `gain_ee_inter` scales only E -> E synapses, which start at the floor 0.05,
    while E -> I keeps its built weight; all earlier surveys held `gain_ei` at 1.
  - **Lowering `gain_ei` lets excitation through, but all-or-none:** e.g. lattice, `gain_ei` 0.2,
    `gain_ie` 1: excitatory spikes outside A and B 0.000 at `gain_ee_inter` 1, 7.0 per neuron at 2
    (9 / 12 explosive). In 60 jobs at most one pair is good.
- **Survey 5 (s58, same pods, 48 jobs):** training background input pt 0.005 to 0.05 (the
  engine's thalamic input, currents up to 15 / 25) x layout all / lattice x `gain_ei` 0.2 / 0.5
  / 1 x `gain_ee_inter` 1 / 2, `gain_ie` 2; new condition `none` (no injection) as baseline,
  counts taken above it.
  - **No fluctuation-driven regime at these levels:** background firing in M is 0.000 to 0.005
    spikes per neuron per round; above pt 0.02 the assemblies' own activation drops (A_max 0.3
    to 0.6). The classes stay silent / explosive, at most 2 good pairs per job.
- **Conclusion (iteration 45):** across about 450 configurations (layout, lam, E -> E, E -> I and
  I -> E gains, in-degree normalization, energy, background input) the reservoir has **no
  regime in which the neurons between A and B fire in a graded, contained way** under joint
  activation. Propagation is all-or-none: below a threshold nothing beyond A and B fires (feedforward
  inhibition clamps the surroundings), above it activity takes over the reservoir; the threshold
  differs between pairs (group heterogeneity, boundary effects in a 7 x 7 x 7 grid where 218 of
  343 groups lie on the surface), so any global setting leaves most pairs on one side.
- **Decision:** the chemistry variants "in the regime the survey finds" are not run: no such
  regime exists in the explored space. Reported to the user with the options (handoff).
  Candidates, most promising first: (1) a genuinely fluctuation-driven, balanced regime
  (background input strong enough that neurons fire irregularly near threshold, with E and I
  scaled together; the engine's thalamic currents are an order of magnitude too weak for it); (2)
  less heterogeneity: a larger grid in which pairs lie away from the surface, or equalized group
  sizes; (3) accept that the path has to be grown by learning (as under the oracle, where the
  presynaptic C1 rule grows potentiation outward from A and B) and look for a chemical selection
  signal that does not need prior path activity.

## Iteration 46 (session s59, 8 pods, 2026-10-26): fluctuation-driven, balanced background
- **User decision:** try a fluctuation-driven, balanced regime (strong background input, E and I
  scaled together), then the propagation survey in it.
- **Change (code):** parameter `bg` (`assoc_protocol.py`): every neuron receives mu + sigma * N(0, 1)
  each step in every phase (E and I separately), and after each reset the network runs `warmup`
  steps without injection; `AssocEngine.add_current_vector`; module check (44 in total). Survey
  `params/session59{a..h}-bg.json`: layout all / lattice x mu 1 / 2.5 / 3.5 x sigma 3 / 6 / 9 / 12 (E
  and I equal) x `gain_ei` 0.5 / 1 x `gain_ee_inter` 1 / 2 with `gain_ie` = 2 x `gain_ee_inter`;
  warm-up 100 steps; 12 pairs, d 4, conditions joint / A / B / none.
- **Result:** module checks 44 / 44 on CPU and GPU. Background firing 0.1 to 1.8 spikes per
  excitatory neuron per 100 steps (about 1 to 18 Hz).
  - **The background ignites boosted groups spontaneously:** without any injection, some group
    outside A, B and the path reaches A_g 0.82 to 1.00 in every one of the 96 configurations
    (median over pairs), so the inactivity threshold (0.1) is violated by background alone, and
    spread relative to that baseline cannot be detected. The "good" counts of `--propclass`
    (up to 7 / 12) are therefore not meaningful here.
  - **Injection into A and B adds nothing measurable on the path:** median joint-minus-baseline
    firing in M is -0.37 to +0.34 spikes per excitatory neuron, with scattered sign (one trial
    per condition); A + B alone likewise. The assemblies' own activation drops (A_max 0.35 to 1.0).
- **Conclusion:** the fluctuation-driven regime does not give graded transmission either. The
  boosted groups (shortcut 1) turn background fluctuations into spontaneous all-or-none
  ignitions, which is incompatible with the task's activity definition (inactive <= 0.1).
- **Decision:** reported to the user. Remaining options: less heterogeneity (larger grid, pairs
  away from the surface), background input on ordinary (non-assembly) neurons only with sparse
  assemblies, or a change of the concept's mechanism (path grown by learning, another selection
  signal).

## Iteration 47 (session s60, 2 pods, 2026-10-26): is there a two-sided input signal for a coincidence-gated release?
- **Question (user: "see if A1 works"):** a release rule driven by coincidence (input from A and
  from B at the same neuron) needs neurons in the middle of the path that receive input from both
  sides, more than neurons off the path or behind A and B. Synaptic input adds linearly, so the
  measure is, per neuron, the input under A alone and under B alone, and min(I_A+, I_B+).
- **Change (code):** job `input_survey` (no learning): per pair, injection into A, B and both for
  `inject_steps`; per neuron the mean net synaptic input per step (engine row 7 right after the
  step, before injection and background; `AssocEngine.input_current`) and the spikes; statistics
  for M, Sh and eight bins of t along the line (`assoc_selectivity.py --input`). Also added
  (default off, module-checked, not yet used): `bridges` (assemblies on the route count as path),
  energy per phase (`energy.in_c1` / `in_c2` / `in_test`), `protocol.accept_uncontained`, energy in
  the selectivity telemetry. Module checks 47 / 47. Grid: layout all / lattice x `gain_ei` 0.2 / 0.5
  / 1 x `gain_ee_inter` 0.6 / 1 / 2 (d 4), two at d 6, and (user remark: the within-group boost of
  shortcut 1 is a free parameter) intra total 10 / 20 with k 24.
- **Result:** **no two-sided signal in any of the 28 configurations.**
  - The net synaptic input to excitatory neurons outside A and B is negative everywhere: under A
    alone, -20 to -43 per step next to A (t -0.25 to 0.25), -2 to -15 at a quarter of the way,
    about -0.1 to -2 at the midpoint, and about 0 beyond it. Inhibition recruited by A dominates
    the excitation it sends, even at `gain_ei` 0.2 (midpoint -1 to -5 under joint injection) and
    with weaker assemblies (intra total 10 / 20).
  - The coincidence signal min(I_A+, I_B+) is 0.00 in the middle of the path, in the shell and in
    every bin of the profile; the M / Sh ratios printed are ratios of numbers near zero and mean
    nothing. No excitatory neuron between A and B spikes (0.00 to 0.04).
  - Reach: the influence of A falls to about zero within half the A-B distance (2 cells at d 4).
    This follows from the wiring: E -> E synapses per group pair fall as exp(-d / 0.4 cells) (d 1:
    1393, d 2: 141, d 3: 17; iteration 40). A neuron 2 cells from A receives a few synapses from
    A, about 0.05 x 4 x 0.6 = 0.12 current units each per spike, against inhibition of order 1.
- **Conclusion:** a coincidence-gated release (A1) has nothing to detect at d 4 in this network:
  single neurons in the middle receive essentially no excitation from either side, only
  inhibition near A and B. More generally, one-step coincidence can only work within the direct
  connection range (about 2 to 3 lam, i.e. d <= about 1 to 1.5 cells here). Beyond it a signal has
  to be relayed, and relaying through ordinary neurons is all-or-none here (iterations 45 and 46).
  Overcoming d 4 therefore needs relays that pass a signal on reliably and specifically. In this
  engine the only units that do that are assemblies (bistable groups), i.e. bridges, which then
  also act as coincidence detectors at group level (an assembly sums input over its ~45 neurons
  and ignites only above a threshold). Reported to the user.

## Iteration 48 (session s61, 9 pods, 2026-10-26): convergence range (A), normalization (B), capture (D)
- **User decisions:** (1) distance is measured relative to the connection range, with direct A <-> B
  synapses frozen as proof of a multi-hop route; (2) synaptic normalization is within "the
  plasticity rule may be revised"; (3) temporal capture triggered by a successful transfer is worth
  a try.
- **Change (code):** plasticity option `norm_factor` (each neuron's summed plastic input weight
  kept at or below factor x its initial sum, by scaling w_fast); `ltp_events` and `capture`
  (move w_fast of synapses that transmitted, pre then post, into w_perm); protocol option
  `capture` (in each C1-phase test, A alone: if B becomes active, C2 released by B is taken to reach
  every synapse, and the synapses that transmitted in that test are made permanent; then a strict
  test; C2 stage off); `input_survey` with excitatory and inhibitory input separately (spikes x
  synaptic current, summed per target). Module checks 50 / 50 on CPU and GPU.
- **Sessions** (12 pairs, d 4 each; oracle and plasticity of s52b, a_pre 0.5, unless noted):
  A: lam 1.0 with `freeze_direct_AB`, chemistry moderate (decay 0.01, threshold 1.2) / decoupled
  (k 0.005, decay 0.001, threshold 3) / oracle; input survey at lam 0.8 / 1.0 / 1.3. B: lam 0.4,
  oracle, `norm_factor` 2 / 4, and 4 with a wide tube (radius 1.5). D: lam 0.4, capture, oracle / real
  long-reach chemistry (s50h).
- **Result:**

  | Variant | Pass / 12 | Ignite | Other failures | Note |
  |---|---|---|---|---|
  | reference s52b (oracle, a_pre 0.5) | 6 (p0, 1, 4, 8, 10, 11) | 2 | 3 none, 1 uncontained | |
  | A lam 1, chemistry moderate, frozen | 0 | 6 | 6 none | direct A <-> B E synapses median 265 (frozen) |
  | A lam 1, chemistry decoupled, frozen | 1 (p1) | 3 | 8 none | |
  | A lam 1, oracle, frozen | 0 | 4 | 8 none | even perfect chemistry fails |
  | B norm 2 | 1 | 0 | 11 none | too restrictive |
  | **B norm 4** | **7** (p0, 1, 4, 6, 8, 10, 11) | **0** | 5 none | ignitions of p7 / p9 removed |
  | B norm 4, wide tube | 0 | 2 | 3 uncontained, 7 none | no route selection |
  | **D capture, oracle** | **7** (same pairs as B norm 4) | **0** | 1 lost, 1 uncontained, 3 none | median 12.5 rounds |
  | D capture, real long-reach chemistry | 0 | 0 | **10 / 12 transfer in the C1 phase**; then 6 uncontained, 4 lost | capture makes the spread permanent |

  - **Input survey, excitation and inhibition separately (lam 0.8 to 1.3):** excitation reaching
    neurons outside A and B is tiny (0.1 to 0.35 per step, next to A as in the middle), inhibition
    is 30 to 100 times larger (-5 to -23). A geometric two-sided excitation exists: min(E_A, E_B)
    peaks in the middle of the line (0.05 to 0.10) and is 2.3 to 3.9 times higher in M than in Sh.
    But the summed excitation, which is all a neuron can sense, is about as high next to A (one
    side, 0.3) as in the middle (two sides, 0.3), so a release driven by excitatory input would
    not prefer the path either.
- **Interpretation:**
  - Normalization (B) and capture (D) each improve the plasticity side a little under the oracle:
    one more pair and no ignitions (B), or the same with fewer rounds and no C2 stage (D). Neither
    selects a route by itself (B with a wide tube 0 / 12; D with broad real chemistry: transfers
    form, but whatever spread is made permanent too).
  - At lam 1 with direct synapses frozen, even the oracle fails: the multi-hop route through
    intermediate neurons does not form there.
  - The untrained network is strongly inhibition-dominated (excitation at the plasticity floor,
    E -> I and I -> E at built weights times gains); this is a consequence of our settings
    (iterations 15 and 11 to 16), not of the concept.
- **Decision:** reported to the user. Remaining budget about $3.8 of $50 (s61 about $3.3,
  estimated). The only combination not yet tried is capture with normalization and real chemistry
  (D + B): capture produced transfers in 10 / 12 pairs, and normalization removed ignitions under
  the oracle.

## Iteration 49 (session s62, 2 pods, 2026-10-26): capture plus normalization with real chemistry
- **User decision:** run capture plus normalization with the real long-reach chemistry, 12 pairs.
  Cost cap raised to $60.
- **Change:** `params/session62{a,b}-D-chlong-norm{4,2}.json`: s61h (capture, s50h long-reach
  chemistry, lam 0.4, a_pre 0.5) with `norm_factor` 4 and 2.
- **Result:**

  | Variant | Pass | Transfers captured | Final |
  |---|---|---|---|
  | s61h, capture, no normalization | 0 | 10 / 12 | 6 uncontained, 4 lost |
  | capture, `norm_factor` 4 | 0 | 4 / 12 | 2 uncontained (the easy pairs 1 and 8), 2 lost, 8 no transfer |
  | capture, `norm_factor` 2 | 0 | 0 / 12 | 12 no transfer |

- **Interpretation:** normalization does not make the transfers of the broad real chemistry
  contained; it suppresses the broad learning that produced them. With normalization, the pairs
  that still transfer are the easy ones, and they still spread. The combination does not select a
  route.
- **Decision:** reported to the user; handoff rewritten for a new agent.

## Iteration 50 (session s63, 10 pods, 2026-10-26): rebalancing excitation and inhibition
- **User decision:** open direction 1 of the handoff: inter-group E -> E start weight above the
  floor and E -> I / I -> E lowered, measured with `input_survey` and `prop_survey` in one session;
  the protocol only if a regime turns up.
- **Hypothesis (iteration 48, item 4 of the handoff):** the path is silent because our settings
  make the untrained network inhibition-dominated (inter-group E -> E at the floor 0.05, E -> I and
  I -> E at built weights 0.45 / -0.44 times gains). With E -> E raised and the inhibitory loop
  lowered, the middle of the route should receive net excitation from both sides without igniting.
- **Review before the session:** s57 (iteration 45, survey 4) already covered most of this space
  in current terms (`gain_ei` 0.05 to 1, `gain_ie` 1 / 2, inter-group E -> E current 0.2 / 0.4 / 0.8
  per spike, layouts all / lattice): silent or explosive everywhere, at most one good pair per job.
  s63 therefore covers only what was new: (A) the inhibitory loop co-scaled with E -> E, and (B) a
  fine grid across the silent / explosive transition, including `gain_ie` below 1.
- **Change (parameters only):** `params/session63{a..j}-ei.json`, s57 setting (lam 0.4, gain 4,
  intra total 40, k 12, I 20, d 4, 12 pairs), layouts all / lattice spacing 2, `gain_ee_inter` 1,
  inter-group start weight `weights.w_ee` varied:
  - A (co-scaled): w_ee 0.05 / 0.075 / 0.1 / 0.15 / 0.2 / 0.3 x r 0.25 / 0.5 / 1, with
    `gain_ei` = r * w_ee / 0.05 and `gain_ie` = 2 x that (r 1 at w_ee 0.05 is the current regime);
  - B (fine): w_ee 0.06 / 0.07 / 0.08 / 0.09 x (`gain_ei`, `gain_ie`) (0.2, 0.5) / (0.2, 1) /
    (0.1, 0.25).
  60 configurations, each as a `prop_survey` and an `input_survey` job (120 jobs).
- **Result:** sessions 49 to 80 s on RTX 4090, no errors. Classes as in `assoc_selectivity.py
  --propclass`; E / Inh = excitatory / inhibitory synaptic input per step to excitatory neurons in
  M under joint injection (medians over pairs).

  | Region of the grid | Classes (12 pairs per job) | E / abs(Inh) in M | E in Sh / E in M |
  |---|---|---|---|
  | A, all 36 configurations | 0 to 1 good (pairs 10, 0); otherwise silent or explosive | 0.005 to 0.19 | 0.55 to 0.8 |
  | B, `gain_ie` 1 (8) | 0 good; 6 to 11 silent | 0.13 to 0.32 | 0.6 to 0.85 |
  | B, (0.2, 0.5), w_ee 0.06 / 0.07 | 0 good; silent / explosive: all 7 / 5 at both; lattice 9 / 3 and 5 / 7 | 0.3 to 0.8 | 0.7 to 1.2 |
  | B, (0.2, 0.5), w_ee 0.08 / 0.09 | 0 good; 10 to 11 explosive | 1.9 to 2.7 | 0.75 to 0.9 |
  | B, (0.1, 0.25), every w_ee | 0 good; 12 / 12 explosive | 4.8 to 8.6 | 0.9 to 1.0 |

  - **No graded regime:** 4 good pair-configurations out of 720, three of them the easy pair 10,
    all in A on the lattice layout.
  - **Net excitation in the middle of the route comes only together with the same excitation off
    the path:** wherever E exceeds abs(Inh) in M, the off-path shell at the same distance from A and
    B receives 75 to 100 % of it, and 10 to 12 of 12 pairs ignite the reservoir.
  - **The transition is a jump, not a slope:** lattice, (0.2, 0.5): net input in M -0.19 at
    w_ee 0.07 (5 silent, 7 explosive, none in between), +47 at 0.08. A 14 % step in the start weight
    moves the median pair from silent to explosive.
  - **Co-scaling (A) only deepens the inhibition:** scaling both E -> I and I -> E by the same factor
    makes the inhibitory loop grow with its square, so E / abs(Inh) falls as w_ee rises (0.19 ->
    0.05 at r 0.25). This was a design slip (each gain should have scaled with the square root),
    but B spans the region where E / abs(Inh) crosses 1 at fixed inhibition and shows the same
    silent / explosive split there, so a square-root line would cross the same transition.
- **Conclusion:** rebalancing excitation and inhibition does not produce graded, route-specific
  firing. Under joint injection the neurons between A and B either stay below threshold or ignite
  the whole reservoir together with everything off the path. This is the bistability of
  iterations 10 and 45 reached from the E / I side, not a consequence of the particular gains.
- **Decision:** no regime found, so the protocol is not run (user's condition). Reported to the user.

## Iteration 51 (session s64, 4 pods, 2026-10-26): bridge threshold diagnostic
- **User decision:** open direction 2 (bridges); start with the threshold diagnostic: does a bridge
  assembly on the route ignite under input from A and B together but not from one alone?
- **Hypothesis:** a bridge assembly sums input over its ~45 neurons and ignites only above a
  threshold (iteration 47), so it can act as a coincidence detector (AND): with a joint input about
  twice the single one, some range of inter-group coupling should ignite the bridge under joint
  injection only.
- **Change (code):** `prop_survey` records the bridges of each pair (assemblies among the path
  groups, with `bridges: true`) and their maximum A_g per condition (`bridge_max`); module check
  `bridge_activity_per_condition` (51 in total); host summary `assoc_selectivity.py --bridge`
  (classes AND / weak AND / one-sided / silent / spread).
- **Sessions** (`params/session64{a..f}-bridge.json`): lattice spacing 2 with `bridges`, d 4 (pairs
  along an axis, exactly one bridge in the middle, 2 cells from A and from B), 12 pairs, conditions
  joint / A / B / none; lam 0.4 / 0.6 x intra total 20 / 40 / 80 x (`gain_ei`, `gain_ie`) (1, 2) /
  (0.5, 1) x inter-group start weight `w_ee` 0.05 / 0.075 / 0.1 / 0.15 / 0.2 / 0.3 / 0.47
  (`gain_ee_inter` 1, gain 4); 84 jobs. RTX 4090 out of capacity, so L4 (same SM 89 build, $0.59/h):
  4 pods, sessions c and f chained behind a and d.
- **Result:** module checks 51 / 51 on CPU and GPU.
  - **No usable AND:** of 1008 pair-configurations, 5 show the bridge active under joint injection
    and inactive (<= 0.1) under both single ones; none is contained (in four, a single injection
    already activates a group outside the route; in one, joint injection spreads). Two more are
    weak AND.
  - **Each pair goes from silent to one-sided in one step:** traced over w_ee with the pairs fixed
    (same 12 pairs per lam), the bridge stays silent under joint injection up to some w_ee and
    ignites from A or B alone at the next grid value (steps of x 1.33 to x 1.5). In five series,
    3 of 55 pair series pass through an AND point on the way. The AND window is therefore narrower
    than x 1.33 to x 1.5 in the coupling, although joint input is about x 2 the single input.
  - **The threshold varies between pairs** by up to a factor of about 2.4 in w_ee (0.2 to 0.47 at
    lam 0.4, intra 80, (1, 2)); one pair (46 -> 42, bridge 44) ignites the bridge from one side at
    every w_ee, even at the floor.
  - Stronger inhibition ((1, 2) against (0.5, 1)) and lam 0.6 shift the thresholds to larger w_ee
    (lam 0.6: fewer synapses between neighbouring cells); the intra total shifts them without a
    consistent direction. None of them widens the window.
- **Interpretation:** a bridge is not a usable coincidence detector here. Its drive does not scale
  linearly with the number of active sources: the relay through the ordinary neurons between A and
  the bridge is itself all-or-none, so once one source gets through, the bridge receives nearly
  everything it would from two. Even if the window were wider, its position varies between pairs by
  more than its width, so no global setting would place most pairs inside it.
- **Decision:** reported to the user. Not run: a finer w_ee grid (it could measure the window
  width per pair, but cannot remove the spread between pairs) and two-bridge chains at d 6.

## Iteration 52 (session s65, 5 pods, 2026-10-26): background input on ordinary neurons only (A1)
- **User decision:** follow the agent's recommendation: A1 first (background on ordinary neurons
  only, sparse assemblies), then a design discussion of grow-and-prune (B1) with homeostatic
  pre-tuning (A3).
- **Hypothesis:** iteration 46 failed because the fluctuating background ignited the boosted
  assemblies. Given only to ordinary neurons, it can hold the neurons between A and B near
  threshold, firing irregularly, so that they respond in a graded way to input from A and B
  (obstacle 1: all-or-none relay).
- **Change (code):** `bg.targets` "ordinary" (`AssocRun`: mu and sigma zero on assembly neurons;
  default "all", unchanged); `prop_survey` records `off_asm_max` (maximum A_g of the assemblies
  off the route), so spread is judged on assemblies, not on ordinary groups firing on background
  input. Module checks extended (51 in total). Analysis script in the agent's scratchpad (not in the
  repository); its method is described below.
- **Sessions** (`params/session65{a..h}-bgord.json`): layouts lattice spacing 2 and random (30
  assemblies, at least one free cell between), `bridges` true, d 4, 12 pairs, intra total 40, lam
  0.4; bg on ordinary neurons, mu 1 / 2.5 / 3.5 x sigma 3 / 6 / 9 (E and I equal), warm-up 100 x
  (`gain_ei`, `gain_ie`) (1, 2) / (0.5, 1) x `w_ee` 0.05 / 0.1 / 0.2; each as `prop_survey` and
  `input_survey` (216 jobs). 5 RTX 4090 pods (L4 and further 4090 out of capacity), sessions f, g
  and h chained.
- **Result:** module checks 51 / 51 on CPU and GPU.
  - **Ordinary neurons fire on the background:** in the middle of the route 0.1 to 6 spikes per
    excitatory neuron per round without injection.
  - **Assemblies still ignite spontaneously:** in the round without injection, some off-route
    assembly reaches A_g 1.0 in at least 3 of 12 pairs in every one of the 108 configurations, and in
    all 12 pairs in most of them. Background given only to ordinary neurons reaches the assemblies
    through their synaptic input and ignites them, as in iteration 46. The task's inactivity
    criterion (<= 0.1) fails without any injection, and spread relative to that baseline cannot be
    detected (the baseline is already at 1.0): "contained" below means only that no rise above the
    baseline was detectable.
  - **Spread at w_ee 0.2 with (0.5, 1):** in 16 of 18 configurations all 12 pairs show a rise of an
    off-route assembly above its baseline (6 and 10 of 12 in the other two).
  - **Joint injection adds nothing measurable on the route.** Each condition is a single trial, so
    the effect per pair, m = spikes in M (joint) minus spikes in M (none), is the difference of two
    noisy samples; counting pairs with m >= 0.2 (as `--propclass` does) gives 0 to 8 "graded"
    pairs per job but is noise, since the median m is -0.78 to +1.19 and as many pairs fall below
    zero. Tested across pairs instead (mean m over the contained pairs against its standard error):
    in 91 configurations with at least 4 contained pairs, t(m) > 2 in 2 and t(m) < -2 in 2, which is
    what chance gives. One configuration exceeds t 3 (random layout, mu 3.5, sigma 9, (0.5, 1),
    w_ee 0.05: mean m 0.44, t 3.7; route against shell t 2.5; not supra-additive, t 0.7), which is
    about what 91 tests give by chance (expected 0.6 above t 3 at 10 degrees of freedom).
  - **No selectivity in the input either:** the excitatory input under joint injection is about as
    large off the path as on it (E_Sh / E_M 0.66 to 2.3, median about 1.1).
- **Interpretation:** A1 fails twice. (1) The boosted assemblies ignite on the background even when
  only ordinary neurons receive it, so the network cannot hold assemblies inactive. (2) The
  influence of A and B on the route is far smaller than the background fluctuations: the excitation
  reaching the middle of the route from both assemblies without background (iterations 47 and 48:
  about 0.1 to 0.35 per step) is lost among the synaptic input the background produces there
  (excitatory input under joint injection 0.5 to 90 per step across configurations, 0.5 to 5 at
  w_ee 0.05; inhibitory 7 to 150). The
  limit is not the operating point of the neurons between A and B: at d 4 and lam 0.4 too few
  synapses connect A and B to the middle of the route for any operating point to carry their signal.
- **Decision:** reported to the user. Not followed up: a replication of the one configuration with
  t > 3 using repeated trials per condition (cheap, but most likely chance). Next per the user's
  decision: design discussion of B1 with A3, no session.

## Iteration 53 (no session yet, 2026-10-26): pass criterion revised; s61h reread
- **User decision:** a few stray groups active in the test are acceptable, whole-network
  activation is not; control 2 (C <= 0.1) is dropped as a pass condition. New criterion: A -> B (or
  the reverse) >= 0.5 in the strict final test, no runaway, at most 10 % of all groups (34 of 343)
  active outside A, B and the route, controls 0 and 1. The previous `contained` check (every group
  outside A, B and the route <= 0.1) was the agent's own definition (iteration 18), not a task
  requirement.
- **Reread of s61h (capture, real long-reach chemistry, iteration 48) under it:** the strict final
  test gives A -> B >= 0.5 in 10 of 12 pairs, C 0.0 in all, control 0 passing, no runaway; all 10
  were rejected only by `contained`. The test does not record how many groups were active; from
  the spike counts (A alone before training: 250 to 520 spikes per 100-step test) pairs 0, 4, 10
  and 11 (2,600 to 5,300 spikes) look like A, B, part of the route and a few strays; pair 6 (12,000)
  broader; pairs 2, 7 and 9 (57,000 to 68,000) close to whole-network; pairs 1 and 8 are the easy
  pairs. Estimate only: control 1 was off, one seed.
- **Found in the code:** under `protocol.capture`, control 1 cannot fail. `control_run` uses
  `protocol_body_fixed_rounds`, which never captures, so w_perm stays at its initial values and the
  strict final test cannot show an association. Earlier capture runs had controls off, so no result
  is affected, but the recheck needs a capture-aware control.
- **Decision:** recheck the s61h setting under the new criterion (plan reported to the user).

### Iteration 53, continued (session s66, 5 pods, 2026-10-26): the recheck
- **Change (code):** `test()` records the groups active (A_g >= active) outside A, B and the path,
  C included (`n_active_outside`, `active_outside`, `n_above_inactive_outside`) and `bounded`;
  `protocol.criterion` "bounded" (new default) or "contained" (the earlier check, for reproducing
  old runs), `protocol.max_active_frac` 0.1; substep4 checks: association = a direction with B
  active and the test bounded, controls 0 and 1, C and containment as `telemetry_checks`;
  control 1 under capture runs the capture loop (`protocol_body`) for at most the main run's
  rounds; the C1-phase early stop uses the criterion. Module checks
  `bounded_criterion_counts_active_groups` and `capture_control_runs_capture_loop` (53 in total).
- **Sessions** (`params/session66{a..f}-recheck.json`): exactly s61h (all groups assemblies, lam 0.4,
  d 4, capture, long-reach chemistry, a_pre 0.5, at most 30 C1 rounds) with controls on, criterion
  bounded; 12 pairs x seeds 0 and 1 (seed 1: network and rewiring seed 1, so other pairs).
- **Result:** module checks 53 / 53 on CPU and GPU. Strays = groups active outside A, B and the path
  in the final strict test (limit 34).

  | | Seed 0 | Seed 1 |
  |---|---|---|
  | No transfer | 2 (pairs 3, 5) | 5 (pairs 0, 1, 3, 5, 10) |
  | Transfer, not bounded (> 34 strays) | 3 (pairs 2, 7, 9: 86 to 188) | 6 (pairs 2, 4, 6, 7, 9, 11: 62 to 259) |
  | Bounded association | 7 (pairs 0, 1, 4, 6, 8, 10, 11: 3 to 16 strays) | 1 (pair 8: 33 strays) |
  | Gating-off control also bounded association | 6 of those 7 | pair 9 (main run not bounded) |
  | Pass (association and controls 0, 1) | 1 (pair 6, B -> A only, 16 strays) | 1 (pair 8, 33 strays) |

  - Control 0 passes in all 24 pairs, the chemistry-off control never produces a transfer, and C is
    0.0 in 23 of 24 final tests. Direct A <-> B excitatory synapses: 0 to 7 per pair (multi-hop).
  - The gating-off control (gates open everywhere, so learning happens wherever there is activity)
    reproduces the bounded association in 6 of the 7 seed-0 pairs, with similar rounds (1 to 14
    against 2 to 15) and similar strays (4 to 15 against 3 to 14).
  - Seed dependence: seed 0 gives 7 bounded associations, seed 1 one.
- **Interpretation:** under the user's criterion, associations with a few strays form in a third of
  the pairs at d 4 (8 of 24), over multi-hop routes. They do not depend on the chemistry: the growth
  rule plus capture on successful transfer forms the same associations when the C1 gate is open
  everywhere. The chemistry is needed only as an on switch (no chemistry, no learning), not as a
  route selector. The two passes are passes only because their gating-off controls happened to
  spread or not transfer; they are not evidence that the gate selects the route. This is the second
  outcome foreseen in the plan: the open problem is the chemical route selection.
- **Cost:** pods a, b, c and f idled 5 to 13 minutes after their sessions were downloaded, because they
  were deleted only after the last session (d, chained behind e) finished; delete each pod as soon as
  its last session is downloaded.
- **Decision:** reported to the user.

## Iteration 54 (session s67, 3 pods, 2026-10-26): C1 skipped; C2 short circuit stage with energy, stage 1
- **User decisions:** (1) provisional: C1 may be skipped in the minimal version. The user's intuition is
  that C1 privileges assemblies tied to the short-term memory against the dream state's random
  activations, which the minimal version (current injection into A and B only) does not have. Recorded
  as provisional; the task file and the README reconstruction are unchanged. (2) C2 is released by
  every active neuron in proportion to its activity during the short circuit state (A, B and the route
  active), not by B alone (the agent's B1 idea of C2 released by B was a departure from the concept and
  is dropped). (3) Energy (shortcut 2) is to focus the short circuit on the real route; its stated
  purpose is the hardening under C2.
- **Protocol (no new mechanism):** C1 gate open everywhere and no C1 release; joint rounds with learning
  wherever there is activity, temporary (w_fast); once A alone activates B (spread accepted:
  `accept_uncontained`), the short circuit stage: A and B jointly injected for 5 to 10 rounds, C2
  released by every neuron in proportion to its spikes, w_fast moved into w_perm where C2 is above
  threshold (`learn_in_c2` false), energy on in that stage only (`energy.in_c2`); final strict test on
  w_perm with energy off, bounded criterion. No capture.
- **Sessions** (`params/session67{a..l}-c2e.json`): s61h network (lam 0.4, all groups assemblies, d 4,
  a_pre 0.5), seed 0, 12 pairs, controls off; C2 reach long (k 0.16, decay 0.003) / short (k 0.02, decay
  0.01), release gain 20, saturation 8; C2 threshold (= softness) 1 / 4; energy off (E0), consume 0.02
  (E1), consume 0.05 with spread k 0.1 (E2), and E2 with exponent 2 (E3), recovery 0.01. 192 jobs. RTX
  4090 at first out of capacity, L4 too; one RTX PRO 4500 Blackwell pod never left startup (5 minutes,
  terminated); then 3 RTX 4090 pods, two session chains each, session h moved to the first free pod.
- **Result** (all 12 pairs; session g, pair 6, was fetched from the volume with the s68 pods after its
  own pod had been terminated):
  - **Associations within the limit in 4 to 6 of 12 pairs** in every configuration (threshold 1: pairs
    0, 1, 8, 10, 11, plus 6 in six of the eight configurations; threshold 4: 0, 1, 4, 8, 11 or 1, 4, 8,
    11), with median 6 to 13 strays; 10 of
    12 transfer in the C1 phase, 1 to 2 are lost in consolidation, 3 to 4 end with more than 34 strays.
    About the same as growth plus capture with the gate open (iteration 53: 7 of 12 in seed 0).
  - **Energy changes nothing measurable:** E0 to E3 give the same pairs and strays within one or two
    groups. Energy was barely depleted: at the end of the injection in the last short-circuit round
    the local energy is 0.97 to 0.99 of baseline on the route and in the shell (pair 0). Route neurons
    fire about 0.6 spikes per 50-step injection (0.012 per step), so consumption 0.02 to 0.05 per spike
    against recovery 0.01 settles a few percent below baseline. The agent sized the settings for
    about 0.1 spikes per step; the test is inconclusive, not negative.
  - **C2 barely favours the route:** C2 route / shell 1.16 to 1.20 (long reach) and 1.26 to 1.37 (short),
    although route neurons fire about 1.9 to 2.1 times as much as the shell (medians over pairs; pair 0:
    2.4). Release gain 20 against
    saturation 8 drives C2 to near its ceiling wherever there is any activity (pair 0: 4.7 on the route,
    4.0 in the shell), so the threshold cannot separate them.
- **Interpretation:** stage 1 did not test what it was meant to test: energy was too weak to act, and the
  saturating C2 release flattens the difference in activity that energy is supposed to create. Both
  are parameter ranges, not the mechanism.
- **Process slip:** pod B was terminated after its collector exited with session g still pending (g had
  all 16 jobs done but no session marker yet); check the collector's PENDING line before deleting.
- **Decision:** reported to the user with a proposed stage 1b (energy strong enough to deplete, C2
  release proportional rather than saturating) before stage 2.

## Iteration 55 (session s68, 5 pods, 2026-10-26): stage 1b, depleting energy and proportional C2
- **User decision:** run stage 1b.
- **Change:** code from iteration 54's stage-2 preparation uploaded (`inject_mode`, `control_modes`,
  control "separate"; module checks 54 / 54 on CPU and GPU), not used in this session. Parameters
  (`params/session68{a..j}-c2e1b.json`): as stage 1 with C2 release gain 1 without saturation, short
  reach (k 0.02, decay 0.01), C2 threshold (= softness) 0.3 / 0.6 / 1.2; energy off (E0) or consumption
  0.3 (E4) / 0.6 (E5) per spike, recovery 0.01, spread 0.1, exponent 1, in the short circuit stage
  only. Pairs 0, 1, 2, 4, 6 to 11 (3 and 5 never transfer, so their short circuit stage never runs),
  90 jobs, 5 RTX 4090 pods with two sessions each, sessions about 3 to 18 minutes. s67g fetched.
- **Result:**
  - **Energy depletes now, and it defocuses:** median local energy at the end of the injection in the
    last short-circuit round 0.56 to 0.66 of baseline on the route and 0.67 to 0.78 in the off-path
    shell. The route fires more, so it loses more excitability than its surroundings; the firing
    ratio route / shell stays at 1.80 to 2.00 (energy off: 1.94 to 2.02), and C2 route / shell does not
    rise either (1.40 to 1.48 with and without energy). As implemented (local consumption, recovery,
    weak spread), energy is fatigue: it penalises the most active region, which is the route.
  - **Proportional C2:** C2 route / shell 1.40 to 1.48 (saturating release, iteration 54: 1.16 to 1.37),
    below the activity contrast itself (about 2), presumably flattened by diffusion (not measured).
  - **Outcome unchanged:** associations within the limit in 3 to 6 of the 10 pairs in every
    configuration (median 5 to 17 strays), 1 to 4 lost in consolidation, 3 to 4 above 34 strays. The
    associations that form are the ones the joint rounds produced; the short circuit stage keeps or
    loses them, but neither C2 selectivity nor energy decides which.
- **Interpretation:** in this network neither proportional C2 nor energy as local fatigue focuses the
  short circuit on the route. For energy to suppress the surroundings of a short circuit, as the
  concept describes, it would have to be competitive (the active route drawing energy away from its
  neighbours faster than it depletes itself, or an excitability that cuts weakly driven neurons off
  while strongly driven ones keep firing); with the present form and range it does the opposite.
- **Cost:** about $1.2 (5 pods, 12 to 23 minutes each).
- **Decision:** reported to the user; stage 2 (controls, 2 seeds) not started, since its premise
  (an energy setting that focuses) did not hold.

## Iteration 56 (session s69, 2026-10-26): stage 2, the joint-activation test
- **User decision:** cost cap raised to $90; "continue as you see fit".
- **Setting** (`params/session69{a..f}-stage2.json`): s68 prop-t0.6-E0, i.e. C1 skipped (gate open, no
  C1 release), joint rounds with learning wherever there is activity, short circuit stage with C2
  released in proportion to spikes (gain 1, no saturation, k 0.02, decay 0.01), consolidation gated by
  C2 from 0 at 0.6 to full at 1.2, no energy; lam 0.4, all groups assemblies, d 4, a_pre 0.5; criterion
  bounded. 12 pairs x seeds 0 and 1, controls on with `control_modes` ["no_chemistry", "separate"]: control 1
  without C2 (nothing can become permanent) and the joint-activation control (A and B injected in
  alternating rounds, never together, same number of rounds).
- **Result:**

  | | Seed 0 | Seed 1 |
  |---|---|---|
  | Association within the limit | 5 (pairs 0, 1, 8, 10, 11; 3 to 15 strays) | 1 (pair 9; 5 strays) |
  | Joint-activation control fails | 1 (pair 6, whose main run is not bounded) | 1 (pair 7, the same) |
  | Control 0 / control 1 (no C2) fail | 0 / 0 | 0 / 0 |
  | **Pass** (association and controls 0, 1, joint activation) | **5** | **1** |

  - **The associations are associative:** in every pair that associates, training A and B in
    alternating rounds forms no association. The two failures of the joint-activation control are in
    pairs whose joint training spread beyond the limit (no association), where one-sided training
    happened to transfer.
  - Otherwise as before: 5 / 3 / 4 pairs (seed 0) and 1 / 6 / 5 (seed 1) associate / transfer beyond
    the limit / end without association (seed 0: pairs 2 and 4 transferred in the C1 phase and were
    lost in consolidation, 3 and 5 never transfer); C1 rounds 1 to 16 in the passing pairs; direct
    A <-> B synapses 0 to 7.
  - Control 1 without C2 cannot fail by construction (no C2, no consolidation); it is recorded only.
- **Interpretation:** under the user's criterion and provisional decisions (C1 skipped, C2 released by
  every active neuron), the minimal version passes in 6 of 24 pairs at d 4 over multi-hop routes, with
  all controls, and the associations depend on joint activation. Remaining gaps: the pass rate (25 %),
  the seed dependence (seed 1: 1 of 12), the 9 of 24 transfers that spread beyond the limit, and d 6.
- **Cost:** included in iteration 57.

## Iteration 57 (session s70, 2026-10-26): shared-pool energy
- **Hypothesis:** energy as local fatigue fails because the route pays for its own activity
  (iteration 55); with maximum spread (k 0.16) and slow recovery (0.002), the route drains a pool it
  shares with its surroundings, so weakly driven neurons nearby should drop out.
- **Setting** (`params/session70{a..e}-pool.json`): s68 prop-t0.6 with energy in the short circuit stage,
  consumption 0.1 / 0.2 x exponent 1 / 2, plus energy off; 10 pairs, seed 0.
- **Result:** the outcome is identical to energy off in every setting (associations in pairs 0, 1, 8, 10,
  11; median 5 to 6 strays). The route still ends up more depleted than the shell (median 0.69 to 0.84
  against 0.80 to 0.90), and the firing ratio route / shell stays at 2.0 to 2.1.
- **Interpretation:** energy that each region pays for itself cannot focus, however far it spreads.
- **Cost (s69 and s70):** 5 RTX 4090 pods, 16 to 36 minutes each (the last one also ran the module
  checks of iteration 58), about $1.8.

## Iteration 58 (no session, 2026-10-26): C3 fuel prepared
- **User proposal:** energy depletion is global, and usage increases local availability; possibly a
  third chemical, C3, a fuel.
- **Change (code, module-checked, not yet run in a session):** `assoc_fields.FuelField`: per voxel a
  trace of recent spikes (tau); a fixed total supply per step, delivered in proportion to
  (trace + floor) ** beta normalized to mean 1; consumption per spike; decay toward 0 and diffusion
  (k); resting level c_ref = supply / decay; excitability = min(C3 / c_ref, cap), scaling each neuron's
  synaptic input as before. Selected with `energy.mode` "fuel" (parameters supply, decay, consume,
  tau, floor, beta, cap, k). Global depletion emerges because the total supply is fixed while
  consumption grows with total activity; concentrated activity draws the supply to itself. Module
  checks `fuel_rests_at_reference_with_fixed_total_supply`,
  `fuel_delivered_where_used_and_depleted_globally`, `fuel_mode_selected_by_energy_params` (57 / 57 on
  CPU and GPU, run on the last s69 pod; the volume then held the repository's pod-side code).
- **Decision:** the C3 sweep is the next step (handoff); prepared, not run.

## Iteration 59 (session s71, 14 + 3 pods, 2026-10-27): C3 fuel, slower growth, distance 6
- **Reanalysis of s69 (host, no session):** the short circuit stage keeps or loses the C1-phase transfer
  but never narrows it: strays at the last C1-phase test against the final test 7 -> 6, 72 -> 84,
  126 -> 122, 199 -> 195, 89 -> 85; lost transfers 179 -> 0, 198 -> 0. The outcome is fixed at the first
  transfer in the joint rounds, which is either contained (3 to 15 strays) or an ignition (60 to 200).
  Strays lie 2 to 3.7 cells (median) from A and B, not next to them; pair geometry (surface, direct
  synapses) does not predict the outcome. Three of the six s69 passes are the easy pairs (seed 0: 1, 8, 10).
- **User decision:** run step 1 as proposed, including C3 in the joint rounds.
- **Change:** `assoc_sweep_summary.py`: seed-aware job names, C1 rounds, C3 / energy route-shell ratios
  (`E1` last joint round, `E2` last short-circuit round), `filt` and `-v` (C1-phase strays -> final, per
  pair). No pod-side code change.
- **Fuel sizing (agent's choice, deviating from the handoff grid):** route neurons fire about 0.016 spikes
  per step, A and B about 30 times more, so with beta 2 A and B were expected to take nearly all the supply,
  and supply = decay = 0.01 (time constant 100 steps) is slower than the 50-step injection. Grid: supply =
  decay 0.01 (handoff) or 0.04, consume 0.5 / 1 / 2, beta 1 (one beta-2 anchor). The beta-2 run did not
  starve the route (E2 M / Sh 1.17), so that prediction was too pessimistic.
- **Sessions** (`params/session71-*.json`): s69 setting with controls off, all 24 d4 pairs (seeds 0, 1):
  E0 (energy off), F2 (C3 in the short circuit stage only: r1c0.5b1, r1c1b1, r1c1b2, r4c0.5b1, r4c1b1,
  r4c2b1; only for the 17 pairs that transfer in s69), F12 (C3 in the joint rounds and the stage: r1c1b1,
  r4c0.5b1, r4c1b1), slow (a_pre 0.25, up to 45 rounds); d6: E0, 24 pairs. 246 jobs, about 41 s each with
  two sessions per RTX 4090. Six sessions crashed at start (two sessions starting together on a fresh pod
  race on VisPy's `stent.npz` download into `/root/.vispy`); rerun on 3 pods after prefetching the file.
- **Result** (associations = bounded associations in the final test; controls off):

  | Config | Associations (of 24) | Lost | Unbounded | Median strays, first transfer | Pairs that differ from E0 |
  |---|---|---|---|---|---|
  | E0 | 6 | 2 | 9 | 76 | (s69's six exactly) |
  | F2 (6 settings, 17 pairs) | 5 to 7 | 1 to 2 | 9 to 10 | 72 to 76 | +s1p2 (199 -> 9 or 10 strays) in 2 settings; -s1p9 in 3 |
  | F12 (3 settings) | 6 | 2 to 3 | 9 to 10 | 53 to 64 | +s0p4 or s0p6, -s1p9 |
  | slow | 5 | 2 | 10 | 58 | +s0p6, -s0p0, -s1p9; C1 rounds median 15 (E0 8) |
  | d6, E0 | 1 | 3 | 10 | 157 | |

  - C3 is higher on the route than in the shell (E M / Sh 1.17 to 1.44 in the stage, 1.26 to 1.32 in the
    joint rounds for supply 0.04), but the route / shell firing ratio does not rise (1.46 to 1.79 against
    1.77 with energy off).
  - The short circuit stage narrows a transfer in 0 or 1 pairs per configuration (s1p2 in F2r1c1b1 and
    F2r1c1b2). Seed 1 still gives 1 association in 12 in every configuration.
  - d6: 14 of 24 pairs transfer in the joint rounds, almost all as ignitions (median 157 strays); 1
    association (s0p11, 21 strays).
- **Interpretation:** neither C3 (in the stage or in the joint rounds) nor slower growth changes how many
  pairs associate: 5 to 7 of 24 against 6, with single pairs moving in both directions. C3 gives the route
  more fuel than the shell but not more firing. The outcome is set by whether the first transfer in the
  joint rounds is an ignition, and at d6 nearly every transfer is one. The "if not" branch of the plan
  applies; synaptic tagging for consolidation would not help either while the short circuit stage itself
  runs as an ignition in those pairs.
- **Process:** collectors run from Git Bash failed to download (`scp` path rewriting); the pods idled about
  35 minutes until they were terminated and the results were fetched from the volume. Run collectors from
  PowerShell, and prefetch `stent.npz` before starting two sessions on a fresh pod.
- **Cost:** 14 pods x about 58 min + 3 pods x about 21 min at $0.89/h, about $13 (about $6 of it idle).
- **Decision:** reported to the user; no further session started.

## Iteration 60 (session s72, 6 pods, 2026-10-27): rollback before ignition
- **Hypothesis:** between the last silent state and the first ignited one there is a contained transfer,
  which smaller learning steps can reach.
- **User decision:** implement the rollback rule as proposed and run the test batch. The rule is a
  protocol-level intervention (it uses the experimenter's test, like capture); the user was told so.
- **Change (code, module-checked 59 / 59 on CPU and GPU):** `GatedPlasticity.rate_scale` multiplies every
  learned change (a_plus, a_minus, a_pre). `protocol.rollback` (default None) `{"factor", "min_scale"}`:
  `w_fast` is saved before each joint round; a round whose test (A alone on `w_fast`) is not bounded, or
  which runs away itself, is undone (`w_fast` restored and written to the engine) and the scale is
  multiplied by `factor`; when the scale would drop below `min_scale` the joint rounds stop
  (`rollback.exhausted`). Rolled-back rounds count toward `max_c1_rounds`. Main run only; not combinable
  with `capture`. Telemetry: `scale` and `rolled_back` per round, `rollback` {n, exhausted, final_scale}.
  Module checks `rollback_restores_fast_weights_and_scales_rate` (exact restore and half-rate relearning,
  with rule pre_c1: rule "both" computes the presynaptic change from weights already updated by STDP, so
  halving the rates is not exactly linear there) and `rollback_stops_at_min_scale_and_counts_rounds`.
- **Sessions** (`params/session72-*.json`): s69 setting, controls off, `max_c1_rounds` 40; R2 (factor 0.5)
  and R4 (factor 0.25), both `min_scale` 1/16; d 4 and d 6, 24 pairs each (seeds 0, 1); 96 jobs, 12
  sessions on 6 RTX 4090 (VisPy data prefetched, collectors from PowerShell). Reference: s71 E0.
- **Result:**

  | | Associations | Ignitions kept | Rollbacks exhausted | No transfer in 40 rounds |
  |---|---|---|---|---|
  | d 4, E0 (s71) | 6 | 9 | - | 7 (30 rounds) |
  | d 4, R2 / R4 | 7 / 7 | 1 / 0 | 4 / 5 | 12 / 11 |
  | d 6, E0 (s71) | 1 | 10 | - | 10 (30 rounds) |
  | d 6, R2 / R4 | 1 / 1 | 0 / 0 | 11 / 9 | 12 / 14 |

  - The 6 d 4 associations of E0 are unchanged (no rollback needed). Of the 10 d 4 pairs whose first
    transfer ignited, 9 reach no contained transfer under rollback: they run into the minimum step, or stay
    below the transfer threshold until round 40 after 2 to 4 rollbacks. One becomes an association (s1p8,
    31 strays, close to the limit of 34). The two lost pairs of E0 behave as before or end without transfer.
  - At d 6 the only association is the one E0 already had (s0p11); every other ignition becomes an
    exhausted rollback or no transfer.
  - Rollbacks were triggered by an ignition that did **not** reach B in about half the cases at d 4
    (22 of 43 for R2) and in three quarters at d 6 (55 of 73): A alone lights up a large part of the
    reservoir before any route to B carries activity.
- **Interpretation:** the hypothesis does not hold in this network: learning in steps down to 1/16 of the
  original rate goes from no transfer straight to an ignition, mostly an ignition that misses B. The
  all-or-none propagation found without learning (iterations 45, 50) also holds along the learning
  trajectory. Raising the pass rate needs a network in which activity can spread in a graded way, not a
  finer schedule of the same growth.
- **Cost:** 6 pods, 20 to 36 minutes each, about $2.6.
- **Decision:** reported to the user.

## Iteration 61 (session s73, 14 pods, 2026-10-27): larger grid, pairs away from the surface
- **Hypothesis:** the ignitions are a finite-size effect of the 7 x 7 x 7 grid, where most pairs at d 4 or
  6 lie near the surface; with the same local structure in a larger grid and A, B away from the surface,
  a first transfer has room to stay local.
- **User decision:** run the larger-grid batch as proposed (9 x 9 x 9 at d 4 and d 6, 11 x 11 x 11 at d 4).
- **Change (code, module-checked 60 / 60 on CPU and GPU):**
  - Engine config `n_delays` (`assoc_build.build_network`, passed through `AssocEngine` and the queue's
    engine key): the delay count D replaces the engine's log-N rule during the build (its
    `_calc_delay_count` is swapped and restored; `snngine_v4/` unchanged). The engine derives the grid
    from D, int(D / sqrt(3)) cells per axis: D 16 gives 9 x 9 x 9, D 20 (the engine's maximum) 11 x 11 x 11.
    The engine's delay rule round((D - 1) d / d_max) then gives 1.08 to 1.10 steps per cell, against 1.15
    at 7 x 7 x 7; delays of synapses up to 3 cells long are unchanged, a straight d 4 route is 4 steps
    instead of 5.
  - Protocol `pair_margin` (default 0, identical draws as before): A and B at least this many cells from
    every face; each result records `pair.margin_cells`. Module check
    `pair_margin_keeps_pairs_off_the_surface`.
- **Sessions** (`params/session73-*.json`): the s71 E0 setting (controls off, 30 rounds), N 42,500 (D 16,
  729 groups) and N 77,600 (D 20, 1331 groups), both 58.3 neurons per group, S 2000, lambda 0.4;
  `pair_margin` 2; stray limit kept at 34 groups (`max_active_frac` 0.0467 and 0.0256). Seeds 0 and 1,
  12 pairs each; 72 jobs, one session per RTX 4090 (VRAM 13.7 and 20.1 GB of 24.5). Builds checked on
  the first pod: grid, group size (min 34 / 38, mean 58.3), intra-group E-E synapses per excitatory
  neuron 867 / 851.
- **Result** (24 pairs per row; 7 x 7 x 7 rows are s71 E0, pairs drawn anywhere):

  | | Associations | C1 transfers | Ignitions | Lost in stage | No transfer | A-alone strays, median / max |
  |---|---|---|---|---|---|---|
  | 7^3, d 4 | 6 | 17 | 9 | 2 | 7 | 26 / 199 |
  | 9^3, d 4 | 3 | 5 | 0 | 2 | 19 | 12 / 44 |
  | 11^3, d 4 | 4 | 6 | 0 | 2 | 18 | 14 / 39 |
  | 7^3, d 6 | 1 | 14 | 10 | 3 | 10 | 94.5 / 271 |
  | 9^3, d 6 | 0 | 0 | 0 | 0 | 24 | 16 / 49 |

  (A-alone strays: the largest number of active groups outside A, B and the route in any test of a pair,
  median and maximum over pairs.)
  - **No ignitions:** every first transfer in the larger grids is contained (8 to 36 strays, median 19 and
    13.5, against 76 at 7^3). Associations: s0p1, s0p6, s1p1 (9^3); s0p11, s1p3, s1p4, s1p9 (11^3), final
    strays 4 to 32. The short circuit stage narrowed two of them (36 -> 15, 11 -> 4).
  - **But A's activity no longer reaches B:** B's largest response in the A-alone tests has median 0.00
    (0.69 and 0.80 at 7^3). The spread around A grows over the first 20 rounds and then levels off
    (median strays at rounds 10 / 20 / 30: 1 / 10 / 11 at 9^3 d 4, 3 / 12.5 / 14 at 11^3, 4 / 13.5 / 16
    at 9^3 d 6), with the route groups during joint injection at 0.69 to 0.70 (d 4) and 0.55 (d 6) of
    their maximum.
- **Interpretation:** the ignitions of the 7^3 grid are a finite-size effect: with A and B two or more
  cells from the surface of a larger grid, activity from A stays local in every pair. The same change
  removes most transfers: at 7^3 the transfers that reached B were mostly carried by those ignitions, and
  learning that stays local plateaus at 10 to 16 groups around A, short of B at d 4 and far short at d 6.
  The pass rate is therefore about the same (3 and 4 against 6 of 24 at d 4; 0 against 1 at d 6), but the
  failure changes from "ignites" to "does not reach": the associations that do form are well contained.
  The comparison mixes grid size, surface margin and a 4- instead of 5-step route; at 7^3 a margin of 2
  leaves no pairs at d 4, so the two cannot be separated there.
- **Cost:** 14 pods, 31 to 38 minutes each (sessions 17 to 21 minutes), about $6.6 (from pod run time;
  the billing read did not list these pods yet).
- **Decision:** reported to the user.

## Iteration 62 (session s74, 9 pods, 2026-10-27): more reach in the larger grid; local activity-dependent inhibition
- **User decision:** "just try everything in whichever order you prefer" (after iteration 61: more reach
  in the larger grid, and a change towards graded propagation), within the $90 cap.
- **Hypotheses:** (a) in the 9^3 grid the spread around A levels off because `w_fast` decays (tau 2000)
  or grows too slowly; slower decay, a larger `a_pre` or more rounds let it reach B. (b) Inhibition that
  grows with a group's own activity caps each group's output, so that at 7^3 a transfer spreads in a
  graded way instead of igniting.
- **Change (code, module-checked 61 / 61 on CPU and GPU):** `local_inh` `{"gain", "a0"}` (default None):
  every step, every excitatory neuron gets -gain * max(0, A_g - a0) of its own group (A_g over the
  activity window, 20 steps), in every phase including the tests. Module check
  `local_inhibition_scales_with_group_activity` (its first version changed `eng.exc` after the activity
  counter had sized the groups and failed for that reason; fixed in the check).
- **Sessions** (`params/session74-*.json`):
  - Reach, 9^3 (s73 setting), d 4, pairs 0 to 5 of seeds 0 and 1: T (`tau_fast` 8000, 60 rounds),
    P (`a_pre` 1.0, 30 rounds), TP (both, 60 rounds); 36 jobs, one session per pod.
  - Inhibition, 7^3 (s71 E0 setting), d 4: the 9 pairs that ignited in s71 E0 and 3 that associated
    (s0: 0, 6, 7, 8, 9; s1: 2, 4, 6, 7, 8, 9, 11), gain 5 / 15 / 40, a0 0.2; 36 jobs, two sessions per pod.
- **Result, reach** (12 pairs; E0 = the same pairs in s73):

  | | Associations | Transfers | Lost | A-alone strays, median at round 10 / 20 / 30 / end | B max, median |
  |---|---|---|---|---|---|
  | E0 (30 rounds) | 2 (s0p1, s1p1) | 3 | 1 | 2.5 / 9 / 10.5 / 10.5 | 0.00 |
  | T (60 rounds) | 1 (s1p1) | 1 | 0 | 4 / 12.5 / 13.5 / 13.5 | 0.00 |
  | P (30 rounds) | 2 (s0p1, s1p1) | 4 | 2 | 10 / 11.5 / 11.5 / 11.5 | 0.15 |
  | TP (60 rounds) | 3 (s0p2, s1p1, s1p4) | 3 | 0 | 12.5 / 15 / 15 / 15 | 0.03 |

  Every transfer stays contained (4 to 27 strays). A larger `a_pre` reaches the plateau sooner (transfer
  in 8 to 10 rounds instead of 14 to 22), slower decay raises it slightly, and neither moves it: from
  round 20 to 60 the spread around A does not grow.
- **Result, inhibition** (12 pairs: 9 ignited and 3 associated in s71 E0):

  | Gain | Associations | Ignitions | Lost | First-transfer strays, median |
  |---|---|---|---|---|
  | 0 (s71 E0) | 3 (s0p0, s0p8, s1p9) | 9 | 0 | 76 |
  | 5 | 3 (s0p0, s0p6, s0p8) | 7 | 1 | 68 |
  | 15 | 3 (s0p0, s0p6, s0p8) | 9 | 0 | 78 |
  | 40 | 1 (s0p0) | 9 | 1 | 67 |

  One former ignition becomes an association (s0p6, 162 -> 17 / 31 strays at gain 5 / 15), one former
  association ignites instead (s1p9, 5 -> 277 / 274); at gain 40 s0p8 also ignites and s0p6 no longer
  transfers. The ignitions keep their size (48 to 243 strays).
- **Interpretation:** (a) the plateau around A is not set by the decay or the rate of `w_fast`: learning
  stops extending the spread at 10 to 15 groups, presumably because activity only reaches the groups
  next to those already active, and the active front fires too weakly to drive learning further out.
  (b) Inhibition proportional to a group's own activity (with a 20-step window) does not make the spread
  graded: it lowers every group equally once active, which removes the weak transfers as readily as it
  checks the strong ones, and an ignition still recruits the network faster than the window responds.
  Neither change raises the pass rate.
- **Cost:** 9 pods, 13 to 42 minutes each (about 4 pod-hours), about $3.6 (estimated from pod lifetimes).
- **Decision:** reported to the user.

## Iteration 63 (session s75, 4 pods, 2026-10-27): short-term synaptic depression
- **User decision:** "continue as you prefer" (after iteration 62). Chosen: a graded mechanism below the
  group level, as one small final test within the cap.
- **Hypothesis:** if a strongly firing neuron transmits less per spike, a group that is driven hard
  cannot drive its neighbours to full activity, so a first transfer spreads in a graded way instead of
  igniting, while weak, sustained activity along the route still transmits.
- **Change (code, module-checked 62 / 62 on CPU and GPU):** `std` `{"U", "tau_rec"}` (default None): each
  excitatory neuron has a resource x (1 at the start of every `run()` call); per spike x -= U x, then
  x relaxes towards 1 with `tau_rec` steps; every step its outgoing weights are written to the engine
  times x (in plastic phases on top of `w_fast` + `w_perm`, in frozen phases on top of the weights in
  place at the start), and the undepressed weights are restored at the end of the call. Spikes already
  in flight are scaled at arrival (harness-side approximation, delays up to 12 steps). Module check
  `depression_scales_outgoing_weights_and_restores_them`.
- **Sessions** (`params/session75-*.json`): the s71 E0 setting (7^3, d 4, controls off), all 24 pairs,
  D1 (U 0.1, tau_rec 200), D2 (0.2, 400), D4 (0.4, 800); 72 jobs, three sessions per pod (20.2 GB of
  24.5; a fourth would not fit). Only 3 RTX 4090 were available at first; three session starts lost
  their SSH connection and were restarted, one on a fourth pod.
- **Result** (24 pairs per row):

  | | Associations | Transfers | Ignitions | Lost | A-alone strays, median / max | B max, median |
  |---|---|---|---|---|---|---|
  | E0 (s71) | 6 | 17 | 9 | 2 | 26 / 199 | 0.69 |
  | D1 | 3 (s0p1, s0p8, s0p11) | 10 | 4 | 4 | 8 / 190 | 0.09 |
  | D2 | 3 (s0p1, s0p8, s0p11) | 6 | 3 | 0 | 3.5 / 173 | 0.00 |
  | D4 | 2 (s0p1, s0p8) | 5 | 2 | 1 | 0 / 77 | 0.00 |

  Depression shrinks the spread around A (median strays 26 -> 8 -> 3.5 -> 0) and the number of
  ignitions (9 -> 4 -> 3 -> 2), but B's response falls with it, and transfers drop from 17 to 10, 6, 5.
  The surviving associations are the pairs that associated easily before (s0p1, s0p8, s0p11; final
  strays 2 to 19); seed 1 has none. The remaining ignitions are seed 1 pairs 7, 8 and 11.
- **Interpretation:** depression does not separate the route from the rest: it weakens transmission
  from A along the route as much as everywhere else, so it trades reach for containment, as the larger
  grid (61) did. Across iterations 59 to 63, every change that removes ignitions also removes most
  transfers; in this network, reaching B 4 cells away has so far required propagation strong enough to
  spread over the reservoir.
- **Cost:** 4 pods, 26 to 38 minutes each (about 2.2 pod-hours), about $1.9 (estimated).
- **Decision:** reported to the user; about $4 of the $90 cap left.

## Iteration 64 (session s76, 3 pods, 2026-10-28): uniform-C2 control; Substep 7 assessment video
- **User decision:** after a review of iterations 1 to 63, run proposals 1 and 2 within the remaining
  cap: a control that removes the spatial information from C2, and the assessment video.
- **Hypothesis (control):** in the passing protocol (iteration 56), learning happens only where there is
  activity, so C2 may only decide *whether* consolidation happens, not *where*. Then holding C2 uniform
  at a level that opens the consolidation gate everywhere gives the same associations.
- **Change (code, module-checked 64 / 64 on CPU and GPU):**
  - `c2.uniform` (default None): while C2 is released, every voxel is held at this value. Module check
    `uniform_c2_holds_every_voxel_while_released`.
  - `assoc_assessment.py` (new; `video.kind` "assessment"): `AssessmentRecorder` keeps A_g per frame and,
    at every phase change, the permanent weights changed since the last one (sparse); `write()` selects
    the 1500 synapses with the largest final change of `w_perm` and renders with `render()` (NumPy +
    Pillow, no GL): neurons coloured by their group's A_g, A / B / C circled, the selected synapses as
    lines, A_g traces of A, B, C, a phase timeline with a playhead, a cube outline, slow rotation.
    `render(..., png_frames=[...])` writes single frames for a preview. Module check
    `assessment_recorder_tracks_permanent_changes`. Pillow lines instead of the VisPy `LineVisual` the
    task names (same content, no GL context on the pod).
  - First render: phase labels were wrong (the frame header carries the step, so every frame counted as
    a phase change and gaps showed as joint activation) and activity was too faint; fixed in the
    renderer (phase from header and step), both videos re-rendered from the saved data, module check
    updated.
- **Sessions** (`params/session76-*.json`): s71 E0 setting (7^3, d 4, controls off), all 24 pairs, C2
  uniform 1.2 (gate fully open: theta2 0.6 + soft2 0.6) and 0.9 (half open); 48 jobs. Video: s71 E0 on
  pairs s0p11 and s0p0, `video.kind` "assessment", frame stride 2, 30 fps.
- **Result, control** (24 pairs; the C1-phase transfers are identical in all three, since C2 acts only
  afterwards):

  | | Associations | Lost in stage | Ignitions kept | Final strays of the associations |
  |---|---|---|---|---|
  | E0, C2 proportional to activity (s71) | 6 (s0p0, s0p1, s0p8, s0p10, s0p11, s1p9) | 2 | 9 | 3 to 15 |
  | C2 uniform 1.2 | 7 (the same 6 + s0p4) | 0 | 10 | 4 to 16 |
  | C2 uniform 0.9 | 5 (s0p1, s0p4, s0p8, s0p10, s0p11) | 1 | 11 | 3 to 29 |

  With the gate open everywhere the same pairs associate, with the same strays (7 -> 8, 14 -> 15,
  13 -> 12, 5 -> 6, 4 -> 4, 5 -> 6), and s0p4, which proportional C2 lost, is kept.
- **Result, video** (`output/s76-video-s0/s7-d4-s0-pair{11,0}-video_main.mp4`, 35 s and 55 s): both
  pairs reproduce s71 (s0p11: 7 joint rounds, A -> B 0.94 with 3 strays; s0p0: 13 rounds, 0.60 with 6
  strays; B -> A 0 in both). Permanent changes: 725,930 synapses (s0p11) and 1,163,931 (s0p0); by distance
  from segment A-B, 92 % (s0p11) and 91 % (s0p0) within 2 cells, under 0.1 % beyond 3 cells. The 1500 drawn
  synapses all sit at the weight bound (change 0.91), so their colour carries no information; they
  cluster on A and B.
- **Interpretation:** in the passing protocol C2 carries no spatial information: it switches
  consolidation on, and *where* weights change is decided by where activity (and so learning) occurred.
  The minimal version therefore shows association by activity-dependent learning made permanent by a
  global consolidation signal, not chemical route selection. The changes are confined to a tube of about
  2 cells around A-B because the activity was, not because of the chemistry.
- **Cost:** 3 pods, 11 to 20 minutes each (about 0.85 pod-hours), about $0.8 (estimated); the preview and
  re-render ran on a pod that was already running.
- **Decision:** reported to the user.

## Iteration 65 (session s77, 3 pods, 2026-10-28): joint rounds without gaps
- **User question and decision:** why have gaps between the joint injections; test rounds without them.
  The gap (50 steps after 50 steps of injection) is the task's default round; the tests reset the
  network themselves (`AssocRun.test` calls `reset_dynamics`), so a gap is not needed for a clean test.
- **Hypothesis (agent's):** without gaps each round gives more learning, so transfers come in fewer
  rounds, with the same pairs (as with a larger `a_pre`, iteration 62).
- **Change (code, module-checked 65 / 65 on CPU and GPU):** `round_inject_steps` (default None =
  `inject_steps`): injection length of the joint and C2 rounds only, so the tests keep their 50-step
  injection of A. Module check `round_injection_length_leaves_tests_unchanged`.
- **Sessions** (`params/session77-*.json`): the s71 E0 setting, all 24 pairs, `gap_steps` 0 with
  NG100 (100-step rounds, injection throughout: same round length, twice the injection) and NG50
  (50-step rounds: same injection per round, no gap); 48 jobs.
- **Result** (24 pairs):

  | | Associations | Transfers | Ignitions | Lost | Rounds to the first transfer, median |
  |---|---|---|---|---|---|
  | E0, 50 + 50 (s71) | 6 (s0p0, s0p1, s0p8, s0p10, s0p11, s1p9) | 17 | 9 | 2 | 8 |
  | NG50, 50 + 0 | 7 (E0's seed 0 pairs + s0p4, s0p6; not s1p9) | 17 | 10 | 0 | 9 |
  | NG100, 100 + 0 | 5 (s0p0, s0p1, s0p8, s0p10, s0p11) | 19 | 11 | 3 | 8 |

  The same seed 0 pairs associate in all three; differences of one or two pairs are within noise. The
  rounds to the first transfer do not fall, even with twice the injection per round.
- **Interpretation:** the gaps make no measurable difference, and continuous joint injection does not
  speed up learning (the hypothesis of fewer rounds is refuted). The outcome is set by which pairs
  transfer in a contained way, as before.
- **Cost:** 3 pods, about 15 to 19 minutes each, about $0.8 (estimated).
- **Decision:** reported to the user.

<!-- Entry template:
## Iteration N (session sK, YYYY-MM-DD)
- **Hypothesis:**
- **Change:**
- **Result:** (job names, the numbers that decided it)
- **Decision:**
-->
