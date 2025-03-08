from typing import ClassVar

import torch

from snngine_v4.geometry.grid.finite_grid import FiniteGrid
from snngine_v4.nn.construction.config_models.neurons.synapse_model import \
    (
    SynapseCountTensors, SynapseModel,
)
from snngine_v4.nn.construction.config_models.reservoir.nn_reservoir_config \
    import NetworkReservoirConfig


# noinspection PyUnresolvedReferences
from snngine_v4.nn.cuda_backend import snn_utils, snn_construction_gpu

from snngine_v4.nn.construction.engine_element import EngineElement
from snngine_v4.nn.neuron_states import NeuronState
from snngine_v4.nn.synapses import Synapses, SynCounts
from snngine_v4.utils.cuda_utils.tensor_dataframe import TensorDataFrame
from snngine_v4.utils.cuda_utils.tensor_dict import TensorDict


# noinspection PyPep8Naming
class NetworkReservoir(EngineElement):

    BUILDER_OBJECT_CLASS_MAP: ClassVar[dict] = {
        SynapseModel: Synapses,
        SynapseCountTensors: SynCounts
    }

    config_model: NetworkReservoirConfig

    L_Group_neuronCounts: TensorDataFrame
    L_Group_flags: TensorDataFrame
    L_Group_properties: TensorDataFrame
    L_Group2Group_flags: TensorDict
    L_Group2Group_properties: TensorDict

    neuron_states: NeuronState
    synapses: Synapses

    def __init__(self, model: NetworkReservoirConfig, device,
                 parent_element=None, **kwargs):

        super().__init__(device=device,
                         parent_element=parent_element,
                         config_model=model, n_curand_states=model.N, **kwargs)

        G = self.config_model.G
        D = self.config_model.D

        self.grid: FiniteGrid = self.add_build(self.config_model.grid)

        self.N_pos = torch.tensor(self.config_model.pos, device=self.device)
        self.G_neuron_typed_ccount = self.zeros_i32((2 * G + 1))
        self.L_Group_delay_counts = self.zeros_i32((G, D + 1))

        self.pseudo_tensor_i32 = self.zeros_i32((1, 1))
        self.fill_tensors()

    def fill_tensors(self,):
        N = self.config_model.N
        S = self.config_model.S
        G = self.config_model.G
        D = self.config_model.D
        model: NetworkReservoirConfig = self.config_model
        type_col = model.neuron_states.N_flags.index.N_type
        group_col = model.neuron_states.N_flags.index.L_group

        for g in self.config_model.type_groups:
            # Set Neuron Type
            # self.N_flags.type[g.start_idx:g.end_idx + 1] = g.ntype.value
            self.neuron_states.N_flags[type_col][g.start_idx:g.end_idx + 1] = (
                g.ntype.value)

        self.N_pos = torch.tensor(self.config_model.pos, device=self.device)

        # rows[0, 1]: inhibitory count, excitatory count,
        # rows[2 * D]: number of neurons per delay (
        # post_synaptic type: inhibitory, excitatory)
        snn_construction_gpu.fill_N_flags_group_id_and_G_neuron_count_per_type(
            N=N, G=G, N_pos=self.N_pos.data_ptr(),
            # N_pos_shape=self.reservoir_config.reservoir_shape.as_tuple(),
            N_pos_shape=self.config_model.grid.shape.as_tuple(),
            N_flags=self.neuron_states.N_flags.data_ptr(),
            # G_shape=self.reservoir_config.reservoir_segmentation.as_tuple(),
            G_shape=self.config_model.grid.seg.as_tuple(),
            G_neuron_counts=self.L_Group_neuronCounts.data_ptr(),
            N_flags_row_type=self.neuron_states.N_flags.get_idx_loc(type_col),
            N_flags_row_group=self.neuron_states.N_flags.get_idx_loc(group_col),
            N_pos_n_cols=self.N_pos.shape[1]
        )

        ravel_counts = self.L_Group_neuronCounts[: 2, :]
        self.G_neuron_typed_ccount[1:] = ravel_counts.ravel().cumsum(dim=0)

        self.neuron_states.N_flags.sync_to_df()
        self.config_model.neuron_states.N_flags.validate_data(
            data=self.neuron_states.N_flags, N_pos=self.N_pos,
            # shape=self.reservoir_config.reservoir_shape.as_tuple(),)
            shape=self.config_model.grid.shape.as_tuple(),)

        b_thalamic_input_row = model.L_Group_flags.index.b_thalamic_input
        sensory_input_type_row = model.L_Group_flags.index.sensory_input_type
        b_monitor_group_firing_count_row = (
            model.L_Group_flags.index.b_monitor_group_firing_count)

        self.L_Group_flags[b_thalamic_input_row] = 0
        self.L_Group_flags[b_thalamic_input_row][: G // 2] = 1
        self.L_Group_flags[sensory_input_type_row] = -1
        self.L_Group_flags[b_monitor_group_firing_count_row] = 1

        G_pos = torch.tensor(self.grid.pos, device=self.device)

        G_distance = torch.cdist(G_pos, G_pos)
        max_dist = G_distance.max()
        G_delay_distance = ((D - 1) * G_distance / max_dist).round().int()
        G_rep = (torch.sort(G_delay_distance, dim=1, stable=True)
                 .indices.int())

        dist_idx = self.config_model.L_Group2Group_properties.index
        LG2GF_idx = self.config_model.L_Group2Group_flags.index

        self.L_Group2Group_properties[dist_idx.distance][:] = G_distance
        self.L_Group2Group_flags[LG2GF_idx.delay_distance][:] = G_delay_distance
        self.L_Group2Group_flags[LG2GF_idx.rep][:] = G_rep

        snn_construction_gpu.fill_G_neuron_count_per_delay(
            S=S, D=D, G=G,
            G_delay_distance=self.L_Group2Group_flags[LG2GF_idx.delay_distance]
            .data_ptr(),
            G_neuron_counts=self.L_Group_neuronCounts.data_ptr())

        self.config_model.L_Group_neuronCounts.validate_data(
            data=self.L_Group_neuronCounts.gpu_values,
            type_groups=self.config_model.type_groups, D=D, G=G,)

        for d in range(D):
            self.L_Group_delay_counts[:, d + 1] = (
                self.L_Group_delay_counts[:, d]
                + G_delay_distance.eq(d).sum(dim=1))

        # self.sync_to_cpu()

        self.neuron_states.apply_preset()

        self.synapses.RepBackend = self._generate_RepBackend()

        group_row = self.config_model.neuron_states.N_flags.index.L_group
        self.synapses.fill_tensors(
            S=S, D=D, G=G, N=N,
            G_rep=self.L_Group2Group_flags[LG2GF_idx.rep],
            N_flags=self.N_flags.gpu_values,
            N_flags_row_group=self.N_flags.get_idx_loc(group_row),
            L_Group_neuronCounts=self.L_Group_neuronCounts.gpu_values,
            G_neuron_typed_ccount=self.G_neuron_typed_ccount,
            L_Group_delay_counts=self.L_Group_delay_counts,
            conn_probs=self.synapses.conn_probs.gpu_values,
            ntypes=self.config_model.type_groups,
            ntype_conns=self.config_model.type_conns,)

        self.sync_to_cpu()

        return

    def _generate_RepBackend(self):
        return snn_construction_gpu.SnnRepresentation(
            N=self.config_model.N,
            G=self.config_model.G,
            S=self.config_model.S,
            D=self.config_model.D,
            curand_states_p=self.curand_states,
            N_pos=self.N_pos.data_ptr(),
            G_group_delay_counts=self.L_Group_delay_counts.data_ptr(),
            G_flags=self.L_Group_flags.data_ptr(),
            G_props=self.L_Group_properties.data_ptr(),
            N_rep=self.synapses.N_rep.data_ptr(),
            N_rep_buffer=self.synapses.N_rep_buffer.data_ptr(),
            N_rep_pre_synaptic=self.synapses.rep_pre_synaptic.data_ptr(),
            N_rep_pre_synaptic_idcs=self.synapses.rep_pre_synaptic_idcs
            .data_ptr(),
            N_rep_pre_synaptic_counts=self.synapses.rep_pre_synaptic_counts
            .data_ptr(),
            N_delays=self.synapses.N_delays.data_ptr(),
            N_flags=self.neuron_states.N_flags.data_ptr(),
            N_weights=self.synapses.N_weights.data_ptr(),
            L_winner_take_all_map=self.pseudo_tensor_i32.data_ptr(),
            max_n_winner_take_all_layers=1,
            max_winner_take_all_layer_size=1
        )

    @property
    def N_flags(self):
        return self.neuron_states.N_flags
