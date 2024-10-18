from __future__ import annotations

from enum import auto, IntEnum
from types import NoneType
from typing import Annotated, ClassVar

import numpy as np
from pydantic import BeforeValidator, Field
from pydantic_extra_types.color import Color

from snngine_v4.geometry.spatial_pars import Ax3D

from snngine_v4.utils.core_utils import ConvertingEnum
from snngine_v4.data.validation.dtype_annotation import (
    Float32, UInt8,
)
from snngine_v4.data.validation.array_annotation import ArrayInterfaces
from snngine_v4.utils.settings.ui_parameter_options import FrozenParamOpts
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.utils.settings.xml_settings_base import (
    default_xml_model_config_dict, XMLSettingsConfigDict,
)


type ColorVBO = ArrayInterfaces().vbo4.array_type


type ColorTypeUnion = (
        str | RGBAColor
        | ColorVBO
        | Color | None)

type RGBAColorTypeUnion = (
        str | RGBAColor
        | Color | None)


def validate_color(v):
    if isinstance(v, tuple) or (isinstance(v, np.ndarray) and v.ndim == 1):
        v = RGBAColor.from_iterable(v)
    return v


ColorType = Annotated[ColorTypeUnion, BeforeValidator(validate_color)]
RGBAColorType = Annotated[RGBAColorTypeUnion, BeforeValidator(validate_color)]

type VispyColorType = tuple


class RGBAEnum(IntEnum):
    R = 0
    G = auto()
    B = auto()
    A = auto()


class WDHKw(ConvertingEnum):
    width = 0
    depth = 1
    height = 2

    @classmethod
    def mapping(cls):
        return {WDHKw.width.name: Ax3D.X.name,
                WDHKw.depth.name: Ax3D.Y.name,
                WDHKw.height.name: Ax3D.Z.name}


class WDHSegKw(ConvertingEnum):
    width_segments = 0
    depth_segments = 1
    height_segments = 2

    @classmethod
    def mapping(cls):
        return {WDHSegKw.width_segments.name: Ax3D.X.name,
                WDHSegKw.depth_segments.name: Ax3D.Y.name,
                WDHSegKw.height_segments.name: Ax3D.Z.name}


class RGBAColor(XMLSettingsModel):

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        renamable=False,
        expanded=False,
        c_numeric_group=True,
        c_group_prefixes=RGBAEnum)

    R: UInt8 = Field(default=127)
    G: UInt8 = Field(default=127)
    B: UInt8 = Field(default=255)
    A: Float32 = Field(default=np.float32(1), ge=0., le=1.)

    def as_type(self, type_):
        if type_ == self.__class__:
            return self
        elif type_ == ArrayInterfaces().rgb_u8.array_type:
            return ArrayInterfaces().rgb_u8.array(self.as_type(tuple)[:3])
        elif type_ in [VispyColorType,
                       ArrayInterfaces().rgb_a_f32.array_type,
                       ArrayInterfaces().vbo4.array_type]:
            return self.to_vispy(self)
        elif type_ == tuple:
            return self.R, self.G, self.B, self.A
        elif type_ == Color:
            return Color(self.as_type(tuple))
        elif type_ == str:
            return self.as_type(Color).as_hex()
        elif type_ == NoneType:
            return None
        else:
            raise NotImplementedError(type_)

    @classmethod
    def from_iterable(cls, value):
        if isinstance(value, np.ndarray):
            if ArrayInterfaces().rgb_a_f32.b_is_valid(value):
                value = [np.uint8(np.round(c * 255)) for c in value[:3]]
            elif ArrayInterfaces().rgb_u8.b_is_valid(value):
                pass
        try:
            value3 = 1 if (len(value) == 3) else value[3]
        except IndexError:
            raise
        return cls(R=value[0], G=value[1], B=value[2], A=value3)

    @classmethod
    def to_vispy(cls, value) -> np.ndarray:
        if isinstance(value, cls):
            value = value.model_dump()
        if isinstance(value, dict):
            value = (
                value[RGBAEnum.R.name],
                value[RGBAEnum.G.name],
                value[RGBAEnum.B.name],
                value[RGBAEnum.A.name],
            )
        if np.issubdtype(type(value[0]), np.integer):
            value = ArrayInterfaces().rgb_a_f32.array(value)
            value[:3] = value[:3] / 255
        return value


class OpenGlStateType(IntEnum):

    SET = 0
    UPDATE = 1


class OpenGLState(XMLSettingsModel):

    class Slots:
        ATTRIBUTE_KEY: ClassVar[str] = 'attribute_key'
        STATE_TYPE: ClassVar[str] = 'state_type'

    model_config: ClassVar[XMLSettingsConfigDict] = (
        default_xml_model_config_dict(
            extra='allow'))

    attribute_key: str | None = None
    state_type: OpenGlStateType


if __name__ == '__main__':
    from snngine_v4.gui.app.debug_app import make_app
    make_app(RGBAColor)
