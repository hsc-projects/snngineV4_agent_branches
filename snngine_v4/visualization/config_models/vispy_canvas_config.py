from typing import ClassVar, Type

from snngine_v4.utils.settings.settings_keywords import ParamOpts
from snngine_v4.utils.settings.xml_settings import (
    XMLSettingsContainerModel,
    XMLSettingsModel,
)
from snngine_v4.visualization.config_models.vispy_camera_configs import \
    TurnTableCameraParameters
from snngine_v4.visualization.config_models.visual_configs import \
    XYZAxisVisualConfig


class VispyOpenGLConfig(XMLSettingsModel, frozen=True):

    red_size: int = 8
    green_size: int = 8
    blue_size: int = 8
    alpha_size: int = 8
    depth_size: int = 24
    stencil_size: int = 0
    double_buffer: bool = True
    stereo: bool = False
    samples: int = 0


class VispyWidgetConfig(XMLSettingsModel, frozen=True):

    pos: tuple[int, int] = (0, 0)
    size: tuple[int, int] = (10, 10)
    border_color: str | None = 'darkslategrey'
    border_width: int = 2
    bgcolor: tuple[float, float, float, float] = (0, 0, 0, 0)
    padding: int = 2
    margin: int = 0


class VispyViewBoxConfig(VispyWidgetConfig):

    parameter_ui_opts: ClassVar[ParamOpts] = ParamOpts(
        renamable=False,
        expanded=False,
    )

    border_width: int = 0
    padding: int = 0
    border_color: str | None = 'black'
    camera: TurnTableCameraParameters


class SceneViews(XMLSettingsContainerModel):
    EXTRA_CLASSES: ClassVar[Type[XMLSettingsModel]] = [VispyViewBoxConfig]


class SceneVisuals(XMLSettingsContainerModel):
    EXTRA_CLASSES: ClassVar[Type[XMLSettingsModel]] = [
        XYZAxisVisualConfig,
    ]


class SceneCameras(XMLSettingsContainerModel):
    EXTRA_CLASSES: ClassVar[Type[XMLSettingsModel]] = [
        TurnTableCameraParameters]


class VispyCanvasConfigOptions(XMLSettingsModel, frozen=True):

    parameter_ui_opts: ClassVar[ParamOpts] = ParamOpts(
        renamable=False,
        expanded=False,
    )

    title: str
    size: tuple[int, int] = (1600, 1200)
    position: tuple[int, int] | None = None
    show: bool = False
    autoswap: bool = True

    create_native: bool = True
    vsync: bool = False
    resizable: bool = True
    decorate: bool = True
    fullscreen: bool = False
    config: VispyOpenGLConfig | None
    keys: str | dict = 'interactive'
    dpi: float | None = None
    always_on_top: bool = False
    px_scale: int = 1
    bgcolor: str = 'black'

    central_widget_options: VispyWidgetConfig | None


class VispyCanvasConfig(XMLSettingsModel):

    class Slots:
        OPTIONS: ClassVar[str] = 'Options'
        CENTRAL_WIDGET_OPTIONS: ClassVar[str] = 'central_widget_options'
        VISUALS: ClassVar[str] = 'Visuals'
        VIEWS: ClassVar[str] = 'Views'
        CAMERAS: ClassVar[str] = 'Cameras'

    Options: VispyCanvasConfigOptions
    Views: SceneViews | None = None
    Visuals: SceneVisuals
    Cameras: SceneCameras
