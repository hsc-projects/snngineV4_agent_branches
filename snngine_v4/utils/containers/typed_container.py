from collections import UserDict
from typing import ClassVar, Type

from snngine_v4.utils.parameter_model.settings_model import BaseSettingsModel


class ExtensionByDuplicateError(Exception):
    pass


class ContainerConfig(BaseSettingsModel, frozen=True):
    allowed_types: tuple[Type] | Type = None
    allowed_key_types: tuple[Type] | Type = None
    b_duplicates_allowed: bool = False
    b_replace_allowed: bool = False


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

    @classmethod
    def cls_filter_dict(
            cls,
            dict_: dict, type_,
            result_dict: UserDict | dict = None,
            b_pop: bool = True) -> dict:
        if result_dict is None:
            result_dict = {}

        pop_keys = []
        for k, v in dict_.items():
            if isinstance(v, type_):
                pop_keys.append(k)

        for k in pop_keys:
            if b_pop is True:
                result_dict[k] = dict_.pop(k)
            else:
                result_dict[k] = dict_[k]
        return result_dict

    def filter_dict(self, dict_: dict | UserDict, result_dict=None):
        self.cls_filter_dict(
            dict_, self._container_conf.allowed_types,
            result_dict=self)

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
    def cls_validate_type(cls, item, type_):
        b_allowed_type = cls.cls_check_type(item, type_=type_)
        if b_allowed_type is False:
            raise TypeError(
                    f"Item must be of type {type_}."
                    f"Got {type(item).__name__} instead.")
        return item

    def validate_items(self, items):
        return self.cls_validate_items(
            items=items,
            type_=self._container_conf.allowed_types,
            duplicate_check=not self._container_conf.b_duplicates_allowed)

    @classmethod
    def cls_validate_items(cls, items, type_, duplicate_check):
        if isinstance(items, dict):
            items = list(items.values())
        if duplicate_check is True:
            try:
                item_set = list(set(items))
            except TypeError:
                item_set = [id(item) for item in items]
            if len(items) != len(item_set):
                raise ValueError("Items must be unique.")

        errors = []
        for item in items:
            try:
                cls.cls_validate_type(item, type_=type_)
            except ExtensionByDuplicateError:
                errors.append(item)
        if len(errors) > 0:
            error_list_msg = "\n".join(
                    [f"{i + 1}. {e}" for i, e in enumerate(errors)])
            raise ExtensionByDuplicateError(
                    f"Duplicate items found ({len(errors)}/{len(items)}):\n"
                    f"{error_list_msg}")
        return items
