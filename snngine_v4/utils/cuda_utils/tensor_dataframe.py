import pandas as pd
import torch

from snngine_v4.utils.cuda_utils.cuda_functions import assert_device_equivalency
from snngine_v4.utils.data_utils.dataframe_config import (
    SeriesModel, TypedDataFrameModel,
)
from snngine_v4.utils.data_utils.index_config import (
    Column, IndexConfig,
    RowOrColumn,
)


class DeviceSyncError(BaseException):
    pass


class InconsistencyError(BaseException):
    pass


class TensorSeries:

    data_cpu: pd.Series

    def __init__(self, device, *args, gpu_values=None, model=None,  **kwargs):
        if model is not None:
            pass
        elif (len(args) == 1) and isinstance(args[0], SeriesModel):
            model = args[0]
            args = []
        self.data_cpu = self.make_cpu_data(*args, model=model, **kwargs)
        self.gpu_values = self.make_gpu_data(gpu_values, device, )

    def data_ptr(self):
        return self.gpu_values.data_ptr()

    @property
    def device(self):
        return self.gpu_values.device

    def make_cpu_data(self, *args, model: SeriesModel = None, **kwargs):
        if len(args) == 1 and isinstance(args[0], pd.Series):
            return args[0]
        else:
            if model is not None:
                kwargs.update(
                    dict(data=model.data,
                         index=model.index,
                         dtype=model.data.dtype))
            if 'index' in kwargs:
                if isinstance(kwargs['index'], IndexConfig):
                    kwargs['index'] = kwargs['index'].to_list()
            res = pd.Series(*args, **kwargs)
            if model is not None:
                model.apply_property()
            return res

    def make_gpu_data(self, tensor, device):
        if tensor is None:
            tensor = torch.tensor(
                self.data_cpu.values,
                device=torch.device(device))
        else:
            self.validate_sync(gpu_values=tensor)
            assert_device_equivalency(tensor.device, device)
        return tensor

    def get_idx_loc(self, item):
        if isinstance(item, RowOrColumn):
            item = item.name
        return self.data_cpu.index.get_loc(item)

    def __getitem__(self, item):
        if isinstance(item, (int, slice, tuple)):
            # return self.__class__(self.tensor[item])
            return self.gpu_values[item]
        elif isinstance(item, (str, RowOrColumn)):
            return self.gpu_values[self.get_idx_loc(item)]
        return [self.gpu_values[i] for i in item]

    def __len__(self):
        return self.data_cpu.shape[0]

    @property
    def loc(self):
        return self.data_cpu.loc

    def __setitem__(self, item, value):
        if isinstance(item, int):
            self.gpu_values[item] = value
        elif isinstance(item, slice):
            self.gpu_values[item] = value
            # raise ValueError('Cannot interpret slice with multiindexing')
        elif isinstance(item, (str, RowOrColumn)):
            self.gpu_values[self.get_idx_loc(item), :] = value
        else:
            for i in item:
                if isinstance(i, slice):
                    raise ValueError(
                        'Cannot interpret slice with multi-indexing')
                self.gpu_values[i] = value

    @property
    def shape(self):
        return self.data_cpu.shape

    def sync_to_df(self):
        self.data_cpu[:] = self.gpu_values.cpu().numpy()

    def validate_sync(self, gpu_values=None):
        if gpu_values is None:
            gpu_values = self.gpu_values
        if gpu_values.shape[0] != self.data_cpu.shape[0]:
            raise DeviceSyncError
        if len(gpu_values.shape) != len(self.data_cpu.shape):
            raise DeviceSyncError
        return gpu_values


class TensorDataFrame(TensorSeries):

    data_cpu: pd.DataFrame

    def get_col_loc(self, item):
        if isinstance(item, RowOrColumn):
            item = item.name
        return self.data_cpu.columns.get_loc(item)

    def make_cpu_data(self, *args,  model=None, **kwargs):
        if len(args) == 1 and isinstance(args[0], pd.DataFrame):
            return args[0]
        else:
            if model is not None:
                kwargs.update(dict(data=model.data,
                                   columns=model.columns,
                                   index=model.index,
                                   dtype=model.data.dtype))
            elif (len(args) < 4) and ('dtype' not in kwargs):
                pass
            if 'columns' in kwargs:
                if isinstance(kwargs['columns'], IndexConfig):
                    kwargs['columns'] = kwargs['columns'].to_list()

            if 'index' in kwargs:
                if isinstance(kwargs['index'], IndexConfig):
                    kwargs['index'] = kwargs['index'].to_list()
            return pd.DataFrame(*args, **kwargs)

    def __setitem__(self, item, value):
        if isinstance(item, Column):
            self.gpu_values[:, self.get_col_loc(item)] = value
        elif isinstance(item, tuple):
            self.gpu_values[item] = value
            pass
        else:
            super().__setitem__(item, value)

    def validate_sync(self, gpu_values=None):
        gpu_values = super().validate_sync(gpu_values)
        if gpu_values.shape[1] != self.data_cpu.shape[1]:
            raise DeviceSyncError
