from copy import copy

import numpy as np
import pandas as pd
# import torch


def _check_shape(array):
    if len(array.shape) != 3:
        raise NotImplementedError(f'Expected 3D array, got {array.shape}.')


def _true_mask(ref_array):
    return ref_array == ref_array


def validate_mask(mask, ref, b_check_shape: bool):
    if b_check_shape is True:
        _check_shape(ref)
    if mask is None:
        mask = _true_mask(ref)
    if mask.shape != ref.shape:
        raise ValueError(f'Mask shape {mask.shape} does not match '
                         f'reference array shape {ref.shape}.')
    return mask


def extend_mask(mask, new_value=True, extension=1):
    """
    Create a mask for the extended part of a 3D array.
    """
    _check_shape(mask)

    new_shape = tuple(np.array(mask.shape) + 2 * extension)
    if isinstance(mask, np.ndarray):
        new_mask = np.zeros(new_shape, dtype=mask.dtype)
    elif isinstance(mask, torch.Tensor):
        new_mask = torch.zeros(new_shape, dtype=mask.dtype).to(mask.device)
    else:
        raise TypeError(f'Expected np.ndarray or torch.Tensor, '
                        f'got {type(mask)}')
    new_mask[:] = bool(new_value)
    new_mask[extension:-extension,
             extension:-extension,
             extension:-extension] = mask
    return new_mask


def _make_mask(init_mask, and_mask, ref_array, b_inv: bool = False,
               b_check_shape: bool = True):

    if not isinstance(b_inv, bool):
        raise TypeError(f'Expected bool, got {type(b_inv)}')

    if not isinstance(b_check_shape, bool):
        raise TypeError(f'Expected bool, got {type(b_check_shape)}')

    if init_mask is not None:
        init_mask = validate_mask(mask=init_mask, ref=ref_array,
                                  b_check_shape=b_check_shape)
    if b_inv is True:
        and_mask = ~and_mask
    if init_mask is None:
        return and_mask
    return init_mask & and_mask


def mask_value_interval(ref_array, value_range: pd.Interval, mask=None,
                        b_invert: bool = False):
    """
    Mask an array according to a value range.
    """
    left = value_range.left
    right = value_range.right

    interval_mask_ = (
        ref_array >= left
        if ((value_range.closed == 'left') or (value_range.closed == 'both'))
        else ref_array > left)

    interval_mask_ &= (
        ref_array <= right
        if ((value_range.closed == 'right') or (value_range.closed == 'both'))
        else ref_array < right)

    return _make_mask(init_mask=mask, and_mask=interval_mask_,
                      ref_array=ref_array,
                      b_inv=b_invert, b_check_shape=False)


def mask_inner(ref_array, mask=None, b_invert: bool = False,
               border_width: int = 1):
    """
    Create a mask for the inner part of a 3D array.
    """
    inner_mask_ = ~_true_mask(ref_array)
    inner_mask_[border_width:-border_width,
                border_width:-border_width,
                border_width:-border_width] = True
    return _make_mask(init_mask=mask, and_mask=inner_mask_, ref_array=ref_array,
                      b_inv=b_invert, b_check_shape=True)


def mask_corners(ref_array, mask, b_invert: bool = False):
    """
    Create a mask for the corner part of a 3D array.
    """
    # noinspection PyTypeChecker
    corner_mask_: np.ndarray = ~_true_mask(ref_array)
    corner_mask_[0, 0, 0] = True
    corner_mask_[0, 0, -1] = True
    corner_mask_[0, -1, 0] = True
    corner_mask_[0, -1, -1] = True
    corner_mask_[-1, 0, 0] = True
    corner_mask_[-1, 0, -1] = True
    corner_mask_[-1, -1, 0] = True
    corner_mask_[-1, -1, -1] = True

    return _make_mask(init_mask=mask, and_mask=corner_mask_,
                      ref_array=ref_array,
                      b_inv=b_invert, b_check_shape=True)


def mask_edges(ref_array, mask=None, b_invert: bool = False):

    """
    Create a mask for the edge part of a 3D array.
    """
    edge_mask_ = ~_true_mask(ref_array)
    edge_mask_[0, 0, 1:-1] = True
    edge_mask_[0, -1, 1:-1] = True
    edge_mask_[-1, 0, 1:-1] = True
    edge_mask_[-1, -1, 1:-1] = True
    edge_mask_[0, 1:-1, 0] = True
    edge_mask_[0, 1:-1, -1] = True
    edge_mask_[-1, 1:-1, 0] = True
    edge_mask_[-1, 1:-1, -1] = True
    edge_mask_[1:-1, 0, 0] = True
    edge_mask_[1:-1, 0, -1] = True
    edge_mask_[1:-1, -1, 0] = True
    edge_mask_[1:-1, -1, -1] = True

    return _make_mask(init_mask=mask, and_mask=edge_mask_, ref_array=ref_array,
                      b_inv=b_invert, b_check_shape=True)


class MaskMaker:

    def __init__(self, ref_array, initial_mask=None):
        self.ref_array = ref_array

        self.initial_mask = initial_mask

    def __call__(self, mask=None, ref_array=None):
        return self.__class__(ref_array=self._ref_array_param(ref_array),
                              initial_mask=self._mask_param(mask))

    def _mask_param(self, mask):
        return self.initial_mask if mask is None else mask

    def _pre_process_kwargs(self, ref_array=None, mask=None, **kwargs):
        kwargs['ref_array'] = self._ref_array_param(ref_array)
        kwargs['mask'] = self._mask_param(mask)
        return kwargs

    def _ref_array_param(self, ref_array):
        return self.ref_array if ref_array is None else ref_array

    def mask_corners(self, **kwargs):
        return mask_corners(**self._pre_process_kwargs(**kwargs))

    def mask_edges(self, **kwargs):
        return mask_edges(**self._pre_process_kwargs(**kwargs))

    def mask_inner(self, **kwargs):
        return mask_inner(**self._pre_process_kwargs(**kwargs))

    def mask_value_interval(self, value_range: pd.Interval, **kwargs):
        return mask_value_interval(value_range=value_range,
                                   **self._pre_process_kwargs(**kwargs))

    def true_mask(self):
        return _true_mask(ref_array=self.ref_array)

    def extend_mask(self, extension=1):
        return extend_mask(mask=self.initial_mask, extension=extension)


def n_neighbours(mask, count_array):

    extended_mask = extend_mask(mask, extension=1)
    mask_maker = MaskMaker(ref_array=extended_mask)
    extended_mask_copy = copy(extended_mask)

    slices = [(slice(2, None), slice(1, -1), slice(1, -1)),
              (slice(-2), slice(1, -1), slice(1, -1)),
              (slice(1, -1), slice(2, None), slice(1, -1)),
              (slice(1, -1), slice(None, -2), slice(1, -1)),
              (slice(1, -1), slice(1, -1), slice(2, None)),
              (slice(1, -1), slice(1, -1), slice(None, -2))]

    inner_array = extended_mask_copy[1:-1, 1:-1, 1:-1]

    for s in slices:
        extended_mask_copy[:] = False
        extended_mask_copy[s] = mask
        extended_mask_copy[:] = mask_maker.mask_inner(
            mask=extended_mask_copy[:])
        count_array += mask & inner_array

    return count_array
