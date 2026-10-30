# Synapse construction (wiring)

How `snngine_v4` builds the synapses of a network: which neuron connects to which, with which delay and initial
weight. Covers `Synapses.fill_tensors` (`snngine_v4/nn/synapses.py`), the construction kernels
(`nn/cuda_backend/src/construction/snn_representation.cu`, `nn/cuda_backend/src/operators/connector.cu`) and the
tables `NetworkReservoir` prepares for them (`nn/spnn_reservoir.py`). The generic config → build machinery is in
`construction.md`; the per-file overview of `nn/` in `nn.md`. This file goes to kernel level on purpose: the memory
layout of these arrays, written by kernels and read by Python (or the reverse), is where construction errors hide.

The invariants a correct build satisfies are at the end; `snngine_v4/tests/` checks each of them.

## Terms

- **Location group** (G of them): the neurons in one cell of the reservoir's grid. The engine numbers groups
  z dim^2 + y dim + x (checked on 7^3 and 9^3 builds).
- **Type connection**: one configured connection between neuron types, `NTypeGroupConn` (source type, target type,
  initial weight `w0`, synapses per neuron `n_synapses`). Default (`n_type_groups.py`, gen_factors inhibitory :
  excitatory = 1 : 4): inhibitory -> excitatory with all S synapses; excitatory -> inhibitory S/5 and
  excitatory -> excitatory 4 S/5 (400 and 1600 at S 2000). There is no inhibitory -> inhibitory connection.
- **Slot range**: the synapse columns a type connection fills while it is built (`syn_idx` to
  `syn_idx + n_synapses`, `NTypeGroupConn.location`); excitatory neurons: 0 to S/5 - 1 for inhibitory targets,
  the rest for excitatory ones.
- **Delay**: whole steps between a spike and its arrival, from the distance between the source's and the target's
  groups: round((D - 1) d / d_max) (`spnn_reservoir.py:116`), 0 within a group.
- **Delay bucket**: a neuron's synapses with one delay; its synapses are stored sorted by delay, and `N_delays`
  holds the bucket boundaries.
- **Local / global target index**: during construction a target is first an index within the target-type
  neurons of the groups at that delay (local), then the neuron's index in the network (global).

## Layout of the arrays

N neurons, S synapses per neuron, D delays, G groups. Neurons are ordered inhibitory first, then excitatory, each
sorted by group (`NetworkReservoirConfig.sort_pos`; `NeuronFlags.cls_validate_data` checks the order).

| array | shape and index | written by | read by |
|---|---|---|---|
| `N_rep` (tensor shape (S, N)) | during construction: (N, S) row-major, element n S + s; after the conversion in `fill_tensors` (`synapses.py:420`): (S, N), element n + N s | construction kernels (n S + s), then the conversion | simulation `update_current_` (n + N s), `fill_N_rep_groups_`, Python (`gpu_values[s, n]`) |
| `N_rep_buffer` (sort keys) | (N, S) row-major, n S + s | `k_set_locally_indexed_connections`, `reindex_N_rep_` | `sort_N_rep` |
| `N_delays` | (D + 1, N), element n + N d: number of synapses of neuron n with delay < d (row 0 = 0, row D = S) | `k_set_locally_indexed_connections` (sum over the neuron's type connections) | `update_current_`: synapses [N_delays[n + N k], N_delays[n + N (k + 1)]) receive a spike k steps after it |
| `N_weights` | (S, N), element n + N s | `fill_tensors` (by the synapse's type pair) | simulation, Python |
| `N_states` | (rows, N): 0 pt, 1 u, 2 v, 3 to 6 a, b, c, d, 7 input current | presets, simulation | simulation, Python |
| `N_flags` | (rows, N): 0 sensory input, 1 type (1 inhibitory, 2 excitatory), 2 group, 3 neuron model (0 Izhikevich) | `fill_N_flags_group_id_and_G_neuron_count_per_type` | all |
| `L_Group_neuronCounts` | (2 + 2 D, G): row 0 inhibitory and row 1 excitatory neurons of the group; row 2 + d inhibitory and row 2 + D + d excitatory neurons in groups at delay d | `fill_N_flags_...`, `fill_G_neuron_count_per_delay` | count kernels, `SynCounts` |
| `G_neuron_typed_ccount` | (2 G + 1,): cumulative neuron counts, inhibitory groups then excitatory groups (first global index of each group's neurons of a type) | `spnn_reservoir.py:94` | `k_set_locally_indexed_connections`, `reindex_N_rep_` (`cc_src`, `cc_snk`) |
| `G2G_delay_distance`, `G_rep` | (G, G): delay between groups; per source group the target groups sorted by delay | `spnn_reservoir.py:116-137` | count and construction kernels |
| `G_exp_ccsyn_per_src_type_and_delay` | (2 (D + 1), G): per source type, cumulative expected synapses per delay (rows 0 to D inhibitory sources, D + 1 to 2 D + 1 excitatory sources) | `fill_G_exp_ccsyn_per_src_type_and_delay_` | `SynCounts`, `cc_syn_` (inhibitory -> excitatory) |
| `G_exp_exc_ccsyn_per_snk_type_and_delay` | (2 (D + 1), G): excitatory sources split by target type (rows 0 to D inhibitory targets, D + 1 to 2 D + 1 excitatory) | `SynCounts.fill_tensors` (Python) | `cc_syn_` (excitatory -> inhibitory, excitatory -> excitatory) |

## Pipeline (`Synapses.fill_tensors`, `synapses.py:288`)

1. **Groups and counts** (before `fill_tensors`, `NetworkReservoir`): group of every neuron from its position,
   neuron counts per group and type, `G_neuron_typed_ccount`, the group-to-group delays, `G_rep`, and the target
   neurons per source group, type and delay (`L_Group_neuronCounts`).
2. **Expected synapses per delay** (`SynCounts.fill_tensors`, `synapses.py:68`): the kernel
   `fill_G_exp_ccsyn_per_src_type_and_delay_` fits a connection probability per group that falls with delay
   (`sigmoidal_connection_probability`, `roughly_optimize_connection_probabilities`) so that S synapses are spent,
   and writes cumulative expected counts per delay; a final correction sets the total to S, spread over the delay
   buckets from the one with the most targets on, each bucket kept within its available targets
   (`spread_ccsyn_correction`); the validator checks every bucket. `SynCounts` splits the
   excitatory sources' counts by target type (S/5 and 4 S/5) and corrects buckets that would exceed the available
   targets (`output_correction`, `validate_sink_counts`).
3. **Local targets** (`RepBackend.fill_N_rep`, `synapses.py:346`; kernel `k_set_locally_indexed_connections`,
   `connector.cu`), once per type connection: for each source neuron and delay, the bucket's slots (from the
   connection's cumulative counts, `cc_syn`) receive distinct random local indices within that delay's target
   neurons; the own index is excluded at delay 0 when source and target type are the same. Writes `N_rep` at
   n S + s, the sort key (bucket start) and the neuron's `N_delays` column.
4. **First sort** (`sort_N_rep`, `synapses.py:378`): each bucket's local indices in ascending order (keys keep the
   buckets in place).
5. **Global targets** (`reindex_N_rep`, `synapses.py:390`; kernel `reindex_N_rep_`), once per type connection:
   local index -> global neuron index, walking the target groups of that delay (`G_rep`) through the target type's
   cumulative counts (`cc_snk`); sort key n S + delay.
6. **Final sort** (`sort_N_rep`, `synapses.py:410`): each neuron's synapses by delay over all its type
   connections (within a delay by target index), matching the buckets of `N_delays`.
7. **Layout conversion** (`synapses.py:420`): from (N, S) row-major to the (S, N) layout the simulation reads.
8. **Group of each target** (`fill_N_rep_groups`) and **initial weights**: each synapse gets the `w0` of its
   (source type, target type) connection, set from the actual target types after the final sort.
9. **Presynaptic index** (`SnnRepresentation.actualize_N_rep_pre_synaptic`, called at the end of
   `fill_tensors`): per neuron its incoming synapses (`rep_pre_synaptic_counts` cumulative in-degrees, `_idcs`
   synapse indices n + N s, `rep_pre_synaptic` their source neurons), read by the engine's STDP; deleted synapses
   (target -1 or -2, `remove_synapses_to_group`) are not listed.

## What the assembly harness does on top

`setups/runpod-assembly-association/assoc_engine.py` (`AssocEngine.rewire_by_distance`, used from iteration 40) redraws
every synapse's target by distance (exp(-d / lambda)) while keeping the target's type, recomputes the delays with
the same rule and re-sorts the buckets; gains and weights by type pair are set by `set_gains` and `typed_weights`.
The per-neuron numbers of synapses onto each type therefore come from the engine's construction. Rewiring does
not rebuild the presynaptic index (step 9): the harness keeps the engine's STDP off; before using it on a rewired
network, call `RepBackend.actualize_N_rep_pre_synaptic()` again. Details in the harness's task files.

## Invariants of a correct build

Checked by `snngine_v4/tests/network_invariants.py` (on exported arrays) and `test_engine.py` (GPU builds).

1. Every target index is a valid neuron; no synapse onto its own neuron.
2. Every neuron has exactly the configured number of synapses onto each target type (`n_synapses` of its type
   connections), and none onto a type without a configured connection.
3. `N_delays` columns start at 0, end at S and do not decrease.
4. Every synapse's delay bucket equals round((D - 1) d / d_max) for its groups; the engine's
   `G2G_delay_distance` equals this rule recomputed from the group cells.
5. Every synapse's initial weight is the `w0` of its (source type, target type) connection.
6. The construction's cumulative count tables are non-decreasing, end at the connection's synapse count, and no
   delay bucket exceeds the available target neurons of that type at that delay.
7. All neurons of a group lie in one grid cell; different groups lie in different cells.
8. Excitatory -> excitatory synapses per group pair fall with distance (the configured probability falls with
   delay).
9. A spike of neuron n delivers exactly its bucket-k synapses' weights to their targets k steps later (delivery
   probe), and the engine's dynamics equal an independent numpy reference within float32 summation rounding.
