from snngine_v4.utils.parameter_model.settings_model import BaseSettingsModel


class EngineAppConfig(BaseSettingsModel):

    backend_name: str = "pyside6"


class OpenGLConfig(BaseSettingsModel):

    gloo_target: str = "gl+"


class EngineConfig(BaseSettingsModel):

    app_config: EngineAppConfig = EngineAppConfig()
    open_gl_config: OpenGLConfig = OpenGLConfig()
