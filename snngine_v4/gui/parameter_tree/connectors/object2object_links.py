from __future__ import annotations


from enum import IntEnum, unique
from functools import cached_property
from typing import Any, Callable, ClassVar, Type

from pydantic import BaseModel, computed_field, Field, ValidationError
from qtpy import QtCore

from snngine_v4.utils.containers.configurable_dict import (
    CallableKeyDict, ConfigurableDict,
    DictContainerConfig,
)
from snngine_v4.utils.containers.configurable_list import ConfigurableList
from snngine_v4.utils.containers.mappings import (
    Many2OneObjectMap,
    Many2OneObjectSingleTonMap, Object2ObjectMap,
)
from snngine_v4.utils.containers.super_maps import TypeSortedMap
from snngine_v4.utils.data_utils.dataframe_config import SeriesModel


class SetAttributeEmitterBase(QtCore.QObject):
    """
    Base class for emitting signals when attributes are set.
    """
    sigAttributeValueChanged = QtCore.Signal(object, str, object)


@unique
class LinkStateType(IntEnum):
    SOURCE2SINK = 0
    SINK2SOURCE = 1


class CallableIsConnectedDict(CallableKeyDict):

    class ContainerConfigClass(CallableKeyDict.ContainerConfigClass):
        allowed_types: Type[bool] = bool
        b_replace_allowed: bool = True
        default_value: bool = False
        b_duplicates_allowed: bool = True


class ObjectSignal(BaseModel,
                   arbitrary_types_allowed=True,
                   extra='forbid'):

    key: str | None = None
    signal: Any | QtCore.Signal = Field(repr=False)
    emitter: Any | None = Field(default=None, repr=False)
    obj: Any = Field(default=None, repr=False)
    default_func: Callable | None = Field(default=None, repr=False)

    @computed_field
    @cached_property
    def is_connected(self) -> dict[Callable, bool] | CallableIsConnectedDict:
        conn = CallableIsConnectedDict()
        if self.default_func:
            conn[self.default_func] = False
        return conn

    def __call__(self, *args, **kwargs):
        return self.default_func(*args, **kwargs)

    def clear(self, b_force: bool = False):
        self.set_connect_all(value=False, b_raise=False)
        self.is_connected.clear(b_force=b_force)

    def connect(self, func: Callable | None = None, b_raise: bool = True):
        self.set_connect(value=True, func=func, b_raise=b_raise)

    def disconnect(self, func: Callable | None = None, b_raise: bool = True):
        self.set_connect(value=False, func=func, b_raise=b_raise)

    def emit(self, value, block=None):
        self.signal.emit(self.obj, self.key, value)

    @classmethod
    def from_key(cls, key, **kwargs):
        emitter = SetAttributeEmitterBase()
        new = cls(key=key, emitter=emitter,
                  signal=emitter.sigAttributeValueChanged, **kwargs)
        return new

    def set_connect_all(self, value, b_raise=True):
        for func in self.is_connected:
            self.set_connect(value=value, func=func, b_raise=b_raise)

    def _set_connect(
            self, func: Callable, value: bool):
        if value is True:
            self.signal.connect(func)
        elif value is False:
            self.signal.disconnect(func)
        else:
            raise TypeError(f"{value}")

    def set_connect(
            self, value: bool,
            b_raise: bool = True, func: Callable | None = None):
        if func is None:
            func = self.default_func
        if self.is_connected[func] is value:
            if b_raise is True:
                if value:
                    raise RuntimeError(f"already connected {id(func)}")
                else:
                    raise RuntimeError(f"already disconnected {id(func)}")
        else:
            self._set_connect(func=func, value=value)
            self.is_connected[func] = value


class Object2ObjectLink(ConfigurableDict):
    ContainerConfigClass = (DictContainerConfig, ObjectSignal, LinkStateType)

    self: dict[LinkStateType, ObjectSignal] | Object2ObjectLink

    __getitem__: Callable[[], ObjectSignal]
    values: Callable[[], list[ObjectSignal]]

    def __init__(self, obj0, obj1,
                 key0, key1=None,
                 default_func0=None, default_func1=None,
                 signal0=None, signal1=None,
                 b_connect: bool = True,
                 data=None, container_conf=None, **kwargs):
        super().__init__(data=data, container_conf=container_conf)
        if key1 is None:
            key1 = key0

        if default_func0 is None:
            def default_func0(*args_, **kwargs_):
                self.default_call(
                    *args_, link_type=LinkStateType.SOURCE2SINK, **kwargs_)

        if default_func1 is None:
            def default_func1(*args_, **kwargs_):
                self.default_call(
                    *args_, link_type=LinkStateType.SINK2SOURCE, **kwargs_)

        self.setup(LinkStateType.SOURCE2SINK, obj=obj0, key=key0,
                   default_func=default_func0, signal=signal0, **kwargs)
        self.setup(LinkStateType.SINK2SOURCE, obj=obj1, key=key1,
                   default_func=default_func1, signal=signal1, **kwargs)
        if b_connect is True:
            self[LinkStateType.SOURCE2SINK].set_connect(value=True)
            self[LinkStateType.SINK2SOURCE].set_connect(value=True)

    def clear(self, b_force: bool = False) -> None:
        for v in self.values():
            v.clear(b_force=self.container_conf.b_clear_allowed or b_force)
        super().clear(b_force=b_force)

    def setup(self, link_type: LinkStateType, obj, key, signal=None, **kwargs):
        if signal is None:
            signal = ObjectSignal.from_key(key=key, obj=obj, **kwargs)
        self[link_type] = signal

    @property
    def source(self):
        return self[LinkStateType.SOURCE2SINK].obj

    @property
    def source_key(self):
        return self[LinkStateType.SOURCE2SINK].key

    @property
    def sink(self):
        return self[LinkStateType.SINK2SOURCE].obj

    @property
    def sink_key(self):
        return self[LinkStateType.SINK2SOURCE].key

    def _default_call(self, *args, link_type: LinkStateType, **kwargs):
        raise NotImplementedError

    def default_call(self, *args, link_type: LinkStateType, **kwargs):
        self[LinkStateType(not link_type)].set_connect(value=False)
        self._default_call(*args, link_type=link_type, **kwargs)
        self[LinkStateType(not link_type)].set_connect(value=True)


class ReplacedSetAttrMap(Many2OneObjectSingleTonMap):
    class ContainerConfigClass(Many2OneObjectMap.ContainerConfigClass):
        b_pop_allowed: bool = True
        allowed_types: Any = Callable

    # class InvertedConfigClass(Int2ObjectMapConfig):
    #     allowed_types: Any = Callable

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __setitem__(self, obj, func):
        super().__setitem__(obj, func)

    def reconnect(self, obj, b_pop=True):
        func = self[obj]
        name = func.__name__
        object.__setattr__(obj, name, func)
        if b_pop is True:
            self.container.pop(obj)


class Object2ObjectLinks(TypeSortedMap):

    sub_maps: tuple = ((str, Object2ObjectLink),
                       (Object2ObjectLink, str),)

    REGISTERED_IDS: ClassVar[ConfigurableList] = ConfigurableList()

    def __init__(self, source=None, sink=None, ext_obj_attr_map=None,
                 allowed_keys=None,
                 replaced_method_map=None,
                 **kwargs):
        super().__init__(**kwargs)
        
        self.source = source
        self.sink = sink
        self.ext_obj_attr_map: Object2ObjectMap | None = ext_obj_attr_map
        if replaced_method_map is None:
            # replaced_method_map = Many2OneObjectMap().from_types(type1=Callable)
            replaced_method_map = ReplacedSetAttrMap()
        self.replaced_method_map = replaced_method_map
        
        self.allowed_keys = allowed_keys

    def clear(self, b_force: bool = False):
        if self.source in self.replaced_method_map:
            self.replaced_method_map.reconnect(self.source)
        for link in self[str].values():
            link: Object2ObjectLink
            link.clear(b_force=b_force)
        super().clear(b_force=b_force,)

    def get_sub_map_by_type(
            self, link_type: LinkStateType) -> dict[str, Object2ObjectLink]:
        match link_type:
            case LinkStateType.SOURCE2SINK:
                if self.ext_obj_attr_map is None:
                    return self[str]
                else:
                    return self.ext_obj_attr_map
            case LinkStateType.SINK2SOURCE:
                return self[ObjectSignal].inv

    # @staticmethod
    # def set_object_attribute(self_, key, value, ):
    #     try:
    #         object.__setattr__(self_, key, value)
    #         # setattr(self_, key, value)
    #         if self_.__setattr__ != set_attr:
    #             # self_.__setattr__ = set_attr
    #             raise AssertionError
    #         try:
    #             link_map[key][LinkStateType.SOURCE2SINK].emit(value)
    #         except KeyError:
    #             pass
    #     except debug_catch as error:
    #         raise error

    def prepare_object(self, obj, link_type: LinkStateType,
                       b_allow_new: bool = False,
                       debug_catch=BaseException):

        link_map = self.get_sub_map_by_type(link_type)
        
        def set_attr(self_, key, value):

            if (b_allow_new is False) and (not hasattr(self_, key)):
                raise KeyError(key)
            try:
                # skip validation for BaseModels
                # object.__setattr__(self_, key, value)
                if isinstance(getattr(self_, key), SeriesModel):
                    setattr(getattr(self_, key), SeriesModel.Slots.DATA, value)
                else:
                    setattr(self_, key, value)
                if self_.__setattr__ != set_attr:
                    # self_.__setattr__ = set_attr
                    raise AssertionError
                try:
                    link_map[key][LinkStateType.SOURCE2SINK].emit(value)
                except KeyError:
                    pass
            except ValidationError:
                from snngine_v4.utils.list_parameter_model import \
                    ListParameterModel
                if isinstance(getattr(self_, key), ListParameterModel):
                    if isinstance(value, str):
                        setattr(getattr(self_, key), 'value', value)
                    else:
                        raise
                        setattr(getattr(self_, key), 'limits', value)
                    link_map[key][LinkStateType.SOURCE2SINK].emit(value)
                else:
                    raise
            except debug_catch as error:
                raise error

        if obj in self.replaced_method_map:
            if self.ext_obj_attr_map is None:
                raise AssertionError
        else:
            self.replaced_method_map[obj] = obj.__setattr__

        # TODO:
        if type(obj.__setattr__).__name__ != 'method':
            if self.ext_obj_attr_map is None:
                raise AssertionError
        # self.__class__.REGISTERED_IDS.append(id(obj))

        obj.__setattr__ = set_attr
        return

    # def add_attribute(self, key0, key1=None):
    #     self[key0] = Object2ObjectLink(
    #         key0=key0, key1=key1, obj0=self.source, obj1=self.sink)

    def __setitem__(self, key, link: Object2ObjectLink):
        if key != link.source_key:
            raise AssertionError
        super().__setitem__(link.source_key, link)
        super().__setitem__(link, link.sink_key)
