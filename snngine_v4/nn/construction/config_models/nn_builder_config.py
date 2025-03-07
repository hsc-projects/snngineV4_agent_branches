from __future__ import annotations

from typing import ClassVar


from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.nn.construction.config_models.engine_element_config import (
    EngineElementConfig,
)
from snngine_v4.nn.construction.config_models.reservoir.nn_reservoir_config \
    import NetworkReservoirConfig


class NetworkConstructionConfig(EngineElementConfig):

    class Slots:
        GRID: ClassVar[str] = "grid"
        ELEMENTS: ClassVar[str] = "elements"

    device: int = 0

    grid: FiniteGridConfig

    elements: list[NetworkReservoirConfig | EngineElementConfig] | None = None
    bools: list[None | bool] | None = [None, True, False, True]


if __name__ == '__main__':
    from pprint import pprint
    pprint(NetworkConstructionConfig().model_dump())
