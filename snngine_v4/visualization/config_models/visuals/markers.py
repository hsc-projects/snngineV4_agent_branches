from typing import ClassVar

import numpy as np
from pydantic import Field, NonNegativeFloat

from snngine_v4.utils.settings.ui_parameter_options import FrozenParamOpts


from snngine_v4.geometry.spatial_pars import Pos3DVBO
from snngine_v4.visualization.config_models.visuals.parameters import \
    ColorType, RGBAColorType
from snngine_v4.visualization.config_models.visuals.visual_config import \
    VisualConfig


class MarkersVisualConfig(VisualConfig):

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        expanded=False,
        c_auto_collapse=True,
        c_collapsed_children=True,
    )

    pos: Pos3DVBO = Field(
        default_factory=lambda: np.array([
            [1.5, 1.5, 1.5],
            [1.5, 1.5, 0],
            [0, 1.5, 1.5],
            [1.5, 0, 1.5],
            [-1.5, 1.5, 1.5],
            [-1.5, 1.5, 0]],
            dtype=np.float32),
        repr=False)
    size: NonNegativeFloat | None = Field(default=7, le=50)
    edge_width: float | None = Field(default=1, ge=0, le=20)
    # edge_width_rel: NonNegativeFloat | None = Field(default=None, le=15)
    edge_color: RGBAColorType = 'green'
    face_color: ColorType = 'white'


