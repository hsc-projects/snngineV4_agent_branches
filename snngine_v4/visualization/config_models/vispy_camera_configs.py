from snngine_v4.utils.settings.settings_keywords import ParamOpts
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


class TurnTableCameraParameters(XMLSettingsModel):

    parameter_ui_opts: ParamOpts = ParamOpts(
        renamable=False,
        expanded=True,
        # c_numeric=True,
        # prefix='X,Y,Z'
    )

    fov: float = 45.0
    elevation: float = 30.0
    azimuth: float = 30.0
    roll: float = 0.0
    distance: float | None = None
    translate_speed: float = 1.0
