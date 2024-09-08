from snngine_v4.config.graphics.app_config_model import EngineAppConfig
from snngine_v4.config.base.base_settings_model import BaseSettingsModel
from snngine_v4.config.construction import NetworkConstructionSettings
from snngine_v4.config.graphics.opengl_config import OpenGLConfig
from snngine_v4.config.graphics.scene_config import SceneConfig


class EngineConfig(BaseSettingsModel):

    app_config: EngineAppConfig = EngineAppConfig()

    open_gl_config: OpenGLConfig = OpenGLConfig()

    scene_config: SceneConfig = SceneConfig()

    construction: NetworkConstructionSettings = NetworkConstructionSettings()
