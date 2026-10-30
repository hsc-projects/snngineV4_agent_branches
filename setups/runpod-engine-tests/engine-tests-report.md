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

Test-suite errors fixed during the runs (no engine change): file ownership when unpacking a pack made on Windows;
apt cannot lock a folder on the network volume (the package cache is now copied around a local apt cache); STDP
probe neurons that chatter (a burst after one forced spike) gave extra updates (now regular-spiking neurons only,
spike counts checked); STDP probes started before the engine enables STDP (t > 20); the distance-profile threshold
was too weak to detect the old construction; exact rounding ties (x.5) in the delay table (float32 in the engine,
float64 in the check); one failing configuration erroring other configurations' cases and probe results lost when
the probe script crashed late (results now saved before the risky probes, failures cached).
