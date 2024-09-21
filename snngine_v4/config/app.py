from typing import ClassVar

from snngine_v4.gui.app_settings import AppSettings
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


class EngineAppSettings(AppSettings):

    parameter_ui_opts: ClassVar[ParamOpts] = ParamOpts(readonly=True)
