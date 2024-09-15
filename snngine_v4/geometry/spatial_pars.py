from pydantic import Field, NonNegativeInt, PositiveFloat

from snngine_v4.utils.settings.settings_keywords import ParamOpts
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


class XYZPars(XMLSettingsModel):

    parameter_ui_opts: ParamOpts = ParamOpts(
        renamable=False,
        expanded=True,
        c_numeric=True,
        prefix='X,Y,Z')

    X: float
    Y: float
    Z: float


class FloatShape3D(XYZPars):

    X: PositiveFloat = Field(default=1, gt=0)
    Y: PositiveFloat = Field(default=1, gt=0)
    Z: PositiveFloat = Field(default=1, gt=0)


class Segmentation3D(XYZPars):

    X: NonNegativeInt = 10
    Y: NonNegativeInt = 10
    Z: NonNegativeInt = 10


class EnginePos3D(XYZPars):

    X: float = Field(default=0., ge=-10, le=10)
    Y: float = Field(default=0., ge=-10, le=10)
    Z: float = Field(default=0., ge=-10, le=10)
