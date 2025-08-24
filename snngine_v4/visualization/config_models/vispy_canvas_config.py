from typing import ClassVar, Type

from pydantic import Field

from snngine_v4.utils.settings.config_model import (
    ConfigContainerModel,
    ConfigModel,
)
from snngine_v4.utils.settings.ui_parameter_options import FrozenParamOpts
from snngine_v4.visualization.config_models.vispy_camera_configs import \
    (
    PanZoomCameraParameters, TurnTableCameraParameters,
)
from snngine_v4.visualization.config_models.visuals.lines import \
    XYZAxisVisualConfig


class VispyOpenGLConfig(ConfigModel, frozen=True):

    red_size: int = 8
    green_size: int = 8
    blue_size: int = 8
    alpha_size: int = 8
    depth_size: int = 24
    stencil_size: int = 0
    double_buffer: bool = True
    stereo: bool = False
    samples: int = 0


class VispyWidgetConfig(ConfigModel, frozen=True):

    pos: tuple[int, int] = (0, 0)
    size: tuple[int, int] = (10, 10)
    border_color: str | None = 'darkslategrey'
    border_width: int = 2
    bgcolor: tuple[float, float, float, float] = (0, 0, 0, 0)
    padding: int = 2
    margin: int = 0


class VispyViewBoxConfig(VispyWidgetConfig):

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        renamable=False,
        c_auto_collapse=True,
        expanded=False,
    )

    border_width: int = 0
    padding: int = 0
    border_color: str | None = 'black'
    camera: TurnTableCameraParameters | PanZoomCameraParameters = Field(
        default_factory=TurnTableCameraParameters)


class SceneViews(ConfigContainerModel):
    EXTRA_CLASSES: ClassVar[Type[ConfigModel]] = [VispyViewBoxConfig]


class SceneVisuals(ConfigContainerModel):
    EXTRA_CLASSES: ClassVar[Type[ConfigModel]] = [
        XYZAxisVisualConfig,
    ]


class SceneCameras(ConfigContainerModel):
    EXTRA_CLASSES: ClassVar[Type[ConfigModel]] = [
        TurnTableCameraParameters]

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        c_b_collect_extra_classes=True,
        expanded=True,
        c_auto_collapse=True,
        c_collapsed_children=True,
    )


class VispyCanvasConfigOptions(ConfigModel, frozen=True):

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        renamable=False,
        c_auto_collapse=True,
        expanded=False,
    )

    title: str
    size: tuple[int, int] = (1600, 1200)
    position: tuple[int, int] | None
    show: bool = False
    autoswap: bool = True

    create_native: bool = True
    vsync: bool = False
    resizable: bool = True
    decorate: bool = True
    fullscreen: bool = False
    config: VispyOpenGLConfig
    keys: str = 'interactive'
    dpi: float | None
    always_on_top: bool = False
    px_scale: int = 1
    bgcolor: str = 'black'

    central_widget_options: VispyWidgetConfig


class VispyCanvasConfig(ConfigModel):

    class Slots:
        OPTIONS: ClassVar[str] = 'Options'
        CENTRAL_WIDGET_OPTIONS: ClassVar[str] = 'central_widget_options'
        VISUALS: ClassVar[str] = 'Visuals'
        VIEWS: ClassVar[str] = 'Views'
        CAMERAS: ClassVar[str] = 'Cameras'

    Options: VispyCanvasConfigOptions
    Views: SceneViews
    Visuals: SceneVisuals
    Cameras: SceneCameras
