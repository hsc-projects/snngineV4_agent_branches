from typing import ClassVar, Type

from qtpy.QtWidgets import QDockWidget, QTreeWidget, QWidget

from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict,
    DictContainerConfig,
)


class QWidgetDictConfig(DictContainerConfig, frozen=True):
    allowed_types: Type[QWidget] = QWidget


class QWidgetDict(ConfigurableDict):
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
