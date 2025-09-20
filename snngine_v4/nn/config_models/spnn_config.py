from __future__ import annotations

from typing import ClassVar

from pydantic import Field, NonNegativeInt

from snngine_v4.geometry.grid.finite_grid_config import FiniteGridConfig
from snngine_v4.construction.engine_element_config import (
    EngineElementConfig,
)
from snngine_v4.nn.config_models.reservoir.nn_reservoir_config \
    import NetworkReservoirConfig
from snngine_v4.nn.sim.sim_parameters import SimulatorOptions


class SpatialNetworkConfig(EngineElementConfig):

    class Slots:
        GRID: ClassVar[str] = "grid"
        ELEMENTS: ClassVar[str] = "elements"

    device: NonNegativeInt | str = Field(default=0)

    grid: FiniteGridConfig

    simulator: SimulatorOptions

    elements: list[NetworkReservoirConfig | EngineElementConfig] | None = None
    bools: list[None | bool] | None = [None, True, False, True]


# if __name__ == '__main__':
#     from pprint import pprint
#     pprint(SpatialNetworkConfig().model_dump())
