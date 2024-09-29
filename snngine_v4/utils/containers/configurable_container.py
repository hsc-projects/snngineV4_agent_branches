from collections import UserDict, UserList
from types import NoneType
from typing import Annotated, Any, ClassVar, Type

from pydantic import BeforeValidator, field_validator
from pydantic.types import AnyType
from pydantic_core import PydanticUndefined, PydanticUndefinedType

from snngine_v4.utils.field_utils import (
    extract_type_from_type_annotation, b_field_has_default,
)
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


class ExtensionByDuplicateError(Exception):
    pass


type ValidKeyType = tuple[Type, ...] | Type
type ValidValueType = tuple[Type | Any, ...] | Type | Any


class ContainerConfig(XMLSettingsModel, frozen=True):
    allowed_types: ValidValueType = Any
    allowed_key_types: ValidKeyType = NoneType
    b_duplicates_allowed: bool = False
    b_duplicate_check_by_id: bool = False
    b_replace_allowed: bool = False
    b_pop_allowed: bool = True

    class Slots:
        ALLOWED_TYPES: ClassVar[str] = 'allowed_types'

    @classmethod
    def default_allowed_types(cls):
        return cls.model_fields[cls.Slots.ALLOWED_TYPES].default

    # noinspection PyNestedDecorators
    @field_validator('allowed_types',
                     'allowed_key_types', mode='after')
    @classmethod
    def type_validator(cls, v: ValidValueType | Type | Any) -> ValidValueType:
        if not isinstance(v, tuple):
            return v,
        return v

    @classmethod
    def _validate_model_before(cls, data: Any) -> Any:
        # if isinstance(data, dict):
        # for k, field_info in cls.model_fields.items():
        k = cls.Slots.ALLOWED_TYPES
        field = cls.model_fields[k]
        if (k not in data) and (not b_field_has_default(field)):
            v = extract_type_from_type_annotation(field.annotation)
            data[k] = v

        return super()._validate_model_before(data)


class ConfigurableContainerBase:

    ContainerConfigClass: ClassVar[Type[ContainerConfig]] = ContainerConfig

    data: list | dict | Any

    def __init__(self, container_conf: ContainerConfig = None):
        self._container_conf: ContainerConfig = self.cls_make_container_conf(
            container_conf=container_conf)

    def assert_emptiness(self):
        if not self.is_empty:
            raise AssertionError("not empty")

    def b_valid_item(self, item):
        b_valid_type = self.b_valid_item_type(item)
        b_duplicated = self.b_duplicated_item(item)
        return b_valid_type and (not b_duplicated)

    def b_duplicated_item(self, item):
        return False

    def b_valid_item_type(self, item):
        return self.cls_b_valid_object_type(
            item, self._container_conf.allowed_types)

    def check_key_type(self, key):
        return self.cls_b_valid_object_type(
            key, self._container_conf.allowed_key_types)

    @classmethod
    def cls_b_valid_object_type(cls, item, type_):
        if type_ in [(Any, ), (AnyType, )]:
            return True
        try:
            return isinstance(item, type_)
        except TypeError:
            return isinstance(item, type_)

    @staticmethod
    def cls_filter_dict(
            dict_: dict, type_, result_dict: UserDict | dict = None,
            b_pop: bool = True) -> dict:
        if result_dict is None:
            result_dict = {}

        valid_keys = []
        for k, v in dict_.items():
            if isinstance(v, type_):
                valid_keys.append(k)

        for k in valid_keys:
            if b_pop is True:
                result_dict[k] = dict_.pop(k)
            else:
                result_dict[k] = dict_[k]
        return result_dict

    @staticmethod
    def cls_filter_list(
            list_: list, type_,
            b_pop: bool = True,
            result_list: list | UserList | None = None):
        if result_list is None:
            result_list = []
        if b_pop is True:
            offset = 0
            for i in range(len(list_)):
                if isinstance(list_[i - offset], type_):
                    result_list.append(list_.pop(i - offset))
                    offset += 1
        else:
            for i in range(len(list_)):
                if isinstance(list_[i], type_):
                    result_list.append(list_[i])
        return result_list

    @classmethod
    def cls_make_container_conf(cls, container_conf=None):
        return container_conf or cls.ContainerConfigClass()

    @classmethod
    def cls_validate_value_type(cls, item, type_):
        b_allowed_type = cls.cls_b_valid_object_type(item, type_=type_)
        if b_allowed_type is False:
            raise TypeError(
                    f"Item must be of type {type_}."
                    f"Got {type(item).__name__} instead.")
        return item

    @classmethod
    def cls_validate_values(cls, items, type_, b_duplicate_check):
        if isinstance(items, dict):
            # keys = list(items.keys())
            items = list(items.values())
        if b_duplicate_check is True:
            try:
                item_set = list(set(items))
            except TypeError:
                item_set = list(set([id(item) for item in items]))
            if len(items) != len(item_set):
                raise ExtensionByDuplicateError("Items must be unique.")

        for item in items:
            cls.cls_validate_value_type(item, type_=type_)
        return items

    def __contains__(self, item):
        if ((not isinstance(item, int)) and
                self._container_conf.b_duplicate_check_by_id):
            return id(item) in self.data_ids
        return item in self.data

    @property
    def container_conf(self):
        return self._container_conf

    @property
    def data_ids(self):
        return [id(x) for x in self.data]

    def filter_dict(self, dict_: dict | UserDict, result_dict=None, b_pop=True):
        return self.cls_filter_dict(
            dict_, type_=self._container_conf.allowed_types,
            result_dict=result_dict, b_pop=b_pop)

    def filter_list(self, list_: list | UserList, result_list=None, b_pop=True):
        return self.cls_filter_list(
            list_, type_=self._container_conf.allowed_types,
            result_list=result_list, b_pop=b_pop)

    @classmethod
    def from_type(cls, type_: Type, **kwargs):
        return cls(
            container_conf=ContainerConfig(allowed_types=type_, **kwargs))

    def get_valid_item_type(self, item, default=PydanticUndefined,
                            types_=None):
        if types_ is None:
            types_ = self._container_conf.allowed_types
        if type(item) in types_:
            return type(item)
        else:
            for t in types_:
                if isinstance(item, t):
                    return t
        if self.b_valid_item_type(item):
            raise ValueError("Unknown but valid type")
        if default is not PydanticUndefined:
            return default
        raise TypeError(f"{item}")

    @property
    def is_empty(self):
        return len(self.data) == 0

    def validate_item(self, item):
        b_valid_item = self.b_valid_item(item)
        if b_valid_item is False:
            if self.b_valid_item_type(item) is False:
                raise TypeError(
                        f"Item must be of type"
                        f" {self._container_conf.allowed_types}."
                        f"Got {type(item).__name__} instead.")
            elif self.b_duplicated_item(item):
                raise ExtensionByDuplicateError(
                    f"Duplicated item: {item}")
            raise AttributeError("Item must be valid.")
        return item

    def validate_items(self, items):
        if isinstance(items, dict):
            keys = list(items.keys())
            self.validate_keys(keys)
        return self.cls_validate_values(
            items=items, type_=self._container_conf.allowed_types,
            b_duplicate_check=not self._container_conf.b_duplicates_allowed)

    def validate_keys(self, keys):
        keys = self.cls_validate_values(
            items=keys, type_=self._container_conf.allowed_key_types,
            b_duplicate_check=True)
        return keys
