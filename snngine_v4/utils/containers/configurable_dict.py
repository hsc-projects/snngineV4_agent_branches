from __future__ import annotations

from collections import UserDict
from enum import Enum

from typing import ClassVar, Type, Union

from snngine_v4.utils.containers.configurable_container import (
    ConfigurableContainerBase, ContainerConfig, ExtensionByDuplicateError,
)


class DefaultDictContainerConfig(ContainerConfig, frozen=True):
    allowed_types: tuple[Type, ...] | Type | None = None
    allowed_key_types: tuple[Type] | Type = str
    b_duplicates_allowed: bool = False  # Keep False
    b_replace_allowed: bool = False  # Keep False
    b_pop_allowed: bool = True  # Keep True
    b_enum_to_str_key: bool = True  # Keep True


class ConfigurableDict(ConfigurableContainerBase, UserDict):

    DICT_CONFIG_CLASS: ClassVar[Type[ContainerConfig]] = (
        DefaultDictContainerConfig)

    def __init__(self, initdict=None,
                 container_conf: ContainerConfig | None = None):
        self._container_conf: DefaultDictContainerConfig | None = None
        UserDict.__init__(self, None)
        ConfigurableContainerBase.__init__(
            self, container_conf=container_conf)
        if initdict is not None:
            self.update(initdict)

    # noinspection PyPep8Naming
    @classmethod
    def Type(cls):

        key_type = cls.DICT_CONFIG_CLASS().allowed_key_types
        if isinstance(key_type, tuple):
            key_type = Union[*key_type]

        value_type = cls.DICT_CONFIG_CLASS().allowed_types
        if isinstance(value_type, tuple):
            value_type = Union[*value_type]
        dict_type = dict[key_type, value_type]
        return cls | dict_type

    @classmethod
    def from_type(cls, type_: type,
                  initdict=None, **kwargs):
        return cls(initdict=initdict,
                   container_conf=ContainerConfig(
                       allowed_types=type_, **kwargs))

    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except (KeyError, TypeError) as error:
            if (self._container_conf.b_enum_to_str_key
                    and isinstance(item, Enum)):
                return super().__getitem__(item.name)
            raise error

    def __setitem__(self, key, item):
        if ((self.check_key_type(key) is False)
                and isinstance(key, Enum)
                and self._container_conf.b_enum_to_str_key):
            key = key.name
        super().__setitem__(self.validate_key(key),
                            self.validate_item(item))

    def __getattribute__(self, item):
        if (item == 'pop') and hasattr(self, '_container_conf'):
            if self._container_conf.b_pop_allowed is False:
                raise PermissionError("Popping not allowed.")
        return super().__getattribute__(item)

    def update(self, m, **kwargs) -> None:
        if isinstance(m, (dict, UserDict)):
            for k, v in m.items():
                self[k] = v
        else:
            for k, v in m:
                self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def validate_key(self, key, b_skip_typecheck: bool = False):
        if b_skip_typecheck is False:
            self.cls_validate_value_type(
                key, self._container_conf.allowed_key_types)

        if self._container_conf.b_replace_allowed is False:
            if key in self:
                raise KeyError(f"Key {key} already exists.")
        return key

    def validate_keys(self, keys):
        super().validate_keys(keys)
        if self._container_conf.b_replace_allowed is False:
            for k in keys:
                self.validate_key(k, b_skip_typecheck=True)

    def validate_item(self, item):
        b_duplicate_check = not self._container_conf.b_duplicates_allowed
        if ((item is not None)
                and (b_duplicate_check is True) and hasattr(self, "data")
                and (item in self.data.values())):
            raise ExtensionByDuplicateError(f"Item {item} already in values.")
        item = super().validate_item(item)
        return item
