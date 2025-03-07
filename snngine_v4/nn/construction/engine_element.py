from __future__ import annotations

from typing import ClassVar

import torch
from pydantic import BaseModel


from snngine_v4.nn.construction.config_models.engine_element_config \
    import EngineElementConfig

from snngine_v4.utils.containers.mappings import ObjectMapConfig
from snngine_v4.utils.containers.node_map import (
    ModelNodeTreeElementConfig,
    ModelTree,
)
from snngine_v4.utils.core_utils import type_assertion
from snngine_v4.utils.cuda_utils.cuda_functions import CudaKeywords
from snngine_v4.utils.cuda_utils.tensor_dataframe import (
    TensorSeries,
)
from snngine_v4.utils.cuda_utils.tensor_dict import TensorDict
from snngine_v4.utils.object_builder.object_builder import \
    ObjectInitializationType
from snngine_v4.utils.object_builder.object_builder_dict import BuilderDict

# noinspection PyUnresolvedReferences
from snngine_v4.nn.cuda_backend import snn_utils


class EngineNodeElementConfig(ModelNodeTreeElementConfig):
    b_skip_forbidden_types: bool = True
    b_read_list_values: bool = True


class EngineNodes(ModelTree):
    InvertedConfigClass: ClassVar[type(ObjectMapConfig)] = (
        EngineNodeElementConfig, EngineElementConfig)


class EngineElement(BuilderDict):

    TENSOR_DICT_KW: ClassVar[str] = 'tensor_dict'

    ROOT_ELEMENT_KW: ClassVar[str] = 'root_element'
    NODE_TREE_KW: ClassVar[str] = 'node_tree'
    node_tree: EngineNodes

    DEFAULT_OBJECT_INIT_TYPE: ObjectInitializationType = (
        ObjectInitializationType.MODEL)

    def __init__(self, device, model,
                 n_curand_states=0,
                 config_model: EngineElementConfig = None,
                 node_tree=None,
                 root_element: EngineElement = None,
                 **kwargs):

        self.device = device
        self.config_model: EngineElementConfig = (
            model if config_model is None else config_model)
        self.tensor_dict: TensorDict = TensorDict()

        if node_tree is None:
            raise ValueError
        self.root_element = root_element
        if self.root_element is not self:
            self.BUILDER_OBJECT_CLASS_MAP.update(
                self.root_element.BUILDER_OBJECT_CLASS_MAP)
            self.BUILDER_OBJECT_SUPERCLASS_MAP.update(
                self.root_element.BUILDER_OBJECT_SUPERCLASS_MAP)
            self.OBJECT_INIT_TYPES.update(
                self.root_element.OBJECT_INIT_TYPES)
            self.OBJECT_INIT_SUPER_TYPES.update(
                self.root_element.OBJECT_INIT_SUPER_TYPES)

        super().__init__(model_container=model,
                         node_tree=node_tree,
                         build_kwargs={
                             CudaKeywords.DEVICE: self.device,
                             self.NODE_TREE_KW: node_tree,
                             self.ROOT_ELEMENT_KW: root_element,
                         },
                         **kwargs)

        if self.node_tree is None:
            raise AssertionError

        if n_curand_states > 0:
            self.curand_states = self._curand_states(n=n_curand_states)
        else:
            self.curand_states = None

        self.set_tensor_attr()

    def __setattr__(self, key, value):
        if ((key != self.TENSOR_DICT_KW) and (not hasattr(self, key))
                and isinstance(value, (TensorSeries,
                                       TensorDict))):
            if ((value in self.inv)
                    and (not hasattr(self.config_model, key))):
                raise PermissionError(f"{key}")
            if isinstance(value, TensorSeries):
                self.tensor_dict[key] = value
            elif isinstance(value, TensorDict):
                self.tensor_dict[key] = value.main_tensor
            else:
                type_assertion(value, (TensorSeries, TensorDict))
        super().__setattr__(key, value)

    def __setitem__(self, key, value):
        if not (self.root_element in [self, None]):
            self.root_element[key] = value
        super().__setitem__(key, value)

    @staticmethod
    def _curand_states(n):
        cu = snn_utils.CuRandStates(n).ptr()
        return cu

    @classmethod
    def make_object_kwargs(cls, object_class, model: BaseModel, **kwargs):
        object_kwargs = super().make_object_kwargs(
            object_class=object_class, model=model, **kwargs)
        if not issubclass(object_class, EngineElement):
            object_kwargs.pop(cls.NODE_TREE_KW, None)
            object_kwargs.pop(cls.ROOT_ELEMENT_KW, None)
        return object_kwargs

    @property
    def children_models(self):
        return self.node_tree.children(self.config_model)

    @property
    def children_elements(self):
        return [self.root_element[x] for x in self.children_models]

    @property
    def parent_element(self):
        return self.root_element[self.node_tree.parent(self.config_model)]

    def set_tensor_attr(self):
        tdf_model_dict = self.config_model.tdf_dict()
        for k, model in tdf_model_dict.items():
            if model in self:
                setattr(self, k, self[model])
            else:
                pass
        elt_model_dict = self.config_model.elt_dict()
        for k, model in elt_model_dict.items():
            if model in self:
                setattr(self, k, self[model])
            else:
                pass

    def sync_to_cpu(self):
        self.tensor_dict.sync_to_cpu()

    def validate_consistency(self):
        pass

    def zeros_i32(self, shape) -> torch.Tensor:
        return torch.zeros(shape, dtype=torch.int32, device=self.device)

    def zeros_f32(self, shape) -> torch.Tensor:
        return torch.zeros(shape, dtype=torch.float32, device=self.device)

    def rand_f32(self, shape) -> torch.Tensor:
        return torch.rand(shape, dtype=torch.float32, device=self.device)
