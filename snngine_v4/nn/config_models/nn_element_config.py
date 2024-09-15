from snngine_v4.geometry.spatial_pars import EnginePos3D
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


class EngineElementConfig(XMLSettingsModel):
    pos: EnginePos3D
