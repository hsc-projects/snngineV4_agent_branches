from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel
from pydantic_settings import BaseSettings


class InternalOpts(BaseSettings, frozen=True):
    class Slots:
        TECHNICAL: ClassVar[str] = 'technical'


class BaseSettingsSlots:

    FROZEN: ClassVar[str] = 'frozen'

    XML_FILE: ClassVar[str] = 'xml_file'

    SUB_SETTINGS_FILE_NAME_PATTERN: ClassVar[str] = '{sub_settings}'

    @classmethod
    def b_is_frozen(cls, model: BaseModel) -> bool:
        # noinspection PyTypedDict
        return model.model_config.get(
            cls.FROZEN, False)
