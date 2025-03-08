from __future__ import annotations

import pydoc
from functools import cached_property
from types import NoneType
from typing import ClassVar, Type

from pydantic import BaseModel, Field

from snngine_v4.utils.core_utils import Singleton


class XMLStringOptions(BaseModel):

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


class BaseTypeCache(metaclass=Singleton):

    def __init__(self):
        self.data = {
            'int': int,
            'float': float,
            'str': str,
            'bool': bool,
            'NoneType': NoneType,
        }

    def __getitem__(self, key):
        try:
            return self.data[key]
        except KeyError:
            t_ = pydoc.locate(key)
            if t_ is None:
                t_ = NoneType
            self.data[key] = t_
            return self.data[key]


class XMLConverterOptions(BaseModel):

    base_types_str: ClassVar[str] = "int,float,str,bool,NoneType"

    type_attribute: str = "type"
    enum_attribute: str = "Enum"
    dict_key_attribute: str = "key"

    sequence_element_tag_suffix: str = "Element"
    sequence_element_types_str: str = "list,tuple"
    dict_item_tag: str = "DictItem"

    dict_key_to_tag_attributes: dict[str, str] | None = None

    to_string_options: XMLStringOptions = Field(
        default=XMLStringOptions())

    @cached_property
    def base_types(self) -> tuple[Type, ...]:

        base_types = BaseTypeCache()
        types = self.base_types_str.split(',')
        res = []
        for t in types:
            t_ = base_types[t.strip(' ')]
            res.append(t_)
        return tuple(res)

    def make_seq_element_name(self, elm_type):
        return elm_type.__name__.capitalize() + self.sequence_element_tag_suffix

    @property
    def sequence_element_types(self) -> list[Type]:
        types = self.sequence_element_types_str.split(',')
        res = []
        for t in types:
            res.append(pydoc.locate(t.strip(' ')))
        # noinspection PyTypeChecker,PydanticTypeChecker
        return res

    @property
    def sequence_element_types_naming(self):
        types = self.sequence_element_types
        res = []
        for t in types:
            res.append(self.make_seq_element_name(t))
        return res
