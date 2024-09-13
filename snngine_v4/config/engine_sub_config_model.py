from typing_extensions import ClassVar

from snngine_v4.utils.settings.settings_keywords import BaseSettingsSlots
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.utils.settings.xml_settings_base import (
    default_xml_model_config_dict, XMLSettingsConfigDict,
)


class EngineSubConfig(XMLSettingsModel):

    model_config: ClassVar[XMLSettingsConfigDict] = (
        default_xml_model_config_dict('.snngine/{settings}.xml'))

    def export(self, fn=None, mode='xml'):
        if (fn is None) or isinstance(fn, bool):
            # noinspection PyTypedDict
            fn = self.model_config[BaseSettingsSlots.XML_FILE]

        for k in self.model_fields:
            getattr(self, k).export(fn.replace('{settings}', k))