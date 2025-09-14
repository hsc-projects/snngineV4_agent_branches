from __future__ import annotations

from enum import IntEnum, unique
from typing import ClassVar

import numpy as np
from pydantic import Field, ValidationError

from snngine_v4.utils.data_utils.dataframe_config import (
    SeriesModel,
)
from snngine_v4.utils.data_utils.validation.array_annotation \
    import ArrayInterfaces
from snngine_v4.utils.core_utils import get_intenum_member
from snngine_v4.utils.settings.config_model import ConfigModel
from snngine_v4.utils.settings.ui_parameter_options import (
    FrozenParamOpts,
    GroupPrefixesType,
)


@unique
class Ax2D(IntEnum):
    X = 0
    Y = 1


@unique
class Ax3D(IntEnum):
    X = 0
    Y = 1
    Z = 2


@unique
class AxDir3D(IntEnum):
    XP = 0
    XM = 1
    YP = 2
    YM = 3
    ZP = 4
    ZM = 5

    @classmethod
    def vispy_name_alias(cls, member):
        member = get_intenum_member(member, cls)
        match member:
            case cls.XP:
                return '+x'
            case cls.XM:
                return '-x'
            case cls.YP:
                return '+y'
            case cls.YM:
                return '-y'
            case cls.ZP:
                return '+z'
            case cls.ZM:
                return '-z'


class SpatialParUIOpts(FrozenParamOpts):
    renamable: bool = False
    expanded: bool = True
    c_numeric_group: bool = True
    c_auto_expand: bool = True
    c_auto_collapse: bool = True
    c_group_prefixes: GroupPrefixesType = Ax3D


type ShapeI32 = ArrayInterfaces().make_type(3, dtype=np.int32)
type ShapeF32 = ArrayInterfaces().make_type(3, dtype=np.float32)
type PosF32 = ArrayInterfaces().make_type(3, dtype=np.float32)


class XYZPars(SeriesModel):

    # parameter_ui_opts: ClassVar[SpatialParUIOpts] = SpatialParUIOpts()

    index: list[str] = Field(default=['X', 'Y', 'Z'], repr=False, exclude=True)
    data: PosF32 = Field(
        default_factory=lambda: np.array([0, 0, 0], dtype=np.float32),
        repr=False)

    def __getitem__(self, item):
        if isinstance(item, str):
            item = Ax3D[item].value
        return self.data[item]

    def __setitem__(self, key, value):
        if isinstance(key, str):
            key = Ax3D[key].value
        self.data[key] = value

# class XYZPars(ConfigModel):
#
#     parameter_ui_opts: ClassVar[SpatialParUIOpts] = SpatialParUIOpts()
#
#     X: float
#     Y: float
#     Z: float
#
#     def as_tuple(self):
#         return self.X, self.Y, self.Z
#
#     def __len__(self):
#         return 3
#
#     def __getitem__(self, item):
#         if isinstance(item, int):
#             item = Ax3D(item).name
#         return getattr(self, item)
#
#     def __setitem__(self, key, value):
#         if isinstance(key, int):
#             key = Ax3D(key).name
#         setattr(self, key, value)
#
#     @classmethod
#     def from_tuple(cls, value):
#         if len(value) == 3:
#             return cls(X=value[0], Y=value[1], Z=value[2])
#         raise TypeError(f"{value} is not a tuple of length 3")
#
#     def prod(self):
#         return self.X * self.Y * self.Z


class Shape3Di32(XYZPars):
    data: ShapeI32 = Field(
        default_factory=lambda: np.array([1, 1, 1], dtype=np.int32),
        repr=False)

    def model_post_init(self, __context):
        if bool(np.any(self.data <= 0)):
            raise ValidationError(
                f"{self.__class__.__name__}.data values must be positive")


class Shape3Df32(Shape3Di32):
    data: ShapeF32 = Field(
        default_factory=lambda: np.array([1, 1, 1], dtype=np.float32),
        repr=False)

    # X: PositiveFloat = Field(default=1, gt=0)
    # Y: PositiveFloat = Field(default=1, gt=0)
    # Z: PositiveFloat = Field(default=1, gt=0)


class Segmentation3D(Shape3Di32):
    data: ShapeI32 = Field(
        default_factory=lambda: np.array([10, 10, 10], dtype=np.int32),
        repr=False)
    # X: NonNegativeInt = 10
    # Y: NonNegativeInt = 10
    # Z: NonNegativeInt = 10


class EnginePos3D(XYZPars):

    class Slots(XYZPars.Slots):
        POS_ORIGIN: ClassVar[str] = 'pos_origin'

    # X: Float32 = Field(default=0., ge=-10, le=10)
    # Y: float = Field(default=0., ge=-10, le=10)
    # Z: float = Field(default=0., ge=-10, le=10)


class Object3DConfig(ConfigModel):
    pos_origin: EnginePos3D


class Directions3DParUIOpts(SpatialParUIOpts):
    c_group_prefixes: GroupPrefixesType = AxDir3D


class Directions3DBoolPars(ConfigModel):

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        expanded=False,
        c_numeric_group=True,
    )

    XP: bool
    XM: bool
    YP: bool
    YM: bool
    ZP: bool
    ZM: bool


type Pos2DVBO = ArrayInterfaces().vbo_array_type(2)
type Pos3DVBO = ArrayInterfaces().vbo_array_type(3)


if __name__ == '__main__':
    from pprint import pprint
    pprint(Object3DConfig())
