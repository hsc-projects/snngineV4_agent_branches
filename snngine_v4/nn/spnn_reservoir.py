from functools import cached_property
from typing import Callable, ClassVar, TYPE_CHECKING

import torch

from snngine_v4.geometry.grid.finite_grid import FiniteGrid
from snngine_v4.nn.construction.config_models.neurons.synapse_model import (
    SynapseCountTensors, SynapseModel,
)
from snngine_v4.nn.construction.config_models.reservoir.nn_reservoir_config \
    import NetworkReservoirConfig

from snngine_v4.nn.construction.engine_element import EngineElement
from snngine_v4.nn.synapses import Synapses, SynCounts
from snngine_v4.utils.cuda_utils.tensor_dataframe import TensorDataFrame
from snngine_v4.utils.cuda_utils.tensor_dict import TensorDict


if TYPE_CHECKING:
    from snngine_v4.nn.neuron_states import NeuronState
    from snngine_v4.nn.spnn import SpatialNetwork
else:
    NeuronState = None
    SpatialNetwork = None


# noinspection PyPep8Naming
class NetworkReservoir(EngineElement):

    BUILDER_OBJECT_CLASS_MAP: ClassVar[dict] = {
        SynapseModel: Synapses,
        SynapseCountTensors: SynCounts,
    }

    config_model: NetworkReservoirConfig
    parent_element: Callable[..., SpatialNetwork]

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

    def fill_tensors(self,):
        if self.b_cuda_backend_available is False:
            return
        # noinspection PyUnresolvedReferences
        from snngine_v4.nn.cuda_backend import (
            snn_utils, snn_construction_gpu, snn_simulation_gpu
        )

        S = self.config_model.S
        G = self.config_model.G
        D = self.config_model.D
        model: NetworkReservoirConfig = self.config_model

        self.neuron_states.fill_tensors_and_group_neuron_type_counts()

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

        # group_row = self.config_model.neuron_states.N_flags.index.L_group
        self.synapses.fill_tensors()

        self.sync_to_cpu()

        return

    def G_neuron_counts_per_type(self, group=None):
        counts = self.L_Group_neuronCounts[:self.config_model.n_type_groups]
        if group is not None:
            counts = counts[:, group]
        return counts

    @property
    def G_rep(self):
        g_rep = self.config_model.L_Group2Group_flags.index.rep
        return self.L_Group2Group_flags[g_rep]

    @property
    def N_flags(self):
        return self.neuron_states.N_flags
