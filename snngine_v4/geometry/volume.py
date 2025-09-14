from __future__ import annotations


from enum import IntEnum, auto
from functools import cached_property

import numpy as np
from pydantic import Field

from snngine_v4.geometry.grid.finite_grid_config import (FiniteGridConfig,
                                                         LinkedFiniteGridConfig)
from snngine_v4.geometry.spatial_pars import (Object3DConfig, Shape3Di32,
                                              ShapeI32)


class IndicesHDW(IntEnum):
    HEIGHT = 0
    DEPTH = auto()
    WIDTH = auto()


class VolumeShapeHDW(Shape3Di32):

    data: ShapeI32 = Field(
        default_factory=lambda: np.array([100, 100, 100], dtype=np.int32),
        repr=False)

    @property
    def height(self):
        return self.data[IndicesHDW.HEIGHT]

    @property
    def depth(self):
        return self.data[IndicesHDW.DEPTH]

    @property
    def width(self):
        return self.data[IndicesHDW.WIDTH]

    @property
    def shape_wdh(self):
        return self.width, self.depth, self.height

    def size(self):
        return self.height * self.depth * self.width

    @classmethod
    def hdw_to_wdh(cls, hdw_shape):
        return (hdw_shape[IndicesHDW.WIDTH],
                hdw_shape[IndicesHDW.DEPTH],
                hdw_shape[IndicesHDW.HEIGHT])


class LinkedVolumeGridConfig(LinkedFiniteGridConfig):
    parent_config: VolumeConfig = Field(exclude=True)

    @property
    def shape(self):
        return Shape3Di32(data=self.parent_config.shape.shape_wdh)

    @property
    def seg(self):
        return self.shape


class VolumeConfig(Object3DConfig):
    shape: VolumeShapeHDW

    @cached_property
    def linked_grid_config(self):
        return LinkedVolumeGridConfig(parent_config=self)

    @classmethod
    def keep_object_init_kwargs(cls, kwargs):
        kwargs_ = {
        }
        return kwargs_
