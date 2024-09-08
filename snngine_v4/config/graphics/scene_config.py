from snngine_v4.config.base.base_settings_model import BaseSettingsModel


class VispyOpenGLConfig(BaseSettingsModel):
    data_path: str
    default_backend: str
    gl_backend: str
    gl_debug: bool
    # glir_file: str
    include_path: list
    logging_level: str
    # qt_lib: str = 'p'
    dpi: int | None = None
    profile: str | None = None
    audit_tests: bool = False
    test_data_path: str | None = None


class VispyCanvasConfig(BaseSettingsModel):

    title: str = 'VisPy canvas'
    size: tuple[int, int] = (1600, 1200)
    position: tuple | None = None
    show: bool = False
    autoswap: bool = True

    create_native: bool = True
    vsync: bool = False
    resizable: bool = True
    decorate: bool = True
    fullscreen: bool = False
    config: VispyOpenGLConfig | dict | None = None
    keys: str | dict = 'interactive'
    dpi: float | None = None
    always_on_top: bool = False
    px_scale: int = 1
    bgcolor: str = 'black'


class MainNetworkSceneConfig(VispyCanvasConfig):
    title: str = 'NetworkView'


class SceneConfig(BaseSettingsModel):
    main: MainNetworkSceneConfig = MainNetworkSceneConfig()
