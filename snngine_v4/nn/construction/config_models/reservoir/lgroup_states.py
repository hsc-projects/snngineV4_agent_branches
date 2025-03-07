from __future__ import annotations

from copy import deepcopy

from pydantic import Field

from snngine_v4.nn.construction.config_models.reservoir.n_type_groups \
    import NTypeGroupList
from snngine_v4.utils.data_utils.dataframe_config import (
    DataFrameF32, DataFrameF32D3, DataFrameI32,
    DataFrameI32D3,
)
from snngine_v4.utils.data_utils.index_config import IndexConfig, Row


class LGroupFlagsColumns(IndexConfig):
    sensory_input_type: Row
    b_thalamic_input: Row
    b_sensory_group: Row
    b_sensory_input: Row
    b_output_group: Row
    output_type: Row
    b_monitor_group_firing_count: Row


class LGroupFlags(DataFrameI32):
    index: LGroupFlagsColumns = Field(repr=False)


class LGroupPropLabels(IndexConfig):
    thalamic_inh_input_current: Row = 25.
    thalamic_exc_input_current: Row = 15.
    sensory_input_current0: Row = 65.
    sensory_input_current1: Row = 25.


class LGroupProps(DataFrameF32):
    index: LGroupPropLabels = Field(repr=False)


class LGNeuronCounts(DataFrameI32):

    @classmethod
    def from_shape(cls, ntypes: NTypeGroupList, d, g) -> LGNeuronCounts:
        index = []
        names = {}
        # cols = []
        for nt_group in ntypes:
            name = nt_group.ntype.name
            names[nt_group.ntype] = name[: min(len(name), 3)].lower()
            index.append("#N " + names[nt_group.ntype] + " (LG)")
        for nt_group in ntypes:
            for delay in range(d):
                index.append("#N " + names[nt_group.ntype] + f"(d={delay})")

        model: LGNeuronCounts = cls()
        model.index = index
        model.data = model.zeroes(n_cols=g)
        return model

    # noinspection PyPep8Naming
    @classmethod
    def cls_validate_data(cls, model: LGNeuronCounts, data,
                          type_groups=None, D=None, G=None,
                          **kwargs):
        max_ntype = 0
        for ntype_group in type_groups:
            if (data[ntype_group.ntype - 1, :].sum()
                    != len(ntype_group)):
                raise AssertionError
            max_ntype = max(max_ntype, ntype_group.ntype)

        for ntype_group in type_groups:
            min_row = max_ntype + D * (ntype_group.ntype - 1)
            max_row = min_row + D
            ones = deepcopy(data[0, :])
            ones[:] = 1
            expected_result = ones * len(ntype_group)
            if ((data[min_row: max_row, :].sum(dim=0)
                 - expected_result).sum() != 0):
                print(data)
                raise AssertionError


class LG2LGFlagLabels(IndexConfig):
    delay_distance: Row
    stdp_config0: Row
    stdp_config1: Row
    syn_count_inh: Row
    syn_count_exc: Row
    rep: Row


class LG2LGFlags(DataFrameI32D3):
    index: LG2LGFlagLabels


class LG2LGPropLabels(IndexConfig):
    distance: Row
    avg_weight_inh: Row
    avg_weight_exc: Row


class LG2LGProp(DataFrameF32D3):
    index: LG2LGPropLabels
