import qdarktheme
from vispy.app import Application

from snngine_v4.snngine_config import EngineConfig
from snngine_v4.config.app import EngineAppSettings
from snngine_v4.gui.windows.main_window import MainEngineWindow
from snngine_v4.snngine import SNNgine


class EngineApp(Application):

    def __init__(self, settings: EngineConfig = None):

        if settings is None:
            # noinspection PyArgumentList
            settings = EngineConfig()

        super().__init__(backend_name=settings.app.backend_name)

        # noinspection PyProtectedMember
        native_app = self._backend._vispy_get_native_app()
        # if not isinstance(settings, SNNgine):
        #     engine = SNNgine(settings=settings, app=self)
        # else:
        #     engine = settings
        engine = SNNgine(settings=settings,
                         # app=self
                         )

        self.engine = engine

        qdarktheme.setup_theme(
            theme=self.conf.theme.name,
            corner_shape=self.conf.corner_shape.name,
        )

        self.window = MainEngineWindow(engine)
        # self.engine.conf.export()

        self.window.show()
        # self.window.windows[WindowTypes.SETTINGS].show()
        # self.window.extraParametersWindow.show()
        self.engine.conf.export()

        # self.engine.conf.construction.network.grid.shape.__setattr__(
        #     self.engine.conf.construction.network.grid.shape,
        #     'X', 10)

        self.window.build()
        # self.window.show()

    @property
    def conf(self) -> EngineAppSettings:
        return self.engine.conf.app
