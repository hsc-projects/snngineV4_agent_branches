from enum import IntEnum, unique

from snngine_v4.utils.settings.config_model import ConfigModel


@unique
class AppThemeType(IntEnum):
    dark = 0
    light = 1
    auto = 2


@unique
class AppCornerShapeType(IntEnum):
    rounded = 0
    sharp = 1


class WindowSettings(ConfigModel):
    screen: int = 0
    size: tuple[int, int] = (1600, 1000)


class Windows(ConfigModel):
    main: WindowSettings


class AppSettings(ConfigModel):

    backend_name: str = "pyside6"
    theme: AppThemeType = AppThemeType.dark
    corner_shape: AppCornerShapeType = AppCornerShapeType.sharp

    windows: Windows
