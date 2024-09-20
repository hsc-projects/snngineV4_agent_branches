from __future__ import annotations

import ctypes
from copy import copy
from dataclasses import dataclass
from typing import ClassVar

import numba.cuda
import numpy as np

import pycuda.driver
import pycuda.gpuarray
import torch
from pycuda.gl import RegisteredBuffer, RegisteredMapping

from snngine_v4.utils.containers.typed_container import ContainerConfig
from snngine_v4.utils.containers.configurable_dict import ConfigurableDict


class GLBufferMap(ConfigurableDict):

    def __init__(self, data=None):
        self.data: dict[int, GLBuffer] | None = None
        super().__init__(
            data=data,
            container_conf=ContainerConfig(
                allowed_types=GLBuffer))

    def unregister_all(self):
        registered_buffers = copy(self.data)
        for rb in registered_buffers.values():
            rb.unregister()


class ExternalMemory(object):
    """
    Provide an externally managed memory.
    Interface requirement: __cuda_memory__, device_ctypes_pointer,
    _cuda_memsize_
    """
    __cuda_memory__ = True

    def __init__(self, ptr, size):
        self.device_ctypes_pointer = ctypes.c_void_p(ptr)
        self._cuda_memsize_ = size


@dataclass(frozen=True, repr=False)
class GLBuffer:

    GLOBAL_MAP: ClassVar[GLBufferMap] = GLBufferMap()

    shape: tuple
    strides: tuple
    dtype: np.dtype
    gpu_data: ExternalMemory | pycuda.driver.Array
    registered_buffer: RegisteredBuffer
    mapping: RegisteredMapping
    opengl_id: int | None
    device: torch.device | int = 0
    stream: int = 0

    def __post_init__(self):
        if self.GLOBAL_MAP is not None:
            self.GLOBAL_MAP[self.opengl_id] = self
        self.unmap()

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.opengl_id}"

    @classmethod
    def from_id(
            cls, dtype: str | np.dtype | None, strides,
            opengl_id: int, shape: tuple | None,
            device: torch.device | int = 0, stream: int = 0):

        if isinstance(dtype, str):
            dtype = np.dtype(dtype)

        numba.cuda.select_device(
            device.index if not isinstance(device, int) else device)

        reg = RegisteredBuffer(opengl_id)
        mapping: RegisteredMapping = reg.map(None)
        ptr, size = mapping.device_ptr_and_size()
        return cls(
            shape=shape, strides=strides,
            gpu_data=ExternalMemory(ptr, size),
            registered_buffer=reg,
            mapping=mapping,
            opengl_id=opengl_id,
            dtype=dtype, device=device, stream=stream)

    def map(self):
        self.registered_buffer.map(None)

    @property
    def size(self):
        # noinspection PyProtectedMember
        return self.gpu_data._cuda_memsize_

    def unregister(self):
        self.registered_buffer.unregister()
        self.GLOBAL_MAP.pop(self.opengl_id)

    def unmap(self):
        self.mapping.unmap()

    def numba_device_array(self):
        # noinspection PyUnresolvedReferences
        numba_device_array = numba.cuda.cudadrv.devicearray.DeviceNDArray(
            shape=self.shape,
            strides=self.strides,
            dtype=self.dtype,
            stream=self.stream,
            gpu_data=self.gpu_data)
        return numba_device_array
