import numpy as np
import torch

from snngine_v4.utils.core_utils import Singleton


class CudaKeywords:

    DEVICE = 'device'


def compare_devices(d0, d1):
    if (not isinstance(d0, int)) and (d0 != 'cpu'):
        d0 = d0.index
    if (not isinstance(d1, int)) and (d1 != 'cpu'):
        d1 = d1.index
    return d0 == d1


def assert_device_equivalency(d0, d1):
    if not compare_devices(d0, d1):
        raise AssertionError(
            f"d0 ({d0}) != d1 ({d1}) ")


class CudaVariables(metaclass=Singleton):
    def __init__(self):
        self.last_allocated_memory = None


def save_current_allocated_memory(f=10**9):
    cuda_variables = CudaVariables()
    cuda_variables.last_allocated_memory = torch.cuda.memory_allocated(0) / f


def print_allocated_memory_diff(naming='', f=10**9):

    cuda_variables = CudaVariables()

    last = cuda_variables.last_allocated_memory
    cuda_variables.last_allocated_memory = now = (
            torch.cuda.memory_allocated(0) / f)
    diff = np.round((cuda_variables.last_allocated_memory - last), 3)
    unit = 'GB'
    unit2 = 'GB'
    if cuda_variables.last_allocated_memory < 0.1:
        now = now * 10 ** 3
        unit = 'MB'
    if diff < 0.1:
        diff = np.round((cuda_variables.last_allocated_memory - last) * 10 ** 3,
                        1)
        unit2 = 'MB'
    now = np.round(now, 1)
    print(f"memory_allocated({naming}) = {now}{unit}"
          f" ({'+' if diff >= 0 else ''}{diff}{unit2})")
