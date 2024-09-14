from pydantic import Field, NonNegativeInt, PositiveFloat

from snngine_v4.utils.settings.settings_keywords import ParameterUIOpts
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


class FloatShape3D(XMLSettingsModel):

    parameter_ui_opts: ParameterUIOpts = ParameterUIOpts(expanded=False)

    X: PositiveFloat = Field(default=1, gt=0)
    Y: PositiveFloat = Field(default=1, gt=0)
    Z: PositiveFloat = Field(default=1, gt=0)


class Segmentation3D(XMLSettingsModel):

    parameter_ui_opts: ParameterUIOpts = ParameterUIOpts(expanded=False)

    X: NonNegativeInt = 10
    Y: NonNegativeInt = 10
    Z: NonNegativeInt = 10


class EnginePos3D(XMLSettingsModel):

    parameter_ui_opts: ParameterUIOpts = ParameterUIOpts(expanded=False)

    X: float = Field(default=0., ge=-10, le=10)
    Y: float = Field(default=0., ge=-10, le=10)
    Z: float = Field(default=0., ge=-10, le=10)
