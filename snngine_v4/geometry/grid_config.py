from snngine_v4.geometry.spatial_pars import FloatShape3D, Segmentation3D
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


class FiniteGridConfig(XMLSettingsModel):

    shape: FloatShape3D
    segmentation: Segmentation3D
    tech_max_z: int = 100
