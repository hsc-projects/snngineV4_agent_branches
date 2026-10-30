# Archive: Results on the Faulty Engine (before 2026-10-30)

Everything here was produced with the engine up to commit a102f3d, before the engine fixes of 2026-10-30
(commit f56ccf8 and later). Its main defect, a transposed synapse table, scrambled every built network: each
neuron's synapses came from other neurons' rows (wrong number of targets per type, I -> I synapses, connectivity
that did not fall with distance). The defects and the tests that now guard against them are in
`setups/runpod-engine-tests/engine-tests-report.md`; which results they invalidate, and the order in which they
are re-established, in `../engine-fix-rerun-task.md`.

Kept as a record, not as evidence: do not build on a number or conclusion from here unless the rerun task has
re-established it. Still valid: the Substep 0 to 3 checks of s1 (synthetic input) and SP0, the field-geometry
check (no engine; entry 1 of `sparse-tuning-log.md`, Substep 0 of `sparse-assemblies-report.md`).

| file | what |
|---|---|
| `runpod-assembly-association-report.md` | report of the minimal-version task (`../runpod-assembly-association-task.md`), iterations 1 to 65 |
| `tuning-log-1-37.md`, `tuning-log.md` | its tuning log, iterations 1 to 37 and 38 to 65 |
| `sparse-assemblies-report.md`, `sparse-tuning-log.md` | report and log of the sparse-assemblies task (`../sparse-assemblies-task.md`), SP0 to SP3 |
| `params/` | parameter files of sessions s1 to s77 and of SP1 to SP3, with their generator scripts |
| `rate-model/` | rate-model reports of rounds 1 to 5 and their spiking ground truth (`s71_ground_truth.json`, `s73_g9_d4_pairs.json`); the code and the round 6 report stay in `../rate-model/` |
| `output/` | downloaded session results (gitignored, local only); the copies on the network volume were not moved |

Paths inside these files refer to their old locations (one folder up).
