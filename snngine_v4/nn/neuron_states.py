from typing import Callable, TYPE_CHECKING

from snngine_v4.nn.construction.config_models.neurons.neuron_state import \
    NeuronStateModel
from snngine_v4.nn.construction.config_models.reservoir.n_type_groups import \
    NeuronType
from snngine_v4.nn.construction.engine_element import EngineElement
from snngine_v4.utils.cuda_utils.tensor_dataframe import (
    InconsistencyError,
    TensorDataFrame,
)


# noinspection PyUnresolvedReferences
from snngine_v4.nn.cuda_backend import (
    snn_utils, snn_construction_gpu, snn_simulation_gpu)


if TYPE_CHECKING:
    from snngine_v4.nn.spnn_reservoir import NetworkReservoir
else:
    NetworkReservoir = None


class NeuronState(EngineElement):

    config_model: NeuronStateModel
    parent_element: Callable[..., NetworkReservoir]

    N_flags: TensorDataFrame
    N_props: TensorDataFrame

    # def __init__(self, model: NeuronStateModel, device, **kwargs):
    #     super().__init__(device=device, config_model=model, **kwargs)

    def validate_consistency(self):
        if self.n_neurons != self.N_props.shape[1]:
            raise InconsistencyError

    @property
    def n_neurons(self):
        return self.N_flags.shape[1]

    def apply_preset(self):
        self.validate_consistency()
        type_col = self.config_model.N_flags.index.N_type.name
        mask_inh = self.N_flags[type_col] == NeuronType.INHIBITORY.value
        mask_exc = self.N_flags[type_col] == NeuronType.EXCITATORY.value
        self.config_model.initializer.presets.default_init(
            df_props=self.N_props,
            r=self.rand_f32(self.n_neurons),
            mask_inh=mask_inh, mask_exc=mask_exc,
        )
        self.sync_to_cpu()

    # noinspection PyPep8Naming
    def fill_tensors_and_group_neuron_type_counts(self):

        reservoir = self.parent_element()
        N = reservoir.config_model.N
        G = reservoir.config_model.G

        for g in reservoir.config_model.type_groups:
            # Set Neuron Type
            # self.N_flags.type[g.start_idx:g.end_idx + 1] = g.ntype.value
            self.N_flags[self.ntype_flag_col][g.start_idx:g.end_idx + 1] = (
                g.ntype.value)

        # rows[0, 1]: inhibitory count, excitatory count,
        # rows[2 * D]: number of neurons per delay (
        # post_synaptic type: inhibitory, excitatory)
        snn_construction_gpu.fill_N_flags_group_id_and_G_neuron_count_per_type(
            N=N, G=G, N_pos=reservoir.N_pos.data_ptr(),
            # N_pos_shape=self.reservoir_config.reservoir_shape.as_tuple(),
            N_pos_shape=reservoir.config_model.grid.shape.as_tuple(),
            N_flags=self.N_flags.data_ptr(),
            # G_shape=self.reservoir_config.reservoir_segmentation.as_tuple(),
            G_shape=reservoir.config_model.grid.seg.as_tuple(),
            G_neuron_counts=reservoir.L_Group_neuronCounts.data_ptr(),
            N_flags_row_type=self.ntype_flag_index,
            N_flags_row_group=self.group_flag_index,
            N_pos_n_cols=reservoir.N_pos.shape[1]
        )

    @property
    def ntype_flag_col(self):
        return self.config_model.N_flags.index.N_type.name

    @property
    def ntype_flag_index(self):
        return self.N_flags.get_idx_loc(self.ntype_flag_col)

    @property
    def group_flag_col(self):
        return self.config_model.N_flags.index.L_group.name

    @property
    def group_flag_index(self):
        return self.N_flags.get_idx_loc(self.group_flag_col)
