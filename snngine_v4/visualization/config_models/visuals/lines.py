from __future__ import annotations

from typing import Literal

import numpy as np
from pydantic import Field, NonNegativeInt

from snngine_v4.utils.data_utils.validation.array_annotation import (
    ArrayInterfaces,
)
from snngine_v4.geometry.spatial_pars import (
    Pos3DVBO,
)

from snngine_v4.visualization.config_models.visuals.parameters import \
    BufferColorType
from snngine_v4.visualization.config_models.visuals.visual_config import \
    VisualConfig

type LineConnectType = Literal['strip', 'segments'] | None


class LineVisualConfig(VisualConfig):

    pos: Pos3DVBO = Field(default=None, repr=False)
    color: BufferColorType = Field(repr=False)
    width: NonNegativeInt = Field(default=1, le=15)
    connect: LineConnectType = Field(default='strip', frozen=True,
                                     repr=False)
    method: Literal['gl', 'agg'] = Field(default='gl', frozen=True)
    antialias: bool = False


class XYZAxisVisualConfig(LineVisualConfig):
    pos: Pos3DVBO = Field(
        default_factory=lambda: np.array([
            [0, 0, 0],
            [1, 0, 0],
            [0, 0, 0],
            [0, 1, 0],
            [0, 0, 0],
            [0, 0, 1]],
            dtype=np.float32),
        repr=False,
    )
    connect: LineConnectType = Field(
        default='segments',
        # readonly=False,
        repr=False,)
    color: BufferColorType = Field(
        default_factory=lambda: np.array([
            [1, 0, 0, 1],
            [1, 0, 0, 1],
            [0, 1, 0, 1],
            [0, 1, 0, 1],
            [0, 0, 1, 1],
            [0, 0, 1, 1]],
            dtype=np.float32),
        repr=False,)


class MultiBoxLinesVisualConfig(LineVisualConfig):
    connect: ArrayInterfaces().make_type(
        '* x', 2, dtype=np.uint32) = Field(repr=False)
    subvisuals: None = None
