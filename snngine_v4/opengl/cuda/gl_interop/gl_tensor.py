import numpy as np
import torch

from snngine_v4.opengl.cuda.gl_interop.gl_buffer import GLBuffer


class GLBufferTensor:

    def __init__(self, dtype: str | np.dtype | None,
                 opengl_id: int, shape: tuple | None,
                 device: torch.device | int = 0, stream: int = 0):
        strides = (shape[1] * dtype.itemsize, dtype.itemsize)
        self.gl_buffer = GLBuffer.from_id(
            dtype=dtype, opengl_id=opengl_id, shape=shape,
            strides=strides, device=device, stream=stream)
        self.tensor = torch.as_tensor(self.gl_buffer.numba_device_array,
                                      device=self.gl_buffer.device)

    @property
    def device(self):
        return self.gl_buffer.device

    @classmethod
    def from_array(cls, opengl_id, array: np.ndarray,
                   device: torch.device | int = 0, stream: int = 0):
        return cls(opengl_id=opengl_id, shape=array.shape,
                   dtype=array.dtype, device=device,
                   stream=stream)


class GLVBOTensor(GLBufferTensor):
    def __init__(self, opengl_id: int, shape: tuple,
                 device: torch.device | int = 0, stream: int = 0):
        super().__init__(opengl_id=opengl_id, shape=shape, device=device,
                         dtype=np.float32, stream=stream)


class GLIBOTensor(GLBufferTensor):
    def __init__(self, opengl_id: int, shape: tuple,
                 device: torch.device | int = 0, stream: int = 0):
        super().__init__(opengl_id=opengl_id, shape=shape, device=device,
                         dtype=np.int32, stream=stream)
