from collections import UserDict, UserList
from typing import ClassVar, Type

from snngine_v4.config.base.base_settings_model import BaseSettingsModel


class ExtensionByDuplicateError(Exception):
    pass


class ContainerConfig(BaseSettingsModel, frozen=True):
    allowed_types: tuple[Type] | Type | None = None
    allowed_key_types: tuple[Type] | Type | None = None
    b_duplicates_allowed: bool = False
    b_replace_allowed: bool = False
    b_pop_allowed: bool = True


class ConfigurableContainerBase:

    CONFIG_CLASS: ClassVar[Type[ContainerConfig]] = ContainerConfig

    def __init__(self, container_conf: ContainerConfig = None):
        self._container_conf: ContainerConfig = (
                container_conf or self.CONFIG_CLASS())

    @classmethod
    def cls_check_type(cls, item, type_):
        if type_ is None:
            return True
        return isinstance(item, type_)

    def check_type(self, item):
        return self.cls_check_type(item, self._container_conf.allowed_types)

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

    def validate_item(self, item):
        b_allowed_type = self.check_type(item)
        if b_allowed_type is False:
            raise TypeError(
                    f"Item must be of type"
                    f" {self._container_conf.allowed_types}."
                    f"Got {type(item).__name__} instead.")
        return item

    @classmethod
    def cls_validate_value_type(cls, item, type_):
        b_allowed_type = cls.cls_check_type(item, type_=type_)
        if b_allowed_type is False:
            raise TypeError(
                    f"Item must be of type {type_}."
                    f"Got {type(item).__name__} instead.")
        return item

    def validate_keys(self, keys):
        if self._container_conf.allowed_key_types is not None:
            self.cls_validate_values(
                items=keys, type_=self._container_conf.allowed_key_types,
                b_duplicate_check=True)

    def validate_items(self, items):
        if isinstance(items, dict):
            keys = list(items.keys())
            self.validate_keys(keys)
        return self.cls_validate_values(
            items=items, type_=self._container_conf.allowed_types,
            b_duplicate_check=not self._container_conf.b_duplicates_allowed)

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
