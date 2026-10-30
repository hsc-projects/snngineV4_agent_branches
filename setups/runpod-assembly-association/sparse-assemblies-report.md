# Sparse assemblies on distance-dependent wiring: report

Report of `sparse-assemblies-task.md`. Per-step details are in `sparse-tuning-log.md`; raw results in
`output/sp*` (gitignored).

## Substep 0: field geometry and new options

**Field-geometry check (done, `sparse-tuning-log.md` entry 1).** A linear C1 field from A and B
does not single out the route middle: C in M is at most 1.5 times C in the off-route shell, at any
diffusion length from 1 to 4 cells, so the stop rule's first branch applies. Read through a threshold
at the level where the regions around A and B first connect (always along the segment), the field
opens 2.4 to 3.3 times more of M than of Sh on 11 x 11 x 11 at d 4 after about 30 rounds (best at a
length of 3 cells), 1.6 to 2.2 at d 6, and only about 2 on 7 x 7 x 7, where A and B lie near the
surface. L4 is kept; C1 for L2 to L5 defaults to a length of 3 cells (k 0.16, decay 0.0011). C2's
settings keep it a marker (0.36 cells).

**New options for Substeps 1 and 2** (`sparse-tuning-log.md` entry 3): S2 to S5, the hysteresis test,
the single-synapse threshold job, `c1.uniform` and K5; 72 module checks pass on CPU and GPU. The L and
K options are not yet written.

## Substep 1: baseline

Sparse assemblies (lattice spacing 2, 7 x 7 x 7) activate under injection and nothing fires without
it; one assembly in five spills into a neighbour at lambda up to 1.0. The single-synapse threshold is a
one-step current of 19.5, a normalized inter-group E -> E weight of 8.1 (162 times the baseline 0.05).

## Substep 2: substrate (stop rule reached)

No substrate shows summation in the route middle (entry 4). At every connection length the excitatory
neurons there receive 60 to 100 times more inhibition than excitation under joint injection; excitation
from A and B adds linearly but stays far below threshold. Heavy-tailed weights (S2, S3b at lambda 1.0)
make the route middle fire a little, but as much under A or B alone, and S3b at lambda 0.4 ignites the
reservoir; S4 and S5 change nothing against that inhibition. The ordinary substrate is not all-or-none
(small hysteresis loops).

**Alternative form tried (S6, weaker inhibition between groups; entry 5).** Lowering inter-group
E -> I or I -> E to as little as 5 % cuts the inhibition onto the route middle tenfold, but the
excitation reaching it from A and B (0.2 to 0.3 per step against 19.5 needed by one synapse) still
fires nothing; with heavy-tailed weights (S2) the route middle fires as much under one assembly alone
and off the route; S3b activates the reservoir. **Result of Substep 2: no substrate shows summation;
the stop rule holds.** Per the task, the substrate needs a change outside these variants (for example
conductance-based synapses with slower excitation than inhibition, Chambers & MacLean 2016, which need
new kernels).

## Cost

| Session | Pods | Cost (estimated from lifetime) |
|---|---|---|
| sp0 field geometry | 2 CPU pods (cpu3c, 16 vCPU, EU-RO-1, $0.48/h), about 7 and 5 minutes | about $0.10 |
| sp1, sp2 substrate | 1 GPU pod (RTX PRO 4500 Blackwell, EU-RO-1, $0.72/h), about 38 minutes | about $0.45 |
| sp3 inhibition (S6) | 1 GPU pod (RTX 4090, EU-RO-1, $0.89/h), about 13 minutes | about $0.20 |
| **Total** | | **about $0.75 of $25** |
