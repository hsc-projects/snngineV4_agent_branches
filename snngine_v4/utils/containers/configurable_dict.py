from __future__ import annotations

from collections import UserDict
from typing import ClassVar, Type

from snngine_v4.utils.containers.configurable_container import (
    ConfigurableContainerBase, ContainerConfig, ExtensionByDuplicateError,
)


class DefaultDictContainerConfig(ContainerConfig, frozen=True):
    allowed_types: tuple[Type] | Type = None
    allowed_key_types: tuple[Type] | Type = None
    b_duplicates_allowed: bool = False  # Keep False
    b_replace_allowed: bool = False  # Keep False
    b_pop_allowed: bool = True  # Keep True


class ConfigurableDict(ConfigurableContainerBase, UserDict):

    CONFIG_CLASS: ClassVar[Type[ContainerConfig]] = DefaultDictContainerConfig

    def __init__(self, initdict=None,
                 container_conf: ContainerConfig | None = None):

        UserDict.__init__(self, initdict)
        ConfigurableContainerBase.__init__(
            self, container_conf=container_conf)

    @classmethod
    def from_type(cls, type_: type,
                  initdict=None, **kwargs):
        return cls(initdict=initdict,
                   container_conf=ContainerConfig(
                       allowed_types=type_, **kwargs))

    def __setitem__(self, key, item):
        super().__setitem__(self.validate_key(key),
                            self.validate_item(item))

    def __getattribute__(self, item):
        if (item == 'pop') and hasattr(self, '_container_conf'):
            if self._container_conf.b_pop_allowed is False:
                raise PermissionError("Popping not allowed.")
        return super().__getattribute__(item)

    def update(self, m, **kwargs) -> None:
        values = list(m.values()) + list(kwargs.values())
        self.validate_items(values)
        super().update(m, **kwargs)

    def validate_key(self, key):
        if self._container_conf.b_replace_allowed is False:
            if key in self.data:
                raise KeyError(f"Key {key} already exists.")

    def validate_keys(self, keys):
        super().validate_keys(keys)
        if self._container_conf.b_replace_allowed is False:
            for k in keys:
                self.validate_key(k)

    def validate_item(self, item):
        b_duplicate_check = not self._container_conf.b_duplicates_allowed
        if ((b_duplicate_check is True) and hasattr(self, "data")
                and (item in self.data.values())):
            raise ExtensionByDuplicateError(f"Item {item} already in values.")
        item = super().validate_item(item)
        return item
