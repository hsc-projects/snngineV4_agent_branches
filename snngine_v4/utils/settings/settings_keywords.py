from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel
from pydantic_settings import BaseSettings


class InternalOpts(BaseSettings, frozen=True):
    class Slots:
        TECHNICAL: ClassVar[str] = 'technical'


class BaseModelSlots:
    CLASS__NAME: ClassVar[str] = 'class__name'
    EXTRA_CLASSES: ClassVar[str] = 'EXTRA_CLASSES'

    @classmethod
    def pop_class__name_kw(
            cls, dct: dict, b_recursive: bool = True):
        key_list = list(dct.keys())
        for k in key_list:
            if k == BaseModelSlots.CLASS__NAME:
                dct.pop(BaseModelSlots.CLASS__NAME)
            elif b_recursive and isinstance(dct[k], dict):
                dct[k] = cls.pop_class__name_kw(
                    dct[k], b_recursive=True)
        return dct


class BaseSettingsSlots:

    FROZEN: ClassVar[str] = 'frozen'

    XML_FILE: ClassVar[str] = 'xml_file'
    XML_FILE_ENDING: ClassVar[str] = '.xml'
    H5_FILE_ENDING: ClassVar[str] = '.h5'

    CLASS_NAME_XML_TAG: ClassVar[str] = 'class'

    SUB_SETTINGS_FILE_NAME_PATTERN: ClassVar[str] = '{sub_settings}'

    @classmethod
    def b_is_frozen(cls, model: BaseModel) -> bool:
        # noinspection PyTypedDict
        return model.model_config.get(
            cls.FROZEN, False)
