from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.nn.construction.nn_element_config import EngineElementConfig
from snngine_v4.nn.construction.nn_reservoir import NetworkReservoir
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.utils.settings.settings_keywords import ParameterUIOpts


class NetworkConstructionConfig(XMLSettingsModel):

    parameter_ui_opts: ParameterUIOpts = ParameterUIOpts(readonly=False)

    grid: FiniteGridConfig

    elements: list[NetworkReservoir | EngineElementConfig] | None = [
        EngineElementConfig(),
        NetworkReservoir(),
        EngineElementConfig(),
    ]
    bools: list[None | bool] | None = [None, True, False, True]
