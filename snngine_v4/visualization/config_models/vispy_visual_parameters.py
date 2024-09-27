from __future__ import annotations

from enum import IntEnum
from typing import ClassVar

from pydantic import Field

from snngine_v4.geometry.spatial_pars import Ax3D
from snngine_v4.utils.core_utils import ConvertingEnum
from snngine_v4.utils.settings.ui_parameter_options import FrozenParamOpts
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.utils.settings.xml_settings_base import (
    default_xml_model_config_dict, XMLSettingsConfigDict,
)


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
        c_group_prefixes='R,G,B,A')

    R: float = Field(default=.5, ge=0., le=1.)
    G: float = Field(default=.5, ge=0., le=1.)
    B: float = Field(default=1., ge=0., le=1.)
    A: float = Field(default=1., ge=0., le=1.)


class BoxPlaneTypes(XMLSettingsModel):

    R: bool = Field(default=.5, ge=0., le=1.)
    G: float = Field(default=.5, ge=0., le=1.)
    B: float = Field(default=1., ge=0., le=1.)
    A: float = Field(default=1., ge=0., le=1.)


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
