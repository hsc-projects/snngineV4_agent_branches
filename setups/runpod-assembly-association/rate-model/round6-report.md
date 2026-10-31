# Round 6: the engine's own network in model B

Raw results are in `output-round6/` (gitignored): per network (`g7-s0`, `g7-s1`, `g9-s0`, `g9-s1`) the export's
`meta.json` (structure report, structure audit, pairs, injected neurons, control-0 tests), `audit_model_b.json`
(the same audit of model B's own network) and `trace.json` (step-2 comparison); `single_*.json` (construction check, step 1),
`hetero.txt` (composition per neuron, group and test; script `round6_hetero.py`, a copy of the scratch script that
produced it) and the pod logs. The exported network arrays (2.9 GB) stay on the network volume in
`/workspace/output/rate-model-round6/`. New code: `round6_export_engine.py`, `round6_compare.py` (`audit`, `trace`,
`single`), and in `spiking_group_model.py` the options `export_dir` (load an exported network) and `frac_I_to_I`
(inhibitory -> inhibitory synapses in the model's own construction); defaults reproduce rounds 4 and 5 (21 module
checks pass, 3 skipped as before).

**After the engine fixes (2026-10-30, last section):** on the fixed engine, model B with the configured
composition and no fitted factor reproduces the engine's single-group response at 7^3 and 9^3 (medians within
3.8 % and 1.6 %), and still reproduces every spike total exactly on the exported networks. Points (1), (3) and
(4) below describe the faulty engine.

**Step 3, admission (2026-10-30, section "Step 3" at the end): not admitted.** At the rerun's settings, with no
fitted parameter, model B on the rerun's own networks meets the class fractions at 7^3 and the uniform-C2
requirement, but not the grid size: at 9^3 it finds 1 association of 24 where the spiking runs find 11 (7^3:
16 against 15). Its first transfers agree at both sizes; its final strays exceed the spiking ones by about 12 at
9^3 (4 at 7^3), so most of its misses are near-misses ("Final strays").

**Summary (before the engine fixes).**
(1) The engine's built network differs from what model B assumed from the configuration code: excitatory neurons
have about 328 E -> I synapses of 2000 (model B: 400), inhibitory neurons have about 328 **I -> I synapses**
(model B: none; engine weight -1.76) and 1672 I -> E (model B: 2000); E -> I normalized weights are 0.45 or 0.47
(mean 0.466; model B 0.45). Delays, neuron parameters, post-warm-up states and the rewiring rule agree.
(2) On the exported network, model B reproduces the engine's A-alone test before learning exactly: identical spike
totals in all 96 tests (4 networks x 12 pairs x 2 directions), input currents equal within float32 summation
order (largest difference 0.05), spike timing identical except one test (from step 42, same total). The neuron
update, delivery, clamp and injection of model B are therefore those of the engine; the single-group excess of
round 5 came only from the network composition.
(3) With the measured composition in its own construction and **no fitted factor**, model B gives at 9 x 9 x 9 a
median of 403.5 spikes per A-alone test against the engine's 413 (inhibitory spikes outside the injected group
189 against 189); with the round-5 composition 954.5 (722). The inter-group E -> I factor of rounds 4 and 5 (0.3
to 0.7) compensated the missing I -> I inhibition and the excess E -> I synapses.
(4) At 7 x 7 x 7 the composition is not uniform: about one neuron in five, in contiguous index blocks and so in
whole location groups, has **no inhibitory targets at all** (all 2000 synapses onto excitatory neurons); the
others have about 400. Injecting into such a group gives 950 to 1500 spikes instead of about 400. At 9 x 9 x 9
there are no such neurons (278 to 426 per neuron). Model B with a uniform composition therefore matches 9^3 but
not 7^3 (378 against 472; the engine's upper quartile 630). This construction pattern of the engine may be the
cause of the spiking network's 7^3 / 9^3 difference (iteration 61) that the admission test asks for; not verified.
(5) Steps 1 and 2 are done, except that the correction of model B's construction (part of step 1) holds for
9^3 and is open for 7^3; step 3 (learning, then admission) and step 4 (check on the sparse substrate) are not
started. Pod cost about $0.21 (estimated).

## Step 1: export and structure audit

Setup: one GPU pod (below); the engine built from the params files of the spiking runs (7^3: `session71-d4-s<seed>-p*.json`,
jobs `*-E0`; 9^3: `session73-g9-d4-s<seed>-{a,b}.json`), 12 pairs per network; `AssocRun` with the job's
parameters and `rng_seed` as in `substep4_protocol`, so the pairs and injected neurons are those of the spiking jobs.
The spiking code on the volume (`assoc_engine.py`, `assoc_protocol.py`) is older than the local copies; the local
versions only add sparse-task options that are off by default; the volume's code was used unchanged.

Replay check: the engine's control-0 tests reproduce the spiking reference (9^3: median 413 spikes over 48 tests,
range 276 to 486; round 5: 415.5, 308 to 554), and each test's total equals the `spikes` the export recorded.

| quantity (per neuron, mean) | engine 7^3 (s0, s1) | engine 9^3 (s0, s1) | model B own (rounds 4, 5) |
|---|---|---|---|
| E -> E synapses per excitatory neuron | 1681 | 1672, 1668 | 1600 |
| E -> I synapses per excitatory neuron | 318.6 (min 0, max 440) | 327.6, 331.7 (278 to 426) | 400 |
| I -> E synapses per inhibitory neuron | 1674 | 1672, 1668 | 2000 |
| I -> I synapses per inhibitory neuron | 325.7, 325.5 | 327.7, 331.8 | 0 |
| E inputs of an inhibitory neuron from groups at distance 1 | 291.8, 290.5 | 299.5, 304.3 | 366 |
| I inputs of an excitatory neuron | 418.6 | 418.1, 417.1 | 500 |
| E -> I normalized weight | 0.45 or 0.47, mean 0.466 | same | 0.45 |
| I -> I engine weight | -1.76 (-0.44 x gain 4; no gain_ie) | same | none |

Unchanged against model B: the delay of every synapse follows round((D - 1) d / d_max) (agreement 1.0 for every
type), the E -> I synapses between groups at distance 1 match the rewiring rule given the per-neuron counts
(observed / expected 1.000 and 1.004), the neuron parameters a, b, c, d and the post-warm-up v, u agree by type,
every neuron uses the Izhikevich branch (`N_flags` row 3 = 0), no synapse is deleted.

Group numbering: the engine numbers location groups z dim^2 + y dim + x, model B x dim^2 + y dim + z (an exchange
of the x and z axes; checked on all four networks). Distances and margins are unchanged, so the pair positions
used in round 5 (engine indices read as model indices) were mirrored positions, statistically equivalent. The
loader relabels the groups.

Origin of the composition: the configuration (`n_type_groups.py`, gen_factors 1 : 4) gives excitatory neurons 400
inhibitory and 1600 excitatory targets and inhibitory neurons only excitatory ones; the built network (before
`rewire_by_distance`, which keeps each target's type) does not follow it. The weights suggest that targets are
chosen largely regardless of the intended type: of the E -> I synapses about 20 % carry the E -> I built weight
0.45 and 80 % the E -> E built weight 0.47. The construction kernel was not read (agents/common.md: kernel
details are deferred).

## Step 2: single-group response, step by step

Model B (`export_dir`) on each exported network, the engine's injected neurons, background off, both control-0
tests of each pair (`round6_compare.py trace`):

| network | tests | pass | spike totals equal | largest input difference | first spike-timing difference |
|---|---|---|---|---|---|
| 7^3 s0 | 24 | 24 | 24 | 0.020 | one test, step 42 |
| 7^3 s1 | 24 | 24 | 24 | 0.046 | none |
| 9^3 s0 | 24 | 24 | 24 | 0.011 | none |
| 9^3 s1 | 24 | 24 | 24 | 0.017 | none |

(Input currents recorded over the first 12 steps; differences come from the summation order of `atomicAdd` in
float32.)

## Step 1, continued: model B's own construction with the measured composition

Options (derived from the export, no fitted factor): `frac_E_to_I` and `frac_I_to_I` the measured means per grid
(9^3: 0.1648 and 0.1649; 7^3: 0.1593 and 0.1628), `w_ei` 0.466; the inter-group E -> I factor 1. A-alone tests
before learning on model B's own networks (seeds 0 to 3) at the engine's 24 pair positions per grid, against the
engine's 48 tests (`round6_compare.py single`, medians with interquartile range; pass **[default]**: median within 5 % as in step 2):

| grid, composition | spikes per test | inhibitory spikes outside the injected group |
|---|---|---|
| 9^3 engine | 413 [381, 455] | 189 [164, 220] |
| 9^3 model B, measured | 403.5 [379, 433] | 189 [168, 217] |
| 9^3 model B, round 5 | 954.5 [861, 1009] | 722 [620, 788] |
| 7^3 engine | 472 [411, 630] | 242 [178, 336] |
| 7^3 model B, measured | 378 [349, 405] | 159 [129, 189] |
| 7^3 model B, round 5 | 821 [722, 946] | 578 [470, 704] |

9^3: within 5 % (2.3 %). 7^3: not matched; the engine's composition is bimodal there
(`hetero.txt`): about one neuron in five has no inhibitory targets, in contiguous index blocks (for example the
inhibitory neurons in the first and sixth tenth of the index range all have none), so that some location groups
have no E -> I synapses at all; the others have about 400. The largest engine tests are exactly the injections
into such groups (7^3 s0: 1479, 1290, 1171, 1115, 946 spikes, E -> I per excitatory neuron of the injected group 0;
s1: 1509, 1427, 1314, 1208). A uniform composition cannot reproduce this. At 9^3 no neuron is without inhibitory
targets; group means are about 300 or about 400.

## Open

Superseded by the engine fixes ("After the engine fixes", last section): the composition was the transposed
synapse table, now fixed, and the consequences for the spiking results are handled by
`../engine-fix-rerun-task.md`. Kept as written at the time:

- **7^3 composition.** Either model B takes the per-neuron numbers of inhibitory targets from an export of the
  engine's construction (it depends on N, S and the seed, not on lambda, since rewiring keeps each target's
  type), or the admission test uses exported engine networks as realizations (one GPU export takes 15 to 25 s of
  build time). Decision for the user.
- **Consequence for the spiking results (to report to the sparse task).** The predecessor's 7^3 substrate has
  location groups without any E -> I synapses; whether that, rather than the lattice size, causes the 7^3 / 9^3
  difference of iteration 61 is not verified. Whether the engine's construction is meant to produce this is a
  question for the engine (`agents/common.md`: connectivity generation "has been a source of past bugs").
- Step 3 (learning, then admission) and step 4 (check on the sparse substrate) not started.

## Cost

Pod `gxegd7wid7ti0b` (`rm6-export`), RTX PRO 4000 Blackwell, 12 vCPU, 31 GB, EU-RO-1, Secure, $0.57/h, network
volume `qze81dpw7q`; created 23:18 UTC (2026-10-29), terminated about 23:40 UTC after the results were downloaded
(delete 204, `list-pods` empty): about 0.37 h, about $0.21 (estimated from the lifetime; billing not read). The
RTX 4090 named in the task was replaced by a Blackwell card because another Blackwell pod was using the volume's
SM 120 backend build when the session was planned (it was gone by the time the pod was created).

Concurrent use of the volume: another agent's SM 89 session started on the same volume about three minutes after
this pod was created and ended about 23:31 UTC; its runner swaps the shared backend build to SM 89 on start (that
agent's report). This pod never swapped the build (its runner step failed on a typo in the session script and was
not repeated; the later steps import no backend). Its four export processes loaded the backend between 23:21 and
23:24 UTC, possibly during that swap; no backend error was logged, and the engine's results are confirmed
independently by step 2 (model B, a separate numpy implementation, reproduces every spike total exactly). The
volume's active build was left at SM 89. Steps 1 and 2
ran on the GPU pod (export, audit, comparison and the construction check took under 15 minutes in total), not on a
separate CPU pod.

## Cause of the composition: the synapse-table transpose (engine construction)

`snngine_v4/nn/synapses.py` (`Synapses.fill_tensors`, line 415 before the fix) converted the synapse table from
the construction kernels' layout (N, S) row-major, index n S + s (`snn_representation.cu`, reindex_N_rep_) to the
layout the simulation reads, (S, N), index n + N s, with `N_rep.gpu_values.T.reshape(N_rep.shape)`. That is a
transpose only for N = S; otherwise final synapse s of neuron n holds the entry at memory position
(p mod S) N + p div S, p = s N + n, of another neuron's list. Every neuron therefore had a mix of other neurons'
synapse lists (excitatory lists hold 400 inhibitory targets, inhibitory lists none), and its delays (N_delays,
written per neuron) did not belong to its targets. Consequences:

- Without rewiring (iterations 1 to 38): connectivity flat in space (iteration 39's survey measured this; it was
  this error, not the engine's connection rule) and delays unrelated to distance (14.7 % of synapses at 7^3,
  10.6 % at 9^3 had the delay of their distance).
- With rewiring (iteration 40 on): targets and delays redrawn by distance, but each synapse's target type is
  kept, so the composition above remained (7^3: 3518 of 16,000 excitatory neurons with the configured 400
  inhibitory targets, 800 of 4000 inhibitory neurons with none).

Fix (user decision 2026-10-30, core code changed with explicit approval): `N_rep.gpu_values.reshape(N, S).T.contiguous()`.

## Test of the fix (GPU pod, local copy of the repository)

The fixed engine was built on a copy of the repository on the pod's own disk, so the shared volume's engine
(used by other sessions) is unchanged. `round6_test_construction_fix.py`, results in `output-round6/fixtest/`:

| check | 7^3 (N 20,000, D 13) | 9^3 (N 42,500, D 16) |
|---|---|---|
| excitatory neurons with exactly 400 inhibitory targets | 16,000 of 16,000 | 34,000 of 34,000 |
| inhibitory neurons with no inhibitory target | 4000 of 4000 | **5713 of 8500** (others up to 563) |
| delay of every synapse = rule round((D - 1) d / d_max) | 100 % | **88.2 %** |
| autapses | 0 | **572** |
| old line reconstructed from the fixed table = old engine (export), inhibitory targets per neuron | 20,000 of 20,000 neurons equal | 42,500 of 42,500 equal |
| E -> E synapses per group pair at 1 / 3 / 6 cells / farthest (median) | 515.5 / 336 / 119 / 54 (old: 211 / 229 / 199 / 121) | 376 / 218 / 82 / 21 (old: 103 / 108 / 105 / 66.5) |
| A-alone test before learning in the spiking setup (rewired, 24 tests, median) | 869.5 (628 to 1200); old engine 472 | 961.5 (485 to 1159); old engine 413 |

- The cause is proven exactly: the old line applied to the fixed table reproduces the old engine's composition
  neuron by neuron at both sizes.
- 7^3 is fully correct after the fix. **9^3 is not:** inhibitory neurons' synapses still reach inhibitory
  neurons, 11.8 % of delays do not match distance, and there are autapses; a second construction error that
  appears in this configuration (delay count forced to 16 by `assoc_build.build_network(n_delays=16)`; the
  delay count is computed in one place only). Likely cause, from reading the code (not yet confirmed by a run):
  the final correction in `fill_G_exp_ccsyn_per_src_type_and_delay_` (`snn_representation.cu`) shifts one delay
  bucket of the inhibitory sources' cumulative counts by the whole surplus without a bound, so the bucket can turn
  negative; the validator checks only the first and last rows; a negative bucket leaves the rest of the neuron's
  slots unwritten (target 0, an inhibitory neuron). `snngine_v4/tests` checks every bucket (`check_count_tables`).
- **Second error, confirmed:** initial weights follow the slot range of the configuration, not the target's type
  (`n_type_groups.apply_init_weights`, called after the final sort by delay). With the fix, at 7^3 1.93 M E -> I
  synapses carry 0.45 and 4.47 M carry the E -> E weight 0.47; 4.47 M E -> E synapses carry 0.45. The harness
  overwrites E -> E weights (`w_ee`), not E -> I. Not fixed (needs approval). (Later fixed with the user's
  approval, as was the 9^3 error above: commit f56ccf8, `setups/runpod-engine-tests/engine-tests-report.md`.)
- With the configured composition, a single injected group drives about 870 to 960 spikes instead of about 415
  to 470 (model B with the configured composition predicted 954.5 at 9^3, step 1): the spiking protocol was
  tuned on the scrambled network and will need re-tuning.

Cost: pod `e60j55jyp3xsda` (`rm6-fixtest`), RTX PRO 4000 Blackwell, EU-RO-1, $0.57/h, 00:02 to 00:08 UTC
(2026-10-30), about $0.06 (estimated); terminated (delete 204, `list-pods` empty).

## After the engine fixes (2026-10-30)

Steps 1 and 2 repeated on the fixed engine (commit f051b62, all engine fixes of f56ccf8 and cc94dde), with the
same params files, pairs and injected neurons as above (rewiring at lambda 0.4, revision 1 of the task). Engine
built from a packed copy of the repository on the pod's own disk (`setups/runpod-engine-tests/pack_tree.sh`), not
from the shared volume, whose engine was then still the old one (deployed later the same day: step 0 of
`../engine-fix-rerun-report.md`). Results in
`output-round6-fixed/` (gitignored). Session: `round6_fixed_pod.sh`, run on the pod after
`setups/runpod-engine-tests/run_on_pod.py` has unpacked and built the copy (it chains the commands below).

**Structure audit** (`round6_export_engine.py`, `round6_compare.py audit`; engine against model B's own network
with the configured composition, means per presynaptic neuron):

| quantity | engine 7^3 (s0) | model B 7^3 | engine 9^3 (s0) | model B 9^3 |
|---|---|---|---|---|
| E -> E within / between groups | 858.7 / 741.3 | 858.4 / 741.6 | 829.4 / 770.6 | 829.9 / 770.1 |
| E -> I within / between groups | 211.8 / 188.2 | 211.0 / 189.0 | 204.6 / 195.4 | 204.4 / 195.6 |
| I -> E within / between groups | 1073.0 / 927.0 | 1073.0 / 927.0 | 1038.5 / 961.5 | 1038.0 / 962.0 |
| I -> I | 0 | 0 | 0 | 0 |
| E inputs of an inhibitory neuron from groups at distance 1 | 365.2 | 365.7 | 365.6 | 366.2 |

Every excitatory neuron has exactly 1600 E -> E and 400 E -> I synapses, every inhibitory neuron 2000 I -> E (all
four networks); E -> I normalized weight 0.45 on every synapse; every delay follows round((D - 1) d / d_max)
(agreement 1.0 for every type); no deleted synapses; E -> I synapses between groups at distance 1 match the
rewiring rule (observed / expected 1.000, 1.000, 1.000). The composition of points (1) and (4) of the summary
is gone.

**Step 2, model B on the exported networks** (`round6_compare.py trace`):

| network | tests | pass | spike totals equal | largest input difference | first spike-timing difference |
|---|---|---|---|---|---|
| 7^3 s0 | 24 | 24 | 24 | 0.033 | none |
| 7^3 s1 | 24 | 24 | 24 | 0.043 | none |
| 9^3 s0 | 24 | 24 | 24 | 0.025 | none |
| 9^3 s1 | 24 | 24 | 24 | 0.024 | none |

**Single-group response on model B's own networks** (`round6_compare.py single`, configured composition, no
fitted factor, model defaults; seeds 0 to 3 at the engine's 24 pair positions per grid, 192 tests, against the
engine's 48; medians with interquartile range; pass **[default]** within 5 %):

| grid | engine spikes per test | model B | difference | engine inhibitory spikes outside the injected group | model B |
|---|---|---|---|---|---|
| 9^3 | 970.5 [868, 1035] | 954.5 [861, 1009] | 1.6 % | 712.5 [623, 807] | 722 [620, 788] |
| 7^3 | 791 [714, 908] | 821 [722, 946] | 3.8 % | 538.5 [490, 687] | 578 [470, 704] |

Both grids pass. Model B's numbers equal the "round 5 composition" rows of step 1 (same seeds and settings): the
configured composition that rounds 4 and 5 assumed was right; the engine was not. A single injected group now
drives about 790 to 970 spikes (about 470 and 410 on the faulty engine), with the parameters tuned on the
faulty engine.

Module checks on the pod: `test_spiking_group_model.py` 21 OK, `test_rate_model.py` 34 OK (1 skipped). Their
intra-group in-degree references were then updated to these exports (858.7 at 7^3, 829.4 at 9^3; 892.7 and 867
on the faulty engine), with the tolerance tightened to 2 %, and passed again on a second pod
(`test_spiking_group_model.py` 21 OK, `test_rate_model.py` 34 OK (1 skipped), `test_popdensity_model.py` 15 OK).

Consequences:

- Model B with its defaults is the reduced network the admission test needs; the fitted factors of rounds 4 and
  5 (`ei_inter_scale`, the plasticity and inhibition factors) and the round 6 option `frac_I_to_I` described the
  faulty networks and are not used.
- Step 3 (learning, then admission) waits for the rerun's ground truth (`../engine-fix-rerun-task.md`, steps 5,
  6 and 8). If the rerun's step 2 replaces the rewiring with the engine's own wiring, these checks are repeated
  on that wiring (model B then needs its distance profile).
- 11^3 not checked (no export; the rerun's step 1 audits it).

Cost: pod `s9o38cl9s4qvny` (`r6-fixed-engine`), RTX PRO 4000 Blackwell, 12 vCPU, EU-RO-1, Secure, $0.57/h,
network volume `qze81dpw7q` (used only for the build cache and the results); created 10:20:42 UTC, terminated
after the download (delete 204, `list-pods` empty), about 12 minutes, about $0.11 (estimated; billing not
read). The first attempt ran four exports at once and a 9^3 build ran out of GPU memory (24 GB); the
rerun built 9^3 one at a time. The check of the updated module checks: pod `6xcip3ngfxowrd` (`r6-test-check`), same
type and price, created 10:33:15 UTC, about 4 minutes, about $0.04 (estimated); terminated (delete 204,
`list-pods` empty).

## Step 3: learning, then admission, on the rerun's networks (2026-10-30)

Spiking reference: `../engine-fix-rerun-task.md`, steps 3, 5 and 6 (summaries `../output/rerun5-summary.txt`,
section `sweep proto-lam0.4`, and `../output/rerun67-summary.txt`, section `rerun6[cd]-grid-g9-d4-*`, config `E0`;
gitignored). Settings of the steps: gain 4, `gain_ie` 2, intra-group input 40, d 4, rewiring at lambda 0.4 with
`gain_ee_inter` 2.4 (the engine's own wiring: 1.2), the C2 stage; uniform-C2 control `c2_uniform` 1.2. Model B
with its defaults (configured composition), these settings and **no fitted parameter**. Each pair is classified
as in Substep 3 (first transfer: contained at most 34 strays, ignition, none); an association is a pair whose
strays at the end are at most 34. Code: `round6_regime_precheck.py` (`own`: model B's own networks; `export`:
the engine's exported networks with the engine's injected neurons, `set_injection`; `--c2`, `--set`),
`round6_admission_compare.py` (pair by pair against a sweep summary; agreement and Cohen's kappa),
`round6_precheck_pod.sh` and `round6_grid_pod.sh` (pod sessions); `round6_compare.py spec_for` now takes lambda
from the export. Results in `output-round6-precheck/` and `output-round6-grid/` (gitignored; the comparisons in
`output-round6-grid/compare_g7.*` and `compare_g9.*`).

**Archived regime first.** Model B at the settings of rounds 4 and 5 (`admission_spiking_group.py`, archived
reference 7 / 10 / 7) gives 47 of 48 none at 7^3 on the fixed engine: those settings were tuned on the
scrambled networks and are not used.

**Class fractions, 7^3, lambda 0.4** (spiking: 24 of 24 ignition; 95 % Clopper-Pearson intervals: ignition
[0.858, 1], contained and none [0, 0.142]):

| model B | contained | ignition | none | within the intervals |
|---|---|---|---|---|
| own networks, realizations 0 and 1 (48) | 1 | 46 | 1 | yes |
| the rerun's exported networks (24) | 1 | 23 | 0 | yes |

Below the step's `gain_ee_inter` 2.4, model B's own networks (one realization, 24 pairs) give 2 contained at 2.0,
1 at 1.6 and 6 at 1.2 (the rest ignition): contained first transfers appear only well below the step's setting.

**Engine's own wiring, 7^3** (step 5, `gain_ee_inter` 1.2, exported networks, first transfer only): spiking
14 ignition / 10 none, model B 11 / 1 contained / 12 none; fractions within the intervals; per pair agreement
0.67, kappa 0.36. 12 of the 24 model runs were stopped as runaways (`runaway_round`).

**Learning, pair by pair on the exported networks** (same network, pair and injected neurons in both):

| comparison (24 pairs) | spiking | model B | agreement | kappa |
|---|---|---|---|---|
| 7^3 first transfer | 24 ignition | 23 ignition, 1 contained | 0.96 | 0 (spiking one class) |
| 7^3 associations, activity-dependent C2 | 15 | 16 | 0.79 | 0.55 |
| 7^3 associations, uniform C2 | 0 | 1 | 0.96 | 0 (spiking one class) |
| 9^3 (d 4) first transfer | 24 ignition | 24 ignition | 1.00 | (one class) |
| 9^3 (d 4) associations, activity-dependent C2 | 11 | 1 | 0.58 | 0.10 |

Strays at the first transfer agree closely: the absolute difference has median 2 at both sizes (within 5 strays:
16 of 24 pairs at 7^3, 19 of 24 at 9^3; equal: 2 and 7). At 9^3 model B associates only `s0p0`, which the spiking run
also associates; it never associates a pair the spiking run does not (confusion: 1 / 10 / 0 / 13).

**Admission (Substep 3), no fitted parameter:**

- Class fractions (7^3): pass, on 2 realizations instead of the default 5 (both are the rerun's networks).
- Grid size: **fail.** The spiking first-transfer class is the same at 7^3 and 9^3 (all ignition) and model B
  reproduces that; the spiking associations fall from 15 to 11 of 24, model B's from 16 to 1.
- Uniform C2: pass (spiking 15 -> 0 associations, model B 16 -> 1).

Model B is therefore not admitted at these settings; per Substep 3 it is not used for screening. Possible reason,
not tested: at 9^3 the spiking associations end with 24 to 33 strays against the limit of 34 (7^3: 8 to 32,
median 16), so the 9^3 count depends on small differences in the last rounds. Model B's rows record only the
first transfer's strays, so how far its 10 missed pairs lie above 34 is not known. Next steps (user decision):
record the final strays per pair and rerun 9^3 (about 1.2 h on one GPU pod); or fit up to three parameters
of the learning stage (Substep 3) on seed 0's pairs.

Cost: pod `xt2eohm6688yx9` (`rm6-precheck`), RTX PRO 4500 Blackwell, $0.72/h: pre-check at the archived regime,
the lambda 1.0 exports and checks (lambda 1.0 later dropped by the rerun's step 3; its 9^3 single-group response
ran out of memory and was not repeated), the 7^3 runs above; $2.18 (billing), including about 15 idle minutes
after a host-session restart. Pod `qcf0q3v2m60w7i` (`rm6-grid`), RTX 4090, $0.89/h (the Blackwell types had no
capacity): the 9^3 exports and model B (a first run with 32 workers ran out of memory; rerun with 12, 72
minutes), 16:06 to about 17:31 UTC, about $1.26 (estimated; billing at termination showed $0.33 and lags).
Both terminated after the download (delete 204, `list-pods` empty). Round 6 after the engine fixes: about
$3.59; with the two pods before the fixes about $3.86, **above the round's [default] limit of $3**.

### Final strays (2026-10-31)

Model B as above, rerun on new exports of the same networks with the final tests' strays recorded per pair and
direction (`round6_regime_precheck.py` rows, `final`; session `round6_strays_pod.sh`; results in
`output-round6-strays/`, gitignored). Spiking side: the per-job results of steps 5 and 6 (`final`, `c2_rounds`,
`c2_runaway_round`). Per pair, "best final strays" is the smaller stray count of the successful final tests (an
association needs one at most 34).

| | 7^3 | 9^3 |
|---|---|---|
| associations, spiking / model B | 15 / 16 | 11 / 2 |
| first transfer strays, model B minus spiking, median | 2 | 2 |
| best final strays, model B minus spiking, median (range; pairs with a successful final test in both) | 4 (-23 to 17; 23 pairs) | 12 (-107 to 80; 20 pairs) |
| C2 stage: same number of rounds in both | 24 of 24 | 20 of 24 |

- **The C2 stage is the same in both.** In both implementations the first C2 round ends in a runaway stop for most
  pairs (7^3: 20 of 24 in both; 9^3: 23 spiking, 21 model B; the final tests then run on the state after that
  round), and at 7^3 the pairs that run all 5 rounds without a runaway are the same.
- **At 9^3 model B's final strays are about 12 higher than the spiking ones; at 7^3 about 4.** Of the 9 spiking
  associations it misses, 7 end just above the limit (37 to 45 strays, spiking 24 to 33) and 2 far above it
  (`s0p9` 113, `s1p2` 64). The first transfer agrees at both sizes (median difference 2), so the excess builds up
  after it, in the C2 round with its consolidation or in the final tests (no joint round follows the first
  transfer), and it grows with the lattice.
- Model B is not reproducible run to run on identical inputs: on the same networks the first run gave 1
  association at 9^3 (`s0p0`), this one 2 (`s0p6`, `s1p4`; `s0p0` now 37 strays); at 7^3 16 both times.
  Parallel float summation is the likely cause (not checked).

So the 9^3 failure is mostly a near-miss: a systematic excess of about 10 final strays, growing with the size.
A fit (Substep 3) needs a parameter that acts after the first transfer: of model B's three free parameters,
`learn_scale` acts on the learning before it as well and `w_inh_scale` and `w_inter_scale` on the first transfer,
which now agrees. Not yet decided (user).

Cost: pod `qf0ofpysmtt5b3` (`rm6-strays`), RTX PRO 4500 Blackwell, 28 vCPU (cgroup limit 23.8), 62 GB, $0.72/h,
00:50:34 to about 01:38 UTC, about $0.58 (estimated; billing not yet posted); a first launch stopped on a params
file missing from the bundle (about 5 minutes). Three pods created and deleted within a minute before it, while
choosing a type (`free` and `nproc` inside the container report the host's resources, not the pod's): about
$0.03. Round 6 after the engine fixes: about $4.20; with the two pods before the fixes about $4.47.
