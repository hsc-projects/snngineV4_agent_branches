from enum import IntEnum

import numpy as np
from pydantic import Field, NonNegativeInt, PositiveInt

from snngine_v4.nn.config_models.nn_element_config import EngineElementConfig
from snngine_v4.geometry.spatial_pars import PositionVBO


class ArraySourceType(IntEnum):
    FILE = 0
    GENERATOR = 1


class NetworkReservoir(EngineElementConfig):
    N: NonNegativeInt = 200
    S: NonNegativeInt = 1
    D: int = Field(default=0, ge=0, le=20)

    # pos_file: PositionVBO = ['./data.h5']
    pos: PositionVBO = Field(
        default_factory=lambda: np.array([
            [1.5, 1.5, 1.5],
            [1.5, 1.5, 0],
            [0, 1.5, 1.5],
            [1.5, 0, 1.5],
            [-1.5, 1.5, 1.5],
            [-1.5, 1.5, 0]],
            dtype=np.float32))
