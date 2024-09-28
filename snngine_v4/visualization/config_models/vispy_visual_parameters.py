from __future__ import annotations

from enum import auto, IntEnum
from typing import Annotated, ClassVar

import numpy as np
from pydantic import BeforeValidator, Field
from pydantic_extra_types.color import Color

from snngine_v4.geometry.spatial_pars import Ax3D

from snngine_v4.utils.core_utils import ConvertingEnum
from snngine_v4.utils.array_utils import (
    ArrayInterfaces, Float32, UInt8,
)
from snngine_v4.utils.settings.ui_parameter_options import FrozenParamOpts
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.utils.settings.xml_settings_base import (
    default_xml_model_config_dict, XMLSettingsConfigDict,
)


type ColorTypeUnion = (
        str | RGBAColor
        | ArrayInterfaces().rgb_a_f32.type
        | ArrayInterfaces().rgb_u8.type
        | Color | None)


def validate_color(v):
    if isinstance(v, (np.ndarray, tuple)):
        v = RGBAColor.from_iterable(v)
    return v


ColorTypeType = Annotated[ColorTypeUnion, BeforeValidator(validate_color)]


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

    def as_tuple(self):
        return self.R, self.G, self.B, self.A

    @classmethod
    def from_iterable(cls, value):
        if isinstance(value, np.ndarray):
            if ArrayInterfaces().rgb_a_f32.check_array(value):
                value = [np.round(c * 255) for c in value]
            elif ArrayInterfaces().rgb_u8.check_array(value):
                pass
        value3 = 1 if len(value) == 3 else value[3]
        return cls(R=value[0], G=value[1], B=value[2], A=value3)

    @classmethod
    def to_vispy(cls, value):
        if isinstance(value, dict):
            value = (
                value[RGBAEnum.R.name],
                value[RGBAEnum.G.name],
                value[RGBAEnum.B.name],
                value[RGBAEnum.A.name],
            )
        if np.issubdtype(type(value[0]), np.integer):
            value = np.array(value, dtype=np.float32)
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
