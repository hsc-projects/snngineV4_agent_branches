from typing import ClassVar

from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.utils.settings.ui_parameter_options import FrozenParamOpts


class OpenGLSettings(XMLSettingsModel):

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        readonly=True,
        movable=False)

    gloo_target: str = "gl+"
