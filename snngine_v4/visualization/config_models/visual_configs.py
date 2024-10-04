from __future__ import annotations

from typing import Literal

import numpy as np
from pydantic import Field, NonNegativeInt

from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.geometry.spatial_pars import (
    Directions3DBoolPars, PositionVBO,
)
from snngine_v4.utils.settings.ui_parameter_options import p_field, ParamOpts
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.visualization.config_models.vispy_visual_parameters import (
    OpenGLState, OpenGlStateType,
)
from snngine_v4.visualization.config_models.vispy_visual_parameters import \
    ColorType


type LineConnectType = Literal['strip', 'segments'] | None


class LineVisualConfig(XMLSettingsModel):

    pos: None = None
    color: ColorType
    width: NonNegativeInt = p_field(default=1,  readonly=False, le=15)
    connect: LineConnectType = p_field(default='strip',  readonly=True)
    method: Literal['gl', 'agg'] = p_field(default='gl',  readonly=True)
    antialias: bool = False


class XYZAxisVisualConfig(LineVisualConfig):
    pos: PositionVBO = Field(
        default_factory=lambda: np.array([
            [0, 0, 0],
            [1, 0, 0],
            [0, 0, 0],
            [0, 1, 0],
            [0, 0, 0],
            [0, 0, 1]],
            dtype=np.float32),
        # json_schema_extra={
        #     ParamOpts.KW.C_COLUMN_NAME_S: ,
        # },
    )
    connect: LineConnectType = p_field(
        default='segments',  readonly=False)
    color: ColorType = Field(
        default_factory=lambda: np.array([
            [1, 0, 0, 1],
            [1, 0, 0, 1],
            [0, 1, 0, 1],
            [0, 1, 0, 1],
            [0, 0, 1, 1],
            [0, 0, 1, 1]],
            dtype=np.float32))


class BoxVisualConfig(FiniteGridConfig):

    planes: Directions3DBoolPars = Directions3DBoolPars(
        XP=True, XM=True,
        YP=True, YM=True,
        ZP=True, ZM=True
    )

    vertex_colors: None = None
    face_colors: None = None
    color: ColorType
    edge_color: ColorType

    border: OpenGLState = OpenGLState(
        state_type=OpenGlStateType.UPDATE,
        line_width=6,
        attribute_key='_border',
    )


class OuterGridVisualConfig(BoxVisualConfig):

    color: ColorType = None
    edge_color: ColorType = 'white'

    mesh: OpenGLState = OpenGLState(
        state_type=OpenGlStateType.SET,
        polygon_offset_fill=True,
        polygon_offset=(1, 1),
        depth_test=False
    )
