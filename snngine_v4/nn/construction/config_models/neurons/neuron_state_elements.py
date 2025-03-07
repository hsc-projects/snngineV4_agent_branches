from __future__ import annotations

import pandas as pd
from pydantic import Field

from snngine_v4.utils.data_utils.dataframe_config import (
    DataFrameF32, DataFrameI32,
)
from snngine_v4.utils.data_utils.index_config import IndexConfig, Row, RowF32


class NeuronFlagsColumns(IndexConfig):
    b_sensory_input: Row
    N_type: Row
    L_group: Row
    N_model: Row
    b_selected: Row
    b_selected_tmp: Row


class NeuronFlags(DataFrameI32):
    index: NeuronFlagsColumns = Field(repr=False)

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


class NPropLabels(IndexConfig):
    pt: RowF32
    u: RowF32
    v: RowF32
    a: RowF32
    b: RowF32
    c: RowF32
    d: RowF32
    i: RowF32
    i_prev: RowF32
    v_prev: RowF32


class NeuronProperties(DataFrameF32):
    index: NPropLabels = Field(repr=False)
