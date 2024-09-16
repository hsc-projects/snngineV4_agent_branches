from dataclasses import dataclass, field
from typing import ClassVar, Type

from pydantic import BaseModel
from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import ListParameter

from snngine_v4.gui.parameter_tree.qt_attribute_emitter import (
    SetAttributeEmitterBase, SetAttributeEmitterMap,
)
from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict,
    DefaultDictContainerConfig,
)
from snngine_v4.utils.containers.configurable_list import (
    ConfigurableList,
)
from snngine_v4.utils.containers.mappings import ConfigurableIDListConfig


class ParameterMapConfig(DefaultDictContainerConfig, frozen=True):
    allowed_types: Type[Parameter] = Parameter


class ParameterMap(ConfigurableDict):
    CONTAINER_CONFIG_CLASS: ClassVar[Type[ParameterMapConfig]] = ParameterMapConfig

    @staticmethod
    def get_parameter_signal(parameter):
        if isinstance(parameter, ListParameter):
            return parameter.sigValueChanged
        else:
            return parameter.sigValueChanging


@dataclass
class ModelParameterSignals:
    model: BaseModel
    emitters: SetAttributeEmitterMap = field(default_factory=dict)
    parameters: ParameterMap = field(default_factory=ParameterMap)

    def __post_init__(self):
        def set_attr(self_, key, value):
            self.emitters[key].sigAttributeValueChanged.emit(self_, key, value)
            setattr(self.model, key, value)

        # TODO:
        self.model.__setattr__ = set_attr

    def add_connection(self, key, parameter: Parameter):

        if key == 'X':
            pass

        self.parameters[key] = parameter
        emitter = SetAttributeEmitterBase(parent=None)
        self.emitters[key] = emitter
        emitter.sigAttributeValueChanged.connect(self.set_parameter_value)

        def set_model_value(par, value):
            self.set_model_value(key, value, emitter=emitter)

        emitter.set_value_callable = set_model_value
        ParameterMap.get_parameter_signal(parameter).connect(set_model_value)

    def set_model_value(self, key, value, emitter):
        emitter.sigAttributeValueChanged.disconnect(self.set_parameter_value)
        self.model.__setattr__(self.model, key, value)
        if key == 'N':
            pass
        print(
            f"Set '{key}' from parameter:",
            getattr(self.model, key))
        emitter.sigAttributeValueChanged.connect(self.set_parameter_value)

    def set_parameter_value(self, obj, key, value):
        parameter = self.parameters[key]
        print(f"Set parameter value '{key}'", value)

        set_value_callable = self.emitters[key].set_value_callable

        ParameterMap.get_parameter_signal(parameter).disconnect(
            set_value_callable)
        parameter.setValue(value)
        ParameterMap.get_parameter_signal(parameter).connect(
            set_value_callable)


class SignalMapRegisterConfig(DefaultDictContainerConfig, frozen=True):
    allowed_types: Type[ModelParameterSignals] = ModelParameterSignals
    allowed_key_types: Type[int] = int
    b_duplicates_allowed: bool = False
    b_replace_allowed: bool = False
    b_pop_allowed: bool = False


class ConnectedModelListConfig(ConfigurableIDListConfig, frozen=True):
    allowed_types: Type[BaseModel] = BaseModel


class SignalMapRegister(ConfigurableDict):

    CONTAINER_CONFIG_CLASS: ClassVar = SignalMapRegisterConfig

    def __init__(self, **kwargs):
        self.data: dict[int, ModelParameterSignals] | None = None
        self.refs = ConfigurableList(
            container_conf=ConnectedModelListConfig())
        super().__init__(**kwargs)

    def connect_parameter(self, obj, key_, parameter: Parameter):
        if id(obj) not in self.data:
            self.data[id(obj)] = ModelParameterSignals(model=obj)
            self.refs.append(obj)

        self.data[id(obj)].add_connection(key=key_, parameter=parameter)

    def __getitem__(self, item):
        if not isinstance(item, int):
            item = id(item)
        return super().__getitem__(item)

    @property
    def connected_models(self):
        return self.refs
