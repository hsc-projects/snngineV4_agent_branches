from __future__ import annotations

import numpy as np

from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.geometry.spatial_pars import (
    Directions3DBoolPars,
)
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.visualization.config_models.vispy_visual_parameters import (
    OpenGLState, OpenGlStateType,
    RGBAColor,
)


ColorType = RGBAColor | str


class LineVisualConfig(XMLSettingsModel):
    pos: None = None
    color: ColorType | None
    width: int = 1
    connect: str | None = 'strip'
    method: str = 'gl'
    antialias: bool = False


class XYZAxisVisualConfig(LineVisualConfig):
    connect: str | None = 'segments'
    color: None = None


class BoxVisualConfig(FiniteGridConfig):

    planes: Directions3DBoolPars = Directions3DBoolPars(
        XP=True, XM=True,
        YP=True, YM=True,
        ZP=True, ZM=True
    )

    vertex_colors: None = None
    face_colors: None = None
    color: ColorType | None
    edge_color: ColorType

    border: OpenGLState = OpenGLState(
        state_type=OpenGlStateType.UPDATE,
        line_width=6,
        attribute_key='_border',
    )


class OuterGridVisualConfig(BoxVisualConfig):

    color: ColorType | None = None
    edge_color: ColorType | None = 'white'

    mesh: OpenGLState = OpenGLState(
        state_type=OpenGlStateType.SET,
        polygon_offset_fill=True,
        polygon_offset=(1, 1),
        depth_test=False
    )
