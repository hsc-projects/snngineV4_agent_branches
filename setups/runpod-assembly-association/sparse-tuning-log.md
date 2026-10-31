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
