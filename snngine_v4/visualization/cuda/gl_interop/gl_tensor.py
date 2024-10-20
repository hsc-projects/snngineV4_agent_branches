from functools import cached_property
from typing import Callable, ClassVar, Iterable, Type

import numpy as np
import torch
from pydantic import BaseModel

from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict,
    DictContainerConfig,
)
from snngine_v4.utils.containers.mappings import (
    Int2ObjectMapConfig, Model2ObjectMap,
    Object2ObjectMap,
)
from snngine_v4.visualization.cuda.gl_interop.gl_buffer import GLBuffer


class GLBufferTensor:

    def __init__(self, dtype: str | np.dtype | None,
                 opengl_id: int, shape: tuple | None,
                 device: torch.device | int = 0, stream: int = 0):
        strides = (shape[1] * dtype.itemsize, dtype.itemsize)
        self.gl_buffer = GLBuffer.from_id(
            dtype=dtype, opengl_id=opengl_id, shape=shape,
            strides=strides, device=device, stream=stream)

    @property
    def device(self):
        return self.gl_buffer.device

    @classmethod
    def from_array(cls, opengl_id, array: np.ndarray,
                   device: torch.device | int = 0, stream: int = 0):
        return cls(opengl_id=opengl_id, shape=array.shape,
                   dtype=array.dtype, device=device,
                   stream=stream)

    def numpy(self):
        return self.tensor.cpu().numpy()

    @cached_property
    def tensor(self):
        return torch.as_tensor(self.gl_buffer.numba_device_array,
                               device=self.gl_buffer.device)


class GLVBOTensor(GLBufferTensor):
    def __init__(self, opengl_id: int, shape: tuple,
                 device: torch.device | int = 0, stream: int = 0):
        super().__init__(opengl_id=opengl_id, shape=shape, device=device,
                         dtype=np.dtype('float32'), stream=stream)


class GLIBOTensor(GLBufferTensor):
    def __init__(self, opengl_id: int, shape: tuple,
                 device: torch.device | int = 0, stream: int = 0):
        super().__init__(opengl_id=opengl_id, shape=shape, device=device,
                         dtype=np.dtype('int32'), stream=stream)


class ArrayToTensorMap(Object2ObjectMap):
    ContainerConfigClass: ClassVar = ((np.ndarray, ), (GLBufferTensor, ))


class GLTensorDict(ConfigurableDict):
    values: Callable[[], Iterable[GLBufferTensor]]
    ContainerConfigClass: ClassVar = (DictContainerConfig, GLBufferTensor)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.array2tensor = ArrayToTensorMap()

    def __setitem__(self, key: str, value: GLBufferTensor):
        super().__setitem__(key, value)
        self.array2tensor[value.numpy()] = value


class CudaRegister(Model2ObjectMap):

    class ContainerConfigClass(Int2ObjectMapConfig, frozen=True):
        allowed_types: Type[GLBufferTensor] = GLBufferTensor
