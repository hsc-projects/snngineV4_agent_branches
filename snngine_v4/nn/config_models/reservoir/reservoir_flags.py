from __future__ import annotations

from copy import deepcopy

import pandas as pd


from snngine_v4.nn.config_models.reservoir.n_type_groups import NTypeGroupList
from snngine_v4.utils.data_utils.dataframe_config import (
    DataFrameF32, DataFrameF32D3, DataFrameI32,
    DataFrameI32D3, DataFrameIndex, FrameVectorType,
)


class NeuronFlagsColumns(DataFrameIndex):
    b_sensory_input: FrameVectorType = 'b_sensory_input'
    N_type: FrameVectorType = 'N_type'
    L_group: FrameVectorType = 'L_group'
    N_model: FrameVectorType = 'N_model'
    b_selected: FrameVectorType = 'b_selected'
    b_selected_tmp: FrameVectorType = 'b_selected_tmp'


class NeuronFlags(DataFrameI32):
    index: NeuronFlagsColumns

    @classmethod
    def cls_validate_data(
            cls, model: NeuronFlags, data: pd.DataFrame, **kwargs):

        n_type_data = data.loc[model.index.N_type.name, :]
        l_group_data = data.loc[model.index.L_group.name, :]

        if (n_type_data == 0).sum() > 0:
            raise AssertionError

        cond0 = (n_type_data[:-1][n_type_data.diff() < 0].size > 0)
        cond1 = (l_group_data[:-1][l_group_data.diff() < 0].size != 1)
        if cond0 or cond1:
            idcs1 = (l_group_data.diff() < 0).nonzero()
            df = pd.DataFrame(kwargs['N_pos'][:, :3].cpu().numpy())
            df[['0g', '1g', '2g']] = kwargs['shape']
            df['group'] = l_group_data.cpu().numpy()
            # print(G_pos)
            print(df)
            df10 = df.iloc[int(idcs1[0]) - 2: int(idcs1[0]) + 3, :]
            df11 = df.iloc[int(idcs1[-1]) - 2: int(idcs1[-1]) + 3, :]
            print(df10)
            print(df11)
            raise AssertionError


class LGroupFlagsColumns(DataFrameIndex):
    sensory_input_type: FrameVectorType = 'sensory_input_type'
    b_thalamic_input: FrameVectorType = 'b_thalamic_input'
    b_sensory_group: FrameVectorType = 'b_sensory_group'
    b_sensory_input: FrameVectorType = 'b_sensory_input'
    b_output_group: FrameVectorType = 'b_output_group'
    output_type: FrameVectorType = 'output_type'
    b_monitor_group_firing_count: FrameVectorType = \
        'b_monitor_group_firing_count'


class LGroupFlags(DataFrameI32):
    index: LGroupFlagsColumns


class LGroupPropLabels(DataFrameIndex):
    thalamic_inh_input_current: FrameVectorType = 'thalamic_inh_input_current'
    thalamic_exc_input_current: FrameVectorType = 'thalamic_exc_input_current'
    sensory_input_current0: FrameVectorType = 'sensory_input_current0'
    sensory_input_current1: FrameVectorType = 'sensory_input_current1'


class LGroupProps(DataFrameF32):
    index: LGroupPropLabels


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

        model = cls()
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


class LG2LGFlagLabels(DataFrameIndex):
    delay_distance: FrameVectorType = 'delay_distance'
    stdp_config0: FrameVectorType = 'stdp_config0'
    stdp_config1: FrameVectorType = 'stdp_config1'
    syn_count_inh: FrameVectorType = 'syn_count_inh'
    syn_count_exc: FrameVectorType = 'syn_count_exc'
    rep: FrameVectorType = 'rep'


class LG2LGFlags(DataFrameI32D3):
    index: LG2LGFlagLabels


class LG2LGPropLabels(DataFrameIndex):
    distance: FrameVectorType = 'distance'
    avg_weight_inh: FrameVectorType = 'avg_weight_inh'
    avg_weight_exc: FrameVectorType = 'avg_weight_exc'


class LG2LGProp(DataFrameF32D3):
    index: LG2LGPropLabels
