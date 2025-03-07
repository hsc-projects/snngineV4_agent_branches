from __future__ import annotations

from sys import getrefcount
from typing import Any, Callable, ClassVar, Type

from pydantic import BaseModel

from snngine_v4.utils.containers.configurable_container import (
    # ContainerConfig,
    ContainerConfig, ValidValueType,
)
from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict, DictContainerConfig, SingletonDict,
)
from snngine_v4.utils.containers.configurable_list import (
    ConfigurableList, ConfigurableListConfig,
)
from snngine_v4.utils.core_utils import type_assertion
from snngine_v4.utils.field_utils import extract_field_default, Undefined


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


class ObjectMapConfig(DictContainerConfig, frozen=True):
    allowed_key_types: Type[int] = int
    forbidden_types: Type[int] = int
    allowed_types: ValidValueType = Any
    b_duplicate_check_by_id: bool = True
    b_duplicates_allowed: bool = False
    b_replace_allowed: bool = False
    b_pop_allowed: bool = False
    b_get_inv_allowed: bool = False
    b_list_mode: bool = False


class Object2ObjectMap(ConfigurableDict):

    ContainerConfigClass: ClassVar[Type[ObjectMapConfig]] = (
        ObjectMapConfig)
    InvertedConfigClass: ClassVar[Type[ObjectMapConfig]] = (
        ObjectMapConfig)

    container_conf: ObjectMapConfig
    _container_conf: ObjectMapConfig
    __getitem__: Callable[[Any], Any]

    def __init__(self, inv: Object2ObjectMap = None,
                 container_conf=None,
                 inv_conf=None,
                 # node_tree=None,
                 **kwargs):
        self._container_conf: ObjectMapConfig | None = None
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
            # raise ValueError("inverted_conf has no effect")
        self.inv = inv

        ref_types = inv_conf.allowed_types
        if inv_conf.b_list_mode is True:
            if isinstance(ref_types, tuple) and len(ref_types) == 1:
                if not issubclass(ref_types[0], ConfigurableList):
                    raise RuntimeError
                ref_types = ref_types[0]().container_conf.allowed_types

        self.refs = ConfigurableList(
            container_conf=UniqueObjectListConfig(
                allowed_types=ref_types,
                b_remove_allowed=container_conf.b_pop_allowed))
        # self.model2nodetree_map = node_tree
        super().__init__(container_conf=container_conf,
                         **kwargs)

    def __contains__(self, item):
        item = self._get_key(item)
        return super().__contains__(item)

    def clear(self, b_force: bool = False, b_clear_inv: bool = True):
        super().clear(b_force=b_force)
        self.refs.clear(b_force=True)
        if b_clear_inv:
            self.inv.clear(b_force=True, b_clear_inv=False)

    @classmethod
    def b_key_value_type_init(cls, conf_value):
        if (isinstance(conf_value, tuple)
            and (isinstance(conf_value[0], tuple)
                 or (not issubclass(conf_value[0], ObjectMapConfig)))):
            if isinstance(conf_value[0], tuple):
                if len(conf_value) != 2:
                    raise AssertionError
            return True
        return False

    @classmethod
    def cls_make_container_conf(
            cls, container_conf=None,
            default_cls: type | tuple = None, **kwargs):
        if default_cls is None:
            default_cls = cls.ContainerConfigClass
        if cls.b_key_value_type_init(default_cls):
            return ObjectMapConfig(allowed_types=default_cls[1])
        return super().cls_make_container_conf(
            container_conf, default_cls=default_cls, **kwargs)

    @classmethod
    def cls_make_inv_conf(
        cls, container_conf: ObjectMapConfig | None, inv_conf=None,
        default_inv_conf_cls: Type | tuple = None,
        default_conf_cls: Type | tuple = None,
        **kwargs
    ):

        if container_conf is None:
            container_conf = super().cls_make_container_conf(
                default_cls=default_conf_cls)
        default_kwargs_source: ObjectMapConfig = container_conf

        if default_conf_cls is None:
            default_conf_cls = cls.ContainerConfigClass
        if default_inv_conf_cls is None:
            default_inv_conf_cls = cls.InvertedConfigClass

        # default_conf_cls = (Type0, ...)
        if 'allowed_types' in kwargs:
            pass
        elif cls.b_key_value_type_init(default_conf_cls):
            kwargs['allowed_types'] = default_conf_cls[0]
        else:  # class or (class, ValueType, KeyType (optional))
            default_kwargs_source = super().cls_make_container_conf(
                container_conf=inv_conf,
                default_cls=default_inv_conf_cls)
            kwargs['allowed_types'] = default_kwargs_source.allowed_types

        # forced override (need to allow pop both ways)
        kwargs['b_pop_allowed'] = container_conf.b_pop_allowed
        if container_conf.b_duplicates_allowed:
            # noinspection PyPep8Naming
            GeneratedTypeListClass = (
                ConfigurableList.class_from_type(
                    type_=kwargs['allowed_types'],
                    b_remove_allowed=kwargs['b_pop_allowed'],
                    b_duplicate_check_by_id=default_kwargs_source
                    .b_duplicate_check_by_id,
                    forbidden_types=default_kwargs_source.forbidden_types,
                    b_remove_by_id_allowed=default_kwargs_source
                    .b_remove_by_id_allowed
                ))
            kwargs['b_list_mode'] = True
            kwargs['allowed_types'] = GeneratedTypeListClass

        if isinstance(kwargs['allowed_types'], tuple) \
                and len(kwargs['allowed_types']) == 1:
            kwargs['allowed_types'] = kwargs['allowed_types'][0]

        return super().cls_make_container_conf(
            container_conf=inv_conf, default_cls=default_inv_conf_cls,
            **kwargs)

    @property
    def data_ids(self):
        return self.data.keys()

    @classmethod
    def from_type(cls, type_: type, **kwargs):
        return cls.from_types(type1=type_, **kwargs)

    @classmethod
    def from_types(cls, type0=None, type1=None,
                   b_pop_allowed=Undefined, **kwargs):

        if type0 is None:
            type0 = cls.InvertedConfigClass.default_allowed_types()
        if type1 is None:
            type1 = cls.ContainerConfigClass.default_allowed_types()

        if b_pop_allowed == Undefined:
            b_pop_allowed = extract_field_default((
                cls.ContainerConfigClass,
                ContainerConfig.Slots.B_POP_ALLOWED,))

        container_conf = cls.ContainerConfigClass(
            allowed_types=type1,
            b_pop_allowed=b_pop_allowed)
        inv_conf = cls.cls_make_inv_conf(
            container_conf=container_conf,
            allowed_types=type0,
        )

        new = cls(
            container_conf=container_conf,
            inv_conf=inv_conf,
            **kwargs)
        return new

    def _make_key(self, item):
        return id(item)

    def _get_key(self, item):
        if not self.b_valid_key_type(item):
            return self._make_key(item)
        return item

    def __getitem__(self, item):
        if not self.b_valid_key_type(item):
            if (self._container_conf.b_get_inv_allowed
                    and self.b_valid_item_type(item)):
                return self.inv[item]
            else:
                item = self._make_key(item)
        try:
            return self.data[item]
        except KeyError:
            raise

    def __invert__(self):
        return self.inv

    @property
    def is_empty(self):
        return super().is_empty and len(self.refs) == 0

    def make_list(self):
        return ConfigurableList(
            container_conf=UniqueObjectListConfig(
                allowed_types=self._container_conf.allowed_types))

    def make_subset(self, *keys, subset_container=None,
                    b_assert_key_exists=True):
        if subset_container is None:
            subset_container = Object2ObjectMap(
                container_conf=self._container_conf,
                inv_conf=self.inv._container_conf)
        subset_container.update(**self._make_sub_dict(
            *keys, b_assert_key_exists=b_assert_key_exists))
        return subset_container

    def pairs(self):
        for ref in self.refs:
            yield ref, self[ref]

    def pop(self, item, default=Undefined):
        key = self._get_key(item)
        value = self[key]
        self.refs.remove(item)

        if default is Undefined:
            res = super().pop(key)
        else:
            res = super().pop(key, default)
        if value in self.inv:
            if self._container_conf.b_duplicates_allowed:
                inv_list = self.inv[value]
                inv_list.remove(item)
                if len(inv_list) == 0:
                    # count = getrefcount(inv_list)
                    # self.inv.pop(id(value))
                    self.inv.pop(value)
            else:
                # self.inv.pop(id(value))
                self.inv.pop(value)
        return res

    def _surjective_make_list(self, item1):
        if isinstance(item1, ConfigurableList):
            pass
        list_type = self.container_conf.allowed_types
        if (not isinstance(list_type, tuple)) or (len(list_type) != 1):
            raise TypeError
        list_type = list_type[0]
        item1: ConfigurableList = list_type(item1)
        return item1

    def __setitem__(self, item0, item1):

        # if self.container_conf.b_list_mode and item0 in self.refs:
        #     pass

        # else:
        if item0 not in self:
            self.refs.append(item0)

        if not isinstance(key := item0, int):
            key = self._get_key(item0)
        else:
            raise RuntimeError
        if self.container_conf.b_list_mode is True:
            if key not in self:
                # print(item0.__class__.__name__, item1.__class__.__name__)
                # if self.container_conf.b_list_mode:
                item1_ = self._surjective_make_list(item1)
                super().__setitem__(key, item1_)
            else:
                # print(item0.__class__.__name__, item1.__class__.__name__)
                self[key].append(item1)
        else:
            super().__setitem__(key, item1)
        if item1 is not None:
            if item1 not in self.inv:
                if self.container_conf.b_list_mode is True:
                    raise AssertionError
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
    class InvertedConfigClass(ObjectMapConfig, frozen=True):
        allowed_types: Type[BaseModel] = BaseModel


class SingletonMap(SingletonDict):

    ContainerConfigClass: ClassVar[Type[ObjectMapConfig] | None] = None
    InvertedConfigClass: ClassVar[Type[ObjectMapConfig] | None] = None

    ContainerClass: ClassVar[Type[Object2ObjectMap]] = Object2ObjectMap
    container: Object2ObjectMap

    @classmethod
    def cls_make_container(
        cls, container, container_class: Type[ConfigurableDict] = None,
        container_conf: Type[ConfigurableDict] = None,
        inv_conf: Type[ObjectMapConfig] = None, **kwargs
    ):
        if container_class is None:
            container_class = cls.ContainerClass

        default_conf_cls = cls.ContainerConfigClass
        if default_conf_cls is None:
            default_conf_cls = cls.ContainerClass.ContainerConfigClass

        default_inv_conf_cls = cls.InvertedConfigClass
        if default_inv_conf_cls is None:
            default_inv_conf_cls = cls.ContainerClass.InvertedConfigClass

        container_conf = container_class.cls_make_container_conf(
                container_conf=container_conf,
                default_cls=default_conf_cls, **kwargs)

        inv_conf = container_class.cls_make_inv_conf(
                container_conf=container_conf, inv_conf=inv_conf,
                default_conf_cls=container_conf.__class__,
                default_inv_conf_cls=default_inv_conf_cls)

        return container_class(container_conf=container_conf,
                               inv_conf=inv_conf)

    def __invert__(self):
        return self.container.__invert__()


class Many2OneObjectMap(Object2ObjectMap):

    class ContainerConfigClass(ObjectMapConfig):
        b_duplicates_allowed: bool = True
        b_remove_by_id_allowed: bool = True

    class InvertedConfigClass(ObjectMapConfig):
        b_duplicate_check_by_id: bool = True
        b_remove_by_id_allowed: bool = True


class Many2OneObjectSingleTonMap(SingletonMap):
    ContainerClass: ClassVar[Type[Object2ObjectMap]] = Many2OneObjectMap


class CallablesMap(Object2ObjectMap):
    class ContainerConfigClass(ObjectMapConfig):
        allowed_types: Any = Callable
