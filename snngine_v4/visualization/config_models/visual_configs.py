from pydantic import Field, NonNegativeInt

from snngine_v4.geometry.spatial_pars import FloatShape3D, Segmentation3D
from snngine_v4.utils.settings.settings_keywords import ParamOpts
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


class ColorType(XMLSettingsModel):

    parameter_ui_opts: ParamOpts = ParamOpts(
        renamable=False,
        expanded=False,
        c_numeric=True,
        prefix='R,G,B,A')

    R: float = Field(default=.5, ge=0., le=1.)
    G: float = Field(default=.5, ge=0., le=1.)
    B: float = Field(default=1., ge=0., le=1.)
    A: float = Field(default=1., ge=0., le=1.)


class BoxVisualConfig(XMLSettingsModel):
    shape: FloatShape3D
    segment: Segmentation3D
    planes: str
    vertex_colors: None
    face_colors: None
    color: ColorType
    edge_color: ColorType
