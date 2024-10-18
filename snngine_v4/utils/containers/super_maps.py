from __future__ import annotations

from types import UnionType
from typing import ClassVar, Type

from pydantic_core import PydanticUndefined

from snngine_v4.utils.containers.configurable_container import (
    ConfigurableContainerBase, ValidKeyType, ValidValueType,
)

from snngine_v4.utils.containers.configurable_dict import DictContainerConfig
from snngine_v4.utils.containers.mappings import (
    Object2ObjectMap,
)


class SuperMapConfigError(BaseException):
    pass


class SortedMapConfig(DictContainerConfig, frozen=True):
    allowed_types: ValidValueType
    allowed_key_types: ValidValueType
    b_auto_create: bool = True
    b_auto_sort: bool = True


class TypeSortedMap(ConfigurableContainerBase):

    # sub_maps: tuple
    ContainerConfigClass: ClassVar = SortedMapConfig
    sub_maps: tuple[tuple[ValidKeyType, ValidValueType], ...]
    container_conf: SortedMapConfig
    _container_conf: SortedMapConfig

    @classmethod
    def cls_make_container_conf(cls, container_conf=None,
                                default_cls=None, **kwargs):
        if default_cls is None:
            default_cls = cls.ContainerConfigClass
        return default_cls(
            allowed_key_types=tuple([x[0] for x in cls.sub_maps]),
            allowed_types=tuple([x[1] for x in cls.sub_maps]),
            **kwargs
        )

    def __init__(self, data=None, **kwargs):
        super().__init__(**kwargs)
        self.validate_configuration()
        self.value_map = None

        allowed_types = self._container_conf.allowed_types
        if len(set(allowed_types)) == len(allowed_types):
            self.value_map = Object2ObjectMap.from_types(
                type | UnionType,
                Object2ObjectMap
            )
        else:
            self.value_map = None
        self.key_map: dict[type, Object2ObjectMap] | Object2ObjectMap = (
            Object2ObjectMap.from_types(
                type | UnionType,
                Object2ObjectMap
            ))

        if data is not None:
            self.value_map.update(data)

    def clear(self, b_force: bool = False) -> None:
        if ((self._container_conf.b_clear_allowed is False)
                and (b_force is False)):
            raise AttributeError("Clearing not allowed.")

        for value in self.key_map.values():
            value.clear(b_force=True)
        self.key_map.clear(b_force=True)
        if self.value_map is not None:
            for value in self.value_map.values():
                value.clear(b_force=True)
            self.value_map.clear(b_force=True)

    def create_sub_map(
            self, key_type, value_type: Type | None = PydanticUndefined):
        value_type_ = self._container_conf.allowed_types[
            self._container_conf.allowed_key_types.index(key_type)]
        if value_type == PydanticUndefined:
            value_type = value_type_
        elif value_type != value_type_:
            raise RuntimeError(
                f"'{value_type}' = value_type "
                f"!= value_type_ = '{value_type_}'")
        map_ = Object2ObjectMap().from_types(key_type, value_type)
        if self.value_map:
            if value_type in self.container_conf.allowed_types:
                self.value_map[value_type] = map_
            else:
                raise TypeError(f"value_type={value_type}")
        if key_type in self.container_conf.allowed_key_types:
            self.key_map[key_type] = map_
        else:
            raise TypeError(f"key_type={key_type}")
        return map_

    def __getitem__(self, key):
        try:
            return self.key_map[key]
        except KeyError:
            if key in self._container_conf.allowed_key_types:
                if self._container_conf.b_auto_create:
                    return self.create_sub_map(key_type=key)
                else:
                    raise PermissionError(
                        f"b_auto_create={self._container_conf.b_auto_create}")
            return self.get_sub_map_by_key(key)[key]

    def get_sub_map_by_key(self, key):

        sm: tuple[Type, Type] | None = None
        sms = self.sub_maps
        for sm_def in sms:
            if isinstance(key, sm_def[0]):
                sm = sm_def
                break
        if sm is None:
            raise TypeError(key)
        if (sm[0] not in self.key_map) and self._container_conf.b_auto_create:
            # if len(self.key_map.refs) == 1:
            #     sm[0] not in self.key_map
            map_ = self.create_sub_map(key_type=sm[0], value_type=sm[1])
        else:
            map_ = self.key_map[sm[0]]
        return map_

    def __setitem__(self, key, value):
        b_auto_sort = self._container_conf.b_auto_sort
        if b_auto_sort:
            self.get_sub_map_by_key(key)[key] = value
        else:
            raise PermissionError(
                f"b_auto_sort={b_auto_sort}, "
                "add items directly to the corresponding map")

    def validate_configuration(self):
        pass
