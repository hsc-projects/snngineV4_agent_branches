from __future__ import annotations

from typing import Iterable, Sized

import numpy as np
import pandas as pd
# import torch

from snngine_v4.geometry.grid.finite_grid_elements import GridStep
from snngine_v4.geometry.grid.grid_mask_maker import (
    mask_value_interval,
    MaskMaker, n_neighbours,
)
from snngine_v4.geometry.grid_config import TechnicalValues


class FiniteGrid:

    def __init__(self,
                 shape: Iterable | Sized | dict,
                 seg: Iterable | Sized | dict,
                 technical: TechnicalValues):

        if isinstance(shape, dict):
            shape = list(shape.values())
        if isinstance(seg, dict):
            seg = list(seg.values())
        if isinstance(technical, dict):
            technical = TechnicalValues(**technical)

        if len(shape) != 3:
            raise ValueError('shape must be a 3-element iterable.')
        if len(seg) != 3:
            raise ValueError('segmentations must be a 3-element iterable.')

        # The shape of the grid
        if not hasattr(self, 'shape'):
            self.shape = np.array(shape)
        # The segmentation of the grid
        if not hasattr(self, 'segmentation'):
            self.segmentation = np.array(seg)

        # A technical maximum z value, used for grid visuals
        self._technical_max_z_value = technical.max_z

        # The lattice of the grid
        self._lattice = (float(self.shape[0] / self.segmentation[0]),
                         float(self.shape[1] / self.segmentation[1]),
                         float(self.shape[2] / self.segmentation[2]))

        # Precompute possible steps with respect to the lattice
        self.steps = GridStep(self._lattice)

        # The position of the grid segments
        self._pos = self._make_pos()
        # The position of the grid segments plus the lattice vectors
        self._pos_end = self._pos.copy()
        self._pos_end[:, 0] = self._pos_end[:, 0] + self._lattice[0]
        self._pos_end[:, 1] = self._pos_end[:, 1] + self._lattice[1]
        self._pos_end[:, 2] = self._pos_end[:, 2] + self._lattice[2]

        # The grid coordinates of the grid segments
        self.grid_coord = self.grid_coordinates(self._pos)

        # The index of the grid segments, reshaped to the shape of the grid
        self.shaped_index = (np.arange(self.n_segments)
                             .reshape(tuple(reversed(self.segmentation))).T)

        # The optional mask-maker of the grid
        self._mask_maker: MaskMaker | None = None

    @staticmethod
    def cls_grid_coordinates(pos, outer_shape, grid_segmentation,
                             as_struct=False):
        arr = (np.floor(
            (pos
             / np.array(outer_shape, dtype=np.float32))
            * np.array(grid_segmentation, dtype=np.float32)).astype(int))
        if as_struct is True:

            struct = np.zeros(len(arr), [('x', np.int32), ('y', np.int32),
                                         ('z', np.int32)])
            struct['x'] = arr[:, 0]
            struct['y'] = arr[:, 1]
            struct['z'] = arr[:, 2]
            return struct
        return arr

    @staticmethod
    def get_hull_mask(value_range: pd.Interval,
                      tensor):
                      # : torch.Tensor

            # -> torch.Tensor\

        mask = mask_value_interval(ref_array=tensor, value_range=value_range)

        n_neighbours_ = n_neighbours(
            mask, count_array=torch.zeros_like(tensor, dtype=torch.int8))

        hull_mask = mask & (n_neighbours_ < 6)

        return hull_mask

    def get_idx_from_grid_pos(self, pos: tuple | list | np.ndarray):
        if len(pos) != 3:
            raise ValueError('pos must be a 3-element iterable.')
        return np.ravel_multi_index(pos, self.segmentation, order='F')

    def grid_coordinates(self, pos, as_struct: bool = False):
        """Get the grid coordinates of given positions."""
        return self.cls_grid_coordinates(
            pos, outer_shape=self.shape, grid_segmentation=self.segmentation,
            as_struct=as_struct)

    @staticmethod
    def is_cube(shape):
        """Check if the grid is a cube."""
        return (shape[0] == shape[1]) and (shape[0] == shape[2])

    @property
    def lattice(self):
        """The lattice vectors of the grid."""
        return self._lattice

    def _make_pos(self):
        """Make the positions of the grid segments."""
        n_segments = self.n_segments

        groups = np.arange(n_segments)
        z = np.floor(groups / (self.segmentation[0] * self.segmentation[1]))
        r = groups - z * (self.segmentation[0] * self.segmentation[1])
        y = np.floor(r / self.segmentation[0])
        x = r - y * self.segmentation[0]
        g_pos = np.zeros((n_segments + 1, 3), dtype=np.float32)

        # The last entry will be ignored by the geometry shader
        # (i.e. invisible).
        # We could also use a primitive restart index instead.
        # The current solution is simpler w.r.t. vispy.
        g_pos[:, 2] = self._technical_max_z_value + 1

        g_pos[:n_segments, 0] = x * self.lattice[0]
        g_pos[:n_segments, 1] = y * self.lattice[1]
        g_pos[:n_segments, 2] = z * self.lattice[2]

        assert np.max(g_pos[:n_segments, 2]) < self._technical_max_z_value
        self.validate_pos(g_pos[:n_segments, :], self.segmentation,
                          n_pos=n_segments)
        # noinspection PyAttributeOutsideInit
        return g_pos

    @property
    def mask_maker(self):
        """The mask-maker of the grid."""
        if self._mask_maker is None:
            self._mask_maker = MaskMaker(ref_array=self.shaped_index)
        return self._mask_maker

    @property
    def n_segments(self):
        """The number of grid segments."""
        return int(np.cumprod(self.segmentation)[-1])

    @property
    def n_technical_segments(self):
        """The number of grid segments, including the technical one."""
        return self.n_segments + 1

    @property
    def pos(self):
        """The positions of the grid segments,
        excluding the last (technical) one."""
        return self._pos[:-1]

    @property
    def pos_end(self):
        """The positions + lattice vectors of the grid segments,
        excluding the last (technical) one."""
        return self._pos_end[:-1]

    @property
    def technical_max_z_value(self):
        return self._technical_max_z_value

    @staticmethod
    def validate_pos(
            pos: np.ndarray, volume_shape, n_pos: int | None = None):
        if (n_pos is not None) and (pos.shape[0] != n_pos):
            raise ValueError
        for i in range(3):
            assert np.min(pos[:, i]) >= 0
            assert np.max(pos[:, i]) <= volume_shape[i]
