# Report: assembly association on the corrected engine

Report of `engine-fix-rerun-task.md`: one section per step; the sessions are in `engine-fix-rerun-log.md`. At the
end, conclusions A1 to A8 of the task, each as holds, changes or falls. The wiring decisions that steps 2 to 5
left to the user are recorded in revision 8 of `runpod-assembly-association-task.md`; the sparse task's decisions
after step 7 in `sparse-assemblies-task.md`, "Rules".

## Step 0: corrected engine on the network volume (2026-10-30)

Done. The volume's checkout `/workspace/snngineV4_cloud/snngineV4_agent_branches` is now a git clone of
`docs/runpod-pi-setup` at f051b62 (from a bundle; `git status` clean). It replaced an uploaded, non-git copy
with engine files from 2026-09-29, kept as `snngineV4_agent_branches.pre-f051b62` without its backend builds.

| check | result |
|---|---|
| engine tests on f051b62 (`full`, run `rerun0-f051b62-full`) | 51 tests OK |
| backend build on the volume (`runpod_assembly_runner.sh env`) | SM 120, built afresh in 81 s; imported from the clone |
| module checks (`test_assoc_modules.py`) | 73 / 73 on CPU, 73 / 73 on CUDA |

The volume holds a backend build for SM 120 (Blackwell) only. The first session on another architecture
(RTX 4090 or L4, SM 89) builds its own, so such a batch starts with one pod, not several (parallel first
builds race over `build`).

Cost: about $0.10 (one pod, about 10 minutes at $0.57/h, estimated).

## Step 1: build audit (2026-10-30)

Passed. The harness's builds on the volume (7^3, 9^3 and 11^3, the last added by the user; each unrewired and
rewired at lambda 0.4; seed 0) satisfy every invariant of `snngine_v4/tests/network_invariants.py`: every
excitatory neuron has 1600 synapses onto excitatory and 400 onto inhibitory neurons, every inhibitory neuron 2000
onto excitatory and none onto inhibitory neurons; no autapses; every delay follows round((D - 1) d / d_max)
(exact x.5 ties may round either way); E -> E synapses per group pair fall with distance. 11^3 can be used in
step 6. Details and the per-build table: `engine-fix-rerun-log.md`, step 1.

For step 2: the engine's own wiring at 7^3 gives 515, 336 and 119 E -> E synapses per group pair at 1, 3 and 6
cells (the figures of A1), but only 8 to 13 E -> E synapses per excitatory neuron within its own group, against
810 to 860 with rewiring. In the unrewired 9^3 and 11^3 builds the corner-to-corner pairs hold more synapses
than the next distance (not explained).

Cost: about $0.09 (one pod, about 9 minutes at $0.57/h, estimated).

## Step 2: wiring (2026-10-30)

Measured at 7^3 and 9^3, network seeds 0 and 1, on the engine's own wiring and rewired at lambda 0.4 and 1.0
(sessions `rerun2a` to `rerun2d`; numbers in `engine-fix-rerun-log.md`, step 2).

| | engine's own | rewired, lambda 1.0 | rewired, lambda 0.4 |
|---|---|---|---|
| effective lambda (cells) | 3.8 (7^3), 4.0 (9^3) | 1.1 | 0.42 to 0.46 |
| E -> E per group pair at 1 / 4 cells (7^3) | 457 / 222 | 1495 / 95 | 1316 / 2 |
| intra-group E -> E per excitatory neuron, median (min to max) | 10 to 13 (6 to 18) | 103 to 123 (50 to 333) | 809 to 846 (512 to 1277) |
| spread at gain 2 to 8 | 0 | 0 | 0 |
| spread at gain 12 / 16 / 24 (cells) | 0 to 5 / 0 to 7 / 4 to 9 | 0 to 1 / 0 to 2 / 1 to 5 | 0 to 1 / 0 to 1 / 0 to 2 |

The engine's own wiring keeps activity inside the injected group up to gain 8; above that, activity reaches
across much of the grid. No gain run gives it a consistent spread of one or two cells: at gain 12 most injected
groups stay alone and the others reach 1 to 5 cells, at gain 16 most reach 3 to 7. Rewired at lambda 0.4, activity stays within one or two
cells at every gain run; at lambda 1.0 within one to five. The regime itself (inhibitory gains, inter-group
gain, intra-group total) is tuned only in step 3, so these spreads compare the wirings at the archived values
of everything but `gain`.

**A1** ("the engine's connectivity is practically flat in space"): **falls.** The corrected engine's E -> E
synapses per group pair fall with distance, with an effective lambda of about 4 cells (7^3: 457 at 1 cell, 73
at 8 cells). Its reach is still about ten times that of rewiring at lambda 0.4.

**A2** (intra-group density varies about threefold, a candidate artifact of bug 1): **changes.** The density
varies about 2.5-fold between groups in the engine's own wiring (6 to 18 synapses per excitatory neuron) and at
lambda 0.4 (512 to 1277), and 5- to 6.6-fold at lambda 1.0, so the variation is not an artifact of bug 1. In the
engine's own wiring the density is about 80 times lower than with rewiring at lambda 0.4.

**Decision (the user's).** The options of the task: the engine's own wiring, rewiring with a chosen lambda, or
later a connection-range parameter in the engine's construction (a core change, its own task).
Recommendation: keep rewiring, now on its own merits rather than because of bug 1: the engine's own wiring
has no gain at which activity stays within a cell or two, which distinct routes need, and it gives assemblies
almost no recurrent synapses. Keep lambda 0.4 as the baseline of steps 3 to 7 (the archived protocol, its
distances and the rate model's exports use it) and run lambda 1.0 as a variant in step 3, since its wider
reach may let A -> B transfers over 4 cells work at lower gains. *(Revised by step 3: with the inter-group
gain raised instead of the global gain, the engine's own wiring has a regime as contained as rewiring's; the
statement "no gain at which activity stays within a cell or two" holds only for the global gain of step 2.)*

Cost: about $0.29 (one check pod, about $0.05; four session pods, about $0.24; estimated).

## Step 3: operating regime (2026-10-30)

Run on the three wirings the user chose (revision 8): 7^3, network seeds 0 and 1, 42 configurations each of gain,
`gain_ee_inter`, `gain_ie` and the intra-group total; per configuration Substep 1 on 100 groups and the
saturated-path diagnostic (6 pairs at d 4 and at d 6). A regime passes when nearly every group is recruited
without spill and a path at the upper weight bound transmits while an untrained one does not (the archive's
criteria). Numbers in `engine-fix-rerun-log.md`, step 3, and `output/rerun3-summary.txt`.

| wiring | passing regimes (both seeds) | width of the passing region |
|---|---|---|
| engine's own | gain 4, `gain_ee_inter` 1.2 or 2.4: Substep 1 99 to 100 / 100, saturated path 6 / 6 at d 4 and d 6 | every `gain_ie` (2 to 8) and intra total (20, 40) |
| rewired, lambda 1.0 | gain 4, total 40, `gain_ee_inter` 1.2 or 2.4: 97 to 100, 6 / 6 | `gain_ie` 2 or 8 at 1.2, every `gain_ie` at 2.4 |
| rewired, lambda 0.4 | gain 4, total 40, `gain_ee_inter` 2.4 (`gain_ie` 2, 4) or 1.2 (`gain_ie` 2): 98 to 100, 6 / 6 | narrower: total 20 under-recruits, `gain_ie` 4 and 8 block at 1.2 |

Every wiring has a regime that meets the archive's criteria. The engine's own wiring has the widest one; its
failure, when the gains are pushed further (`gain_ee_inter` 4.8, or gain 8 with stronger inhibition), is
wide-range spill (6 to 10 cells) and, at gain 8, runaways, where the rewired networks spill one to five
cells. The diagnostic sets path weights to their upper bound: whether learning reaches such weights, and
whether untrained routes stay selective, is for steps 4 and 5.

**A3** (the regime tuned on the faulty engine: gain 4, `gain_ie` 2, `gain_ee_inter` 0.6, intra total 40):
**changes.** It still recruits single groups without spill (98 to 100 of 100) in every wiring, but a saturated
path transmits in at most 1 of 6 pairs at d 4 and in none at d 6; the inter-group gain has to be about doubled
(1.2 to 2.4).

**For the user (wiring of steps 4 to 7).** Proposal: take two wirings into step 4, the engine's own (gain 4,
`gain_ee_inter` 1.2, `gain_ie` 2, total 40: the middle of its passing region) and rewiring at lambda 0.4 (gain
4, `gain_ee_inter` 2.4, `gain_ie` 2, total 40: continuity with the archive and the rate model's exports), and
drop lambda 1.0, which lies between the two without a property of its own in these measurements.

Cost: about $1.41 (six session pods, about 15 to 24 minutes each, and a summary pod; estimated). Rerun so far:
about $1.89 of the $20 cap.

## Step 4: propagation survey (2026-10-30)

Run on all three wirings (the user's choice): 7^3, network seeds 0 and 1, `prop_survey` on 12 pairs at d 4 per
configuration, gain 4, intra total 40, `gain_ee_inter` 0.6 to 3.6 x `gain_ie` 2, 4, 8, no learning, no
chemistry. Numbers in `engine-fix-rerun-log.md`, step 4.

| wiring | `gain_ee_inter` 0.6 to 2.4 | `gain_ee_inter` 3.6 |
|---|---|---|
| engine's own | every pair silent (median M 0.00) | 2 to 8 of 12 pairs explosive, 1 good pair per seed at `gain_ie` 8 |
| rewired, lambda 1.0 | silent; at `gain_ie` 8 up to 3 pairs weakly active (M 0.05 to 0.2) | silent or weakly active (up to 5 pairs); 2 explosive at one seed |
| rewired, lambda 0.4 | silent; at `gain_ie` 8 one pair weakly active | silent; at `gain_ie` 8 one pair weakly active |

Without learning, joint activation of A and B does not make the neurons between them fire in any wiring within
the regime region of step 3 (`gain_ee_inter` 1.2 to 2.4); the route has to be built by learning. Beyond that
region the engine's own wiring jumps from silent to explosive, pair by pair; the rewired networks stay silent or
weakly active.

**A4** (all-or-none propagation with pair-dependent thresholds; pairs 3 and 5 never transfer, 1, 8 and 10
easily): **changes.** On the corrected network no pair propagates untrained in the regime region, in any
wiring: there are no easy pairs. The all-or-none, pair-dependent jump remains only in the engine's own wiring,
above the regime region (`gain_ee_inter` 3.6). Whether learning then transfers some pairs more easily than
others is for step 5.

**For the user (wiring of steps 5 to 7).** Step 4 does not separate the wirings inside the regime region (all
silent untrained); it shows again the engine's own wiring's sharper failure beyond it. The proposal of step 3
stands: step 5 on the engine's own wiring (`gain_ee_inter` 1.2) and on rewiring at lambda 0.4
(`gain_ee_inter` 2.4), without lambda 1.0.

Cost: about $0.40 (three pods, about 12 minutes; estimated). Rerun so far: about $2.29 of the $20 cap.

## Step 5: protocol and uniform-C2 control (2026-10-30)

Run on the engine's own wiring and rewiring at lambda 0.4 (the user's choice), in their step 3 regimes, 7^3, 24
pairs at d 4 (network seeds 0 and 1); the protocol with controls as s69a and the uniform-C2 control as s76.
Numbers in `engine-fix-rerun-log.md`, step 5, and `output/rerun5-summary.txt`.

| | rewired, lambda 0.4 | engine's own |
|---|---|---|
| associations passing every control | **15 of 24** | **0 of 24** |
| transfers in the C1 phase | 24 (strays about 180) | 14 (strays about 200) |
| with C2 uniform (1.2 / 0.9) | 0 / 0 (every transfer unbounded) | 1 / 0 |

With rewiring at lambda 0.4, every pair transfers within three joint rounds, at first with about half of
the reservoir active; the short circuit stage then narrows 15 transfers to bounded associations (median 16
strays, every one at most half its C1-phase strays). Held uniform, C2 narrows none. Without chemistry no pair
transfers, and A and B trained in separate rounds never associate. The engine's own wiring transfers in 14
pairs, with about 200 strays, and the short circuit stage narrows none.

**A6** (archived items, on the faulty engine): **changes.**
- Item 2 (associations in a quarter to a third of the pairs, 6 of 24): **changes**: 15 of 24 at lambda 0.4.
- Item 3 (the associations need joint activation): **holds**: the separate-rounds control never associates
  at lambda 0.4.
- Item 6 (the outcome is fixed in the joint rounds; the short circuit stage keeps or loses the first transfer
  with its strays): **falls**: the stage narrows every association, from about 180 strays to about 16.
- Item 13 (C2 carries no spatial information; uniform C2 gives the same associations): **falls**: with C2
  uniform no pair associates; the spatial pattern of C2 is what narrows the transfer.
Items 7 and 10 to 12 depend on variants (C3 fuel, rollback, depression, local inhibition) not rerun here.

**For the user (wiring of steps 6 and 7).** Proposal: rewiring at lambda 0.4 only. The engine's own wiring
forms no association in 24 pairs; its transfers spread and the chemistry does not narrow them.

Cost: about $1.39 (four pods, 30 to 40 minutes; estimated). Rerun so far: about $3.68 of the $20 cap.

## Step 6: grid comparison (2026-10-30)

Rewiring at lambda 0.4 in its step 3 regime, the passing protocol without controls (as s71 and s73), 24 pairs per
row over network seeds 0 and 1, a strays limit of 34 groups at every size, pairs at least 2 cells from the
surface at 9^3 and 11^3. Numbers in `engine-fix-rerun-log.md`, step 6.

| | 7^3 | 9^3 | 11^3 |
|---|---|---|---|
| d 4: associations | **15 of 24** (step 5) | **11 of 24** | **0 of 24** |
| d 4: strays at the C1-phase transfer, median | 180 of 343 groups | 426 of 729 | 853 of 1331 |
| d 6: associations | 1 of 24 (4 transfers) | 0 of 24 (11 transfers) | not run |

At d 4 every pair transfers within three joint rounds at every size, each time with about half of the reservoir
active; the short circuit stage then narrows the transfer to the strays limit in 15 pairs at 7^3, in 11 at 9^3
(to 24 to 33 strays, close to the limit) and in none at 11^3. At d 6 few pairs transfer at all.

**A5** (item 9: the ignitions are a finite-size effect; at 9^3 no transfer ignites and B mostly stays silent):
**falls.** On the corrected network every transfer at d 4 is an ignition at every size, 9^3 and 11^3 included;
the associations come from the short circuit stage narrowing it, which works at 7^3 and 9^3 and fails at 11^3.

**Item 12** (every change that removes ignitions removes most transfers; reach has needed spread over the
reservoir): **holds in a changed form**: no transfer here comes without an ignition, but the chemistry turns
many ignitions into bounded associations, up to 9^3.

Cost: about $1.16 (two pods, about 54 minutes each; estimated).

## Step 7: sparse substrate SP1 to SP3 (2026-10-30 and 31)

The archived generators, unchanged (the sparse layout, lattice spacing 2, on the settings of
`session69a-stage2.json`), lambda 0.4 to 1.5. Numbers in `engine-fix-rerun-log.md`, step 7.

- The single-synapse threshold is unchanged: a normalized inter-group E -> E weight of 8.125 (the isolated-neuron
  scan does not depend on the wiring).
- The excitation reaching the route middle under joint injection is as before (0.16 to 0.27 per step); the
  inhibition is about three times stronger (-56 to -67 against -18 to -23), so the ratio is 200 to 350, not 60
  to 100: the corrected network has its configured E -> I synapses.
- S0, S1, S3a, S4, S5, and S6 on S0: no excitatory neuron in the route middle fires. S2 (with or without S6):
  it fires a little, as much under A or B alone and off the route. S6 on S3b activates the reservoir.
- S3b alone (lognormal weights, Teramae's ratio of mean to threshold) now leaves the reservoir quiet (on the
  faulty engine it activated it at lambda 0.4), and the route middle fires slightly more under joint injection
  than under A and B alone together and than off the route (0.012 against 0.009 and 0.006 at lambda 0.4; 0.037
  against 0.028 and 0.024 at lambda 1.0): a weak sign of summation, at about one spike per 30 to 80 neurons
  and round, its uncertainty not computed.

**A7** (60 to 100 times more inhibition than excitation, no substrate showing summation, hence the stop rule):
**changes.** The inhibition dominates even more (200 to 350 times); S0 to S6 still show no summation, except a
weak one in S3b, which the faulty engine had hidden behind a reservoir-wide activation. On 48 pairs (below)
it holds at lambda 1.0, not at 0.4; the sparse task's stop rule does not apply, and its Substep 3 runs on S3b
with a milder S6 (below; `sparse-assemblies-task.md`, "Rules").

Cost: about $0.63 (the session pod, about 48 minutes, and a summary pod; estimated). Rerun so far: about $5.47
of the $20 cap.

**S3b decision (2026-10-31; 48 pairs over two seeds, the decision rule fixed before the run, log "Step 7, S3b
decision").** At lambda 1.0, S3b sums: in 30 of 41 untied pairs the route middle fires more under joint injection
than under A and B alone together (Wilson 95 % 0.58 to 0.84; both seeds alike), and in 43 of 48 more than off the
route (0.78 to 0.96). The effect is small: medians 0.041 against 0.037 (A + B) and 0.025 (shell) spikes per
excitatory neuron and round. At lambda 0.4 it does not sum (8 against 18, 22 ties); step 7's sign there came
from 12 pairs. The keep rule of Substep 2 also asks for a hysteresis loop narrower than S0's: at lambda 1.0
neither S3b nor S0 shows a loop, so S3b's is no wider but not narrower. The loop measure is also not
reproducible on one network (S3b at lambda 0.4, seed 0: 0.195 in step 7, 0.010 now). The user kept S3b at lambda
1.0 (2026-10-31; superseded by the screening below). Cost about $0.20; rerun so far about $5.67.

**S3b screening (2026-10-31; the Substep 2 variants not yet run on S3b, log "Step 7, S3b screening").** S4 on S3b
activates the reservoir and S5 on S3b silences the route. Milder S6 on S3b (inter-group I -> E or E -> I gain 0.5
or 0.7) sums in every form; the two at 0.5 passed the 48-pair decision: with I -> E 0.5, 42 of 47 untied pairs
(Wilson 95 % 0.77 to 0.95, median difference 0.014 spikes per excitatory neuron and round, twice S3b's), route
selectivity 45 of 48; with E -> I 0.5, 39 of 45 (0.74 to 0.94). No form sums beyond 4 lambda: S3b and S3b with
I -> E 0.5 show no significant summation at lambda 0.6 (6.7 lambda), and at 11^3, d 10 (10 lambda, the distance
the sparse task compares at) the route middle barely fires (0.001). So the substrate's summation is local; an
association at 10 lambda would have to be carried by learning, not by the substrate. The hysteresis job of S3b at
lambda 0.6 stopped with the engine's illegal memory access (`snn_simulation.cu:969`), the error of the archive's
SP3 crash in another configuration. The user chose S3b with I -> E 0.5 for Substep 3, run first at 4 lambda as
a gate and then at 10 lambda, rules that do not need the route middle to fire first (`sparse-assemblies-task.md`,
"Rules"). Cost about $0.33; rerun so far about $6.00.

## Conclusions A1 to A8

| | conclusion on the faulty engine | outcome | decided in |
|---|---|---|---|
| A1 | the engine's connectivity is practically flat in space | falls: E -> E synapses fall with distance, effective lambda about 4 cells | step 2 |
| A2 | intra-group density varies about threefold | changes: it varies about 2.5-fold on the corrected engine, so not an artifact of bug 1 | step 2 |
| A3 | the regime: gain 4, `gain_ie` 2, `gain_ee_inter` 0.6, intra total 40 | changes: single groups are still recruited without spill, but a saturated path transmits only with `gain_ee_inter` about doubled (1.2 to 2.4) | step 3 |
| A4 | all-or-none propagation with pair-dependent thresholds | changes: untrained, no pair propagates in the regime region in any wiring; the all-or-none jump remains only in the engine's own wiring, at `gain_ee_inter` 3.6 | step 4 |
| A5 | the ignitions are a finite-size effect | falls: every transfer at d 4 ignites at 7^3, 9^3 and 11^3 (about 180, 420 and 850 strays) | step 6 |
| A6 | archived items 2, 3, 6 and 13 | changes: 15 of 24 pairs associate at 7^3 (lambda 0.4), C2's narrowing carries spatial information (uniform C2: 0 of 24); item 3 holds, items 6 and 13 fall | step 5 |
| A7 | 60 to 100 times more inhibition than excitation, no substrate sums, the sparse task stops | changes: 200 to 350 times; S3b sums at 4 lambda, twice as strongly with inter-group I -> E gain 0.5, not beyond; the stop rule does not apply | step 7 |
| A8 | the rate model over-propagates, neither model admitted | open: model B with the configured composition is not admitted without fitted parameters (9^3: 1 association of 24 against 11, `rate-model/round6-report.md`, "Step 3"); the fit of up to three learning parameters is still running | step 8 |
