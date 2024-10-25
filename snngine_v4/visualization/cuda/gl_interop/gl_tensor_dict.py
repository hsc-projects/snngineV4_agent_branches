from typing import ClassVar

import torch

from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict,
    DictContainerConfig,
)
from snngine_v4.utils.containers.mappings import Object2ObjectMap
from snngine_v4.visualization.cuda.gl_interop.gl_tensor import GLBufferTensor
from snngine_v4.visualization.cuda.tensor_dict import TensorDict


class TensorToGLBufferTensorMap(Object2ObjectMap):
    ContainerConfigClass: ClassVar = ((torch.Tensor, ), (GLBufferTensor, ))


class StringToGLBufferTensorMap(ConfigurableDict):
    ContainerConfigClass: ClassVar = (DictContainerConfig, GLBufferTensor)


class GLTensorDict(TensorDict):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tensor2gl: (dict[str, GLBufferTensor]
                         | TensorToGLBufferTensorMap) = (
            TensorToGLBufferTensorMap())
        self.str2gl: dict[str, GLBufferTensor] | StringToGLBufferTensorMap = (
            StringToGLBufferTensorMap())

    def __setitem__(self, key: str, value: GLBufferTensor):
        super().__setitem__(key, value.tensor)
        self.tensor2gl[value.tensor] = value
        self.str2gl[key] = value
