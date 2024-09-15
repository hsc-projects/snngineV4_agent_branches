from enum import IntEnum

from pydantic import Field, NonNegativeInt, PositiveInt

from snngine_v4.nn.config_models.nn_element_config import EngineElementConfig


class ArraySourceType(IntEnum):
    FILE = 0
    GENERATOR = 1


class NetworkReservoir(EngineElementConfig):
    N: NonNegativeInt = 200
    S: NonNegativeInt = 1
    D: int = Field(default=0, ge=0, le=20)
