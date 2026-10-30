# Engine test runs

One entry per run of `snngine_v4/tests/` on Runpod (`README.md`): code state, pod, duration, cost, results.
Raw logs and summaries are in `results/<run>/` (gitignored).

## 2026-10-30: first runs, committed engine against the fixed working tree

Code: `head` = engine at commit a102f3d (before the fixes) with the working tree's tests; `worktree` = the working
tree with the uncommitted engine fixes (synapse-table transpose, initial weights by type pair, bounded synapse-count
correction, autapse-search offset, presynaptic index built and guarded against deleted synapses, removal index,
STDP bound by presynaptic type, chemistry kernel, spike-buffer rewind threshold and size). Pods `1u1c7is6g87smq`
(head) and `y69hsoavo8wh0c` (worktree), RTX PRO 4000 Blackwell (SM 120), EU-RO-1, $0.57/h each, 01:19 to about
01:53 UTC, about $0.63 together (estimated from the lifetimes); terminated (delete 204, `list-pods` empty).

Measured: build tools 20 s; CUDA build 55 s (then from the cache in about 1 s); `quick` tests about 95 s; `full`
tests about 160 to 170 s.

Final runs (after the test-suite fixes below):

| run | level | result |
|---|---|---|
| `worktree-q4` | quick | 49 tests, OK |
| `worktree-f2` | full | 49 tests, OK |
| `head-q3` | quick | 22 failures, all expected |
| `head-f2` | full | 41 failures, no errors, all expected |

What the committed engine fails (and the fixed one passes), by configuration:

- construction, all sizes (small, odd, 7^3, 9^3): synapses per target type, delays, autapses, initial weights by
  type, distance profile (near/far ratio 1.3 to 1.8 against at least 3; fixed engine 10 to 13);
- 9^3 only: count tables (negative delay buckets) and delay buckets;
- presynaptic index not built with the network (small, odd, D 16);
- STDP potentiation of an inhibitory weight bounded by the excitatory bound (small, odd, D 16);
- spike buffer at D 16 and 90 % activity: wrong delivered currents (`test_delivery_under_near_total_activity`);
  in the first full run the old engine ended in an illegal memory access in `update_current_`;
- removal: rebuilding the presynaptic index after a removal ends in an illegal memory access (deleted-synapse
  index -2 used as a neuron index), so the removal results are missing (all removal tests).

Passed by both engines (no difference between them shown): delivery probe, dynamics against the numpy reference,
excitatory STDP pairs, unconfigured pair, chemistry (one and ten steps, determinism, mass, point source, also on a
grid of 30), thalamic and sensory input. The chemistry kernel's defects found by reading (in-place update read by
other blocks, `__syncthreads` in a branch, border cell overwritten for grids not a multiple of 8) did not show at
these grid sizes; the rewritten kernel passes the same tests.

Found by the tests, not fixed: the engine's construction refuses an elongated reservoir (6 x 1 x 1, D 4) with its
own check that autapse candidates appear only at delay 0 (`synapses.py`, after `fill_N_rep`), on both engines; the
configuration is left out (`test_engine.py`), so the autapse-search fix in `connector.cu` is not exercised.

Resolved in the next entry: the elongated reservoir, and a chemistry test that the old kernel fails.

Test-suite errors fixed during the runs (no engine change): file ownership when unpacking a pack made on Windows;
apt cannot lock a folder on the network volume (the package cache is now copied around a local apt cache); STDP
probe neurons that chatter (a burst after one forced spike) gave extra updates (now regular-spiking neurons only,
spike counts checked); STDP probes started before the engine enables STDP (t > 20); the distance-profile threshold
was too weak to detect the old construction; exact rounding ties (x.5) in the delay table (float32 in the engine,
float64 in the check); one failing configuration erroring other configurations' cases and probe results lost when
the probe script crashed late (results now saved before the risky probes, failures cached).

## 2026-10-30: elongated reservoir, chemistry on a large grid

Code: `wt3`/`wt4` = commit cc68e7a plus the empty-delay fix in the autapse search (`connector.cu`,
`set_local_typed_delay_repr_idx_kernel`: a source group without target groups at a delay has no autapse there);
`old` = engine at a102f3d (`pack_tree.sh head ... a102f3d`) with the current tests; `mut` = `wt3` without the
`Ng_prev` update in the same function (mutation check). Tests: `elongated` (6 x 1 x 1, D 4) enabled and added to
`quick`; the `small` probes' chemistry grid raised from 32 to 96 cells. Pods `7plq91xhi7aigr` (fixed),
`l1tgmrg4ecfbvb` (old), `pkh1vrg9kdxqi2` (mutation), RTX PRO 4000 Blackwell, EU-RO-1, $0.57/h each, from 04:33 UTC.

| run | code | configurations | result |
|---|---|---|---|
| `fixed-f3` | `wt3` | full | all pass except the `small` probes (grid 128, see below) |
| `fixed-small4` | `wt4` | small | 49 tests, OK |
| `old-a102f3d-3` | `old` | small, elongated | elongated: construction refused (`synapses.py:367`) |
| `old-a102f3d-4` | `old` | small (grid 96) | 15 failures, including four chemistry tests |
| `mut-ngprev` | `mut` | elongated | `targets_valid`: 219 autapses |

Cause of the refusal: for a source group whose largest delays have no target groups (a central group of an
elongated grid), the autapse search read `G_rep` from the next delay's or the next row's first entry; when that
entry was the source group itself (a neighbour at delay 0 of the next group), it reported an autapse candidate at
that delay, and the construction's own check stopped the build. With the fix the elongated network builds and
passes every invariant; without the `Ng_prev` update it contains autapses, so both fixes in that function are now
tested.

Chemistry: a grid of 128 cells is refused by the engine itself (`finite_grid.py:150`, positions must stay below
`max_z = 100`), so the probe uses 96 cells (1728 blocks of 8^3, more than the GPU runs at once). The old kernel,
which updated `C_old` in place while other blocks read it as their border, fails: one step 8.2 % of cells wrong
(by up to 22.6 on values of 0 to 100), two identical runs of ten steps differ in 86.7 % of cells (up to 1.47),
ten steps 74 % wrong, the point source likewise. The rewritten kernel passes. The other two defects of the old
kernel (barrier inside a branch, border cell of grids not a multiple of 8) still show no effect at grid 30.

After a review of the suite (same day, pod `7plq91xhi7aigr`, 04:33 to about 04:54 UTC; all three pods about
$0.35 together, estimated from the lifetimes; terminated, `list-pods` empty): the chemistry kernel's x now runs
along depth, the contiguous index (blocks of 32 x 4 x 4; before, a warp's loads were 8 cells apart in memory);
the delivery probe draws regular-spiking neurons only (a chattering neuron would fire a second time); probe and
export folders are cleared before a build; a reused run name no longer reads the previous run's `finished`
marker. `fixed-f5`: full, 49 tests OK (231 s); the same run name again with `quick`: 49 tests OK.

## 2026-10-30: step-by-step dynamics, non-cubic chemistry grid

Two tests suggested by an independent review. `test_engine.Dynamics.test_neuron_update_every_step` and
`test_delivery_every_step` check every step of the injected run from the engine's own state, input and spikes
(the export now records them), so rounding does not accumulate and the whole run is checked; `test_reference`,
which stops at the first step where the free-running spike sets differ, now prints that step. The `odd` probes use
a chemistry grid of 30 x 22 x 38 (`AssocEngine(engine_chem_shape_hwd=...)`, `engine_probes.py --chem-shape`), so
a mixed-up width and depth in the kernel's indexing or launch shows; a cube cannot tell them apart.
`pack_tree.sh` packs the working tree's harness with `HARNESS=worktree` (the harness change was not committed).

Pods `4vsns8xw1ab51i` (fixed) and `v1nq8p4axdhrco` (mutation), RTX PRO 4000 Blackwell, EU-RO-1, $0.57/h each,
07:22 to about 07:28 UTC, about $0.12 together; terminated, `list-pods` empty.

| run | code | level | result |
|---|---|---|---|
| `fable-f6` | working tree | full | 51 tests, OK; the free-running spike sets never differed within 100 steps (all five configurations) |
| `fable-mut2` | working tree with two mutations | quick | 8 failures, as intended |

Mutations: the neuron update `u += a (b v - u)` plus 0.02 every step, and the chemistry launch's width and depth
swapped back. The neuron-update mutation fails `test_neuron_update_every_step` in all three configurations (every
neuron, by 0.02), while `test_reference` fails only for `odd`: in `small` and `elongated` the spike sets first
differed at steps 22 and 21, beyond its step-20 limit, so it passed. The launch mutation fails four chemistry tests
on the 30 x 22 x 38 grid (one step: 15.8 % of cells wrong, by up to 74.7) and none on the 96^3 cube.

## 2026-10-30: commit f051b62 before its deployment to the network volume

Code: `pack_tree.sh head` at f051b62 (engine and tests as committed; step 0 of
`runpod-assembly-association/engine-fix-rerun-task.md`). Pod `nf30u221xzjwmt`, RTX PRO 4000 Blackwell, EU-RO-1,
$0.57/h, shared with the deployment (cost in `runpod-assembly-association/engine-fix-rerun-report.md`).

| run | code | level | result |
|---|---|---|---|
| `rerun0-f051b62-full` | f051b62 | full | 51 tests, OK (162 s; 236 s with the CUDA build, no cached build for its source hash) |
