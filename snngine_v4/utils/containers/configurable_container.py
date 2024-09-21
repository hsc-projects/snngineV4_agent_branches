from collections import UserDict, UserList
from types import NoneType
from typing import Any, ClassVar, Type

from snngine_v4.utils.field_utils import (
    extract_type_from_type_annotation, b_field_has_default,
)
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


class ExtensionByDuplicateError(Exception):
    pass


class ContainerConfig(XMLSettingsModel, frozen=True):
    allowed_types: tuple[Type, ...] | Type | None = None
    allowed_key_types: tuple[Type] | Type = NoneType
    b_duplicates_allowed: bool = False
    b_duplicate_check_by_id: bool = False
    b_replace_allowed: bool = False
    b_pop_allowed: bool = True

    class Slots:
        ALLOWED_TYPES: ClassVar[str] = 'allowed_types'

    @classmethod
    def default_allowed_types(cls):
        return cls.model_fields[cls.Slots.ALLOWED_TYPES].default

    @classmethod
    def _validate_model_before(cls, data: Any) -> Any:
        # if isinstance(data, dict):
        for k, field_info in cls.model_fields.items():
            if (k not in data) and (not b_field_has_default(field_info)):
                if k == cls.Slots.ALLOWED_TYPES:
                    v = extract_type_from_type_annotation(
                        field_info.annotation)
                    data[k] = v

        return super()._validate_model_before(data)


class ConfigurableContainerBase:

    ContainerConfigClass: ClassVar[Type[ContainerConfig]] = ContainerConfig

    def __init__(self, container_conf: ContainerConfig = None):
        self._container_conf: ContainerConfig = self.cls_make_container_conf(
            container_conf=container_conf)

    def assert_emptiness(self):
        if not self.is_empty:
            raise AssertionError("not empty")

    def check_item_type(self, item):
        return self.cls_check_type(item, self._container_conf.allowed_types)

    def check_key_type(self, key):
        return self.cls_check_type(
            key, self._container_conf.allowed_key_types)

    @classmethod
    def cls_check_type(cls, item, type_):
        if type_ is None:
            return True
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
        b_allowed_type = cls.cls_check_type(item, type_=type_)
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

    @property
    def is_empty(self):
        return len(self.data) == 0

    def validate_item(self, item):
        b_allowed_type = self.check_item_type(item)
        if b_allowed_type is False:
            raise TypeError(
                    f"Item must be of type"
                    f" {self._container_conf.allowed_types}."
                    f"Got {type(item).__name__} instead.")
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
