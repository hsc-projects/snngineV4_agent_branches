from typing import ClassVar

from pydantic import Field

from snngine_v4.utils.settings.settings_keywords import ParamOpts
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


class TurnTableCameraParameters(XMLSettingsModel):

    parameter_ui_opts: ClassVar[ParamOpts] = ParamOpts(
        renamable=False,
        expanded=False,
    )

    name: str | None = None
    fov: float = Field(default=45, ge=0, le=180)
    elevation: float = Field(default=30, ge=-90, le=90)
    azimuth: float = Field(default=30, ge=-180, le=180)
    roll: float = Field(default=0, ge=-180, le=180)
    distance: float | None = None
    translate_speed: float = Field(default=1, ge=0, le=10)
