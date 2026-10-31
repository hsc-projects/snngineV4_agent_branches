# Sparse tuning log (corrected engine)

Sessions and code changes of `sparse-assemblies-task.md` after the engine fixes of 2026-10-30, one entry each
(hypothesis, change, result, decision). Substeps 0 to 2 on the faulty engine are in
`archive-pre-engine-fix/sparse-tuning-log.md`; Substep 2 on the corrected engine ran as step 7 of
`engine-fix-rerun-task.md` (`engine-fix-rerun-log.md`, "Step 7" to "Step 7, S3b screening").

## Entry 1 (Substep 3, 2026-10-31): options for L1 to L5

- **Change (code):** `assoc_plasticity.py`, `assoc_protocol.py`, all off by default, so earlier parameter files
  reproduce their runs:
  - L3: plasticity `rule` "pre_c1_signed" with `rate_thr` (spikes per step) and `rate_tau` (steps): `pre_c1`
    times clamp(rate / `rate_thr` - 1, -1, 1) of an exponential presynaptic rate trace, depression times |w|,
    potentiation times bound - |w| (`weight_dep` "upper").
  - L1, L2: `rule` "btsp" with `btsp` {`gate` "plateau" (random, `plateau_rate` per step) or "c1" (C1 rising
    through theta1), `form` "binary" or "continuous", `window` 200, `before` 133, `once`, `rate`, `seed`}.
    Only synapses onto the gated neuron whose presynaptic neuron fired in the window change. Binary: each
    flips with probability 0.5, weak (below the middle of its bounds) to the upper bound, strong to the
    lower; at most one event per neuron with `once`. Continuous: it moves by `rate` toward bound * Ip / (Ip +
    Id), the overlaps of potentiation and depression traces of the presynaptic spikes (time constants
    `before` / 3 and twice that) with a gate trace decaying from the event (time constant (`window` -
    `before`) / 3). Since the depression trace is the longer, Id >= Ip and the target stays below half the
    bound: weak synapses rise toward it, more for inputs close to the event, distant inputs fall.
  - A joint round (100 steps) is shorter than the window (200 steps): a window still open at a reset is
    evaluated then, on the part that ran.
  - L4: `protocol.theta1_fall`: after each joint round without a transfer, theta1 falls by that fraction.
  - L5: `l5` {`gain`, `c1_min`}: while C1 is released in a learning phase, each neuron also releases `gain`
    spikes' worth of C1 per 0.95 of positive learned change of `w_fast` onto it in the previous step, only
    where its C1 is at least `c1_min`, and per group at most as much as all its excitatory neurons firing.
  - L6 is not written yet (last in the rule order, "Rules").
- **Module checks** (`test_assoc_modules.py`, five new): L3's sign; binary BTSP changes only active synapses
  onto the gated neuron, once, also when a reset cuts the window; continuous BTSP favours inputs near the
  event; L5's release is gated by `c1_min` and capped per group; L4's threshold falls until the first
  transfer. On a pod (RTX PRO 4000 `6uygzl18oy4vdi`, the files copied outside the volume's clone): 79 of 79
  pass on CPU and on CUDA, after one fix (a reset cleared the spike times before evaluating cut windows).
  Pod about 6 minutes, about $0.06.
- **Settings for the screening** (from the archive and the rerun): C1 k 0.16, decay 0.0011 (3 cells,
  archived Substep 0); L3's rate threshold 9e-5 spikes per step, the mean rate of ordinary excitatory
  neurons under joint injection on the substrate (0.009 per 100-step round, `rerun7j` propagation survey).
  The C1 thresholds of L2 to L5 are relative to C1 at A in the archived field check, so they wait for C1's
  level in the spiking runs, which the L0 baseline records (its gate is always open).

## Entry 2 (Substep 3, stage 1, 2026-10-31): screening of L0 and L1

- **Hypothesis:** at lambda 1.0, d 4 (4 lambda), where the substrate sums, a BTSP-like rule gated by random
  plateaus (L1), which needs no postsynaptic spike, builds a route from A to B on S3b with the inter-group I -> E
  gain at 0.5, and possibly on S0, where the route middle stays silent. L0 is the baseline, and records C1's
  level in the spiking runs for the thresholds of L2 to L5.
- **Change:** `params/sparse3a` to `sparse3l`: the protocol of the rerun's step 5 (`rerun5e`: substep 4, up to 30
  joint rounds, C2 stage, final bounded test, at most 34 strays) without controls, on the substrate of
  `rerun7j` (sparse lattice, spacing 2, bridges, S3b, `gain_ee_inter` 0.6, inter-group I -> E 0.5; S0: S0's
  weights and I -> E 1.0), lambda 1.0, seed 0, pairs 0 to 23 (two sessions of 12 per setting). C1 released
  (gain 1, k 0.16, decay 0.0011, no saturation): L0 does not read it (theta1 -1). L0: rule `both`; L1a: `btsp`,
  plateau gate, binary; L1b: `btsp`, plateau gate, continuous (`rate` 0.5); plateau rate 1e-4 per step (about
  one neuron in three gets one in 30 rounds). L0, L1a and L1b each on S3b with I -> E 0.5 and on S0 (12 sessions, three per pod).
- **Screening rule (fixed before the run),** per setting over its 24 pairs: associations (the final bounded
  test passes A -> B), and the median strays of the first transfer and of the final test. A rule is a
  candidate for the full decision if it has more associations than L0 on the same substrate without higher
  median final strays; the best one or two candidates get the full decision (48 pairs, two seeds, all
  controls).
- **Runs:** four pods from 03:47 UTC, three sessions each: `nsjb3xuc8trj0t`, `8hwk4ataz5ysjj` (RTX PRO 4000,
  $0.57/h), `jk0jk9sdenfy1z`, `n2g6ti2ycwb5is` (RTX PRO 4500, $0.72/h); the volume's clone first brought from
  edc3c9e to 2d03a19 (bundle, `git pull --ff-only`). All 12 sessions without error, the last at 04:51 UTC.
- **Result** (`assoc_sweep_summary.py -v` and `sparse_c1_levels.py`, new, on the last pod:
  `output/sparse3-summary.txt`):

  | setting | transfers in the joint rounds | associations | joint rounds |
  |---|---|---|---|
  | L0 on S3b, I -> E 0.5 | 1 (unbounded, 274 strays) | 0 | 3 to 7 in 23 pairs: the training round runs away (pair 0: `w_fast` mean 0.002, 0.012, 0.020, 0.032, then 0.33 and a runaway in round 5; off-route groups at A_g 1 from round 4; B never active in the test) |
  | L1a, L1b on S3b, I -> E 0.5 | 0 | 0 | 30 |
  | L0, L1a, L1b on S0 | 0 | 0 | 30 (L0: one runaway in round 30) |

  - C1 (median over pairs, after the round's gap): C1 at the midpoint of A-B against C1 at A is 0.92 after
    round 1 and 0.98 to 1.11 later on S3b, 0.90 to 1.06 on S0; C1 at A grows from about 0.9 (S3b) and 0.55
    (S0) after round 1 to about 9 (S3b, round 5) and 18 (S0, round 30), the field's mean about half to
    three quarters of it. At 7^3 with a length of 3 cells C1 is nearly uniform along the route from the
    first round, so a C1 threshold cannot separate the route (L2 to L5) here.
- **Screening rule:** no candidate: no rule associates any pair, on either substrate.
- **Cost:** pods a 03:47 to about 04:18 UTC, c to about 04:19, b to about 04:27, d to about 04:53 (it ran the
  summaries), about $1.85 (estimated); all terminated (delete 204). With entry 1's pod, Substep 3 so far about
  $1.91 of the sparse task's $25.
- **Decision:** the user's.

## Entry 3 (Substep 3, stage 1 at 9^3, 2026-10-31): L0 with the rollback rule, C1's contrast

- **Hypothesis:** at 9^3 (A and B two or more cells from every face) C1 separates the route middle from the
  off-route shell, which it does not at 7^3 (entry 2: C1 in M against Sh about 1.1); L0 with the rollback rule
  (a round whose test is not bounded, or which runs away, is undone and repeated at half the learning rates)
  no longer runs away on S3b with I -> E 0.5. This batch sets the 9^3 baselines and the C1 thresholds for L2,
  L3 and L5 (next batch).
- **Change:** `params/sparse3m` to `sparse3t`: as entry 2's L0 (S3b with I -> E 0.5, and S0), at 9^3 (N 42 500,
  D 16), lambda 1.0, d 4 (4 lambda), `pair_margin` 2, rollback {factor 0.5, min_scale 0.0625}, pairs 0 to 23 of
  seed 0 in four sessions of 6 per substrate. Strays limit 10 % of all groups (`max_active_frac` 0.1, 72 groups;
  the user's default since 2026-10-31; entry 2's 7^3 runs used the same 10 %, 34 groups).
  `sparse_c1_levels.py` now also gives C1 in M and Sh at the end of each round's injection.
- **Points of the review of 2026-10-31 (a third agent's; the decisions are the user's) that bear on Substep 3:**
  the C2 stage's narrowing comes from its first round being cut by the runaway stop (`runaway_frac`) after about
  15 steps; by the user's decision the stop stays in Substep 3 for now (its end is a to-do of the minimal task).
  The "no chemistry" control sets C2's gain to 0, so its final test equals control 0 by construction and adds
  nothing to a full decision. On this substrate the joint rounds transfer in 0 to 2 of 24 pairs, so the stage
  before C2 limits Substep 3, and the stop does not bear on its counts.
- **Rule (fixed before the run):** a C1 threshold can separate the route if C1 in M exceeds C1 in Sh by at least
  1.5 (median over pairs) after some joint round; then L2, L3 and L5 get thresholds between the two at that
  round. Otherwise the C1-gated rules are not screened at this length, and a shorter C1 length is the next
  question. L0's associations here are the baselines of the rules at 9^3.
- **Runs:** four pods from 04:59 UTC, two sessions each: `8ys8ffohwbcx9k`, `ijko8jzg81cuu1` (RTX PRO 4000,
  $0.57/h), `1u11pejjytix95`, `z33a2ri6yhvyzx` (RTX PRO 4500, $0.72/h). On the 24 GB cards the second 9^3 session
  (sparse3m, sparse3o) stopped in preflight, CUDA out of memory while rewiring; both were rerun on
  the same pod behind their sibling. All 8 sessions then without error.
- **Result** (`assoc_sweep_summary.py -v` and `sparse_c1_levels.py` on the pods:
  `output/sparse3-g9-s3b-summary.txt`, `output/sparse3-g9-s0-summary.txt`; 24 pairs each):

  | setting (9^3, lambda 1.0, d 4) | transfers | associations | rollback |
  |---|---|---|---|
  | L0 on S3b, I -> E 0.5 | 2 (64 and 57 strays) | 1 (pair 15, 61 strays) | exhausted (rates down to 1/16, still igniting) in 17 pairs, 3 to 5 rollbacks in 21 |
  | L0 on S0 | 0 | 0 | none needed |

  - C1 in M against Sh (median over pairs, end of the round's injection): S3b 1.32 after round 1, 1.27 after 3,
    1.20 after 5, 1.12 after 10, 1.06 after 30; S0 1.32, 1.28, 1.23, 1.16, 1.09. Along A-B, C1 at the
    midpoint stays 0.95 to 1.12 of C1 at A.
- **Rule:** C1 in M stays below 1.5 times C1 in Sh after every round on both substrates, so the C1-gated rules
  (L2, L3, L5) are not screened at this C1 length (3 cells); a shorter length is the next question. L0's
  baselines at 9^3: 1 of 24 (S3b with I -> E 0.5), 0 of 24 (S0).
- **Cost:** pods a 04:59 to about 05:33 UTC, b to about 05:40, c to about 05:50, d to about 05:53 (the S0
  summary ran there), about $1.96 (estimated); all terminated (delete 204, `list-pods` empty). Substep 3 so far
  about $3.87 of the sparse task's $25.
- **Decision:** the user's.

## Entry 4 (Substep 3 at 9^3, 2026-10-31): thresholded C1 readout

- **Hypothesis:** entry 3's mean contrast (C1 in M against Sh at most 1.32) repeats the archived field check's
  result for a linear field (below 2 at every length) and is not the test L2, L3 and L5 need; they read C1
  through a threshold, and the archived check passed on the thresholded readout (at 11^3, d 4, M 0.56 open
  against Sh 0.17 at a length of 3 cells). Entry 3's rule was the wrong test (agent's error).
- **Change (code, not yet committed; the session runs from a copy of the clone with the changed files on the
  pod's own disk):** protocol option `c1_open` (a list of factors f; off by default): the selectivity telemetry
  also records the fraction of M and of Sh voxels whose C1 is at least f times Sh's mean C1; module check
  `c1_open_fractions_of_middle_and_shell`. `sparse_c1_levels.py` prints it per round.
- **Runs:** `params/sparse3u`, `sparse3v`: entry 3's L0 with the rollback rule at 9^3 on S3b with I -> E 0.5 and
  on S0, pairs 0 to 5, at most 10 joint rounds (C1 settles in about 9), f 1.0, 1.1, 1.2, 1.35, 1.5, 2.0.
- **Rule (fixed before the run):** a threshold separates the route if, after some joint round and at some f,
  the median open fraction is at least 0.5 in M and at most half of M's in Sh; then L2, L3 and L5 are screened
  with theta1 at f times the median Sh mean C1 of that round. Otherwise the C1-gated line ends at this
  substrate and field.
- **Runs:** pod `kybjtqx7tchtd8` (RTX PRO 4500, $0.72/h) from 05:54 UTC, both sessions side by side from a copy
  of the clone (2d03a19 with the changed files); preflight module checks pass, the new one included; both
  without error. No pair transferred in its 10 rounds.
- **Result** (`output/sparse3-c1open-summary.txt`; medians over 6 pairs; open fraction of M / Sh voxels at C1 >= f
  times Sh's mean C1):

  | round | S3b, I -> E 0.5: f 1.1 | f 1.2 | f 1.35 | S0: f 1.1 | f 1.2 | f 1.35 |
  |---|---|---|---|---|---|---|
  | 1 | 0.99 / 0.27 | 0.84 / 0.14 | 0.30 / 0.05 | 0.94 / 0.27 | 0.71 / 0.16 | 0.32 / 0.07 |
  | 3 | 1.00 / 0.24 | 0.84 / 0.05 | 0.07 / 0.00 | 0.97 / 0.26 | 0.68 / 0.14 | 0.30 / 0.05 |
  | 5 | 1.00 / 0.21 | 0.48 / 0.02 | 0 / 0 | 0.99 / 0.23 | 0.55 / 0.06 | 0.11 / 0.01 |
  | 10 | 0.66 / 0.29 | 0.00 / 0.01 | 0 / 0 | 0.86 / 0.20 | 0.17 / 0.02 | 0.01 / 0 |

  Sh's mean C1 grows from 0.39 (round 1) to 1.93 (3), 3.73 (5) and 16.7 (10) on S3b, from 0.31 to 1.05, 1.82
  and 3.45 on S0.
- **Rule:** passes on both substrates: at f 1.2 after round 3, M 0.84 against Sh 0.05 (S3b) and 0.68 against 0.14
  (S0); at f 1.1 after round 1, 0.99 against 0.27 and 0.94 against 0.27. The thresholded C1 does separate the
  route middle at 9^3, which the mean ratio (entry 3) hid.
- **Caveat for the screening of L2, L3 and L5:** the separating threshold is relative to C1's current level,
  and C1 keeps growing through the joint rounds (S3b: about ninefold from round 3 to round 10). A fixed theta1
  set from one round (the rule: f times that round's Sh mean) is selective only around that round; a few rounds
  later C1 exceeds it everywhere, and earlier it is closed everywhere. A threshold that follows C1's level
  without using where A and B are (for example f times C1's mean over the reservoir, which on S3b is about 0.6
  of Sh's) would keep the separation; that is a change to the rules' gate (user's decision).
- **Cost:** pod 05:54 to about 06:16 UTC, about $0.27 (estimated); terminated (delete 204, `list-pods` empty).
  Substep 3 so far about $4.14 of the sparse task's $25.

## Entry 5 (Substep 3, stage A, 2026-10-31): readouts of the four gate forms

- **Hypothesis:** at least one gate form keeps the route middle separated through the joint rounds, where a fixed
  threshold (G4) does so for about one round (entry 4).
- **Change (code, not yet committed; the sessions run from a copy of the clone with the changed files):** protocol
  options `c1_open_mean` (G1: open where C1 >= f times the reservoir's mean C1) and `c1_open_rise` (G3: open where
  C1 >= f times an exponential average of C1 at the same voxel, time constant `tau`), both off by default; module
  check `c1_open_against_reservoir_mean_and_own_slow_average`; `sparse_c1_levels.py` prints all three readouts.
- **Runs:** `params/sparse3w` to `sparse3B`: entry 4's L0 with the rollback rule at 9^3, both substrates, pairs 0 to
  5, at most 10 joint rounds, with the parameters of the sparse task ("C1 gate of L2 to L5"): C1 decay 0.0011
  (G1, G3, G4 readouts), 0.0025 and 0.01 (G2, with G4's and G1's readouts).
- **Rule (fixed before the run),** per form and substrate, entry 4's: a form passes if after some joint round, at
  some f, the median open fraction is at least 0.5 in M and at most half of M's in Sh. Since G4 already passes
  around one round, a form is better than G4 if it passes in at least three of the readout rounds 1, 3, 5 and 10.
- **Runs:** three pods (RTX PRO 4500, $0.72/h) from 06:51 UTC, `fp6tq4xpucurj6`, `ndxmdx621csjoe`, `2212kcea90px6g`, two
  sessions each, from a copy of the clone at 21c93c5 with the changed files; preflight 82 of 82 module checks on CPU
  and CUDA (the new one and the review's hysteresis check included); all six without error; no pair transferred.
- **Result** (`output/sparse3-stageA-gA.txt`, `-gB.txt`, `-gC.txt`; medians over 6 pairs; open fraction M / Sh):
  - G3 (C1 against the voxel's own slow average, tau 150): no separation; M and Sh open alike (1 / 1 through round
    5 at every f, 0.91 / 0.91 at f 1.1 after round 10 on S3b).
  - G1 and G2 pass in single rounds, at different f. With one f, as a gate has (best f per setting; rounds out of 1,
    3, 5 and 10 that pass):

  | C1 decay (length) | S3b with I -> E 0.5, G1 | S0, G1 |
  |---|---|---|
  | 0.0011 (3 cells) | f 2: rounds 3, 5 (1.00 / 0.49, 0.73 / 0.12) | f 2.5: round 3 (0.96 / 0.24) |
  | 0.0025 (2 cells) | f 2: rounds 3, 5 (1.00 / 0.50, 0.90 / 0.15) | f 2: rounds 5, 10 (1.00 / 0.49, 0.62 / 0.09) |
  | 0.01 (1 cell) | f 2.5: rounds 1, 3 (1.00 / 0.38, 0.77 / 0.14) | **f 2.5: rounds 1, 3, 5, 10** (1.00 / 0.49, 1.00 / 0.38, 0.91 / 0.26, 0.62 / 0.12) |

  - Why: on S3b with I -> E 0.5 C1 jumps as L0's activity rises (Sh's mean C1 times 3 to 4 from round 5 to round 10
    at every length), on S0 it grows slowly at the 1-cell length (0.23, 0.52, 0.69, 0.87 after rounds 1, 3, 5, 10).
    G4's readout (f times Sh's current mean) separates at f 1.1 to 1.2 in every round and setting, but that
    reference follows the field with knowledge of the regions; as a fixed theta1 it is the one-round gate of entry 4.
- **Rule:** with one f per gate, only G1 with the 1-cell C1 (G2) on S0 passes at least three rounds; it is the one
  form better than G4. On S3b with I -> E 0.5 no form does. G3 does not pass at all. Stage B per the funnel: L3
  under G1 with the 1-cell C1 (f 2.5) and under G4, both substrates.
- **Cost:** three pods 06:51 to about 07:20 UTC, about $1.05 (estimated); terminated (delete 204). Substep 3 so far
  about $5.19 of the sparse task's $25.

## Entry 6 (Substep 3, stage B, 2026-10-31): L3 under G1 (1-cell C1) and under G4

- **Hypothesis:** L3 (presynaptic rate times C1, depression below the rate threshold), which needs no spike in the
  route middle, builds the route where its C1 gate separates it; with G1 at the 1-cell length on S0 (entry 5: route
  middle open, shell at most half as much, in every readout round) better than with G4's fixed threshold.
- **Change (code, not yet committed; the sessions run from a copy):** plasticity option `theta1_rel` (G1: theta1 is
  a factor times the current mean C1 over all neurons, in the learning gate, the consolidation gate and L2's C1
  events); module check `theta1_rel_gates_relative_to_the_mean_c1`.
- **Runs:** `params/sparse4a` to `sparse4p`: entry 3's protocol at 9^3 (lambda 1.0, d 4, rollback rule, 30 joint
  rounds, C2 stage, strays limit 10 %), L3 = rule `pre_c1_signed` (`rate_thr` 9e-5, `rate_tau` 100, `weight_dep`
  "upper", `a_pre` 0.5, gate at both ends), soft1 0, pairs 0 to 23 of seed 0 in four sessions of 6 per setting:
  G1 with C1 decay 0.01 and theta1 2.5 x mean C1, on S3b with I -> E 0.5 and on S0; G4 with the default C1 (decay
  0.0011) and theta1 2.32 (S3b) and 1.26 (S0), 1.2 times Sh's mean C1 after round 3 (entry 4).
- **Rule (fixed before the run):** a setting is a candidate for the full decision if it has more associations than
  L0 on the same substrate at 9^3 (entry 3: 1 of 24 on S3b, 0 on S0) without higher median final strays; G1 is
  better than G4 if it has more associations on the same substrate. Then L2 and L5 run under the better form.
- **Runs:** eight pods (RTX PRO 4500, $0.72/h) from 07:15 UTC, two sessions each, from a copy of the clone at
  21c93c5 with the changed files; all 16 sessions without error, the last at 07:45 UTC.
- **Result** (`assoc_sweep_summary.py -v` and `sparse_c1_levels.py` on the last pod: `output/sparse4-stageB-summary.txt`;
  24 pairs per setting):

  | setting (9^3, lambda 1.0, d 4) | transfers | associations (final strays) | joint rounds | rollbacks |
  |---|---|---|---|---|
  | L3 under G1, 1-cell C1, S3b with I -> E 0.5 | 5 | **4** (16, 28, 62, 38; median 33) | 30 in 18 pairs; transfers after 3, 4, 5, 11, 19 | 3 pairs (1 exhausted) |
  | L3 under G1, 1-cell C1, S0 | 0 | 0 | 30 | none |
  | L3 under G4 (theta1 2.32), S3b with I -> E 0.5 | 0 | 0 | 30 (one 22) | 3 pairs (1 exhausted) |
  | L3 under G4 (theta1 1.26), S0 | 0 | 0 | 30 | none |
  | L0 with rollback, S3b with I -> E 0.5 (entry 3) | 2 | 1 (61) | | 21 pairs, 17 exhausted |

  - Under G1 the gate stays selective through all 30 rounds in the runs themselves (median open fraction M / Sh at
    2.5 times the mean C1: S3b 1.00 / 0.55, 0.42, 0.37 after rounds 1, 3, 5, then 0.98 to 0.93 / 0.35 to 0.37;
    S0 1.00 / 0.68 to 0.47). On S3b with I -> E 0.5, L3 does not run away as L0 does (rollback in 3 of 24 pairs,
    against 21).
  - Pair 15 (seed 0) associates under both L0 and L3; the other three of L3's are new.
- **Rule:** L3 under G1 on S3b with I -> E 0.5 is a candidate for the full decision (4 against L0's 1, median final
  strays 33 against 61), and G1 is better than G4 there (4 against 0). On S0 no setting associates. 4 of 24 is a
  screening count, not yet significant: the full decision (48 pairs, two seeds, controls) decides.
- **Cost:** eight pods 07:15 to about 07:37 to 07:47 UTC, about $2.70 (estimated); all terminated (delete 204).
  Substep 3 so far about $7.89 of the sparse task's $25.

## Entry 7 (Substep 3, stage C, 2026-10-31): full decision for L3 under G1 on S3b with I -> E 0.5

- **Hypothesis:** entry 6's 4 of 24 is a real gain over L0, and it needs C1's spatial pattern and the joint
  activation of A and B.
- **Runs:** `params/sparse5a` to `sparse5t`, all at 9^3, lambda 1.0, d 4, as entry 6:
  - main: L3 under G1 (1-cell C1, theta1 2.5 x mean C1), seeds 0 and 1, pairs 0 to 23 each, with control 0 and
    the separate-rounds control in every job (`protocol.controls`; not the "no chemistry" control, which equals
    control 0 by construction);
  - uniform-C1 control, as the user decided on 2026-10-31: the gate open everywhere (theta1 -1, the same C1 and
    everything else), the same 48 pairs; under G1 a uniform C1 would shut the gate everywhere and test nothing;
  - L0 with the rollback rule on seed 1 (seed 0 is entry 3's), the baseline for the paired comparison.
- **Rule (fixed before the run),** over the 48 pairs, paired by pair (McNemar's exact one-sided test on the
  discordant pairs, p < 0.05): L3 under G1 is kept if (1) it associates more pairs than L0 and (2) more than with
  the gate open everywhere, (3) the separate-rounds control associates fewer pairs than the main run, and (4) its
  median final strays are not above L0's (L0 with associations) or the gate-open run's. Control 0 must hold in
  every associated pair. If kept, it goes to stage 2 (11^3, d 10); otherwise the report says which condition
  failed.
- **Runs:** ten pods (RTX PRO 4500, $0.72/h) from 08:24 UTC, two sessions each, from a copy of the clone at 21c93c5
  with the changed files. The gate-open sessions finished by 08:42. At 08:48:27 Runpod terminated every pod of the
  account (the account had run out of funds; audit log, actor "runpod"): the eight main sessions and the four L0
  sessions were cut after 2 to 5 of their 6 jobs; their partial outputs are kept on the volume as `-killed` and not
  used. The twelve sessions were rerun on six pods from 09:51 UTC, all without error, the last at 10:37.
- **Result** (`sparse_decision.py`, new, and the sweep and controls summaries on the last pod:
  `output/sparse5-stageC-decision.txt`; 48 pairs, seeds 0 and 1, paired by pair):

  | run | associations | median final strays |
  |---|---|---|
  | L3 under G1, 1-cell C1 (main) | **11 of 48** (seed 0: 4, seed 1: 7) | 42 |
  | separate-rounds control (in the main jobs) | 0 of 48 | |
  | gate open everywhere (uniform-C1 control) | 0 of 48 | |
  | L0 with the rollback rule | 1 of 48 (seed 0, pair 15) | 61 |

  - Paired, McNemar's exact one-sided test: main against L0 10 to 0, p 0.001; against the gate-open control 11 to
    0, p 0.0005; against the separate-rounds control 11 to 0, p 0.0005. Control 0 holds in every associated pair.
  - Main's associated pairs (final strays): seed 0 pairs 0 (16), 3 (28), 8 (62), 15 (38), the same pairs and
    strays as in entry 6's screening; seed 1 pairs 2 (37), 3 (44), 5 (55), 7 (42), 15 (57), 16 (39), 19 (47). 15
    pairs transferred in the joint rounds, 4 of them lost in the C2 stage; none unbounded.
- **Rule:** all four conditions hold: more associations than L0 (p 0.001) and than with the gate open everywhere
  (p 0.0005), fewer under separate rounds (p 0.0005), median final strays 42 against L0's 61 (the gate-open run has
  none). L3 under G1 with the 1-cell C1 is **kept** at 4 lambda, on S3b with inter-group I -> E gain 0.5: the first
  association in the sparse task that needs both C1's spatial pattern and the joint activation of A and B. It goes
  to stage 2 (11^3, d 10). Route selectivity (`R_off`, pass criterion 3) was not measured in these runs.
- **Cost:** the first ten pods about $2.45 (four until about 08:37 to 08:42, six until the termination at 08:48),
  the six rerun pods about $2.75 (09:51 to about 10:20 to 10:37 UTC), about $5.20 in all (estimated); all
  terminated (delete 204, `list-pods` empty). Substep 3 so far about $13.10 of the sparse task's $65.
