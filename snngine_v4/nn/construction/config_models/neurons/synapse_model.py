from __future__ import annotations

from typing import ClassVar

from snngine_v4.nn.construction.config_models.engine_element_config import \
    EngineElementConfig
from snngine_v4.nn.construction.config_models.reservoir.n_type_groups import \
    NTypeGroupList
from snngine_v4.utils.data_utils.dataframe_config import (
    DataFrameF32,
    DataFrameI32,
)
from snngine_v4.utils.field_utils import get_attr_or_key, Undefined


class SynapseDelaysCounts(DataFrameI32):
    pass


class SynapseConnections(DataFrameI32):
    pass


class LGConnProb(DataFrameF32):
    pass


class SynapseWeights(DataFrameF32):
    pass


class PreSynapticCounts(DataFrameI32):
    pass


class LGroupExpCCSynPerSrcTypeAndDelay(DataFrameI32):
    pass

    @classmethod
    def cls_validate_data(cls, model, data, type_groups, D, S, G):
        for ntype_group in type_groups:
            first_row = data[
                        (D + 1) * (ntype_group.ntype - 1), :]
            if first_row.sum() != 0:
                print(first_row)
                raise AssertionError
            last_row = data[
                       (D + 1) * (ntype_group.ntype - 1) + D, :]
            if ((last_row - S).abs()).sum() != 0:
                print(last_row)
                print((last_row - S).abs())
                raise AssertionError


class LGroupExpExcCCSynPerSnkTypeAndDelay(DataFrameI32):
    pass


class SynapseCountTensors(EngineElementConfig):

    G_exp_ccsyn_per_src_type_and_delay: LGroupExpCCSynPerSrcTypeAndDelay
    G_exp_exc_ccsyn_per_snk_type_and_delay: LGroupExpExcCCSynPerSnkTypeAndDelay

    @classmethod
    def reset_model(cls, model: dict | SynapseCountTensors,
                    n_delays, n_groups,
                    ntypes: NTypeGroupList):
        if isinstance(model, dict):
            model = SynapseCountTensors(**model)

        shape = (len(ntypes.groups) * (n_delays + 1), n_groups)

        cls.reset_array(model.G_exp_ccsyn_per_src_type_and_delay,
                        n_indices=shape)
        cls.reset_array(model.G_exp_exc_ccsyn_per_snk_type_and_delay,
                        n_indices=shape)


class SynapseModel(EngineElementConfig):

    class Slots(EngineElementConfig.Slots):
        DELAYS: ClassVar[str] = 'N_delays'
        REP: ClassVar[str] = 'N_rep'
        COUNTS: ClassVar[str] = 'counts'
        CONN_PROBS: ClassVar[str] = 'conn_probs'
    #     REP_BUFFER: ClassVar[str] = 'rep_buffer'

    N_rep: SynapseConnections
    N_delays: SynapseDelaysCounts

    N_weights: SynapseWeights

    rep_pre_synaptic: SynapseConnections
    rep_pre_synaptic_idcs: SynapseConnections
    rep_pre_synaptic_counts: PreSynapticCounts

    conn_probs: LGConnProb

    counts: SynapseCountTensors

    @classmethod
    def reset_model(cls, model: dict | SynapseModel,
                    n_neurons, n_delays, S, n_groups,
                    ntypes: NTypeGroupList):
        if isinstance(model, dict):
            model = SynapseModel(**model)

        cls.reset_array(model.N_delays, n_indices=(n_delays + 1, n_neurons))

        cls.reset_array(model.N_rep, n_indices=(S, n_neurons))
        cls.reset_array(model.N_weights, n_indices=(S, n_neurons))

        cls.reset_array(model.rep_pre_synaptic, n_indices=(n_neurons,  S))
        cls.reset_array(model.rep_pre_synaptic_idcs, n_indices=(n_neurons,  S))
        cls.reset_array(model.rep_pre_synaptic_counts, n_indices=n_neurons+1)

        cls.reset_array(model.conn_probs,
                        n_indices=(len(ntypes.groups) * n_groups, n_delays))

        counts = get_attr_or_key(model, 'counts')

        SynapseCountTensors.reset_model(
            counts, n_delays,
            n_groups=n_groups, ntypes=ntypes)

        return model
