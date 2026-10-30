# Rerun log: assembly association on the corrected engine

One entry per session of `engine-fix-rerun-task.md`: hypothesis, change, result, decision (as in the archived
`archive-pre-engine-fix/tuning-log.md`). Each step's outcome goes to `engine-fix-rerun-report.md`.

## Step 0 (pod `nf30u221xzjwmt`, 2026-10-30): corrected engine on the network volume

- **Goal:** the volume's checkout at the branch's latest commit (f051b62, which contains the engine fixes of
  f56ccf8 and cc94dde), the old backend builds gone, a fresh build, the module checks passing.
- **Found:** `/workspace/snngineV4_cloud/snngineV4_agent_branches` was not a git clone but an uploaded copy
  (engine files dated 2026-09-29) with backend builds `build` and `build_sm120`.
- **Decision (the user's):** replace it with a clone of the branch from a git bundle; keep the old copy.
- **Change:**
  - Bundle of `docs/runpod-pi-setup` at f051b62 (MD5 d65ff149..., checked on the pod) cloned to the same path;
    `origin` set to the GitHub URL; `git status` clean. The old copy is kept as
    `snngineV4_agent_branches.pre-f051b62`, its builds deleted (compiled from the old CUDA code).
  - Engine tests (`setups/runpod-engine-tests/`, pack `head` at f051b62, run `rerun0-f051b62-full`):
    `full`, 51 tests OK (162 s; CUDA build in the copy, no cached build for its source hash).
  - `runpod_assembly_runner.sh env`: found no build (SM none), built the backend for SM 120 through the
    smoke-test runner (staged CMakeLists fallback, as before) in 81 s; import from the clone confirmed.
- **Result:** module checks (`test_assoc_modules.py`) 73 / 73 on CPU and 73 / 73 on CUDA; `git status` still
  clean after the build. Logs: `output/rerun0/`.
- **Cost:** 1 pod, RTX PRO 4000 Blackwell, $0.57/h, 10:16 to about 10:26 UTC, about $0.10 (estimated from the
  lifetime); terminated (delete 204, `get-pod` 404).
- **Note:** a pod not created by this task, `s9o38cl9s4qvny` ("r6-fixed-engine", same volume), was created at
  10:20:42 UTC, during the deploy: the rate model's round 6 repeat on the fixed engine
  (`rate-model/round6_fixed_pod.sh`). It ran from its own copy of the repository and wrote only the build cache
  and its results on the volume, not the checkout; terminated by its session.
- **Decision:** step 0 done; step 1 waits for the user's go and cost cap.

## Step 1 (pod `34wjdbsndwoo2f`, 2026-10-30): build audit at 7^3, 9^3 and 11^3

- **User decision:** 11^3 added to the audit, so that step 6 can use it.
- **Hypothesis:** the harness's builds on the corrected engine have the configured composition (excitatory
  neurons 400 synapses onto inhibitory and 1600 onto excitatory neurons, inhibitory neurons 2000 onto excitatory
  and none onto inhibitory), no autapses, delays by round((D - 1) d / d_max), and E -> E synapses per group pair
  that fall with distance, unrewired and rewired (lambda 0.4), at all three sizes.
- **Change:** parameter files `params/rerun1{a..f}-audit-g{7,9,11}-{unrewired,rewired}.json` (the first E0 job of
  `session71-d4-s0-p00.json`, `session73-g9-d4-s0-a.json` and `session73-g11-d4-s0-a.json`; `rewire` removed for
  the unrewired ones). The task named `round6_export_engine.py --no-arrays`, but its structure audit checks
  neither autapses nor the distance profile, and without the arrays these cannot be checked afterwards. So the
  export runs with arrays (on the pod's own disk) and the new `rerun_build_audit.py` applies
  `snngine_v4/tests/network_invariants.py` to them (exact x.5 ties of the delay rule may round either way, as in
  the engine tests); `rerun1_audit_pod.sh` chains the six builds and audits. Run from the volume's checkout
  (f051b62, clean) and its SM 120 build.
- **Result** (`output/rerun1/`): all six builds pass every check. The first attempt of 1a failed before its build:
  the two 7^3 exports, started together on a fresh pod, both downloaded vispy's sample data (`volume/stent.npz`,
  read by `chem_volume.py`) and one hit `FileExistsError` on `/root/.vispy/data/volume`; 1a then ran alone and
  passed (log kept as `export_rerun1a-audit-g7-unrewired.race.log`).

  | build | E -> E / E -> I / I -> E / I -> I per neuron | intra-group E -> E per excitatory neuron | E -> E per group pair at 1, 2, 3, 6 cells | control 0, spikes AB / BA |
  |---|---|---|---|---|
  | 7^3 unrewired | 1600 / 400 / 2000 / 0, every neuron | 13.3 | 515, 432, 336, 119 | 3428 / 3402 |
  | 7^3 rewired | same | 858.7 | 3234, 264, 21, 0 | 788 / 1099 |
  | 9^3 unrewired | same | 10.0 | 376, 298, 217, 81 | 3128 / 2678 |
  | 9^3 rewired | same | 829.4 | 3091, 254, 20, 0 | 860 / 1135 |
  | 11^3 unrewired | same | 8.0 | 295, 230, 165, 42 | 3577 / 2348 |
  | 11^3 rewired | same | 810.3 | 3043, 249, 20, 0 | 1111 / 994 |

  No autapses, no deleted synapses, delay buckets well formed. Delays follow the rule; in the unrewired 9^3 and
  11^3 builds 32 650 and 313 946 synapses lie on exact x.5 ties rounded the other way (the engine computes in
  float32, as the engine tests found), none in the rewired builds. The rewired builds' intra-group numbers equal
  round 6's exports from the engine-test copy (858.7, 829.4), so the volume's build is the same engine.
- **Noted, not a failure:** in the unrewired 9^3 and 11^3 builds the corner-to-corner pairs (largest distance)
  have more E -> E synapses than the next distance (43.5 against 17 at 9^3, 45 against 7 at 11^3; 7^3: 47
  against 52); not explained. The unrewired builds put few E -> E synapses inside the own group (8 to 13 per
  excitatory neuron, against 810 to 860 rewired); the harness's `w_intra_ee_total` 40 is spread over them
  (step 2). Control 0 (one pair, archived parameters): about 3000 spikes unrewired against about 1000 rewired.
- **Cost:** 1 pod, RTX PRO 4000 Blackwell, $0.57/h, 11:22 to about 11:31 UTC, about $0.09 (estimated);
  terminated (delete 204, `list-pods` empty).
- **Decision:** step 1 passes at all three sizes; 11^3 is open for step 6. Step 2 next (needs the cost cap).

## Step 2, preparation (pod `niud1pnq6zsbun`, 2026-10-30): spread measurement and parameter files

- **User decision:** cost cap $20 for the rerun.
- **Change (code):** `assoc_protocol.py`: `activity_by_distance` (the peak activity of every other group during a
  Substep 1 run, by cell distance from the injected group, rounded as in `conn_survey`; `spread_cells`, the
  largest distance at which a group exceeds `inactive`) in every row of `substep1_activation`;
  `intra_ee_per_group` (A2: intra-group E -> E synapses per excitatory neuron of every group, summarized as
  `network.intra_ee_per_exc_neuron_by_group`); `s1_groups` (injected groups per job, default 5). Module check
  `activity_by_distance_and_intra_density_per_group` (and `intra_ee_mask` on the stub engine). Host summary:
  `rerun_wiring_summary.py` (effective lambda by a log-linear fit over distances 1 to d_max - 1, the largest
  left out because of the corner pairs of step 1; spread per job).
- **Check** (from a copy of the harness on the pod's disk, the clone untouched): module checks 74 / 74 on CPU
  and CUDA; `conn-g7-s0-unrewired` and `s1-g7-s0-unrewired-gain4` ran (session 45 s, the Substep 1 job 1.1 s).
  Unrewired 7^3: effective lambda 3.8 cells (rewiring: 0.4). At gain 4 every injected group is fully recruited
  (A_max 1.0, about 3000 spikes, all of them its own) and no excitatory neuron of any other group fires
  (`others_max` 0, every distance 0): a neighbouring group's neuron receives about 11 synapses from the
  injected group (515 per group pair over about 46 excitatory neurons) against about 70 with rewiring.
- **Change (parameters):** so that the comparison reaches the gains at which the engine's own wiring
  propagates, `gain` runs over 2, 3, 4, 6, 8, 12, 16 and 24 instead of the **[default]** three values around 4
  (a Substep 1 job takes about a second). `params/rerun2{a..d}-wiring-g{7,9}-s{0,1}.json`: per network seed
  (0, 1) and size (7^3, 9^3), the three wirings (unrewired, lambda 0.4, lambda 1.0), each with `conn_survey`
  and `substep1` at the eight gains (10 injected groups per job), archived regime otherwise (the first E0 job of
  `session71-d4-s0-p00.json` and `session73-g9-d4-s0-a.json`).
- **Cost:** 1 pod, RTX PRO 4000 Blackwell, $0.57/h, 11:42 to about 11:47 UTC, about $0.05 (estimated);
  terminated (delete 204, `list-pods` empty).
- **Next:** commit the code (the clone takes only commits), pull it into the volume's clone, run the four
  sessions on four pods.

## Step 2 (pods `qvf2rifaldvrk2`, `qom2nz5qxv6qy9`, `s4z11qnj74ymb7`, `9ugmyma1756x7p`, 2026-10-30): wiring

- **Hypothesis:** the engine's own wiring, now correct, falls with distance; whether its activity stays local
  enough for distinct routes decides between it and rewiring (revision 1).
- **Change:** commit edc3c9e pulled into the volume's clone (bundle, fast-forward; clean). Sessions
  `rerun2a` to `rerun2d` (7^3 and 9^3, network seeds 0 and 1), started with `runpod_assembly_runner.sh start`,
  about 100 s each; pods a and b RTX PRO 4000 Blackwell, c and d RTX PRO 4500 Blackwell (the 4000 had no
  capacity left; both SM 120, checked before each start). Summary: `python rerun_wiring_summary.py output
  "rerun2*"` (`output/rerun2-summary.json`).
- **Result, connectivity** (E -> E synapses per group pair, median, at 1, 2, 4, 8 cells; effective lambda;
  both seeds agree within a few synapses):

  | wiring | 7^3 | lambda_eff 7^3 | 9^3 | lambda_eff 9^3 |
  |---|---|---|---|---|
  | engine's own | 457, 356, 222, 73 | 3.8 | 324, 264, 138, 41 | 4.0 |
  | rewired, lambda 1.0 | 1495, 559, 95, 3 | 1.1 | 1291, 479, 79, 2 | 1.1 |
  | rewired, lambda 0.4 | 1316, 135, 2, 0 | 0.46 | 1261, 130, 1, 0 | 0.42 |

  The fit returns the rewired networks' lambda (0.42 to 0.46 for 0.4, 1.1 for 1.0), so the engine's own
  wiring has an effective lambda of about 4 cells. At 9^3 the corner-to-corner pairs again hold more synapses
  than the next distance (43 and 53 against 23).
- **Result, intra-group E -> E synapses per excitatory neuron, over all groups** (min, median, max): engine's
  own 7 / 13 / 18 (7^3), 6 / 10 / 14 to 16 (9^3); lambda 0.4 512 to 594 / 842 to 846 / 1161 to 1277 (7^3),
  535 to 560 / 809 / 1197 to 1203 (9^3); lambda 1.0 50 to 64 / 121 to 123 / 263 to 333 (7^3), 50 to 51 / 103 /
  278 to 287 (9^3). The ratio max / min is about 2.5 in the engine's own wiring and at lambda 0.4, 5 to 6.6 at
  lambda 1.0.
- **Result, activity** (Substep 1, 10 injected groups per job, archived regime with `gain` varied; spread =
  the largest distance at which another group exceeds 0.1; both seeds similar):

  | gain | engine's own, 7^3 / 9^3 | lambda 1.0, 7^3 / 9^3 | lambda 0.4, 7^3 / 9^3 |
  |---|---|---|---|
  | 2 to 8 | 0 / 0 | 0 / 0 | 0 / 0 (gain 2 and 3: 4 to 8 of 10 groups recruited) |
  | 12 | 0 to 5 / 0 to 3 | 0 to 1 / 0 to 1 | 0 to 1 / 0 to 1 |
  | 16 | 3 to 7 / 0 to 6 | 0 to 2 / 0 to 2 | 0 to 1 / 0 to 1 |
  | 24 | 5 to 9 (one runaway) / 4 to 8 | 1 to 4 / 1 to 5 | 0 to 2 / 1 to 2 |

  Mean peak activity of the groups at distance 1 at gain 16: engine's own 0.5 to 0.7, lambda 1.0 0.07 to
  0.15, lambda 0.4 0.04 to 0.07; at gain 24: 0.6 to 0.8, about 0.2 to 0.3, 0.17 to 0.29. In the engine's own
  wiring the injected group stays alone up to gain 8, and above it activity reaches across much of the grid
  (spread up to 9 of at most 10 cells at 7^3, 8 of 14 at 9^3), with half of the groups still silent at gain 12
  (bimodal); the rewired networks
  stay within 1 to 2 cells at lambda 0.4 and within 1 to 5 at lambda 1.0 at every gain run.
- **Cost:** 4 pods, 12:06 to about 12:12 UTC, 2 x $0.57/h and 2 x $0.72/h, about $0.24 (estimated); terminated
  (delete 204 each, `list-pods` empty). The first collector, started from Git Bash, failed (its `-F NUL` needs
  Windows OpenSSH); run from PowerShell it collected all four.
- **Decision:** the user's (report, step 2).

## Step 3 (6 session pods and 1 summary pod, 2026-10-30): operating regime on three wirings

- **User decision:** step 3 runs rewiring at lambda 0.4 (baseline), at lambda 1.0 and the engine's own wiring
  (revision 8 of `runpod-assembly-association-task.md`); the wiring of steps 4 to 7 is discussed after step 3.
- **Hypothesis:** step 2 varied only `gain`; with the inter-group gain, the inhibitory gain and the intra-group
  total varied as well, each wiring may have a regime in which a single group is recruited without spill, an
  untrained path does not transmit and a saturated one does (the archive's criteria, iterations 40 and 41).
- **Change:** parameter files `params/rerun3{a..f}-regime-{own,lam0.4,lam1.0}-s{0,1}.json` (7^3, network seeds
  0 and 1), uploaded to `/workspace/engine-fix-rerun/params/` outside the clone (no code change; clone at
  edc3c9e). Per configuration: Substep 1 on 100 groups and `diag_saturated_path` (radius 1, 6 pairs) at d 4 and
  6. Grid: gain 4 with `gain_ee_inter` 0.3, 0.6, 1.2, 2.4, 4.8 x `gain_ie` 2, 4, 8 x intra total 20, 40; gain 8
  with `gain_ee_inter` 0.3, 0.6, 1.2, 2.4 x `gain_ie` 2, 4, 8, total 40 (42 configurations, 126 jobs per
  session, about 12 s per configuration). Pods a, b RTX PRO 4000, c to f RTX PRO 4500 (SM 120). The I -> I gain
  question of the task is gone: the corrected engine builds no I -> I synapses (step 1).
- **Summary:** `rerun_regime_summary.py` (run on a pod: on the host it did not finish in minutes and slowed the
  host, 11 MB of results per session; on the pod 5 s); `output/rerun3-summary.txt` and `.json`.
- **Result** (both seeds agree; Substep 1 pass of 100, saturated path transmitting at d 4 / d 6, fraction of 6
  pairs; the untrained path transmits in no configuration below gain 8 except single pairs):

  | wiring | configurations passing Substep 1 (>= 97) with a saturated path transmitting at d 4 and d 6 (>= 5 / 6) |
  |---|---|
  | engine's own | gain 4: `gain_ee_inter` 1.2 at every `gain_ie` (2, 4, 8) and total (20, 40): 100 / 100, 1.00 / 1.00; 2.4 likewise (99 to 100); gain 8: 1.2 with `gain_ie` 2 (98 to 100) |
  | lambda 1.0 | gain 4, total 40: `gain_ee_inter` 1.2 with `gain_ie` 2 or 8, 2.4 with every `gain_ie` (97 to 100); gain 8: 1.2 with `gain_ie` 2 (96 to 100) |
  | lambda 0.4 | gain 4, total 40: `gain_ee_inter` 1.2 with `gain_ie` 2, 2.4 with `gain_ie` 2 or 4 (98 to 100); gain 8: 1.2 with `gain_ie` 2 (98 to 99) |

  - Recruitment: intra total 20 leaves groups under-recruited in the rewired networks (about 77 of 100 at
    lambda 0.4, about 50 at lambda 1.0), none in the engine's own wiring; total 40 recruits every group.
  - Spill begins at `gain_ee_inter` 2.4 with `gain_ie` 8 (1 to 12 groups), grows at 4.8 (all wirings) and at
    gain 8 with `gain_ie` 4 or 8; in the engine's own wiring it then reaches 6 to 10 cells, in the rewired ones
    1 to 5. Runaways only in the engine's own wiring
    at gain 8, `gain_ee_inter` 2.4, `gain_ie` 4 or 8 (5 and 91 to 92 of 100 groups).
  - The archived regime (gain 4, `gain_ee_inter` 0.6, `gain_ie` 2, total 40) passes Substep 1 (98 to 100) in
    every wiring, but a saturated path transmits in at most 1 of 6 pairs at d 4 and none at d 6: on the
    corrected network the inter-group gain must be about twice as high (1.2) for a learned path to carry.
- **Cost:** session pods a 12:26 to 12:41 and b to 12:43 UTC (RTX PRO 4000, $0.57/h), c, d to 12:46 and e, f
  to 12:50 (RTX PRO 4500, $0.72/h), summary pod 12:54 to 12:58 ($0.72/h): about $1.41 (estimated); all
  terminated (delete 204 each; `list-pods` then showed only `xt2eohm6688yx9`, "rm6-precheck", an RTX 4090
  created at 12:56 UTC by another session, not touched).
- **Decision:** the user's (report, step 3).

## Step 4 (3 pods, 2026-10-30): propagation survey on three wirings

- **User decision:** step 4 runs all three wirings (it is cheap); the wiring of steps 5 to 7 is decided after
  step 4 (revision 8).
- **Question:** in the step 3 regime region, does activity propagate in a graded way between A and B under
  joint injection (the path fires, nothing beyond A, B and the path), or all-or-none, with pair-dependent
  thresholds (A4)?
- **Change:** parameter files `params/rerun4{a..f}-prop-{own,lam0.4,lam1.0}-s{0,1}.json` (7^3, network seeds 0
  and 1): `prop_survey`, 12 pairs at d 4, gain 4, intra total 40, energy off, `gain_ee_inter` 0.6, 0.9, 1.2,
  1.8, 2.4, 3.6 x `gain_ie` 2, 4, 8; otherwise as `session54a-prop2.json`. Uploaded to
  `/workspace/engine-fix-rerun/params/` (clone unchanged at edc3c9e). Only three of six pods could be created
  (capacity), so each pod runs two sessions side by side: a RTX PRO 4000 (own), c and d RTX PRO 4500 (lambda
  0.4, lambda 1.0), all SM 120, the volume's build checked as SM 120 before each start.
- **First attempt:** four of the six sessions (a, c, d, e) stopped in preflight with exit code 3: two sessions
  started together on a fresh pod both downloaded vispy's sample data (`volume/stent.npz`, read by
  `chem_volume.py`) and collided on `/root/.vispy/data/volume` (as in step 1). Fetched once per pod, then
  restarted; all six ended with exit code 0. No job of the failed attempts had run.
- **Result** (`assoc_selectivity.py --propclass` and `--prop` on a pod: `output/rerun4-propclass.txt`,
  `output/rerun4-prop.txt`; per job 12 pairs; good = the middle of the route fires under joint injection, M >=
  0.2 spikes per excitatory neuron, with nothing beyond A, B and the route; silent = M < 0.05; explosive =
  spread or runaway):
  - Up to `gain_ee_inter` 2.4, at every `gain_ie`, every pair in every wiring is silent, except at `gain_ie` 8
    in the rewired networks: 1 to 3 pairs between silent and good at lambda 1.0 (M 0.05 to 0.2), 1 pair at
    lambda 0.4. Under joint injection without learning, the neurons between A and B do not fire; the median M
    is 0.00 in every job.
  - At `gain_ee_inter` 3.6 the engine's own wiring turns explosive in a pair-dependent way (2 to 8 of 12 pairs),
    with one good pair per seed (`gain_ie` 8: pair 9 at seed 0, pair 5 at seed 1); the rewired networks stay
    silent or weakly active (lambda 1.0, `gain_ie` 8: up to 5 pairs weakly active, 2 explosive at seed 1).
- **Cost:** 3 pods, 13:07 to about 13:19 UTC (1 x $0.57/h, 2 x $0.72/h), about $0.40 (estimated); terminated
  (delete 204 each; `list-pods` then showed only `xt2eohm6688yx9`, another session's RTX 4090, still without a
  runtime since 12:56 UTC, not touched).
- **Decision:** the user's (report, step 4).
