from typing import ClassVar, Type

from qtpy import QtCore

from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict, DefaultDictContainerConfig,
)


class SetAttributeEmitterBase(QtCore.QObject):
    """
    Base class for emitting signals when attributes are set.
    """
    sigAttributeValueChanged = QtCore.Signal(object, str, object)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.set_value_callable = None


class SetAttributeEmitterMapConfig(DefaultDictContainerConfig, frozen=True):
    allowed_types: Type[SetAttributeEmitterBase] = SetAttributeEmitterBase


class SetAttributeEmitterMap(ConfigurableDict):
    CONTAINER_CONFIG_CLASS: ClassVar[Type[SetAttributeEmitterMapConfig]] = (
        SetAttributeEmitterMapConfig)
