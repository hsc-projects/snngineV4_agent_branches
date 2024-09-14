from snngine_v4.nn.construction.nn_element_config import NetworkElementConfig
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.utils.settings.settings_keywords import ParameterUIOpts


class NetworkConstructionConfig(XMLSettingsModel):

    parameter_ui_opts: ParameterUIOpts = ParameterUIOpts(readonly=False)

    elements: list[NetworkElementConfig] | None = None
