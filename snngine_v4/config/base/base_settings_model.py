from typing import ClassVar

from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings


class BaseSettingsConfigKW:

    FROZEN: ClassVar[str] = 'frozen'

    @classmethod
    def b_is_frozen(cls, model: BaseModel) -> bool:
        # noinspection PyTypedDict
        return model.model_config.get(
            BaseSettingsConfigKW.FROZEN, False)


class BaseSettingsModel(BaseSettings):

    model_config = ConfigDict(
        strict=True,
        validate_default=True,
        validate_assignment=True,
        extra='forbid',
        arbitrary_types_allowed=False)
