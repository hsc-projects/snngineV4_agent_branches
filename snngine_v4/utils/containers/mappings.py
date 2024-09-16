from __future__ import annotations

from multiprocessing.managers import Value
from typing import ClassVar, Type

from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict, DefaultDictContainerConfig,
)
from snngine_v4.utils.containers.configurable_list import (
    ConfigurableList, ConfigurableListConfig,
)


class Object2KeyMapConfig(DefaultDictContainerConfig, frozen=True):
    allowed_key_types: Type[int] = int
    allowed_types: Type[str] = str
    b_duplicates_allowed: bool = False
    b_replace_allowed: bool = False
    b_pop_allowed: bool = False


class Object2KeyMap(ConfigurableDict):
    """
    TODO:
        * optional weakrefs
        * implement remove
        * (consistency)
    """

    CONTAINER_CONFIG_CLASS: ClassVar = Object2KeyMapConfig

    def __init__(self, **kwargs):
        self.refs = []
        super().__init__(**kwargs)

    def __getitem__(self, item):
        if not isinstance(item, int):
            item = id(item)
        return self.data[item]

    @property
    def is_empty(self):
        return super().is_empty and len(self.refs) == 0

    def __setitem__(self, key, value):
        self.refs.append(key)
        if not isinstance(key, int):
            key = id(key)
        super().__setitem__(key, value)

    def __contains__(self, key):
        if not isinstance(key, int) and id(key) in self.keys():
            if not id(key) in [id(x) for x in self.refs]:
                raise AssertionError
            return True
        return key in list(self.keys())


class MappedDict(ConfigurableDict):

    def __init__(self, initdict=None, object2key_map=None, container_conf=None):
        self.object2key_map: Object2KeyMap = object2key_map
        super().__init__(initdict=initdict, container_conf=container_conf)

    def add_to_object_2_key_map(self, key, item):
        pass

    def __setitem__(self, key, item):
        if self.object2key_map is not None:
            self.add_to_object_2_key_map(key, item)
        super().__setitem__(key, item)


class ConfigurableIDListConfig(ConfigurableListConfig, frozen=True):
    b_append_allowed: bool = True
    b_duplicates_allowed: bool = False
    b_duplicate_check_by_id: bool = True
    b_replace_allowed: bool = False
    b_pop_allowed: bool = False
    b_clear_allowed: bool = False
    b_extend_allowed: bool = False
    b_insert_allowed: bool = False
    b_remove_allowed: bool = False


class Object2ObjectMapConfig(Object2KeyMapConfig, frozen=True):
    allowed_key_types: Type[int] = int
    allowed_types: Type | None = None


class Object2ObjectMap(Object2KeyMap):

    CONTAINER_CONFIG_CLASS: ClassVar = Object2ObjectMapConfig

    def __init__(self, inverted: Object2ObjectMap = None,
                 inverted_conf=None,
                 **kwargs):
        if inverted is None:
            inverted = Object2ObjectMap(
                inverted=self, container_conf=inverted_conf)
        elif inverted_conf is not None:
            raise ValueError("inverted_conf has not effect")
        self.inverted = inverted
        super().__init__(**kwargs)

    @classmethod
    def from_types(cls, type0, type1):
        conf0 = ConfigurableIDListConfig(allowed_types=type0)
        conf1 = ConfigurableIDListConfig(allowed_types=type1)
        new = cls(container_conf=Object2ObjectMapConfig(allowed_types=type1),
                  inverted_conf=Object2ObjectMapConfig(allowed_types=type0))
        new.assert_emptiness()
        new.refs = ConfigurableList(container_conf=conf0)
        new.inverted.refs = ConfigurableList(container_conf=conf1)
        return new

    def __getitem__(self, item):
        if not isinstance(item, self._container_conf.allowed_key_types):
            item = id(item)
        return self.data[item]

    def __setitem__(self, key, item):
        self.inverted.__class__.mro()[1].__setitem__(self.inverted, item, key)
        super().__setitem__(key, item)
