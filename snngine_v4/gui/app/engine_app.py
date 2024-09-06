from vispy.app import Application

from snngine_v4.config.engine_config_model import EngineAppConfig, EngineConfig
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

    @property
    def conf(self) -> EngineAppConfig:
        return self.engine.conf.app_config
