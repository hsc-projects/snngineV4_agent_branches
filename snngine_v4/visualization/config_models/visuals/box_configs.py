from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.geometry.spatial_pars import Directions3DBoolPars
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.utils.settings.xml_settings_base import (
    default_xml_model_config_dict, XMLSettingsConfigDict,
)
from snngine_v4.visualization.config_models.visuals.mesh_visual_config import \
    MeshVisualConfig
from snngine_v4.visualization.config_models.visuals.visual_parameters import (
    RGBAColorType,
    OpenGLState,
    OpenGlStateType
)


class BoxVisualInitConfig(FiniteGridConfig):

    model_config: ClassVar[XMLSettingsConfigDict] = (
        default_xml_model_config_dict(extra='allow'))

    planes: Directions3DBoolPars = Directions3DBoolPars(
        XP=True, XM=True,
        YP=True, YM=True,
        ZP=True, ZM=True
    )

    vertex_colors: None = None
    face_colors: None = None
    color: RGBAColorType
    edge_color: RGBAColorType

    subvisuals: list[MeshVisualConfig] = Field(default_factory=list)

    # border: OpenGLState = Field(default_factory=lambda: OpenGLState(
    #     state_type=OpenGlStateType.UPDATE,
    #     line_width=6,
    #     attribute_key='_border',
    # ))


class OuterGridVisualInitConfig(BoxVisualInitConfig):

    color: RGBAColorType = None
    edge_color: RGBAColorType = 'white'

    mesh: OpenGLState = Field(default_factory=lambda: OpenGLState(
        state_type=OpenGlStateType.SET,
        polygon_offset_fill=True,
        polygon_offset=(1, 1),
        depth_test=False
    ))
