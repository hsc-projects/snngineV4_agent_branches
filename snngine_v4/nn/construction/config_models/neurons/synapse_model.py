from __future__ import annotations

from typing import ClassVar

from snngine_v4.nn.construction.config_models.engine_element_config import \
    EngineElementConfig
from snngine_v4.utils.data_utils.dataframe_config import (
    DataFrameF32,
    DataFrameI32,
)


class SynapseDelaysCounts(DataFrameI32):
    pass


class SynapseConnections(DataFrameI32):
    pass


class SynapseWeights(DataFrameF32):
    pass


class PreSynapticCounts(DataFrameI32):
    pass


class WinnerTakesAllMap:
    pass


class SynapseModel(EngineElementConfig):

    # class Slots(EngineElementConfig.Slots):
    #     DELAYS: ClassVar[str] = 'delays'
    #     REP: ClassVar[str] = 'rep'
    #     REP_BUFFER: ClassVar[str] = 'rep_buffer'

    delays: SynapseDelaysCounts

    rep: SynapseConnections
    weights: SynapseWeights

    rep_buffer: SynapseConnections

    rep_pre_synaptic: SynapseConnections
    rep_pre_synaptic_idcs: SynapseConnections
    rep_pre_synaptic_counts: PreSynapticCounts

    @classmethod
    def reset_model(cls, model: dict | SynapseModel,
                    n_neurons, n_delays, S):
        if isinstance(model, dict):
            model = SynapseModel(**model)

        cls.reset_array(model.delays, (n_delays + 1, n_neurons))

        cls.reset_array(model.rep, (n_neurons, S))
        cls.reset_array(model.weights, (S, n_neurons))
        cls.reset_array(model.rep_buffer,  (S,  n_neurons))

        cls.reset_array(model.rep_pre_synaptic, (n_neurons,  S))
        cls.reset_array(model.rep_pre_synaptic_idcs, (n_neurons,  S))
        cls.reset_array(model.rep_pre_synaptic_counts, n_neurons+1)

        cls.reset_array(model.rep_pre_synaptic_counts, n_neurons+1)


        return model
