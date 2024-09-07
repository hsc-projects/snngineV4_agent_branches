from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class BaseSettingsModel(BaseSettings):

    model_config = ConfigDict(
        strict=True,
        validate_default=True,
        validate_assignment=True,
        extra='forbid',
        arbitrary_types_allowed=False)
