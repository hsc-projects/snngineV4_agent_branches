from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from functools import cached_property
from typing import Any, Callable, Type

from pydantic import BaseModel, computed_field
from qtpy import QtCore

from snngine_v4.utils.containers.configurable_dict import (
    CallableKeyDict, ConfigurableDict,
    DictContainerConfig,
)
from snngine_v4.utils.containers.super_maps import TypeSortedMap


class SetAttributeEmitterBase(QtCore.QObject):
    """
    Base class for emitting signals when attributes are set.
    """
    sigAttributeValueChanged = QtCore.Signal(object, str, object)

    # def __init__(self, key, parent=None):
    #     self.key = key
    #     super().__init__(parent=parent)
    #
    # # noinspection PyMethodOverriding
    # def emit(self, value):
    #     self.sigAttributeValueChanged.emit(self, self.key, value)


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
    signal: Any | QtCore.Signal
    emitter: Any | None = None
    obj: Any = None
    default_func: Callable | None = None

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
                raise RuntimeError
        else:
            self._set_connect(func=func, value=value)
            self.is_connected[func] = value


class Object2ObjectLink(ConfigurableDict):
    ContainerConfigClass = (DictContainerConfig, ObjectSignal, LinkStateType)

    self: dict[LinkStateType, ObjectSignal]

    __getitem__: Callable[[], ObjectSignal]
    values: Callable[[], list[ObjectSignal]]

    def __init__(self, obj0, obj1,
                 key0, key1=None,
                 default_func0=None, default_func1=None,
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
                   default_func=default_func0, **kwargs)
        self.setup(LinkStateType.SINK2SOURCE, obj=obj1, key=key1,
                   default_func=default_func1, **kwargs)
        if b_connect is True:
            self[LinkStateType.SOURCE2SINK].set_connect(value=True)
            self[LinkStateType.SINK2SOURCE].set_connect(value=True)

    def clear(self, b_force: bool = False) -> None:
        for v in self.values():
            v.clear(b_force=self.container_conf.b_clear_allowed or b_force)
        super().clear(b_force=b_force)

    def setup(self, link_type: LinkStateType, obj, key, **kwargs):
        self[link_type] = ObjectSignal.from_key(key=key, obj=obj, **kwargs)

    @property
    def source(self):
        return self[LinkStateType.SOURCE2SINK].obj

    @property
    def sink(self):
        return self[LinkStateType.SINK2SOURCE].obj

    def _default_call(self, *args, link_type: LinkStateType, **kwargs):
        raise NotImplementedError

    def default_call(self, *args, link_type: LinkStateType, **kwargs):
        self[LinkStateType(not link_type)].set_connect(value=False)
        self._default_call(*args, link_type=link_type, **kwargs)
        self[LinkStateType(not link_type)].set_connect(value=True)


class Object2ObjectLinks(TypeSortedMap):

    sub_maps: tuple = ((str, Object2ObjectLink), (Object2ObjectLink, str),)

    def __init__(self, source=None, sink=None, **kwargs):
        super().__init__(**kwargs)
        self.source = source
        self.sink = sink

    def get_sub_map_by_type(
            self, link_type: LinkStateType) -> dict[str, Object2ObjectLink]:
        match link_type:
            case LinkStateType.SOURCE2SINK:
                return self[str]
            case LinkStateType.SINK2SOURCE:
                return self[ObjectSignal].inv

    def prepare_object(self, obj, link_type: LinkStateType,
                       debug_catch=BaseException):

        link_map = self.get_sub_map_by_type(link_type)

        def set_attr(self_, key, value):
            try:
                setattr(self_, key, value)
                link_map[key][LinkStateType.SOURCE2SINK].emit(value)
            except debug_catch as error:
                raise error
        # TODO:
        obj.__setattr__ = set_attr
