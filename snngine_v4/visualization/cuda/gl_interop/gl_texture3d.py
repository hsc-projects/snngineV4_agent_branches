from functools import cached_property

import numba
import numpy as np
import pycuda
import pycuda.driver

import torch
from pycuda.gl import (
    RegisteredImage,
    RegisteredMapping,
    graphics_map_flags
)
from vispy.gloo import gl

from snngine_v4.utils.data_utils.validation.array_annotation import (
    f32_3D
)
from snngine_v4.visualization.cuda.gl_interop.gl_buffer import GLBuffer
from snngine_v4.visualization.cuda.gl_interop.gl_tensor import GLBufferTensor


class OpenglTextureDataError(AssertionError):
    pass


class GLRegisteredTexture3D(GLBuffer):

    def __post_init__(self):
        super().__post_init__()

    @classmethod
    def from_id(cls, dtype: str | np.dtype | None, strides,
                opengl_id: int, shape: tuple | None,
                device: torch.device | int = 0, stream: int = 0):

        # noinspection PyUnresolvedReferences
        reg = RegisteredImage(opengl_id, gl.GL_TEXTURE_3D,
                              graphics_map_flags.NONE
                              # graphics_map_flags.WRITE_DISCARD
                              )
        mapping: RegisteredMapping = reg.map(None)
        gpu_data = mapping.array(0, 0)
        # ptr = gpu_data.handle
        return cls(shape=shape,
                   strides=strides,
                   dtype=dtype,
                   gpu_data=gpu_data,
                   registered_buffer=reg,
                   mapping=mapping,
                   opengl_id=opengl_id,
                   device=device,
                   stream=stream)


class GLTexture3DTensor(GLBufferTensor):

    def __init__(self,
                 texture_id,
                 cpu_data: np.ndarray,
                 device: torch.device | int,
                 stream: int = 0,
                 validation_interface=None):

        validation_interface = (validation_interface or f32_3D)
        dtype = np.dtype('float32')

        super().__init__(
            dtype=dtype, opengl_id=texture_id,
            shape=cpu_data.shape, device=device,
            stream=stream,
            validation_interface=validation_interface)

        # noinspection PyArgumentList
        self._cpy_tnsr2tex = pycuda.driver.Memcpy3D()
        self._cpy_tnsr2tex.set_src_device(self.tensor.data_ptr())
        self._cpy_tnsr2tex.set_dst_array(self.gl_buffer.gpu_data)

        # noinspection PyArgumentList
        self._cpy_tex2tnsr = pycuda.driver.Memcpy3D()
        self._cpy_tex2tnsr.set_src_array(self.gl_buffer.gpu_data)
        self._cpy_tex2tnsr.set_dst_device(self.tensor.data_ptr())

        self._cpy_tnsr2tex.width_in_bytes \
            = self._cpy_tex2tnsr.width_in_bytes \
            = dtype.itemsize * self.gl_buffer.shape[2]

        self._cpy_tnsr2tex.src_pitch \
            = self._cpy_tex2tnsr.src_pitch \
            = dtype.itemsize * self.gl_buffer.shape[2]

        self._cpy_tnsr2tex.src_height \
            = self._cpy_tnsr2tex.height \
            = self._cpy_tex2tnsr.src_height \
            = self._cpy_tex2tnsr.height \
            = self.gl_buffer.shape[1]

        self._cpy_tnsr2tex.depth \
            = self._cpy_tex2tnsr.depth \
            = self.gl_buffer.shape[0]

        # self.cpy_tnsr2tex()
        self.cpy_tex2tnsr(cpu_data)

    def cpy_tnsr2tex(self, cpu_data=None):
        """
        TODO: Restrict copying to actually modified data.
        """
        # self.map()
        #
        # if cpu_data is not None:
        #     self.tensor[:] = torch.from_numpy(cpu_data)
        # torch.cuda.synchronize()
        # noinspection PyArgumentList
        self._cpy_tnsr2tex()
        return

    def cpy_tex2tnsr(self, cpu_data=None, validate: bool = True):
        self.gl_buffer.map()
        torch.cuda.synchronize()
        # noinspection PyArgumentList
        self._cpy_tex2tnsr()
        if cpu_data is not None:
            t = self.tensor.cpu().numpy()
            if (validate is True) and (((cpu_data - t) != 0).all()):
                raise OpenglTextureDataError("((cpu_data - t) != 0).all()")
        return

    def _make_buffer(self, dtype: str | np.dtype | None,
                     opengl_id: int, shape: tuple | None,
                     device: torch.device | int = 0, stream: int = 0,):
        strides = (shape[1] * (dtype.itemsize ** 2),
                   shape[2] * dtype.itemsize,
                   dtype.itemsize)
        gl_buffer = GLRegisteredTexture3D.from_id(
            dtype=dtype, opengl_id=opengl_id, shape=shape,
            strides=strides, device=device, stream=stream)
        return gl_buffer

    @cached_property
    def tensor(self):
        return torch.zeros(
                self.gl_buffer.shape, device=self.device,
                dtype=torch.float32)
