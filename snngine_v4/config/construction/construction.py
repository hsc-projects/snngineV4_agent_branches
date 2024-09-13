from pydantic import Field

from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.utils.settings.settings_keywords import ParameterUIOpts


class NetworkConstructionSettings(XMLSettingsModel):

    ui_opts: ParameterUIOpts = ParameterUIOpts(readonly=False)

    N: int = Field(default=100, gt=0)
