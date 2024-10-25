from functools import cached_property

import numpy as np
import torch

from snngine_v4.utils.data.validation.array_annotation import ArrayInterfaces
from snngine_v4.utils.data.validation.np_interface import TypedNumpyInterface
from snngine_v4.visualization.cuda.gl_interop.gl_buffer import GLBuffer


class GLBufferTensor:

    def __init__(self, dtype: str | np.dtype | None,
                 opengl_id: int, shape: tuple | None,
                 device: torch.device | int = 0, stream: int = 0,
                 validation_interface=None):
        strides = (shape[1] * dtype.itemsize, dtype.itemsize)
        self.gl_buffer = GLBuffer.from_id(
            dtype=dtype, opengl_id=opengl_id, shape=shape,
            strides=strides, device=device, stream=stream)
        self.validation_interface: TypedNumpyInterface = validation_interface

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
                 device: torch.device | int = 0, stream: int = 0,
                 validation_interface=None):
        validation_interface = (validation_interface or ArrayInterfaces()
                                .vbo_array_type(shape[1]))
        super().__init__(opengl_id=opengl_id, shape=shape, device=device,
                         dtype=np.dtype('float32'), stream=stream,
                         validation_interface=validation_interface)


class GLIBOTensor(GLBufferTensor):
    def __init__(self, opengl_id: int, shape: tuple,
                 device: torch.device | int = 0, stream: int = 0,
                 validation_interface=None):
        validation_interface = (validation_interface or ArrayInterfaces()
                                .ibo_array_type(shape[1]))
        super().__init__(opengl_id=opengl_id, shape=shape, device=device,
                         dtype=np.dtype('int32'), stream=stream,
                         validation_interface=validation_interface)
