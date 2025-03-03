from typing import ClassVar, Type

import torch
from pydantic import BaseModel

from snngine_v4.geometry.grid.finite_grid import FiniteGrid
from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.nn.config_models.nn_element_config import EngineElementConfig
# noinspection PyUnresolvedReferences
from snngine_v4.nn.cuda_backend import snn_utils
from snngine_v4.utils.core_utils import type_assertion
from snngine_v4.utils.cuda_utils.cuda_functions import CudaKeywords
from snngine_v4.utils.cuda_utils.tensor_dataframe import TensorDataFrame
from snngine_v4.utils.cuda_utils.tensor_dict import TensorDict
from snngine_v4.utils.data_utils.dataframe_config import (
    TypedDataFrameBase, TypedDataFrameBase3D,
)
from snngine_v4.utils.object_builder.object_builder import \
    ObjectInitializationType
from snngine_v4.utils.object_builder.object_builder_dict import BuilderDict


class EngineElement(BuilderDict):

    TENSOR_DICT_KW: ClassVar[str] = 'tensor_dict'

    BUILDER_OBJECT_CLASS_MAP: ClassVar[dict[Type[BaseModel], Type]] = {
        FiniteGridConfig: FiniteGrid,
        # TypedDataFrameBase3D: TensorDict,
    }

    BUILDER_OBJECT_SUPERCLASS_MAP: ClassVar[dict[Type[BaseModel], Type]] = {
        TypedDataFrameBase3D: TensorDict,
        TypedDataFrameBase: TensorDataFrame,
    }

    OBJECT_INIT_SUPER_TYPES = {
        TypedDataFrameBase3D: ObjectInitializationType.MODEL}

    def __init__(self, device, model,
                 n_curand_states=0,
                 config_model: EngineElementConfig = None,
                 **kwargs):

        self.device = device
        self.config_model: EngineElementConfig = (
            model if config_model is None else config_model)
        self.tensor_dict = TensorDict()

        super().__init__(model_container=model,
                         build_kwargs={CudaKeywords.DEVICE: self.device},
                         **kwargs)

        if n_curand_states > 0:
            self.curand_states = self._curand_states(n=n_curand_states)

        self.set_tensor_attr()

    def __setattr__(self, key, value):
        if ((key != self.TENSOR_DICT_KW) and (not hasattr(self, key))
                and isinstance(value, (TensorDataFrame, TensorDict))):
            if ((value in self.inv)
                    and (not hasattr(self.config_model, key))):
                raise PermissionError(f"{key}")
            if isinstance(value, TensorDataFrame):
                self.tensor_dict[key] = value
            elif isinstance(value, TensorDict):
                self.tensor_dict[key] = value.main_tensor
            else:
                type_assertion(value, (TensorDataFrame, TensorDict))
        super().__setattr__(key, value)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)

    @staticmethod
    def _curand_states(n):
        cu = snn_utils.CuRandStates(n).ptr()
        # self.print_allocated_memory('curand_states')
        return cu

    def set_tensor_attr(self):
        tdf_model_dict = self.config_model.tdf_dict()
        for k, model in tdf_model_dict.items():
            if model in self:
                setattr(self, k, self[model])
            else:
                pass

    def sync_to_cpu(self):
        self.tensor_dict.sync_to_cpu()

    def zeros_i32(self, shape) -> torch.Tensor:
        return torch.zeros(shape, dtype=torch.int32, device=self.device)

    def zeros_f32(self, shape) -> torch.Tensor:
        return torch.zeros(shape, dtype=torch.float32, device=self.device)
