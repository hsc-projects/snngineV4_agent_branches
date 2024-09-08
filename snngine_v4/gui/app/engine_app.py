import qdarktheme
from vispy.app import Application

from snngine_v4.config.engine_config_model import EngineConfig
from snngine_v4.config.graphics.app_config_model import EngineAppConfig
from snngine_v4.gui.windows.main_window import MainEngineWindow
from snngine_v4.snngine import SNNgine
from snngine_v4.visualization.scenes.main_network_scene import \
    MainNetworkSceneCanvas


class EngineApp(Application):

    def __init__(
            self, engine_or_settings: SNNgine | EngineConfig | str = None):

        if not isinstance(engine_or_settings, SNNgine):
            engine = SNNgine(settings=engine_or_settings)
        else:
            engine = engine_or_settings

        self.engine = engine

        super().__init__(backend_name=self.conf.backend_name)
        # noinspection PyProtectedMember
        self._backend._vispy_get_native_app()

        qdarktheme.setup_theme(
            theme=self.conf.theme.name,
            corner_shape=self.conf.corner_shape.name,
        )

        self.window = MainEngineWindow(engine.conf)
        self.window.show()

        self.main_network_scene = MainNetworkSceneCanvas(
            conf=self.engine.conf.scene_config.main, app=self)

        self.window.main.layout().addWidget(self.main_network_scene.native)


    @property
    def conf(self) -> EngineAppConfig:
        return self.engine.conf.app_config
