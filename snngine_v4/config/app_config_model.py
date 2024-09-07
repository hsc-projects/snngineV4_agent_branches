from enum import IntEnum

from snngine_v4.config.base.base_settings_model import BaseSettingsModel
from snngine_v4.config.base.ui_options import ParameterUIOpts


class EngineAppThemeType(IntEnum):
    dark = 0
    light = 1
    auto = 2


class EngineAppCornerShapeType(IntEnum):
    rounded = 0
    sharp = 1


class EngineAppConfig(BaseSettingsModel):

    ui_opts: ParameterUIOpts = ParameterUIOpts()

    backend_name: str = "pyside6"
    theme: EngineAppThemeType = EngineAppThemeType.dark
    corner_shape: EngineAppCornerShapeType = EngineAppCornerShapeType.sharp
