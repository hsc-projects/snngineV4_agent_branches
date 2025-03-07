from typing import Callable, ClassVar, Iterable, Type

import numpy as np
# import pandas as pd
import torch

from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict,
    DictContainerConfig,
)
from snngine_v4.utils.containers.mappings import (
    Object2ObjectMap,
)
from snngine_v4.utils.cuda_utils.cuda_functions import (
    compare_devices, CudaKeywords,
)
from snngine_v4.utils.cuda_utils.tensor_dataframe import (
    TensorDataFrame,
    TensorSeries,
)
from snngine_v4.utils.data_utils.dataframe_config import (
    TypedDataFrameBase3D,
)
from snngine_v4.utils.data_utils.index_config import RowOrColumn


class ArrayToTensorMap(Object2ObjectMap):
    ContainerConfigClass: ClassVar = np.ndarray, torch.Tensor


# class DataFrameToTensorMap(Object2ObjectMap):
#     ContainerConfigClass: ClassVar = pd.DataFrame, torch.Tensor


class TensorDataFrameDict(ConfigurableDict):
    ContainerConfigClass: ClassVar = DictContainerConfig, TensorSeries


class TensorDict(ConfigurableDict):
    values: Callable[[], Iterable[torch.Tensor]]
    # ContainerConfigClass: ClassVar = (DictContainerConfig, torch.Tensor)

    class ContainerConfigClass(DictContainerConfig):
        allowed_types: Type[torch.Tensor] = torch.Tensor
        b_clear_allowed: bool = True
        b_duplicate_check_by_id: bool = True

    def __init__(self, model: TypedDataFrameBase3D | None = None, **kwargs):

        device = kwargs.pop(CudaKeywords.DEVICE, None)

        super().__init__(**kwargs)

        self.array2tensor = ArrayToTensorMap()
        # self.df2tensor = DataFrameToTensorMap()
        self.tdf_dict = TensorDataFrameDict()

        if not hasattr(self, '_main_tensor'):
            self._main_tensor = None

        if model is not None:
            self.main_tensor = self.update_from_dataframe_3d_config(
                device, model)

    def clear(self, b_force: bool = False) -> None:
        super().clear(b_force=b_force)
        self.array2tensor.clear(b_force=True)
        # self.df2tensor.clear(b_force=True)
        self.tdf_dict.clear(b_force=True)

    def __getitem__(self, item):
        if isinstance(item, RowOrColumn):
            item = item.name
        return super().__getitem__(item)

    @property
    def main_tensor(self):
        return self._main_tensor

    @main_tensor.setter
    def main_tensor(self, value):
        if self._main_tensor is not None:
            raise PermissionError
        self._main_tensor = value

    def __setitem__(self, key: str, value: torch.Tensor | TensorDataFrame):

        if isinstance(value, TensorSeries):
            array = value.data_cpu.values
            # self.df2tensor[value.data_cpu] = value.gpu_values
            self.tdf_dict[key] = value
            value = value.gpu_values
        else:
            array = value.cpu().numpy()

        super().__setitem__(key, value)

        self.array2tensor[array] = value

    def update_from_dataframe_3d_config(
            self, device, model: TypedDataFrameBase3D):
        items = list(model.items())
        main_tensor = torch.tensor(model.data, device=device)
        for i, (k, v) in enumerate(items):
            self[k] = TensorDataFrame(
                device, gpu_values=main_tensor[i],
                data=v, columns=model.columns)
        return main_tensor

    def sync_to_cpu(self):
        for k, v in self.items():
            if compare_devices(v.device, 'cpu') is False:
                if isinstance(v, TensorDataFrame):
                    v.sync_to_df()
                elif isinstance(v, torch.Tensor):
                    self.array2tensor.inv[v][:] = v.cpu().numpy()
