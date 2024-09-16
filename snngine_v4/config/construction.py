from snngine_v4.nn.config_models.nn_builder_config import \
    NetworkConstructionConfig
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


class EngineConstructionConfig(XMLSettingsModel):

    network: NetworkConstructionConfig

    # visuals: Visuals
