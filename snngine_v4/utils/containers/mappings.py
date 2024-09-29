from __future__ import annotations

from typing import Any, ClassVar, Type

from pydantic import BaseModel

from snngine_v4.utils.containers.configurable_container import (
    ValidValueType
)
from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict, DictContainerConfig,
)
from snngine_v4.utils.containers.configurable_list import (
    ConfigurableList, ConfigurableListConfig,
)


class UniqueObjectListConfig(ConfigurableListConfig, frozen=True):
    b_append_allowed: bool = True
    b_duplicates_allowed: bool = False
    b_duplicate_check_by_id: bool = True
    b_replace_allowed: bool = False
    b_pop_allowed: bool = False
    b_clear_allowed: bool = False
    b_extend_allowed: bool = False
    b_insert_allowed: bool = False
    b_remove_allowed: bool = False


class Int2ObjectMapConfig(DictContainerConfig, frozen=True):
    allowed_key_types: Type[int] = int
    allowed_types: ValidValueType = Any
    b_duplicate_check_by_id: bool = True
    b_duplicates_allowed: bool = False
    b_replace_allowed: bool = False
    b_pop_allowed: bool = False


class Object2ObjectMap(ConfigurableDict):

    ContainerConfigClass: ClassVar = Int2ObjectMapConfig
    InvertedConfigClass: ClassVar = Int2ObjectMapConfig

    def __init__(self, inverted: Object2ObjectMap = None,
                 container_conf=None,
                 inverted_conf=None,
                 **kwargs):
        if inverted is None:
            container_conf = self.cls_make_container_conf(
                container_conf=container_conf)
            if inverted_conf is None:
                inverted_conf = self.InvertedConfigClass()
            inverted = Object2ObjectMap(
                inverted=self, container_conf=inverted_conf,
                inverted_conf=container_conf)
        elif inverted_conf is None:
            inverted_conf = inverted.container_conf
            # raise ValueError("inverted_conf has not effect")
        self.inverted = inverted
        self.refs = ConfigurableList(
            container_conf=UniqueObjectListConfig(
                allowed_types=inverted_conf.allowed_types))
        super().__init__(container_conf=container_conf,
                         **kwargs)

    @property
    def data_ids(self):
        return self.data.keys()

    @classmethod
    def from_type(cls, type_: type, **kwargs):
        return cls.from_types(type1=type_, **kwargs)

    @classmethod
    def from_types(cls, type0=None, type1=None, **kwargs):

        if type0 is None:
            type0 = cls.InvertedConfigClass.default_allowed_types()
        if type1 is None:
            type1 = cls.ContainerConfigClass.default_allowed_types()

        new = cls(
            container_conf=cls.ContainerConfigClass(allowed_types=type1),
            inverted_conf=cls.InvertedConfigClass(allowed_types=type0),
            **kwargs)
        return new

    def __getitem__(self, item):
        if not isinstance(item, self._container_conf.allowed_key_types):
            item = id(item)
        try:
            return self.data[item]
        except KeyError:
            raise KeyError(item)

    @property
    def is_empty(self):
        return super().is_empty and len(self.refs) == 0

    def pairs(self):
        for ref in self.refs:
            yield ref, self[ref]

    def __setitem__(self, item0, item1):
        self.refs.append(item0)

        if not isinstance(key := item0, int):
            key = id(item0)
        super().__setitem__(key, item1)
        if item1 is not None:
            if item1 not in self.inverted:
                self.inverted[item1] = item0
            elif (item_ := self.inverted[item1]) is not item0:
                raise ValueError(f"self.inverted[item1] = {item_} != {item0}")

    def update(self, m, **kwargs) -> None:
        if isinstance(m, Object2ObjectMap):
            for k, v in m.pairs():
                self[k] = v
        else:
            super().update(m, **kwargs)


class Model2ObjectMap(Object2ObjectMap):

    class InvertedConfigClass(Int2ObjectMapConfig, frozen=True):
        allowed_types: Type[BaseModel] = BaseModel
