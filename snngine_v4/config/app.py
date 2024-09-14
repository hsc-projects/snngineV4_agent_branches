from snngine_v4.gui.app_settings import AppSettings
from snngine_v4.utils.settings.settings_keywords import ParameterUIOpts


class EngineAppSettings(AppSettings):

    parameter_ui_opts: ParameterUIOpts = ParameterUIOpts(readonly=True)
