from snngine_v4.config.base.base_settings_model import BaseSettingsModel
from snngine_v4.config.base.ui_options import ParameterUIOpts


class OpenGLConfig(BaseSettingsModel, frozen=True):

    ui_opts: ParameterUIOpts = ParameterUIOpts(movable=False)

    gloo_target: str = "gl+"
