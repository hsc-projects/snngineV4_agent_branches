from dataclasses import dataclass, field
from typing import ClassVar, Type

from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import ListParameter
from qtpy import QtCore

from snngine_v4.utils.containers.configurable_container import ContainerConfig
from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict,
    DefaultDictContainerConfig,
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
    allowed_key_types: Type[str] = str


class SetAttributeEmitterMap(ConfigurableDict):
    CONFIG_CLASS: ClassVar[Type[SetAttributeEmitterMapConfig]] = (
        SetAttributeEmitterMapConfig)

    def __init__(self, initdict=None):
        self.data: dict[int, Parameter] | None = None
        super().__init__(initdict=initdict)


class ParameterMapConfig(DefaultDictContainerConfig, frozen=True):
    allowed_types: Type[Parameter] = Parameter
    allowed_key_types: Type[str] = str


class ParameterMap(ConfigurableDict):
    CONFIG_CLASS: ClassVar[Type[ParameterMapConfig]] = ParameterMapConfig

    def __init__(self, initdict=None):
        self.data: dict[int, Parameter] | None = None
        super().__init__(initdict=initdict)


@dataclass
class SignalMapItem:
    emitters: SetAttributeEmitterMap = field(default_factory=dict)
    parameters: ParameterMap = field(default_factory=ParameterMap)

    def add_connection(self, key, parameter: Parameter):
        self.parameters[key] = parameter
        self.emitters[key] = SetAttributeEmitterBase(parent=None)


class SignalMapRegister(ConfigurableDict):

    def __init__(self, initdict=None):
        self.data: dict[int, SignalMapItem] | None = None
        super().__init__(
            initdict=initdict,
            container_conf=ContainerConfig(
                allowed_types=SignalMapItem,
                b_replace_allowed=False,
                b_duplicates_allowed=False))

    def connect_parameter(self, obj, key_, parameter: Parameter):
        if id(obj) not in self.data:
            self.data[id(obj)] = SignalMapItem()

        def set_attr(self_, key, value):
            (self.get_sigAttributeValueChanged(obj, key)
             .emit(self_, key, value))
            setattr(obj, key, value)

        obj.__setattr__ = set_attr

        self.data[id(obj)].add_connection(
            key=key_, parameter=parameter)

        signal = self.get_sigAttributeValueChanged(obj, key_)
        signal.connect(self.set_parameter_value)

        def set_model_value(par, value):
            signal.disconnect(self.set_parameter_value)
            obj.__setattr__(obj, key_, value)
            print(f"Set '{key_}' from parameter:",
                  getattr(obj, key_))
            signal.connect(self.set_parameter_value)

        emitter = self.get_emitter(obj, key_)
        emitter.set_model_value_callable = set_model_value
        self.get_parameter_signal(parameter).connect(set_model_value)

    def get_emitters(self, obj):
        return self.data[id(obj)].emitters

    def get_emitter(self, model_instance, key):
        return self.get_emitters(model_instance)[key]

    # noinspection PyPep8Naming
    def get_sigAttributeValueChanged(self, obj, key):
        return self.get_emitter(obj, key).sigAttributeValueChanged

    def get_parameter(self, model, key) -> Parameter:
        return self.data[id(model)].parameters[key]

    @staticmethod
    def get_parameter_signal(parameter):
        if isinstance(parameter, ListParameter):
            return parameter.sigValueChanged
        else:
            return parameter.sigValueChanging

    def set_parameter_value(self, obj, key, value):
        parameter = self.get_parameter(obj, key)
        print(f"Set parameter value '{key}'", value)

        set_value_callable = (self.get_emitter(obj, key)
                              .set_value_callable)
        self.get_parameter_signal(parameter).disconnect(set_value_callable)
        parameter.setValue(value)
        self.get_parameter_signal(parameter).connect(set_value_callable)
