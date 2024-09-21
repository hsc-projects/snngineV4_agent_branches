from typing import ClassVar

from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


class OpenGLSettings(XMLSettingsModel):

    parameter_ui_opts: ClassVar[ParamOpts] = ParamOpts(
        readonly=True,
        movable=False)

    gloo_target: str = "gl+"
