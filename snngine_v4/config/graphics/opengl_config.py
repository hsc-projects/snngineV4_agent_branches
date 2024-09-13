from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.utils.settings.settings_keywords import ParameterUIOpts


class OpenGLConfig(XMLSettingsModel):

    ui_opts: ParameterUIOpts = ParameterUIOpts(
        readonly=True,
        movable=False)

    gloo_target: str = "gl+"
