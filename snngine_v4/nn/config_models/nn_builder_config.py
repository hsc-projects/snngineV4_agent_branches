from __future__ import annotations

from typing import ClassVar

from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.nn.config_models.nn_element_config import EngineElementConfig
from snngine_v4.nn.config_models.reservoir.nn_reservoir_config \
    import NetworkReservoirConfig
from snngine_v4.utils.settings.xml_settings import (
    XMLSettingsContainerModel,
)


class NetworkConstructionConfig(XMLSettingsContainerModel):

    class Slots:
        GRID: ClassVar[str] = "grid"
        ELEMENTS: ClassVar[str] = "elements"

    device: int = 0

    grid: FiniteGridConfig

    elements: list[NetworkReservoirConfig | EngineElementConfig] | None = None
    bools: list[None | bool] | None = [None, True, False, True]

    # @classmethod
    # def _validate_model_after(cls, data: NetworkConstructionConfig):
    #     super()._validate_model_after(data=data)

