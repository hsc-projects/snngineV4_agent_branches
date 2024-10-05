from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.nn.config_models.nn_element_config import EngineElementConfig
from snngine_v4.nn.config_models.nn_reservoir_config import NetworkReservoir
from snngine_v4.utils.settings.xml_settings import (
    XMLSettingsContainerModel,
)


class NetworkConstructionConfig(XMLSettingsContainerModel):

    grid: FiniteGridConfig

    elements: list[NetworkReservoir | EngineElementConfig] | None = None
    bools: list[None | bool] | None = [None, True, False, True]
