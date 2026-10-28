# Task: Rate Model for Screening the Assembly-Association Parameters

> [!NOTE]
> **Approved (2026-10-29); on hold, do not start without the user's go.** A tool for the
> sparse-assemblies task (`../sparse-assemblies-task.md`, "the sparse task"): it never decides a path
> on its own, it only narrows the parameter ranges that the sparse task then tests with the spiking
> network on pods. **[default]** marks a starting value the agent may change (log the reason).

## Why

Every decision in the sparse task costs pod time (about $2.4 per full decision of 144 jobs). Many
choices are ranges to scan: the connection length lambda, the diffusion length and threshold of the
C1 field, `lam_sup`, the C2 gate. A model with one rate per location group, the same lattice, wiring
statistics, fields and protocol, runs on CPU in seconds and can discard settings that cannot work
before any pod session. It is only useful if it reproduces what the spiking network did.

## Read first

1. `../sparse-assemblies-task.md`: Terms, Setup, Paths, Method (the vocabulary used here).
2. `../runpod-assembly-association-report.md`: "The protocol that passes" and "What is established".
3. `../tuning-log.md`, iterations 56, 59, 61 and 64 (the runs to calibrate against).
4. Code to reuse rather than rewrite: `../assoc_fields.py` (`ChemicalField`, `FuelField`),
   `../assoc_build.py` and `../assoc_engine.py` (grid, `rewire` by distance), and the per-pair
   summaries of `../assoc_sweep_summary.py` (`-v`). Results are in `../output/assoc-s*.tgz`
   (gitignored; local only).

## Model

- One unit per location group (343 on 7 x 7 x 7): excitatory and inhibitory rates with a sigmoid
  transfer function and a time constant of **[default]** 10 steps (1 step = 1 ms).
- Coupling between groups: the expected number of synapses from the spiking network's connection
  rule (`rewire`, lambda) times the mean weight and the gains of the passing protocol (`gain_ee_inter`,
  `gain_ie`, intra-group boost for assemblies).
- Fields C1, C2, C3 with `ChemicalField` / `FuelField` unchanged, released from the group rates.
- Plasticity on the group-to-group couplings: rule `both` approximated as rate products, `w_fast` and
  `w_perm` as in the protocol.
- Protocol, tests and measures as in the sparse task (transfer, ignition, strays, `R_off`).

## Substeps

**1. Build** the model and module checks (CPU): coupling counts match the spiking network's
connection statistics within 5 %; a field driven by constant rates matches `ChemicalField` exactly.

**2. Admission test** against the spiking runs, decided before use: for the 24 pairs at d 4 of the
s71 reference setting (E0), the model must place the pairs that transfer contained, ignite, or never
transfer better than chance (**[default]** Cohen's kappa >= 0.4), and reproduce the two qualitative
results "larger grid removes ignitions and most transfers" (iteration 61) and "uniform C2 gives the
same associations" (iteration 64). Fit only the sigmoid's threshold and gain and the time constant,
on seed 0; test on seed 1. If the test fails, stop and report; the model is not used.

**3. Screening runs** (only after admission): scans requested by the sparse task, such as lambda
against d / lambda, C1 diffusion length and L4's starting threshold. Each scan reports the settings
it excludes and why; the sparse task tests the remaining ones on pods.

## Rules

- CPU only, on the host (the host is weak: keep each run small, one process at a time); no pods.
- Work only in this folder; import from the parent folder, do not change its files.
- No commits without the user's go.
- **Files:** this file, `rate-model-report.md`, `rate_model.py`, `test_rate_model.py`.
