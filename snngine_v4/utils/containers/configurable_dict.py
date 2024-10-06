from __future__ import annotations

from collections import UserDict
from enum import Enum

from typing import Any, Callable, ClassVar, Type

from snngine_v4.utils.containers.configurable_container import (
    ConfigurableContainerBase, ContainerConfig, UndefinedDefaultError,
    ValidValueType, ValidKeyType,
)
from snngine_v4.utils.field_utils import Undefined, KeepUndefinedType


class DictContainerConfig(ContainerConfig,
                          frozen=True, arbitrary_types_allowed=True):

    allowed_types: ValidValueType = Any
    allowed_key_types: ValidKeyType = str
    b_duplicates_allowed: bool = False  # Keep False
    b_replace_allowed: bool = False  # Keep False
    b_pop_allowed: bool = True  # Keep True
    b_enum_to_str_key: bool = True  # Keep True
    default_value: KeepUndefinedType = Undefined


class ConfigurableDict(ConfigurableContainerBase, UserDict):

    ContainerConfigClass: ClassVar[Type[ContainerConfig]] = (
        DictContainerConfig)

    def __init__(self, data=None,
                 container_conf: ContainerConfig | None = None):
        self._container_conf: DictContainerConfig | None = None
        UserDict.__init__(self, None)
        ConfigurableContainerBase.__init__(
            self, container_conf=container_conf)
        if data is not None:
            self.update(data)

    def b_duplicated_item(self, item):
        b_duplicate_check = not self._container_conf.b_duplicates_allowed
        # return ((item is not None)
        #         and (b_duplicate_check is True) and hasattr(self, "data")
        #         and self.values_contain(item))
        return ((b_duplicate_check is True) and hasattr(self, "data")
                and self.values_contain(item))

    def clear(self, b_force: bool = False) -> None:
        if ((self._container_conf.b_clear_allowed is False)
                and (b_force is False)):
            raise AttributeError("Clearing not allowed.")
        super().clear()

    def __contains__(self, item):
        contains = super().__contains__(item)
        if ((contains is False)
                and (self._container_conf.b_enum_to_str_key
                     and isinstance(item, Enum))):
            contains = super().__contains__(item.name)
        return contains

    @classmethod
    def from_type(cls, type_: type,
                  data=None, **kwargs):

        return cls(data=data,
                   container_conf=cls.ContainerConfigClass(
                       allowed_types=type_,
                       **kwargs))

    def __getattribute__(self, item):
        if (item == 'pop') and hasattr(self, '_container_conf'):
            if self._container_conf.b_pop_allowed is False:
                raise PermissionError("Popping not allowed.")
        return super().__getattribute__(item)

    def set_default(
            self, item,
            error: BaseException | Type[BaseException] = UndefinedDefaultError):
        if self._container_conf.default_value != Undefined:
            self[item] = self._container_conf.default_value
            return self[item]
        else:
            raise error

    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except (KeyError, TypeError) as error:
            if (self._container_conf.b_enum_to_str_key
                    and isinstance(item, Enum)):
                try:
                    return super().__getitem__(item.name)
                except KeyError as error:
                    return self.set_default(item, error=error)
            if self._container_conf.default_value != Undefined:
                return self.set_default(item, error=error)
            raise error

    def get_unique_values(self, *keys):
        if len(keys) == 0:
            keys = list(self.keys())
        vals = []
        for k in keys:
            vals.append(self[k])
        return set(vals)

    def __setitem__(self, key, item):
        if ((self.b_valid_key_type(key) is False)
                and isinstance(key, Enum)
                and self._container_conf.b_enum_to_str_key):
            key = key.name
        super().__setitem__(self.validate_key(key),
                            self.validate_item(item))

    def update(self, m=None, **kwargs) -> None:
        if m is not None:
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

    def values_contain(self, item):
        if (not isinstance(item, int) and
                self._container_conf.b_duplicate_check_by_id):
            return id(item) in self.value_ids
        return item in self.values()

    @property
    def value_ids(self):
        return [id(v) for v in self.values()]


class CallableKeyDict(ConfigurableDict):

    class ContainerConfigClass(DictContainerConfig):
        allowed_key_types: Any = Callable
