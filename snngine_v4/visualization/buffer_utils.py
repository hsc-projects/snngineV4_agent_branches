import numpy as np


def is_2d_buffer_array(array: np.ndarray) -> bool:
    return isinstance(array, np.ndarray) and array.ndim == 2


def adapt_dim(buffer: np.ndarray, ref: np.ndarray, axis=0) -> np.ndarray:
    if buffer.shape[axis] != ref.shape[axis]:
        if buffer.shape[axis] > ref.shape[axis]:
            buffer = np.delete(buffer, obj=-1, axis=axis)
        else:
            add = np.take(buffer, indices=-1, axis=axis)
            add = np.expand_dims(add, axis=axis)
            buffer = np.concatenate((buffer, add), axis)

    return buffer
