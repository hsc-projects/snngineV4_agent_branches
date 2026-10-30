# snngine_v4 tests

Correctness tests for the engine: the built network is compared with its configuration and with independent
recomputations, the simulation with an independent numpy reference. Background and the invariants:
`agents/mapping/synapse-construction.md`.

| file | what |
|---|---|
| `network_invariants.py` | invariant checks on exported arrays (numpy only) |
| `reference_dynamics.py` | numpy reference of the neuron update and spike delivery |
| `engine_export.py` | builds one network on the GPU and exports it, with a delivery probe and an injected run |
| `test_network_invariants.py` | the checks and the reference on synthetic networks, including mutations that reproduce known construction errors (numpy only) |
| `test_engine.py` | the checks, the probe and the reference on engine builds of several configurations (GPU; skipped unless `SNN_ENGINE_TESTS=1`) |
| `test_ring_buffer.py` | the simulation's spike ring buffer transliterated to Python and replayed with synthetic spike counts (numpy only) |
| `engine_probes.py` | records probes of the other CUDA paths on one GPU build: presynaptic index, STDP, ring buffer under near-total activity, chemistry, thalamic and sensory input, synapse removal |
| `test_engine_probes.py` | tests on those probes (GPU; skipped unless `SNN_ENGINE_TESTS=1`) |

Not covered: `SnnRepresentation.swap_groups` (no Python caller) and the plot kernels (visual only).

Run on a GPU pod (the development host is for editing only), normally through `setups/runpod-engine-tests/`
(packs the code, builds the backend inside the copy, runs, collects). The commands it runs, from the root of the
copy:

```bash
PYTHONPATH=$PWD python -m unittest discover -s snngine_v4/tests -p "test_*.py" -v
SNN_ENGINE_TESTS=1 PYTHONPATH=$PWD python -m unittest discover -s snngine_v4/tests -p "test_*.py" -v
```

`SNN_ENGINE_CONFIGS=small,odd` selects configurations, `SNN_ENGINE_EXPORT_DIR=...` keeps the exports. The
headless build goes through the assembly harness's builder (`setups/runpod-assembly-association/assoc_engine.py`),
currently the only headless builder. A change to the engine comes with a test that fails before it and passes
after it.
