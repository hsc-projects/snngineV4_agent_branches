from typing import ClassVar, Type

from qtpy import QtCore
from qtpy.QtWidgets import QDockWidget, QTreeWidget, QWidget

from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict,
    DictContainerConfig,
)


class QObjectDictSignals(QtCore.QObject):
    sigAdded = QtCore.Signal(object, object, object)
    sigRemoved = QtCore.Signal(object, object, object)
    sigReplaced = QtCore.Signal(object, object, object)

    def qobject__setitem__(self, key, value):
        b_key_exists = key in self
        old_value = None
        if b_key_exists:
            old_value = self[key]
        # setitem(self, key, value)
        mro = self.__class__.mro()
        mro[mro.index(QObjectDict) + 1].__setitem__(self, key, value)
        self.sigAdded.emit(self, key, value)
        if b_key_exists:
            self.sigReplaced.emit(self, key, old_value)

    def qobject__pop(self, key):
        value = super().pop(key)
        self.sigRemoved.emit(self, key, value)
        return value


class QObjectDict(ConfigurableDict):

    def __init__(self, *arg, **kwargs):
        self.emitter = QObjectDictSignals(parent=None)
        self.sigAdded = self.emitter.sigAdded
        self.sigRemoved = self.emitter.sigRemoved
        self.sigReplaced = self.emitter.sigReplaced
        super().__init__(*arg, **kwargs)

    __setitem__ = QObjectDictSignals.qobject__setitem__
    pop = QObjectDictSignals.qobject__pop


class QWidgetDictConfig(DictContainerConfig, frozen=True):
    allowed_types: Type[QWidget] = QWidget


class QWidgetDict(QObjectDict):
    ContainerConfigClass: ClassVar[Type[QWidgetDictConfig]] = QWidgetDictConfig

    def add_widget(self, widget: QWidget):
        name = widget.objectName()
        self[name] = widget


class QTreeWidgetDictConfig(QWidgetDictConfig, frozen=True):
    allowed_types: Type[QTreeWidget] = QTreeWidget


class QTreeWidgetDict(QWidgetDict):
    ContainerConfigClass: ClassVar[Type[QTreeWidgetDictConfig]] = (
        QTreeWidgetDictConfig)


class QDockWidgetDictConfig(QWidgetDictConfig, frozen=True):
    allowed_types: Type[QDockWidget] = QDockWidget


class QDockWidgetDict(QWidgetDict):
    CONFIG_CLASS: ClassVar[Type[QDockWidgetDictConfig]] = QDockWidgetDictConfig
