import qdarktheme
from vispy.app import Application

from snngine_v4.snngine_config import EngineConfig
from snngine_v4.config.app import EngineAppSettings
from snngine_v4.gui.windows.main_window import MainEngineWindow, WindowTypes
from snngine_v4.snngine import SNNgine


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

        self.window = MainEngineWindow(engine)
        self.engine.conf.export()

        self.main_network_scene = self.engine.scene_manager[
            self.engine.conf.scenes.main
        ]
        self.window.centralWidget().layout().addWidget(
            self.main_network_scene.native)

        self.window.show()
        self.window.windows[WindowTypes.SETTINGS].show()
        self.engine.conf.export()

    @property
    def conf(self) -> EngineAppSettings:
        return self.engine.conf.app
