from typing import ClassVar, Type

from qtpy import QtCore
from qtpy.QtWidgets import QDockWidget, QTreeWidget, QWidget

from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict,
    DictContainerConfig,
)


class QObjectDictSignals(QtCore.QObject):

    sigAdded = QtCore.Signal(object, object, object)
    sigChanged = QtCore.Signal(object, object)
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

    def __init__(self, *arg, emitter=None, **kwargs):
        self.emitter = emitter or QObjectDictSignals(parent=None)
        self.sigAdded = self.emitter.sigAdded
        self.sigChanged = self.emitter.sigRemoved
        self.sigRemoved = self.emitter.sigRemoved
        self.sigReplaced = self.emitter.sigReplaced
        super().__init__(*arg, **kwargs)

    __setitem__ = QObjectDictSignals.qobject__setitem__
    pop = QObjectDictSignals.qobject__pop

    def onSigChanged(self, key, value):
        raise NotImplementedError


class QWidgetDictConfig(DictContainerConfig, frozen=True):
    allowed_types: Type[QWidget] = QWidget
    allowed_key_types: Type[str] = str


class QWidgetDict(QObjectDict):

    ContainerConfigClass: ClassVar[Type[QWidgetDictConfig]] = QWidgetDictConfig

    def add_widget(self, widget: QWidget):
        if str in self.container_conf.allowed_key_types:
            name = widget.objectName()
            self[name] = widget
        else:
            raise NotImplementedError

    def add_widgets(self, *widgets: QWidget):
        for w in widgets:
            self.add_widget(w)

    def widget(self):
        raise NotImplementedError


class QTreeWidgetDict(QWidgetDict):
    ContainerConfigClass: ClassVar = (QWidgetDictConfig, QTreeWidget)


class QDockWidgetDict(QWidgetDict):
    ContainerConfigClass: ClassVar = (QWidgetDictConfig, QDockWidget)
