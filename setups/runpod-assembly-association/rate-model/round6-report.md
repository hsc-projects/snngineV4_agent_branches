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

**Summary.**
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
  overwrites E -> E weights (`w_ee`), not E -> I. Not fixed (needs approval).
- With the configured composition, a single injected group drives about 870 to 960 spikes instead of about 415
  to 470 (model B with the configured composition predicted 954.5 at 9^3, step 1): the spiking protocol was
  tuned on the scrambled network and will need re-tuning.

Cost: pod `e60j55jyp3xsda` (`rm6-fixtest`), RTX PRO 4000 Blackwell, EU-RO-1, $0.57/h, 00:02 to 00:08 UTC
(2026-10-30), about $0.06 (estimated); terminated (delete 204, `list-pods` empty).
