from snngine_v4.nn.construction.config_models.neurons.synapse_model import \
    SynapseModel
from snngine_v4.nn.construction.engine_element import EngineElement


class Synapses(EngineElement):

    config_model: SynapseModel

    def __init__(self, model: SynapseModel, **kwargs):

        super().__init__(model=model.tdf_values(),
                         config_model=model, **kwargs)
