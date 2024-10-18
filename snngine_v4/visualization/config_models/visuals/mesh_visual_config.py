from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.visualization.config_models.visuals.visual_parameters import \
    RGBAColorType


class MeshVisualConfig(XMLSettingsModel):
    color: RGBAColorType
