from __future__ import annotations

import pydoc
from types import NoneType
from typing import ClassVar, Type


from snngine_v4.utils.settings.xml_settings_base import (
    default_xml_model_config_dict,
    XMLSettingsConfigDict,
    XMLSettingsModelBase,
)


class XMLStringOptions(XMLSettingsModelBase):

    class Slots:
        B_PRETTY: ClassVar[str] = 'b_pretty'
        INDENT: ClassVar[str] = 'indent'
        NEWL: ClassVar[str] = 'newl'
        ENCODING: ClassVar[str] = 'encoding'

    b_pretty: bool = True
    encoding: str = 'utf8'
    method: str = 'xml'
    indent: str = "  "
    newl: str = "\n"


class XMLConverterOptions(XMLSettingsModelBase):

    model_config: ClassVar[XMLSettingsConfigDict] = (
        default_xml_model_config_dict(
            xml_file='./xml_converter_settings.xml'))

    base_types_str: str = "int,float,str,bool,NoneType"

    type_attribute: str = "type"
    enum_attribute: str = "Enum"
    dict_key_attribute: str = "key"

    sequence_element_tag_suffix: str = "Element"
    sequence_element_types_str: str = "list,tuple"
    dict_item_tag: str = "DictItem"

    dict_key_to_tag_attributes: dict[str, str] | None = None

    to_string_options: XMLStringOptions

    @property
    def base_types(self) -> tuple[Type, ...]:
        types = self.base_types_str.split(',')
        res = []
        for t in types:
            t_str = t.strip(' ')
            t_ = pydoc.locate(t_str)
            if t_ is None:
                t_ = NoneType
            res.append(t_)
        # noinspection PyTypeChecker
        return tuple(res)

    def make_seq_element_name(self, elm_type):
        return elm_type.__name__.capitalize() + self.sequence_element_tag_suffix

    @property
    def sequence_element_types(self) -> list[Type]:
        types = self.sequence_element_types_str.split(',')
        res = []
        for t in types:
            res.append(pydoc.locate(t.strip(' ')))
        # noinspection PyTypeChecker
        return res

    @property
    def sequence_element_types_naming(self):
        types = self.sequence_element_types
        res = []
        for t in types:
            res.append(self.make_seq_element_name(t))
        return res

    @classmethod
    def settings_customise_sources(
            cls, settings_cls: type[XMLSettingsModelBase],
            init_settings, env_settings,
            dotenv_settings, file_secret_settings):
        # noinspection PyTypeChecker
        return (
            init_settings,
            # XMLConfigSettingsSource(settings_cls),
        )


if __name__ == '__main__':
    opts_ = XMLConverterOptions()
    opts_.export()
