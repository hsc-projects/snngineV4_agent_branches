from enum import IntEnum

from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.utils.settings.settings_keywords import ParameterUIOpts


class EngineAppThemeType(IntEnum):
    dark = 0
    light = 1
    auto = 2


class EngineAppCornerShapeType(IntEnum):
    rounded = 0
    sharp = 1


class EngineAppConfig(XMLSettingsModel):

    ui_opts: ParameterUIOpts = ParameterUIOpts(readonly=True)

    backend_name: str = "pyside6"
    theme: EngineAppThemeType = EngineAppThemeType.dark
    corner_shape: EngineAppCornerShapeType = EngineAppCornerShapeType.sharp
