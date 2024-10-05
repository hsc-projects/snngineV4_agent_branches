from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from functools import cached_property
from typing import Any, Callable, Type

from pydantic import BaseModel, computed_field, Field
from qtpy import QtCore

from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict,
    DictContainerConfig,
)


class SetAttributeEmitterBase(QtCore.QObject):
    """
    Base class for emitting signals when attributes are set.
    """
    sigAttributeValueChanged = QtCore.Signal(object, str, object)

    def __init__(self, key, parent=None):
        self.key = key
        super().__init__(parent=parent)

    # noinspection PyPep8Naming
    def attributeValueChanged(self, value):
        self.sigAttributeValueChanged.emit(self, self.key, value)


class LinkStateType(IntEnum):
    SOURCE2SINK = 0
    SINK2SOURCE = 1


@dataclass
class BoolValue:
    value: bool
    # history: list = field(default_factory=list)


class CallableDict(ConfigurableDict):

    class ContainerConfigClass(DictContainerConfig):
        allowed_key_types: Any = Callable


class LinkState(BaseModel, arbitrary_types_allowed=True,
                extra='forbid'
                ):
    key: str | None = None
    signal: Any | QtCore.Signal
    emitter: Any | None = None
    obj: Any = None
    default_func: Callable | None = None

    @computed_field
    @cached_property
    def connected(self) -> dict[Callable, bool] | ConfigurableDict:
        conn = CallableDict.from_type(type_=BoolValue)
        conn[self.default_func] = BoolValue(False)
        return conn

    def __call__(self, *args, **kwargs):
        return self.default_func(*args, **kwargs)

    @classmethod
    def from_key(cls, key, **kwargs):
        emitter = SetAttributeEmitterBase(key)
        new = cls(key=key, emitter=emitter,
                  signal=emitter.sigAttributeValueChanged, **kwargs)
        return new

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
        if self.connected[func].value is value:
            if b_raise is True:
                raise RuntimeError
        else:
            self._set_connect(func=func, value=value)
            self.connected[func].value = value
            # self.connected[func].history.append(value)


class Object2ObjectLink(ConfigurableDict):
    ContainerConfigClass = (DictContainerConfig, LinkState, LinkStateType)

    self: dict[LinkStateType, LinkState]

    __getitem__: Callable[[], LinkState]

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

    def setup(self, link_type: LinkStateType, obj, key, **kwargs):
        self[link_type] = LinkState.from_key(key=key, obj=obj, **kwargs)

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
