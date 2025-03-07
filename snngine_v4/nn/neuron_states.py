from snngine_v4.nn.construction.config_models.neurons.neuron_state import \
    NeuronStateModel
from snngine_v4.nn.construction.config_models.reservoir.n_type_groups import \
    NeuronType
from snngine_v4.nn.construction.engine_element import EngineElement
from snngine_v4.utils.cuda_utils.tensor_dataframe import (
    InconsistencyError,
    TensorDataFrame,
)


class NeuronState(EngineElement):

    flags: TensorDataFrame
    props: TensorDataFrame

    config_model: NeuronStateModel

    def __init__(self, model: NeuronStateModel, device, **kwargs):

        super().__init__(device=device, model=model.tdf_values(),
                         config_model=model, **kwargs)

    def validate_consistency(self):
        if self.n_neurons != self.props.shape[1]:
            raise InconsistencyError

    @property
    def n_neurons(self):
        return self.flags.shape[1]

    def apply_preset(self):
        self.validate_consistency()
        type_col = self.config_model.flags.index.N_type.name
        mask_inh = self.flags[type_col] == NeuronType.INHIBITORY.value
        mask_exc = self.flags[type_col] == NeuronType.EXCITATORY.value
        self.config_model.initializer.presets.default_init(
            df_props=self.props,
            r=self.rand_f32(self.n_neurons),
            mask_inh=mask_inh, mask_exc=mask_exc,
        )
        self.sync_to_cpu()
