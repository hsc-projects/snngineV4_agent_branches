from typing import Callable, ClassVar, Iterable, Type

import numpy as np
import pandas as pd
import torch

from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict,
    DictContainerConfig,
)
from snngine_v4.utils.containers.mappings import (
    Model2ObjectMap,
    Object2ObjectMap,
)
from snngine_v4.utils.containers.super_maps import TypeSortedMap
from snngine_v4.utils.cuda_utils.cuda_functions import \
    (
    assert_device_equivalency, CudaKeywords,
)
from snngine_v4.utils.cuda_utils.tensor_dataframe import TensorDataFrame
from snngine_v4.utils.data_utils.dataframe_config import (
    TypedDataFrameBase,
    TypedDataFrameBase3D,
)


class ArrayToTensorMap(Object2ObjectMap):
    ContainerConfigClass: ClassVar = ((np.ndarray, ), (torch.Tensor, ))


class DataFrameToTensorMap(Object2ObjectMap):
    ContainerConfigClass: ClassVar = ((pd.DataFrame, ), (torch.Tensor, ))


class TensorDataFrameDict(ConfigurableDict):
    ContainerConfigClass: ClassVar = (DictContainerConfig, TensorDataFrame)


class TensorDictConfig(DictContainerConfig):
    allowed_types: Type[torch.Tensor] = torch.Tensor
    b_clear_allowed: bool = True
    b_duplicate_check_by_id: bool = True


class TensorDict(ConfigurableDict):
    values: Callable[[], Iterable[torch.Tensor]]
    # ContainerConfigClass: ClassVar = (DictContainerConfig, torch.Tensor)
    ContainerConfigClass: ClassVar = TensorDictConfig

    def __init__(self, model: TypedDataFrameBase3D | None = None, **kwargs):

        device = kwargs.pop(CudaKeywords.DEVICE, None)

        super().__init__(**kwargs)

        self.array2tensor = ArrayToTensorMap()
        self.df2tensor = DataFrameToTensorMap()
        self.tdf_dict = TensorDataFrameDict()

        if not hasattr(self, '_main_tensor'):
            self._main_tensor = None

        if model is not None:
            self.main_tensor = self.update_from_dataframe_3d_config(
                device, model
            )

    def clear(self, b_force: bool = False) -> None:
        super().clear(b_force=b_force)
        self.array2tensor.clear(b_force=True)
        self.df2tensor.clear(b_force=True)
        self.tdf_dict.clear(b_force=True)

    @property
    def main_tensor(self):
        return self._main_tensor

    @main_tensor.setter
    def main_tensor(self, value):
        if self._main_tensor is not None:
            raise PermissionError
        self._main_tensor = value

    def __setitem__(self, key: str, value: torch.Tensor | TensorDataFrame):

        if isinstance(value, TensorDataFrame):
            array = value.df.values
            self.df2tensor[value.df] = value.tensor
            self.tdf_dict[key] = value
            value = value.tensor
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
                device, tensor=main_tensor[i],
                data=v, columns=model.columns)
        return main_tensor

    # @classmethod
    # def from_dataframe_3d_config(
    #         cls, device, model: TypedDataFrameBase3D):
    #     new = cls()
    #     main_tensor = new.update_from_dataframe_3d_config(
    #         device=device, model=model)
    #     return new, main_tensor


# # class Model2TensorMap(Model2ObjectMap):
# #     values: Callable[[], Iterable[TensorDict]]
# #     ContainerConfigClass: ClassVar = (DictContainerConfig, torch.Tensor)
#
#
# # class Model2TensorDictMap(Model2ObjectMap):
# #     values: Callable[[], Iterable[TensorDict]]
# #     ContainerConfigClass: ClassVar = (DictContainerConfig, TensorDict)
# #
# #     def __init__(self, **kwargs):
# #         self.tensor_dict = Model2TensorMap()
# #         self.tensor_map = Model2TensorMap()
# #         super().__init__(**kwargs)
# #
# #     def add_model(self, model: TypedDataFrameBase3D, device):
# #         dct, main_tensor = TensorDict.from_dataframe_3d_config(
# #             device=device, model=model)
# #         self[model] = dct
# #         self.tensor_dict[model] = main_tensor
#
# class TensorDictMap(TypeSortedMap):
#
#     sub_maps: tuple = ((str, TensorDict),
#                        (TensorDict, TypedDataFrameBase3D),)
#
#     def add_model(self, key, model: TypedDataFrameBase3D, device):
#         dct, main_tensor = TensorDict.from_dataframe_3d_config(
#             device=device, model=model)
#         self[key] = dct
#         self[dct] = model
#         return dct, main_tensor
#
#
# # class TensorMap(TypeSortedMap):
# class TensorMap(TensorDict):
#
#     # sub_maps: tuple = (
#     #     (str, (torch.Tensor, TensorDataFrame)),
#     #     ((torch.Tensor, TensorDataFrame), TypedDataFrameBase),
#     # )
#
#     def __init__(self, device=None, **kwargs):
#         self.device = device
#
#         self.tensor_dict_map = TensorDictMap()
#         self.model2tensor_map = TensorDictMap()
#
#         super().__init__(**kwargs)
#
#     def __setitem__(self, key, value):
#
#         if isinstance(value, TypedDataFrameBase3D):
#             model = value
#             dct, value = self.tensor_dict_map.add_model(
#                 key, model, device=self.device)
#
#         elif isinstance(value, TypedDataFrameBase):
#             model = value
#             value = TensorDataFrame(self.device, model)
#         else:
#             model = None
#         super().__setitem__(key, value)
#         if model is not None:
#             self.model2tensor_map[key] = value
#         #     super().__setitem__(value, model)
#
# # class DataSetDict(TensorDict):
# #     def __init__(self, device=None, model=None, **kwargs):
# #         super().__init__(**kwargs)
# #         if model is not None:
# #             self._tensor = self.update_from_dataframe_3d_config(
# #                 device, model
# #             )
# #
# #     @property
# #     def tensor(self):
# #         return self._tensor
# #
# #     @tensor.setter
# #     def tensor(self, tensor):
# #         if self._tensor is not None:
# #             raise AttributeError("tensor already set")
# #         self._tensor = tensor
