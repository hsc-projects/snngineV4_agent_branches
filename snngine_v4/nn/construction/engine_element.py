from __future__ import annotations

from functools import cached_property
from typing import ClassVar, Tuple, Type

import torch
from pydantic import BaseModel

from snngine_v4.visualization.cuda.gl_interop import GLTensorDict

from snngine_v4.nn.construction.config_models.engine_element_config import (
    EngineElementConfig,
    EngineElementConfigMixin,
)

from snngine_v4.utils.containers.node_map import (
    ModelNodeTreeElementConfig,
    ModelTree,
)
from snngine_v4.utils.cuda_utils.cuda_functions import CudaKeywords
from snngine_v4.utils.cuda_utils.tensor_dataframe import (
    TensorDataFrame, TensorSeries,
)
from snngine_v4.utils.cuda_utils.tensor_dict import TensorDict
from snngine_v4.utils.data_utils.dataframe_config import (
    SeriesModel, TypedDataFrameBase3D,
    TypedDataFrameModel,
)
from snngine_v4.utils.object_builder.object_builder import \
    ObjectInitializationType
from snngine_v4.utils.object_builder.object_builder_dict import BuilderDict


class EngineNodesConfig(ModelNodeTreeElementConfig):
    b_skip_forbidden_types: bool = True
    b_read_list_values: bool = True


class EngineNodes(ModelTree):
    InvertedConfigClass: ClassVar[
        Tuple[type(EngineNodesConfig), type(EngineElementConfigMixin)]] = (
        EngineNodesConfig, EngineElementConfigMixin)


# class UndefinedEngineElement(BuilderDict):
#     def __init__(self, model_container=None, build_kwargs=None,
#                  node_tree=None,
#                  **kwargs):
#         super().__init__(model_container=model_container,
#                          build_kwargs=build_kwargs,
#                          node_tree=node_tree)
#
#     @property
#     def children_models(self):
#         return []


class EngineElement(BuilderDict):
    """

    """
    TENSOR_DICT_KW: ClassVar[str] = 'tensor_dict'

    ROOT_ELEMENT_KW: ClassVar[str] = 'root_element'
    PARENT_ELEMENT_KW: ClassVar[str] = 'parent_element'
    NODE_TREE_KW: ClassVar[str] = 'node_tree'
    node_tree: EngineNodes

    DEFAULT_OBJECT_INIT_TYPE: ObjectInitializationType = (
        ObjectInitializationType.MODEL)

    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
    }

    BUILDER_OBJECT_SUPERCLASS_MAP: ClassVar[dict] = {
        TypedDataFrameBase3D: TensorDict,       # Keep order (1/3)
        TypedDataFrameModel: TensorDataFrame,   # Keep order (2/3)
        SeriesModel: TensorSeries,              # Keep order (3/3)
    }

    # BUILDER_DEFAULT_OBJECT_CLASS: ClassVar = UndefinedEngineElement
    # root_element: SpatialNetwork

    def __init__(self, device,
                 model=None,
                 config_model: EngineElementConfig = None,
                 build_model=None,
                 n_curand_states=0,
                 node_tree=None,
                 root_element: EngineElement = None,
                 parent_element: EngineElement = None,
                 **kwargs):

        if EngineElementConfig not in self.BUILDER_OBJECT_SUPERCLASS_MAP:
            self.BUILDER_OBJECT_SUPERCLASS_MAP[EngineElementConfig] = (
                EngineElement)

        if model is not None:
            if build_model is not None:
                raise ValueError
            if config_model is not None:
                raise ValueError
            config_model = model
            build_model = model
        else:
            if config_model is None:
                raise ValueError
            if build_model is None:
                build_model = (config_model.tdf_values()
                               + config_model.elt_values())

        self.device = device
        self.config_model: EngineElementConfig = config_model
        self.tensor_dict: TensorDict = TensorDict()

        if node_tree is None:
            raise ValueError

        self.root_element = root_element

        if self.root_element is not self:
            self.update_build_kwargs(parent_element)
        else:
            self._cuda_opengl_map = None

        super().__init__(model_container=build_model,
                         node_tree=node_tree,
                         # build_kwargs={
                         #     CudaKeywords.DEVICE: self.device,
                         #     self.NODE_TREE_KW: node_tree,
                         #     self.ROOT_ELEMENT_KW: root_element,
                         #     self.PARENT_ELEMENT_KW: self,
                         # },
                         **kwargs)

        if self.node_tree is None:
            raise AssertionError
        # if self.parent_element is not parent_element:
        #     raise AssertionError

        if (n_curand_states > 0) and self.b_cuda_backend_available:
            self.curand_states = self._curand_states(n=n_curand_states)
        else:
            self.curand_states = None

        self.set_tensor_attr()

    def __setattr__(self, key, value):
        if key != self.TENSOR_DICT_KW:
            if isinstance(value, (TensorSeries, TensorDict, torch.Tensor)):
                if isinstance(value, (TensorSeries, TensorDict)):
                    if ((not hasattr(self, key))
                            and (value in self.inv)
                            and (not hasattr(self.config_model, key))):
                        raise PermissionError(
                            f"missing configuration for'{key}'")
                self.tensor_dict[key] = value

        super().__setattr__(key, value)

    def __setitem__(self, key, value):
        if not (self.root_element in [self, None]):
            self.root_element[key] = value
        super().__setitem__(key, value)

    @cached_property
    def b_cuda_backend_available(self):
        try:
            # noinspection PyUnresolvedReferences
            from snngine_v4.nn.cuda_backend import snn_utils
        except ModuleNotFoundError:
            return False
        return True

    @property
    def children_models(self):
        return self.node_tree.children(self.config_model)

    @property
    def children_elements(self):
        return [self.root_element[x] for x in self.children_models]

    @staticmethod
    def _curand_states(n):
        # noinspection PyUnresolvedReferences
        from snngine_v4.nn.cuda_backend import snn_utils
        cu = snn_utils.CuRandStates(n).ptr()
        return cu

    @property
    def cuda_gl_dict(self) -> GLTensorDict:
        gl_dict = self.cuda_opengl_map[self.config_model]
        return gl_dict

    @cached_property
    def default_build_kwargs(self):
        return {
            CudaKeywords.DEVICE: self.device,
            self.NODE_TREE_KW: self.node_tree,
            self.ROOT_ELEMENT_KW: self.root_element,
            self.PARENT_ELEMENT_KW: self,
            'b_ignore_default_object_class': True,
            'b_raise_if_missing_object_class': False
        }

    @classmethod
    def make_object_kwargs(cls, object_class, model: BaseModel, **kwargs):
        object_kwargs = super().make_object_kwargs(
            object_class=object_class, model=model, **kwargs)
        if not issubclass(object_class, EngineElement):
            object_kwargs.pop(cls.NODE_TREE_KW, None)
            object_kwargs.pop(cls.ROOT_ELEMENT_KW, None)
            object_kwargs.pop(cls.PARENT_ELEMENT_KW, None)
        return object_kwargs

    @property
    def cuda_opengl_map(self):
        return self.root_element._cuda_opengl_map

    @cuda_opengl_map.setter
    def cuda_opengl_map(self, value):
        self.root_element._cuda_opengl_map = value

    def parent_element(self):
        parent_model = self.node_tree.parent(self.config_model)
        try:
            return self.root_element[parent_model]
        except KeyError:
            if parent_model is self.root_element.config_model:
                self.root_element[parent_model] = self.root_element
                return self.root_element[parent_model]
            raise

    def set_tensor_attr(self):
        if isinstance(self.config_model, EngineElementConfigMixin):
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
        for c in self.children_elements:
            c.sync_to_cpu()

    def update_build_kwargs(self, other: EngineElement):
        self.BUILDER_OBJECT_CLASS_MAP.update(
            other.BUILDER_OBJECT_CLASS_MAP)
        self.BUILDER_OBJECT_SUPERCLASS_MAP.update(
            other.BUILDER_OBJECT_SUPERCLASS_MAP)
        self.OBJECT_INIT_TYPES.update(
            other.OBJECT_INIT_TYPES)
        self.OBJECT_INIT_SUPER_TYPES.update(
            other.OBJECT_INIT_SUPER_TYPES)

    def validate_consistency(self):
        pass

    def zeros_i32(self, shape) -> torch.Tensor:
        return torch.zeros(shape, dtype=torch.int32, device=self.device)

    def zeros_f32(self, shape) -> torch.Tensor:
        return torch.zeros(shape, dtype=torch.float32, device=self.device)

    def rand_f32(self, shape) -> torch.Tensor:
        return torch.rand(shape, dtype=torch.float32, device=self.device)
