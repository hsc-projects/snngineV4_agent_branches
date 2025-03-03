import pandas as pd
import torch

from snngine_v4.utils.cuda_utils.cuda_functions import assert_device_equivalency
from snngine_v4.utils.data_utils.dataframe_config import (
    DataFrameIndex,
    FrameVector, TypedDataFrameBase,
)


class TensorDataFrame:

    df: pd.DataFrame

    def __init__(self, device, *args, tensor=None, **kwargs):

        if len(args) == 1 and isinstance(args[0], pd.DataFrame):
            self.df = args[0]
        else:
            if len(args) == 1 and isinstance(args[0], TypedDataFrameBase):
                model = args[0]
                args = []
                kwargs.update(dict(data=model.data,
                                   columns=model.columns,
                                   index=model.index,
                                   dtype=model.data.dtype))
            elif (len(args) < 4) and 'dtype' not in kwargs:
                pass
            if 'columns' in kwargs:
                if isinstance(kwargs['columns'], DataFrameIndex):
                    kwargs['columns'] = kwargs['columns'].to_list()

            if 'index' in kwargs:
                if isinstance(kwargs['index'], DataFrameIndex):
                    kwargs['index'] = kwargs['index'].to_list()

            self.df = pd.DataFrame(*args, **kwargs)
        if tensor is None:
            tensor = torch.tensor(self.df.values, device=torch.device(device))
        else:
            if tensor.shape[0] != self.df.shape[0]:
                raise ValueError
            elif tensor.shape[1] != self.df.shape[1]:
                raise ValueError
            assert_device_equivalency(tensor.device, device)
        self.tensor = tensor

    def __getitem__(self, item):
        if isinstance(item, (int, slice, tuple)):
            # return self.__class__(self.tensor[item])
            return self.tensor[item]
        elif isinstance(item, (str, FrameVector)):
            return self.tensor[self.get_idx_loc(item)]
        return [self.tensor[i] for i in item]

    def __setitem__(self, item, value):
        if isinstance(item, int):
            self.tensor[item] = value
        elif isinstance(item, slice):
            self.tensor[item] = value
            # raise ValueError('Cannot interpret slice with multiindexing')
        elif isinstance(item, (str, FrameVector)):
            self.tensor[self.get_idx_loc(item), :] = value
        else:
            for i in item:
                if isinstance(i, slice):
                    raise ValueError(
                        'Cannot interpret slice with multi-indexing')
                self.tensor[i] = value

    def data_ptr(self):
        return self.tensor.data_ptr()

    @property
    def device(self):
        return self.tensor.device

    # @classmethod
    # def from_dataframe_config(cls, model: TypedDataFrameBase, device):
    #     return cls(device=device, data=model.data, columns=model.columns,
    #                index=model.index,
    #                dtype=model.data.dtype)

    def get_idx_loc(self, item):
        if isinstance(item, FrameVector):
            item = item.name
        return self.df.index.get_loc(item)

    @property
    def loc(self):
        return self.df.loc

    def sync_to_df(self):
        self.df[:] = self.tensor.cpu().numpy()
