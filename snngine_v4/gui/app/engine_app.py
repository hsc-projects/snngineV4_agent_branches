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

        self.engine = SNNgine(settings=settings,)

        qdarktheme.setup_theme(
            theme=self.conf.theme.name,
            corner_shape=self.conf.corner_shape.name,
        )

        self.window = MainEngineWindow(self.engine)
        self.engine.conf.export()

        # self.engine.conf.template.network.grid.shape.__setattr__(
        #     self.engine.conf.template.network.grid.shape,
        #     'X', 10)

        self.window.construct_network()

    @property
    def conf(self) -> EngineAppSettings:
        return self.engine.conf.app
