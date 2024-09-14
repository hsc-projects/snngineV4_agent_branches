from enum import IntEnum

from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


class AppThemeType(IntEnum):
    dark = 0
    light = 1
    auto = 2


class AppCornerShapeType(IntEnum):
    rounded = 0
    sharp = 1


class WindowSettings(XMLSettingsModel):
    screen: int = 0
    size: tuple[int, int] = (1600, 1000)


class Windows(XMLSettingsModel):
    main: WindowSettings


class AppSettings(XMLSettingsModel):

    backend_name: str = "pyside6"
    theme: AppThemeType = AppThemeType.dark
    corner_shape: AppCornerShapeType = AppCornerShapeType.sharp

    windows: Windows
