from pydantic import Field

from snngine_v4.config.base.base_settings_model import BaseSettingsModel


class NetworkConstructionSettings(BaseSettingsModel):
    N: int = Field(default=100, gt=0)
