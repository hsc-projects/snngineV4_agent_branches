from __future__ import annotations

from typing import Any, Callable, ClassVar, Type

from pydantic import BaseModel

from snngine_v4.utils.containers.configurable_container import (
    # ContainerConfig,
    ValidValueType,
)
from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict, DictContainerConfig,
)
from snngine_v4.utils.containers.configurable_list import (
    ConfigurableList, ConfigurableListConfig,
)
from snngine_v4.utils.core_utils import Singleton
from snngine_v4.utils.field_utils import Undefined


class UniqueObjectListConfig(ConfigurableListConfig, frozen=True):
    forbidden_types: Type[int] = int
    b_append_allowed: bool = True
    b_duplicates_allowed: bool = False
    b_duplicate_check_by_id: bool = True
    b_replace_allowed: bool = False
    b_pop_allowed: bool = False
    b_clear_allowed: bool = False
    b_extend_allowed: bool = False
    b_insert_allowed: bool = False
    b_remove_allowed: bool = False
    b_remove_by_id_allowed: bool = True


class Int2ObjectMapConfig(DictContainerConfig, frozen=True):
    allowed_key_types: Type[int] = int
    forbidden_types: Type[int] = int
    allowed_types: ValidValueType = Any
    b_duplicate_check_by_id: bool = False
    b_duplicates_allowed: bool = False
    b_replace_allowed: bool = False
    b_pop_allowed: bool = False
    b_get_inv_allowed: bool = False
    b_list_mode: bool = False


class Object2ObjectMap(ConfigurableDict):

    ContainerConfigClass: ClassVar[Type[Int2ObjectMapConfig]] = (
        Int2ObjectMapConfig)
    InvertedConfigClass: ClassVar[Type[Int2ObjectMapConfig]] = (
        Int2ObjectMapConfig)

    container_conf: Int2ObjectMapConfig
    _container_conf: Int2ObjectMapConfig
    __getitem__: Callable[[Any], Any]

    def __init__(self, inv: Object2ObjectMap = None,
                 container_conf=None,
                 inv_conf=None,
                 # node_tree=None,
                 **kwargs):
        self._container_conf: Int2ObjectMapConfig | None = None
        if inv is None:
            container_conf = self.cls_make_container_conf(
                container_conf=container_conf)
            if inv_conf is None:
                inv_conf = self.cls_make_inv_conf(
                    container_conf=container_conf
                )
            inv = Object2ObjectMap(
                inv=self, container_conf=inv_conf,
                inv_conf=container_conf)
        elif inv_conf is None:
            inv_conf = inv.container_conf
            # raise ValueError("inverted_conf has not effect")
        self.inv = inv

        ref_types = inv_conf.allowed_types
        if inv_conf.b_list_mode is True:
            if isinstance(ref_types, tuple) and len(ref_types) == 1:
                ref_types = ref_types[0]().container_conf.allowed_types

        self.refs = ConfigurableList(
            container_conf=UniqueObjectListConfig(
                allowed_types=ref_types,
                b_remove_allowed=container_conf.b_pop_allowed))
        # self.model2nodetree_map = node_tree
        super().__init__(container_conf=container_conf,
                         **kwargs)

    def __contains__(self, item):
        if not isinstance(item, int):
            item = id(item)
        return super().__contains__(item)

    def clear(self, b_force: bool = False, b_clear_inv: bool = True):
        super().clear(b_force=b_force)
        self.refs.clear(b_force=True)
        if b_clear_inv:
            self.inv.clear(b_force=True, b_clear_inv=False)

    @classmethod
    def cls_make_container_conf(
            cls, container_conf=None,
            default_cls=None, **kwargs):
        if default_cls is None:
            default_cls = cls.ContainerConfigClass
        if (isinstance(default_cls, tuple)
                and (
                    isinstance(default_cls[0], tuple)
                    or (not issubclass(default_cls[0], Int2ObjectMapConfig)))):
            return Int2ObjectMapConfig(allowed_types=default_cls[1])
        return super().cls_make_container_conf(
            container_conf, default_cls=default_cls, **kwargs)

    @classmethod
    def cls_make_inv_conf(
        cls, container_conf: Int2ObjectMapConfig | None, inv_conf=None,
        default_inv_conf_cls: Type | tuple = None,
        default_conf_cls: Type | tuple = None,
        **kwargs
    ):
        if default_conf_cls is None:
            default_conf_cls = cls.ContainerConfigClass
        if default_inv_conf_cls is None:
            default_inv_conf_cls = cls.InvertedConfigClass

        if (isinstance(default_conf_cls, tuple)
                and (not issubclass(
                    default_conf_cls[0], Int2ObjectMapConfig))):
            kwargs['allowed_types'] = default_conf_cls[0]
        else:
            kwargs['allowed_types'] = super().cls_make_container_conf(
                container_conf=inv_conf,
                default_cls=default_inv_conf_cls).allowed_types
        if container_conf is None:
            container_conf = super().cls_make_container_conf(
                default_cls=default_conf_cls)

        if container_conf is not None:
            if container_conf.b_duplicates_allowed:
                # noinspection PyPep8Naming
                GeneratedTypeListClass = (
                    ConfigurableList.class_from_type(
                        kwargs['allowed_types'],
                        b_remove_allowed=container_conf.b_pop_allowed
                    ))
                kwargs['b_list_mode'] = True
                kwargs['allowed_types'] = GeneratedTypeListClass
            kwargs['b_pop_allowed'] = container_conf.b_pop_allowed

        if isinstance(kwargs['allowed_types'], tuple) \
                and len(kwargs['allowed_types']) == 1:
            kwargs['allowed_types'] = kwargs['allowed_types'][0]

        return super().cls_make_container_conf(
            container_conf=inv_conf, default_cls=default_inv_conf_cls,
            **kwargs)

    @classmethod
    def cls_make_default_conf_classes(
        cls,
        container_conf: Type[Int2ObjectMapConfig] | None = None,
        inv_conf: Type[Int2ObjectMapConfig] = None,
        default_conf_cls: Type[Int2ObjectMapConfig] = None,
        default_inv_cls: Type[Int2ObjectMapConfig] = None,
    ):
        if container_conf is None:
            container_conf = cls.cls_make_container_conf(
                default_cls=default_conf_cls
            )
        elif inv_conf is None:
            inv_conf = cls.cls_make_inv_conf(
                default_inv_conf_cls=default_inv_cls,
                default_conf_cls=default_conf_cls,
                container_conf=container_conf,
            )
        return container_conf, inv_conf

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
            inv_conf=cls.InvertedConfigClass(allowed_types=type0),
            **kwargs)
        return new

    def __getitem__(self, item):
        if not self.b_valid_key_type(item):
            if (self._container_conf.b_get_inv_allowed
                    and self.b_valid_item_type(item)):
                return self.inv[item]
            else:
                item = id(item)
        try:
            return self.data[item]
        except KeyError:
            raise KeyError(item)

    def __invert__(self):
        return self.inv

    @property
    def is_empty(self):
        return super().is_empty and len(self.refs) == 0

    def make_list(self):
        return ConfigurableList(
            container_conf=UniqueObjectListConfig(
                allowed_types=self._container_conf.allowed_types))

    def pairs(self):
        for ref in self.refs:
            yield ref, self[ref]

    def pop(self, key, default=Undefined):
        if self._container_conf.b_duplicates_allowed:
            raise NotImplementedError
        value = self[key]
        self.refs.remove(key)
        if default is Undefined:
            res = super().pop(key)
        else:
            res = super().pop(key, default)
        if value in self.inv:
            self.inv.pop(id(value))
        return res

    def __setitem__(self, item0, item1):

        if self.container_conf.b_list_mode and item0 in self.refs:
            pass
        else:
            self.refs.append(item0)

        if not isinstance(key := item0, int):
            key = id(item0)
        if self.container_conf.b_list_mode is True:
            if key not in self:
                list_type = self.container_conf.allowed_types
                if (not isinstance(list_type, tuple)) or (len(list_type) != 1):
                    raise TypeError
                list_type = list_type[0]
                item1: ConfigurableList = list_type(item1)
                # print(item0.__class__.__name__, item1.__class__.__name__)
                super().__setitem__(key, item1)
            else:
                # print(item0.__class__.__name__, item1.__class__.__name__)
                self[key].append(item1)
        else:
            super().__setitem__(key, item1)
        if item1 is not None:
            if item1 not in self.inv:
                self.inv[item1] = item0
            elif ((self.inv.container_conf.b_list_mode is True)
                  and (item1 in self.inv)
                  and (item0 not in self.inv[item1])):
                self.inv[item1] = item0
            elif (item_ := self.inv[item1]) is not item0:
                if self.inv.container_conf.b_list_mode is False:
                    raise ValueError(
                        f"self.inverted[item1] = {item_} != {item0}")
                elif item0 not in (item_ := self.inv[item1]):
                    raise ValueError(
                        f"{item0} not in self.inverted[item1] = {item_}")

    def update(self, m=None, **kwargs) -> None:
        if isinstance(m, Object2ObjectMap):
            for k, v in m.pairs():
                self[k] = v
        super().update(**kwargs)

    def values_contain(self, item):
        # if not isinstance(item, int):
        return id(item) in self.value_ids
        # return item in self.values()


class Model2ObjectMap(Object2ObjectMap):
    class InvertedConfigClass(Int2ObjectMapConfig, frozen=True):
        allowed_types: Type[BaseModel] = BaseModel


class SingletonMap(metaclass=Singleton):

    ContainerConfigClass: ClassVar[Type[Int2ObjectMapConfig]] = (
        Int2ObjectMapConfig)
    InvertedConfigClass: ClassVar[Type[Int2ObjectMapConfig]] = (
        Int2ObjectMapConfig)

    Object2ObjectMapClass: ClassVar[Type[Object2ObjectMap]] = Object2ObjectMap

    def __init__(self, obj_map=None, map_options=None):
        self.obj_map = obj_map or self.cls_make_map(**(map_options or {}))

    @classmethod
    def cls_make_map(
        cls, map_class: Type[Object2ObjectMap] = None,
        container_conf: Type[Int2ObjectMapConfig] = None,
        inv_conf: Type[Int2ObjectMapConfig] = None
    ):
        if map_class is None:
            map_class = cls.Object2ObjectMapClass
        container_conf, inv_conf = (
            cls.Object2ObjectMapClass
            .cls_make_default_conf_classes(
                container_conf=container_conf, inv_conf=inv_conf,
                default_conf_cls=cls.ContainerConfigClass,
                default_inv_cls=cls.InvertedConfigClass,
            ))
        return map_class(
            container_conf=container_conf,
            inv_conf=inv_conf
        )

    def __invert__(self):
        return self.obj_map.__invert__()

    def __getitem__(self, item):
        return self.obj_map[item]

    def __setitem__(self, item0, item1):
        self.obj_map[item0] = item1
