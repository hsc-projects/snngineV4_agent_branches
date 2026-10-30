# Assembly association (minimal main feature): report

## Summary

**Update (2026-10-28, iteration 65):** joint rounds without gaps (50 or 100 steps of injection, no
pause) give 7 and 5 associations of 24 against 6, the same seed 0 pairs, and transfers come no faster:
the gaps make no measurable difference. Cost about $88 of the $90 cap.

**Update (2026-10-28, iteration 64):** a control with C2 held uniform (consolidation gate open
everywhere) associates the same 6 pairs as activity-proportional C2, plus one: in the passing protocol
C2 switches consolidation on but carries no spatial information. The minimal version shows association
by activity-dependent learning plus a global consolidation signal, not chemical route selection. The
Substep 7 assessment video is built (`assoc_assessment.py`) and rendered for two passing pairs. Cost
about $87 of the $90 cap.

**Update (2026-10-27, iteration 63):** short-term synaptic depression (`std`, new) at 7 x 7 x 7 cuts
the ignitions (9 -> 4, 3, 2 of 24) but also the transfers (17 -> 10, 6, 5): 3, 3 and 2 associations
against 6. Like the larger grid, it trades reach for containment. Every change tried in iterations 59
to 63 that removes ignitions also removes most transfers. Cost about $86 of the $90 cap; no further
session planned without the user's decision.

**Update (2026-10-27, iteration 62):** in the 9 x 9 x 9 grid, slower `w_fast` decay, a doubled `a_pre`
and 60 rounds do not extend the spread around A beyond 10 to 15 groups (best: 3 of 12 pairs, against 2).
Inhibition proportional to each group's own activity (`local_inh`, new) leaves the 7 x 7 x 7 ignitions
in place (at most 3 of 12 selected pairs, as before). Cost about $84 of the $90 cap.

**Update (2026-10-27, iteration 61):** in a larger grid (9 x 9 x 9 and 11 x 11 x 11, same group size and
wiring, A and B at least 2 cells from the surface) no transfer ignites: activity from A stays within
10 to 16 groups around it. But it also no longer reaches B: 3 and 4 of 24 pairs associate at distance 4
(6 at 7 x 7 x 7), 0 of 24 at distance 6. The ignitions were a finite-size effect, and at 7 x 7 x 7 they
carried most transfers. Cost about $80 of the $90 cap.

**Update (2026-10-27, iteration 60):** undoing a joint round whose test ignites and continuing with
smaller learning steps (down to 1/16) adds one association at distance 4 (7 of 24) and none at distance
6 (1 of 24). The other ignited pairs go from no transfer straight to an ignition at every step size,
mostly one that does not reach B: propagation is all-or-none along the learning trajectory as well.
Cost about $73 of the $90 cap.

**Update (2026-10-27, iteration 59):** the C3 fuel (in the short circuit stage or also in the joint
rounds) and slower growth leave the distance-4 result at 5 to 7 associations of 24 (6 without them).
At distance 6 the protocol associates 1 pair of 24: nearly every transfer is a whole-network ignition.
The outcome of a pair is fixed by whether its first transfer in the joint rounds is an ignition; the
short circuit stage keeps or loses that transfer but does not narrow it. Cost about $70 of the $90 cap.

**Status (2026-10-26, iteration 58): the minimal version passes in 6 of 24 pairs at distance 4 with
all controls; the task's goal (any pair, larger distances) is not reached yet.** Substeps 0 to 3
pass. On a distance-dependent wiring (the engine's own wiring is flat in space), two assemblies
injected together become associated over multi-hop routes: joint rounds with learning wherever there
is activity, then a short circuit stage in which C2, released by every active neuron in proportion to
its activity, makes the changes permanent. Under the user's revised criterion (a few strays allowed),
6 of 24 pairs pass with control 0, control 1 (no C2) and a joint-activation control (seed 0: 5 of 12,
seed 1: 1 of 12). C1 is skipped (the user's provisional decision); energy as local fatigue does not
focus the short circuit; the user's C3 fuel is implemented but not yet run. Cost about $56.7 of a $90
cap. Start with "Handoff for the next agent"; "History of approaches" summarizes why earlier
approaches failed.

**Terms.** *Route:* the neurons and synapses between A and B that carry an association (in the code:
`path_groups`, the groups whose cell lies within 1 cell of segment A-B). *Strays:* groups active
(A_g >= 0.5) in a test outside A, B and the route, C included. *Stray limit:* 34 strays (10 % of the
343 groups); a test with more strays, or with a runaway, fails (the user's "whole-network activation
is bad", made measurable). *M / Sh:* the middle of the route and an off-path shell at the same
distance from A and B, compared in the selectivity telemetry.

## Handoff for the next agent

This section replaces every earlier handoff (written 2026-10-26, after s70). It is written for an
agent that starts cold.

### Read first, in this order
1. This section.
2. `tuning-log.md`, iterations 53 to 65 (the current line of work), then 38 to 52 for why the earlier
   approaches failed; iterations 1 to 37 are in `tuning-log-1-37.md`. Italic notes mark conclusions
   that later iterations superseded.
3. The task file `runpod-assembly-association-task.md` (requirements, protocol, rules). Several of its
   points were revised later by the user; "Decisions taken by the user" below takes precedence.
4. `agents/main_feature/main-feature-readme-reconstruction.md` (the concept).

### State
- **No pods running** (`list-pods` returned `[]` after s77, 2026-10-28). All results up to s77 are in
  `output/`.
- **Cost:** about $88 of the user's **$90** cap (s77 about $0.8). `list-pod-billing` read before s71 (2026-10-24 to
  2026-10-27): $52.64 billed over 217 pods, below the running estimate of $56.7; s71 about $13, s72
  about $2.6, s73 about $6.6, s74 about $3.6, s75 about $1.9 and s76 about $0.8 on top (estimated from
  pod lifetimes x $0.89/h). Check `list-pod-billing` before the next session.
- **The volume matches the repository** (64 module checks pass on CPU and GPU, s76; the final renderer
  fix in `assoc_assessment.py` and its module check were copied to the volume afterwards and checked on
  CPU only).
- **Autonomy:** the user said "continue as you see fit" within the $90 cap (choose sessions, report).

### Open problems (from s69, 24 pairs at d 4)
- **Pass rate:** 6 of 24; 9 pairs transfer but exceed the stray limit; 9 end without association
  (7 never transfer, 2 lose the transfer in consolidation).
- **Seed dependence:** seed 0 5 of 12, seed 1 1 of 12 (unchanged by C3 or slower growth, s71).
- **Distance 6** (s71): 1 of 24 associates; 14 transfer, almost all as ignitions (median 157 strays).
- **Reach in a larger grid** (s73): without ignitions, activity from A levels off at 10 to 16 groups
  around it; 5 or 6 of 24 pairs transfer at d 4, none at d 6. Slower decay, larger `a_pre` and 60
  rounds do not move that plateau (s74).
- **Sparse layouts:** not yet tried with this protocol (the Substep 7 video is built, iteration 64).

### The protocol that passes (iteration 56; `params/session69a-stage2.json`)
- **Network:** N 20,000, S 2000, 7 x 7 x 7 location groups, every group an assembly (shortcut 1:
  normalized intra-group input, total 40), distance-dependent rewiring `rewire: {"lam": 0.4}`, gain 4,
  `gain_ee_inter` 0.6, `gain_ie` 2, injection k 12 neurons at I 20, runaway check 0.5, input clamp
  +-100.
- **Joint rounds:** A and B injected together (50 steps + 50 gap); C1 skipped (gate open everywhere,
  `theta1` -1, `soft1` 0, C1 gain 0), so learning happens wherever there is activity (rule "both",
  a_pre 0.5), temporary (`w_fast`, tau 2000); after each round a test with A alone on `w_fast`;
  up to 30 rounds.
- **Short circuit stage** once A alone activates B (spread accepted, `accept_uncontained`): A and B
  injected together for 5 to 10 rounds, C2 released by every neuron in proportion to its spikes (gain
  1, no saturation, k 0.02, decay 0.01), `w_fast` moved into `w_perm` at kappa 0.05 per step times a
  C2 gate that rises from 0 at C2 0.6 to 1 at 1.2 (`theta2` 0.6, `soft2` 0.6), no new learning
  (`learn_in_c2` false), no energy.
- **Final test:** A alone (and B alone) on `w_perm` only; pass = B >= 0.5 within 100 steps, no runaway,
  at most 34 of 343 groups active outside A, B and the route (`criterion` "bounded").

### What is established (with the iteration that shows it)
1. **Activity-proportional chemistry cannot select a route that is silent before learning**
   (iterations 41 to 52): the neurons between A and B do not fire under joint injection, and no
   regime of gains, balance, background input or layout makes them fire in a graded way; propagation
   is all-or-none, with pair-dependent thresholds.
2. **Growth plus consolidation finds a route without chemical selection** (iterations 53 and 56):
   learning wherever there is activity, made permanent by capture on transfer (iteration 53) or by the
   C2 short circuit stage (iteration 56), forms associations in about a quarter to a third of the
   pairs; whether C1 gates the learning makes no difference (iteration 53, gating-off control).
3. **The associations need joint activation** (iteration 56).
4. **Energy as local fatigue defocuses** (iterations 55 and 57): the route fires most and loses the most
   excitability, with or without wide spread. It does not change the outcome.
5. **C2 favours the route only weakly:** proportional release 1.4 to 1.5 times higher on the route than
   in the off-path shell (saturating release 1.2 to 1.4), against a firing ratio of about 2.
6. **The outcome is fixed in the joint rounds** (iteration 59): the short circuit stage keeps or loses
   the first transfer with its strays (7 -> 6, 126 -> 122, 199 -> 195; or 179 -> lost) and narrowed one
   in 24 pairs in two of nine C3 settings. A pair associates when its first transfer is contained
   (3 to 15 strays) and fails when it is an ignition (60 to 260); at d 6 nearly every transfer is one.
7. **C3 fuel does not change the pass rate** (iteration 59): in the stage, in the joint rounds, or both,
   5 to 7 associations of 24 against 6 without it. C3 is 1.2 to 1.4 times higher on the route than in the
   shell, but the firing ratio route / shell does not rise. Slower growth (a_pre 0.25) gives 5 in about
   twice the rounds.
8. **Measurement notes:** with background input, every condition is a single trial; judge effects
   across pairs (mean against standard error), not by counting pairs above a threshold (iteration 52).
   Pairs 3 and 5 of seed 0 never transfer; pairs 1, 8 and 10 of seed 0 transfer easily.
9. **The ignitions are a finite-size effect, and they carried the reach** (iteration 61): with the same
   group size and wiring in a 9^3 or 11^3 grid (`engine.n_delays` 16 / 20) and A, B at least 2 cells from
   the surface (`protocol.pair_margin` 2), no transfer ignites (A-alone strays at most 39 to 49), but the
   spread around A levels off at 10 to 16 groups after about 20 rounds and B mostly stays silent: 5 / 6
   pairs transfer at d 4 (17 at 7^3), 3 / 4 associate (6), none at d 6.
10. **The plateau is not set by `w_fast` decay or rate, and per-group feedback inhibition does not grade
   the spread** (iteration 62): at 9^3, `tau_fast` 8000, `a_pre` 1.0 and 60 rounds leave the spread
   around A at 10 to 15 groups from round 20 on (best 3 of 12 pairs against 2). At 7^3, `local_inh`
   (-gain * max(0, A_g - 0.2) on the group's excitatory neurons, gain 5 to 40) keeps the ignitions
   (48 to 243 strays) and trades one association for another (3, 3, 1 of 12 against 3).
11. **Short-term depression trades reach for containment** (iteration 63): `std` (per-neuron resource,
   U 0.1 to 0.4, tau_rec 200 to 800) cuts the ignitions at 7^3 d 4 (9 -> 4, 3, 2 of 24) and the
   transfers with them (17 -> 10, 6, 5); 3, 3, 2 associations against 6, all among the pairs that
   associated easily before.
12. **Across iterations 59 to 63**, every change that removes ignitions (larger grid, depression) also
   removes most transfers, and every change that keeps reach (C3, rollback, feedback inhibition) keeps
   the ignitions: in this network, reaching B 4 cells away has so far needed propagation strong enough
   to spread over the reservoir.
13. **C2 carries no spatial information in the passing protocol** (iteration 64): with C2 held uniform
   at a level that opens the consolidation gate everywhere, the same 6 pairs associate (plus s0p4),
   with the same strays. Control 1 (no C2) fails by construction, since C2 is the only route to
   `w_perm`. The permanent changes lie within about 2 cells of segment A-B (91 to 92 %) because the
   activity did. The minimal version shows activity-dependent learning made permanent by a global
   consolidation signal, not chemical route selection.

### Review after iteration 63 (2026-10-28)
- **Diagnosis:** with boosted intra-group weights in every group and a connection range of 0.4 cells,
  each location group is a bistable unit (off or fully on), weakly coupled to its neighbours. Activity
  in such a lattice either stays near its source or sweeps outward in all directions; learning that
  raises coupling around activity only moves the network between the two. This explains why every
  change in iterations 59 to 63 traded containment for reach. Iteration 52 showed the other half: at
  d 4, too few synapses link A and B to the middle of the route for their signals to add up there.
- **Statistics:** with 24 single-trial pairs and a pass rate near 25 %, the binomial error is about
  +-2 pairs; differences such as 6 / 7 / 3 associations are within noise. Use paired comparisons on the
  same pairs, at least 48 pairs, repeated trials where noise is used, and a decision threshold fixed
  before the run.

### Successor task (2026-10-28)
The work continues in `sparse-assemblies-task.md` (approved by the user): sparse assemblies on the
distance-dependent wiring, with route selectivity and controls for each chemical field. The options
below are kept for reference.

### Next step: open, for the user to decide (after iteration 64)
About $3 of the cap is left; no session is planned. Each needs the user's decision:
- **Accept the current result** as the minimal version, described as in item 13, and commit.
- **Redesign the substrate before retrying chemical route selection** (needs a cap increase and a
  design discussion): sparse assemblies with ordinary neurons between them, a connection range of
  about one cell or more (distance scaled with it, larger grid), then a cheap diagnostic first: does the
  input to a middle group grow in proportion to the number of active sources? Only if it does can a
  chemical mark where activity from A and B meets.
- **Synaptic tagging for consolidation** (only synapses that carried pre -> post spikes in the short
  circuit stage become permanent) is unlikely to help while that stage itself runs as an ignition.

### C3 fuel sweep (iteration 58 plan; run in iteration 59, see the tuning log)
- **Idea (the user's):** energy depletion is global and usage increases local availability, modelled
  as a third chemical C3 ("fuel"): a fixed total supply per step, delivered in proportion to recent
  local use, consumed by spikes. It should concentrate excitability on A, B and the route during the
  short circuit and starve weaker activity around them, and lower everyone's excitability when
  activity spreads over the whole reservoir.
- **Code:** `assoc_fields.FuelField`, selected with `energy: {"mode": "fuel", ...}` (see its docstring);
  use it in the short circuit stage only (`in_c1` false, `in_c2` true, `in_test` false).
- **Suggested sweep:** the s69 setting (copy a job of `params/session69a-stage2.json`, controls off),
  energy `{"mode": "fuel", "supply": 0.01, "decay": 0.01, "tau": 50, "floor": 0.05, "cap": 2, "k": 0.02}`
  with `consume` 0.5 / 1 / 2 x `beta` 1 / 2, plus energy off as reference; seed 0, the 10 pairs that
  transfer (0, 1, 2, 4, 6 to 11); about 70 jobs, 5 pods, about $1.5. Rough scale: route neurons fire
  about 0.012 spikes per step during injection, with about one neuron per voxel, so the trace there
  reaches about 0.6 against a floor of 0.05, and the route's share of the supply should be several
  times the mean.
- **Measure:** strays in the final test, associations, transfers beyond the limit, and in the last
  short-circuit round `sel_inject_end` (`E`, `spikes_per_exc` and `C2` for the route M against the
  shell Sh): C3 should now be higher on the route than in the shell.
- **If it helps:** confirm with controls (`control_modes` ["no_chemistry", "separate"]) on 2 seeds; the
  energy-off result of the same pairs is control 3. Then distance 6, more seeds, and the Substep 7
  assessment video.

### How to run a session
The general pod workflow (stock, one GPU architecture per batch, upload once, module checks, detached
sessions, one collector per pod, terminating and verifying, cost) is in
[`setups/runpod-technical.md`](../runpod-technical.md), section "Running pod sessions". Specific to
this task:
- **Pod body:** `{"name", "image": "runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404", "dataCenterIds": ["EU-RO-1"], "cloud": "SECURE", "gpu": {"id": "NVIDIA GeForce RTX 4090", "count": 1, "minCudaVersion": "12.8"}, "ports": ["22/tcp"], "startSsh": true, "mounts": {"network": [{"volumeId": "qze81dpw7q", "path": "/workspace"}]}, "disk": 20}`
  (RTX 4090 at $0.89/h; the L4 at $0.59/h runs the same SM 89 build).
- **Upload** from PowerShell: `scp -O -F NUL -i setups/.secrets/id_ed25519 -P PORT -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL <files> root@HOST:/workspace/snngineV4_cloud/snngineV4_agent_branches/setups/runpod-assembly-association/`
  (parameter files to `params/`).
- **Module checks:** `source /workspace/venv/bin/activate; cd /workspace; PYTHONPATH=/workspace/snngineV4_cloud/snngineV4_agent_branches python <dir>/test_assoc_modules.py --device cpu`, then `--device cuda`.
  A failing check aborts every session's preflight.
- **Parameter files:** generate them with short Python snippets from an earlier file (s69 for the
  current protocol); one pair per file keeps sessions short (about 10 to 30 minutes).
- **Start:** `bash <dir>/runpod_assembly_runner.sh start <dir>/params/<file>.json --session-limit-min 60`;
  results go to `/workspace/output/assembly-association/<session>/`, marker `<params stem>.finished`.
- **Collect:** `python collect_pod_sessions.py <pods.csv> output params`, one per pod.
- **Analyse** on the host (weak: standard library only, keep it light):
  `assoc_sweep_summary.py output "<session glob>"` (one line per configuration),
  `assoc_controls_summary.py output "<session glob>"` (one line per pair with controls),
  `assoc_selectivity.py` (surveys: `--propclass`, `--bridge`, `--input`).
- Keep `runpod_assembly_runner.sh` with LF line endings. In module checks, region boundaries must not
  coincide with neuron positions (GPU rounding differs).

### Code: options added in this work (all module-checked, 65 checks)
- **Iteration 65:** `round_inject_steps` (injection length of the joint and C2 rounds only; tests keep
  their own).
- **Iteration 64:** `c2.uniform` (C2 held at a value in every voxel while released; control);
  `video.kind` "assessment" (`assoc_assessment.py`: Substep 7 recorder and renderer, `render(...,
  png_frames=[...])` for previews).
- **Iteration 63:** `std` `{"U", "tau_rec"}` (short-term depression of each excitatory neuron's outgoing
  weights, harness-side, reset at the start of every `run()` call).
- **Iteration 62:** `local_inh` `{"gain", "a0"}` (each excitatory neuron gets -gain * max(0, A_g - a0) of
  its own group every step, in every phase).
- **Iteration 61:** engine `n_delays` (D instead of the engine's log-N rule; the grid follows as
  int(D / sqrt(3)) cells per axis, e.g. D 16: 9^3, D 20: 11^3); `protocol.pair_margin` (A and B at least
  this many cells from every face; `pair.margin_cells` in the result).
- **Iteration 60:** `protocol.rollback` `{"factor", "min_scale"}` (undo a joint round whose test is not
  bounded, continue with the learning rates times `factor`); `GatedPlasticity.rate_scale`.
- **Protocol:** `criterion` ("bounded", default, or "contained"), `max_active_frac` 0.1;
  `control_modes` ("no_chemistry", "gating_off", "separate"); `inject_mode` ("joint" or "alternate",
  used by "separate"); `capture`; `accept_uncontained`; `oracle` (diagnostic); `bridges`; energy per
  phase (`energy.in_c1` / `in_c2` / `in_test`); `energy.mode` "fuel" (C3); `bg` with `targets`
  "ordinary"; `inter_norm`.
- **Plasticity:** `norm_factor`, `weight_dep`, `ltp_events` / `capture`.
- **Tests record:** `n_active_outside` / `active_outside` / `bounded` per test; selectivity telemetry
  (`regions`, `selectivity`, `weight_selectivity`; M = middle of the route, Sh = off-path shell at the
  same distance from A and B).
- **Jobs:** `substep4` (protocol with controls), `prop_survey` (with `bridge_max`, `off_asm_max`),
  `input_survey`, `conn_survey`, `diag_saturated_path`.

### Decisions taken by the user
Earlier: gains and intra-group weights above 1, explicit S, background input, separate inhibitory
gains, the presynaptic C1 rule, excitatory-only `A_g`, the runaway check, self-limiting release,
larger reservoirs, parallel pods, the Substep 7 video, safeguards, module checks on the pod, the
global Substep 1 retune, Substep 8, distance-dependent wiring, bridge assemblies may be active in the
test, at most one free cell between assemblies, the within-group boost is a free parameter, distance
relative to the connection range, synaptic normalization and capture as allowed rule revisions,
speed and data over cost, keep local work small (weak host). On 2026-10-26:
- **pass criterion revised:** an association passes if A -> B (or the reverse) >= 0.5 in the strict
  final test, no runaway, at most 10 % of all groups (34 of 343) active outside A, B and the route,
  control 0 and control 1. A few stray groups are acceptable; whole-network activation is not. C is
  recorded but no longer a pass condition (control 2 dropped);
- **provisional:** C1 may be skipped in the minimal version (the user's intuition: C1 privileges
  short-term-memory assemblies against the dream state's random activations, which the minimal
  version does not have). C2 is released by every active neuron in proportion to its activity during
  the short circuit state, not by B alone. Energy is to focus the short circuit on the real route;
  the user's form: global depletion, usage increases local availability, possibly a third chemical
  C3 (fuel). Control 1 then concerns C2; the joint-activation control is added;
- **cost cap $90** (raised from $50 / $60), "continue as you see fit".
These decisions are also listed in the task file ("Revisions agreed with the user"), and the user's
statements on C1, C2, energy and strays in the README reconstruction.

### Choices made by the agent (tell the user if you change them)
Normalized intra-group input; `gain_ee_inter`; `learn_in_c2` false; the rewiring rule; the final test
on `w_perm`; RTX 4090 (L4 as fallback); the oracle as a diagnostic; the M / Sh regions (`sel_radius`
1); the stray limit counted as groups with A_g >= 0.5 outside A, B and the route (path radius 1 cell),
C included; the C3 form (trace, floor, beta, cap, decay) in `FuelField`.

## History of approaches

Details and numbers are in the tuning log under the iterations named. Iterations 1 to 37
(`tuning-log-1-37.md`) built the harness, found a working regime of gains and numerical safeguards,
retuned for N = 20,000, passed the protocol on the engine's own wiring at distance 2 (10 of 12 pairs,
s36), extended it to longer distances and sparse layouts, and examined why transfers were lost in
consolidation.

| Iterations | Approach | Result |
|---|---|---|
| 38 to 40 | mechanism check; engine wiring against distance-dependent rewiring | associations ran over direct A <-> B synapses; the engine's wiring is flat in space; rewiring with λ 0.4 |
| 41 to 44 | C1-gated learning on the rewired network; oracle diagnostic (chemistry fixed along A-B) | 0 of 60 with real chemistry; oracle 6 of 12 at d 4, 0 of 24 at d 6; the route is silent before learning |
| 45, 46, 50, 52 | propagation regime: layout, gains, excitation / inhibition balance, background input | all-or-none propagation with pair-dependent thresholds; no graded regime |
| 47, 51 | coincidence detection by single neurons or by bridge assemblies | no usable two-sided signal |
| 48, 49, 53 | capture on successful transfer, synaptic normalization; revised pass criterion | 8 of 24 pairs associate; the gating-off control reproduces 6 of the 7 in seed 0 (independent of the chemistry) |
| 54, 55, 57 | C1 skipped; C2 short circuit stage; energy as local fatigue | 3 to 6 associations in 10 to 12 pairs; fatigue defocuses |
| 56 | the best setting without energy, with controls on 2 seeds | 6 of 24 pass; the associations need joint activation |
| 58 | C3 fuel (global supply delivered where it is used) | implemented and module-checked |
| 59 | C3 fuel in the short circuit stage or also in the joint rounds; slower growth; d 6 | 5 to 7 of 24 against 6; the outcome is fixed by whether the first transfer ignites; d 6: 1 of 24 |
| 60 | rollback before ignition (undo the round, smaller steps down to 1/16) | d 4: 7 of 24; d 6: 1 of 24; growth goes from no transfer straight to an ignition, mostly one that misses B |
| 61 | larger grid (9^3, 11^3; same group size and wiring), pairs 2 cells from the surface | no ignitions, but A's spread levels off at 10 to 16 groups: d 4 3 and 4 of 24, d 6 0 of 24 |
| 62 | more reach at 9^3 (slower decay, larger a_pre, 60 rounds); per-group feedback inhibition at 7^3 | plateau unchanged (best 3 of 12 against 2); ignitions unchanged (3, 3, 1 of 12 against 3) |
| 63 | short-term synaptic depression at 7^3 (U 0.1 to 0.4) | fewer ignitions (4, 3, 2) and fewer transfers (10, 6, 5): 3, 3, 2 of 24 against 6 |
| 64 | uniform-C2 control; Substep 7 assessment video | uniform C2 associates the same 6 pairs (+1): C2 carries no spatial information; video built for two passing pairs |
| 65 | joint rounds without gaps (50 + 0, 100 + 0) | 7 and 5 of 24 against 6, same pairs, no faster: gaps make no difference |

## Implementation

| File | Role |
|---|---|
| `assoc_engine.py` | headless network (built through the sibling chem-diffusion builder, imported), per-step hooks, gains (option `inter_norm`), intra-group normalization, **`rewire_by_distance`** |
| `assoc_build.py` | builder with explicit S |
| `assoc_fields.py` | voxel mapping, C1 / C2 fields (release, 7-point zero-flux diffusion, decay), local energy field, **`FuelField`** (C3 fuel), group activity `A_g` |
| `assoc_plasticity.py` | chemical-gated plasticity on the fixed N × S synapses: `w_fast` (decays), `w_perm` (permanent), rule `stdp` / `pre_c1` / `both`, options `consolidate_ee_only`, `weight_dep` ("mult" / "upper") |
| `assoc_protocol.py` | Substeps 0 to 4 as jobs with controls (`control_modes`, joint-activation control, pass `criterion`); `diag_saturated_path`, `conn_survey`, `prop_survey`, `input_survey`; telemetry `split` (E / I, along A-B), `gate_profile`, `direct_stats`, stray counts per test, route selectivity (`regions`, `selectivity`, `weight_selectivity`); diagnostics `freeze_direct_AB`, `oracle` |
| `assoc_queue.py`, `runpod_assembly_runner.sh` | pod-side queue (preflight, one child process per engine, resumable jobs, wall-clock limits) |
| `assoc_summarize.py`, `assoc_selectivity.py`, `wait_pod_session.py` | host-side summaries (selectivity: M / Sh ratios per variant); background waiting for a detached session |
| `assoc_sweep_summary.py`, `assoc_controls_summary.py` | host-side summaries of protocol sessions: one line per configuration, or one line per pair with controls |
| `test_assoc_modules.py` | 57 analytic checks on CPU and GPU (stub engine) |
| `collect_pod_sessions.py` | host-side collector: waits for every pod's session marker, downloads and extracts; exits 1 if a session is still pending |
| `assoc_video.py` | `A_g` heat-map video with C1 / C2 projections |

Engine facts: one `update()` is 1 ms (two Izhikevich half-steps). Current added to row 7 of
`N_states` between steps is read by the next step. The kernel delivers synapse bucket d of
`N_delays` d steps after the spike, and reads only `N_rep`, `N_weights` and `N_delays`; the
pre-synaptic reverse indices matter only to the engine's STDP, which stays off. Inhibitory
neurons project only onto excitatory ones. Weight bounds: excitatory [0.05, 1], inhibitory
[−1, −0.05].

## Substep 0: Harness

**Summary:** passes (s1). Python-side current injection works, weights written between steps
are delivered exactly, the voxel mapping puts every neuron in its group's cell, and an
unstimulated run stays silent. Thalamic noise is off by default, and a step is 1 ms. Telemetry
and video are produced.

## Substep 1: Assembly activation

**Summary:** passes on nearly all groups after a global retune.
- **Engine wiring, N = 20,000, S = 2000:** 332 to 338 of 343 groups (s34). This needed intra-group
  input normalized per neuron (total 30, i.e. current 120 when the whole group fires), k = 12,
  I = 20, g 4, `gain_ie` 4.
- **Rewired, λ 0.4, `gain_ie` 2, intra total 40:** 86 to 91 of 100 groups (s48). The failures
  are spill into neighbours, which rises with `gain_ee_inter`.
- **Sparse layouts, old wiring, total 160:** lattice 52 to 59 of 64, random 27 of 30 (s41).

Early sessions (s1 to s6) found the structural cause of the first failures: too few
intra-group synapses at small S, and weights bounded at 1. Tuning-log iterations 1 to 5 and
25 to 27.

## Substep 2: Chemical release, diffusion, optional energy

**Summary:** passes (s1). Release is proportional to spikes, diffusion matches the engine's C0
kernel (relative error 1e-6), and the plume forms and fades. Energy consumption and recovery
work; the suppression check passed only trivially. In the protocol, energy as local fatigue does not
focus the short circuit (iterations 54, 55, 57); the C3 fuel is prepared (iteration 58).

## Substep 3: Chemical-gated plasticity (isolated)

**Summary:** passes (s1) on the real synapse tensors with synthetic spikes and chemistry:
changes occur only where the gates are on, `w_fast` decays, `w_perm` persists, and the bounds
hold. Module checks: 57 / 57 (iteration 58).

## Substep 4: Full protocol

**Summary:** passes in 6 of 24 pairs at d 4 on the rewired network (iteration 56, s69), under the
user's revised criterion and with C1 skipped (provisional): control 0, control 1 (no C2) and the
joint-activation control hold in all six (seed 0: 5 of 12, seed 1: 1 of 12). Setting:
`params/session69a-stage2.json`; protocol in "Handoff for the next agent". Earlier results:
- **Rewired, C1 skipped, C2 short circuit stage** (s67, s68, s70): 3 to 6 associations in 10 to 12
  pairs in every configuration of C2 reach, threshold and energy.
- **Rewired, capture on transfer** (s66): associations in 8 of 24 pairs; the gating-off control
  reproduces 6 of the 7 in seed 0.
- **Engine wiring, d 2** (s36): 10 of 12 random pairs, 1 to 3 C1 rounds, strict transfer 0.51 to
  1.00. Setting: `params/session36-seed{0,1}-learnc2off-N20k-pairs.json`.
- **Mechanism** (s44, s45; iterations 37, 38):
  - the gates open only at A and B;
  - learning sits on synapses linking A and B directly (about 340 direct E→E synapses per pair,
    at every distance);
  - with those synapses frozen, 6 / 28 pairs pass instead of 20 / 28.
- **Rewired, C1-gated, λ 0.4 / 0.5** (s48 to s50): 0 / 60. Longer chemical reach opens the gate
  along the route but also everywhere else (the C1 profile along A-B is flat, iteration 43).
- **Rewired, decoupled chemistry** (s51, ten variants, 6 pairs each): no contained association
  except the two easy pairs; the gate never prefers the route (M / Sh 0.35 to 1.4).
- **Rewired, oracle chemistry** (diagnostic, s51 / s52): d 4 up to 6 / 12 (a_pre 0.5 or 1), d 6
  0 / 24. The route is silent before learning (iteration 44).
- Control 0 has held throughout. Control 2 (C) is recorded but no longer a pass condition
  (iteration 53). Two fixes for transfers lost in consolidation did not help (s44): consolidating
  onto excitatory neurons only, and a higher C2 threshold.

## Substep 5: Tuning loop

**Summary:** 58 iterations in `tuning-log.md` (index at its top). The main milestones were:
- a working regime (gains, s17 to s19);
- a numerical safeguard (input clamp at −100 and +100) and a runaway detector, which removed a
  kernel crash (s29 to s31);
- the N = 20,000 retune (s32 to s36);
- runaway control at long range (s40, s41);
- the mechanism check and the flat-wiring finding (s44 to s46);
- distance-dependent wiring (s47 onward);
- the oracle split into plasticity and chemistry, and the finding that the route is silent under
  joint activation (s51, s52);
- surveys of the propagation regime, coincidence detection and background input, all negative (s53
  to s65);
- the user's revised criterion and the recheck with controls (s66);
- C1 skipped, the C2 short circuit stage, energy variants, and the first passes with all controls
  (s67 to s70);
- the C3 fuel, prepared (iteration 58).

## Substep 6: Scale-up and any-pair test

**Summary:** not passed.
- **Engine wiring, N = 20,000, d 3 to 6:** best about 55 to 70 % of random pairs (s41, s44),
  but distant pairs are directly connected.
- **Larger N:** does not create distance in this engine (s46).
- **Rewired network:** the current protocol has been run at d 4 only (Substep 4); d 6 is not yet
  tried with it (the C1-gated rule gave 0 of 24 at d 6 even with oracle chemistry, iteration 44).

## Substep 7: Assessment video

**Summary:** built in iteration 64 (`assoc_assessment.py`, `video.kind` "assessment") and rendered for
two passing pairs of the s71 E0 setting: `output/s76-video-s0/s7-d4-s0-pair11-video_main.mp4` (35 s,
A -> B 0.94, 3 strays) and `..._pair0-video_main.mp4` (55 s, A -> B 0.60, 6 strays). Each shows the
neurons coloured by their group's A_g, A / B / C circled, the 1500 synapses with the largest permanent
change as lines, A_g traces of A, B and C, and a phase timeline (joint activation, gap, C1-phase test,
short circuit stage, final test) with a playhead; the view turns slowly.
- **Deviation from the task:** lines are drawn with Pillow, not the VisPy `LineVisual`, to avoid a GL
  context on the pod; content and one colour per synapse are as specified.
- **Limit:** 726k and 1.16M synapses changed permanently; the 1500 drawn all sit at the weight bound
  (0.91), so line colour does not vary, and they cluster on A and B. The telemetry's distance profile
  (91 to 92 % of the changes within 2 cells of segment A-B) is the better summary of where weights
  changed. A sample drawn across the whole changed set would show the tube around A-B.
- A milestone `A_g` video of a passing pair on the old wiring is in `output/s37-N20k-milestone-video/`.

## Substep 8: Sparse assemblies

**Summary:** tested on the old (flat) wiring only. Total intra current 160 with runaway control:
- `a_pre` 0.25: lattice 22 / 24, random 17 / 24 (d 2 and 4) (s41);
- `a_pre` 0.5: 53 / 72 with about 2 C1 rounds, d 6 18 / 24 (s43).

Not checked for direct synapses. On the rewired network only surveys so far: propagation
(iteration 45, all-or-none) and the bridge threshold diagnostic (iteration 51, no usable
coincidence window). The current protocol (Substep 4) treats every group as an assembly; sparse
layouts are not yet tried with it; this continues in the successor task `sparse-assemblies-task.md`
(approved 2026-10-28, not started). Layouts:
`assemblies: {"layout": "lattice", "spacing": 2}` or
`{"layout": "random", "count": 30, "min_gap": 1, "seed": 0}`.

## Pod sessions and cost

| Sessions | GPUs | Notes | Cost |
|---|---|---|---|
| s1 to s23 | RTX 2000 Ada, L4, one RTX 4090 | N ≤ 5000, 1 pod each, 3 to 14 min | about $1.7 |
| s24 to s40 | RTX 4090 (some L4) | N = 20,000 / 40,000, up to 4 pods in parallel | about $8.1 |
| s41 to s45 | 2 to 6 × RTX 4090 | long range, sparse, mechanism check | about $9.8 |
| s46 to s50 | 1 to 8 × RTX 4090 | connectivity survey, rewiring, regime, chemistry reach | about $6.5 (s46 to s48 billed $1.49; s49e / s50 about $5 estimated) |
| s51 | 16 × RTX 4090 | oracle and decoupled chemistry, 6 pairs per variant, 4 to 10 min sessions | about $4.6 (estimated) |
| s52 | 13 × RTX 4090 | oracle learning speed, 12 pairs per variant, 10 to 23 min sessions | about $4.6 (estimated) |
| s53, s54 | 16 + 6 × RTX 4090 | propagation surveys 1 and 2 (no learning, about 1 min sessions) | about $3.5 (estimated) |
| s55, s57, s58 | 8 × RTX 4090, reused | propagation surveys 3 to 5 | about $3.1 (estimated) |
| s59 | 8 × RTX 4090 | balanced background survey | about $1.3 (estimated) |
| s60 | 2 × RTX 4090 | two-sided input survey | about $0.4 (estimated) |
| s61 | 9 × RTX 4090 | convergence range, normalization, capture | about $3.3 (estimated) |
| s62 | 2 × RTX 4090 | capture plus normalization, real chemistry | about $0.8 (estimated) |
| s63 | 10 × RTX 4090 | E / I rebalancing survey (120 jobs, sessions 49 to 80 s, pods about 8 min) | about $1.2 (estimated) |
| s64 | 4 × L4 (RTX 4090 out of capacity) | bridge threshold diagnostic (84 jobs, six sessions, two chained; pods about 10 min) | about $0.4 (estimated) |
| s65 | 5 × RTX 4090 (no further capacity) | background on ordinary neurons (216 jobs, eight sessions, three chained; pods about 15 min) | about $1.1 (estimated) |
| s66 | 5 × RTX 4090 | recheck under the revised criterion (24 protocol jobs with controls, one session chained; pods 20 to 29 min, partly idle) | about $1.6 (estimated) |
| s67 | 3 × RTX 4090 (+ 1 Blackwell that never started) | C2 + energy sweep, stage 1 (192 jobs, 12 sessions, two chains per pod; pods 33 to 64 min) | about $2.4 (estimated) |
| s68 | 5 × RTX 4090 | stage 1b: depleting energy, proportional C2 (90 jobs, two sessions per pod; pods 12 to 23 min) | about $1.2 (estimated) |
| s77 | 3 × RTX 4090 | joint rounds without gaps (48 jobs, three sessions per pod; pods 15 to 19 min) | about $0.8 (estimated) |
| s76 | 3 × RTX 4090 | uniform-C2 control (48 jobs) and the assessment video (2 jobs), three sessions per pod; pods 11 to 20 min | about $0.8 (estimated) |
| s75 | 4 × RTX 4090 (capacity-limited) | short-term depression, 7^3 d 4 (72 jobs, three sessions per pod; pods 26 to 38 min) | about $1.9 (estimated) |
| s74 | 9 × RTX 4090 | reach at 9^3 (36 jobs, one session per pod) and local inhibition at 7^3 (36 jobs, two per pod); pods 13 to 42 min | about $3.6 (estimated) |
| s73 | 14 × RTX 4090 | larger grid, 9^3 d 4 / d 6 and 11^3 d 4 (72 jobs, one session per pod for memory; pods 31 to 38 min) | about $6.6 (estimated) |
| s72 | 6 × RTX 4090 | rollback before ignition, d 4 and d 6 (96 jobs, two sessions per pod; pods 20 to 36 min) | about $2.6 (estimated) |
| s71 | 14 + 3 × RTX 4090 | C3 fuel, slower growth, d 6 (246 jobs, two sessions per pod; 6 sessions rerun after a start-up race; pods about 58 and 21 min, about 35 min idle because of failed downloads) | about $13 (estimated) |
| s69, s70 | 5 × RTX 4090 | stage 2 with controls (24 jobs) and shared-pool energy (50 jobs); C3 module checks on the last pod (pods 16 to 36 min) | about $1.8 (estimated) |

Billing (`list-pod-billing`, day buckets 2026-10-25 and 2026-10-26) totals $20.36, which
covers everything up to s48 and may include a few pods of other tasks on 2026-10-25. Later pods
are estimated from pod lifetime × $0.89/h (s51 and s52 were not yet posted when last read).
Read again before s63 (buckets 2026-10-24 to 2026-10-26): $41.78 billed over 180 pods, below the
running estimate, so the estimates are conservative. Total about $56.7 of the $90 cap. The per-session group costs above are approximate sums of the
earlier per-session estimates. Per-pod costs are in `list-pod-billing` (by pod id).

Hiccups:
- `exec_pod.py` from Git Bash rewrites remote paths; PowerShell works.
- A dropped long SSH connection once left a pod idle for 31 minutes, hence detached sessions
  with markers.
- An L4 hit the 45-minute session limit on protocol runs; RTX 4090 only since then.
- `pkill -f` matched its own SSH shell; use the bracket pattern.
