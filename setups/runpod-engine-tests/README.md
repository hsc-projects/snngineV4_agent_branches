# Engine tests on Runpod

Runs the engine's test suite (`snngine_v4/tests/`) on a Runpod GPU pod, on a packed copy of the repository, so
that a run tests exactly a chosen state of the code and never touches the code or the backend build on the shared
network volume (other sessions import from there). The development host runs nothing but these scripts' ssh/scp.

| file | what |
|---|---|
| `pack_tree.sh` | packs the code to test: `worktree` (the local working tree) or `head` (the engine as committed, with the working tree's tests and support files) |
| `pod_run_tests.sh` | on the pod: unpacks to `/root/engine-tests/tree`, takes the CUDA backend from the build cache or builds it inside the copy (`runpod-engine-smoke-test/runpod_engine_test_runner.sh build`) and caches it, compiles the tests, runs them, writes a summary and a `finished` marker to `/workspace/output/engine-tests/<run>/` |
| `run_on_pod.py` | on the host: uploads the pack and the pod script, starts the run detached, waits for the marker, downloads the results to `results/<run>/` and prints the summary |
| `engine-tests-report.md` | one entry per run: code state, level, GPU, duration, cost, results |
| `results/` | downloaded logs and summaries (gitignored) |

## Levels

- `quick` (default): the small configurations (`small`, `odd`, for the construction tests and the probes), for
  routine checks.
- `full`: all configurations, adding the assembly networks 7 x 7 x 7 and 9 x 9 x 9 (85 million synapses) and the
  D 16 probes (`ring16`); after changes to the construction or the simulation, and before a commit.

`--configs a,b` runs exactly the named configurations instead (names in `test_engine.py` and
`test_engine_probes.py`).

## Caches (on the volume, in their own folder `/workspace/engine-tests-cache/`)

- `builds/<hash>-sm<arch>/`: compiled CUDA backends, keyed by a hash of the backend's C++/CUDA sources and
  CMakeLists (including the staged fallback in `runpod-engine-smoke-test/`), the nvcc and Python versions, and the
  GPU architecture. A change to the CUDA code gives a new key and a fresh build; Python-only changes reuse the
  cached build. The copy is always unpacked to the same path, because the compiled libraries refer to each other
  by absolute path.
- `apt/`: the package files of the build tools (cmake, Mesa/EGL and Python headers), installed into the container
  only when missing.

Delete a cache folder to force a rebuild. These caches are separate from the backend build that the assembly
runner uses (`snngine_v4/nn/cuda_backend/build*` on the volume).

## A run

1. Create a GPU pod with the network volume (`setups/runpod-technical.md`, "Running pod sessions"); quote the
   price first. Any architecture works (the build is cached per architecture). One run per pod at a time (the copy's
   path is fixed).
2. Pack and run (Git Bash, from the repository root):

```bash
bash setups/runpod-engine-tests/pack_tree.sh worktree setups/runpod-engine-tests/results/tree-worktree.tgz
```

```bash
python setups/runpod-engine-tests/run_on_pod.py --host HOST --port PORT --tree setups/runpod-engine-tests/results/tree-worktree.tgz --run fixed-01 --level quick
```

   `--no-wait` starts the run and returns.
3. Terminate the pod once the results are downloaded; add an entry to `engine-tests-report.md`.

Old against new: pack `head` and `worktree` and run them on two pods at the same time.

## Durations (measured 2026-10-30, RTX PRO 4000 Blackwell)

| | first run (CUDA build) | with a cached build |
|---|---|---|
| pod start | about 1.5 min | about 1.5 min |
| build tools | 20 s | 20 s |
| CUDA backend | 55 s | about 1 s |
| `quick` tests | about 95 s | about 95 s |
| `full` tests | about 165 s | about 165 s |
