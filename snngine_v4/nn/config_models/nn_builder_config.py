from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.nn.config_models.nn_element_config import EngineElementConfig
from snngine_v4.nn.config_models.nn_reservoir_config import NetworkReservoir
from snngine_v4.utils.settings.settings_keywords import ParamOpts
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


class NetworkConstructionConfig(XMLSettingsModel):

    parameter_ui_opts: ParamOpts = ParamOpts(readonly=False)

    grid: FiniteGridConfig

    elements: list[NetworkReservoir | EngineElementConfig] | None = [
        EngineElementConfig(),
        NetworkReservoir(),
        EngineElementConfig(),
    ]
    bools: list[None | bool] | None = [None, True, False, True]
