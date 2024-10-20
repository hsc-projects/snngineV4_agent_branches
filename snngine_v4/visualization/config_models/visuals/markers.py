import numpy as np
from pydantic import Field, NonNegativeFloat

from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


from snngine_v4.geometry.spatial_pars import PositionVBO
from snngine_v4.visualization.config_models.visuals.parameters import \
    ColorType, RGBAColorType


class MarkersVisualConfig(XMLSettingsModel):

    pos: PositionVBO = Field(
        default_factory=lambda: np.array([
            [1.5, 1.5, 1.5],
            [1.5, 1.5, 0],
            [0, 1.5, 1.5],
            [1.5, 0, 1.5],
            [-1.5, 1.5, 1.5],
            [-1.5, 1.5, 0]],
            dtype=np.float32))
    size: NonNegativeFloat | None = Field(default=7, le=50)
    edge_width: float | None = Field(default=1, gt=0, le=20)
    # edge_width_rel: NonNegativeFloat | None = Field(default=None, le=15)
    edge_color: RGBAColorType = 'green'
    face_color: ColorType = 'white'
