from snngine_v4.config.app_config_model import EngineAppConfig
from snngine_v4.config.base.base_settings_model import BaseSettingsModel


class OpenGLConfig(BaseSettingsModel):
    gloo_target: str = "gl+"


class EngineConfig(BaseSettingsModel):

    app_config: EngineAppConfig = EngineAppConfig()
    open_gl_config: OpenGLConfig = OpenGLConfig()
