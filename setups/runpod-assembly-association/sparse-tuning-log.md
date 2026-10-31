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
- **Points of the user's review of 2026-10-31 that bear on Substep 3:** the C2 stage's narrowing comes from its
  first round being cut by the runaway stop (`runaway_frac`) after about 15 steps; the stop stays in Substep 3
  for now (its end is a to-do of the minimal task). The "no chemistry" control sets C2's gain to 0, so its final
  test equals control 0 by construction and adds nothing to a full decision.
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
