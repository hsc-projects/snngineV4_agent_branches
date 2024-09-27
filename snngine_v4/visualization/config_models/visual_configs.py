from __future__ import annotations

from typing import Literal

import numpy as np
from pydantic import Field

from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.geometry.spatial_pars import (
    Directions3DBoolPars,
)
from snngine_v4.utils.settings.ui_parameter_options import p_field
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.visualization.config_models.vispy_visual_parameters import (
    OpenGLState, OpenGlStateType,
    RGBAColor,
)
from snngine_v4.utils.array_utils import ArrayL3F32


type ColorType = RGBAColor | str
type ColorType2 = str | RGBAColor | ArrayL3F32 | None
type LineConnectType = Literal['strip', 'segments'] | None


class LineVisualConfig(XMLSettingsModel):

    pos: None = None
    color: ColorType | None
    width: int = p_field(default=1,  readonly=True)
    connect: LineConnectType = p_field(default='strip',  readonly=True)
    method: Literal['gl', 'agg'] = p_field(default='gl',  readonly=True)
    antialias: bool = False


class XYZAxisVisualConfig(LineVisualConfig):
    connect: LineConnectType = p_field(
        default='segments',  readonly=False)
    color: ColorType2 = Field(
        default_factory=lambda: np.array([.5, .5, .5], dtype=np.float32))

    def __setattr__(self, key, value):
        pass
        super().__setattr__(key, value)


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
