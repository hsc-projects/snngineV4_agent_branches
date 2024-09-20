from typing import ClassVar

from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.utils.settings.settings_keywords import ParamOpts


class OpenGLSettings(XMLSettingsModel):

    parameter_ui_opts: ClassVar[ParamOpts] = ParamOpts(
        readonly=True,
        movable=False)

    gloo_target: str = "gl+"
