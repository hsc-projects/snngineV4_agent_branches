from typing import ClassVar

from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.utils.settings.settings_keywords import ParameterUIOpts


class VispyOpenGLConfig(XMLSettingsModel):

    ui_opts: ParameterUIOpts = ParameterUIOpts(readonly=True)

    red_size: int = 8
    green_size: int = 8
    blue_size: int = 8
    alpha_size: int = 8
    depth_size: int = 24
    stencil_size: int = 0
    double_buffer: bool = True
    stereo: bool = False
    samples: int = 0


class VispyWidgetOptions(XMLSettingsModel):

    ui_opts: ParameterUIOpts = ParameterUIOpts(readonly=True)

    pos: tuple[int, int] = (0, 0)
    size: tuple[int, int] = (10, 10)
    border_color: str | None = 'darkslategrey'
    border_width: int = 2
    bgcolor: tuple[float, float, float, float] = (0, 0, 0, 0)
    padding: int = 2
    margin: int = 0


class VispyCanvasOptions(XMLSettingsModel):

    ui_opts: ParameterUIOpts = ParameterUIOpts(readonly=True)

    class Slots:
        CENTRAL_WIDGET_OPTIONS: ClassVar[str] = 'central_widget_options'

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

    central_widget_options: VispyWidgetOptions | None


class MainNetworkSceneOptions(VispyCanvasOptions):
    title: str = 'NetworkView'


class SceneConfig(XMLSettingsModel):
    main: MainNetworkSceneOptions = MainNetworkSceneOptions()
