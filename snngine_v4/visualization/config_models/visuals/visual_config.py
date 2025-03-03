from pydantic import Field

from snngine_v4.geometry.spatial_pars import EnginePos3D
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


class VisualConfig(XMLSettingsModel):
    visible: bool = True
    pos_origin: EnginePos3D = Field(
        default_factory=lambda: EnginePos3D.from_tuple((0, 0, 0)))
