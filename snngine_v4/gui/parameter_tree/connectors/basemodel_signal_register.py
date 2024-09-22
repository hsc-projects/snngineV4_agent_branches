from __future__ import annotations

from typing import Type

import pandas as pd
from pydantic import BaseModel, ValidationError
from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import GroupParameter, ListParameter
from qtpy import QtCore

from snngine_v4.gui.parameter_tree.parameter_builder import ParameterBuilder
from snngine_v4.utils.containers.configurable_dict import ConfigurableDict

from snngine_v4.utils.containers.mappings import (
    Int2ObjectMapConfig, Model2ObjectMap, Object2ObjectMap,
)
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


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


class ObjectParameterLink(SetAttributeEmitterBase):

    def __init__(self, key, obj=None, parameter=None, parent=None):
        super().__init__(key=key, parent=parent)
        self._obj = obj
        self._parameter = None
        self.parameter = parameter
        self.sigAttributeValueChanged.connect(self.set_parameter_value)

    @property
    def obj(self):
        return self._obj

    @obj.setter
    def obj(self, value):
        if self._obj is not None:
            raise AttributeError("obj already set")
        self._obj = value

    @property
    def parameter(self):
        return self._parameter

    @parameter.setter
    def parameter(self, value):
        if self._parameter is not None:
            raise AttributeError("parameter already set")
        self._parameter = value
        self.get_parameter_signal(self._parameter).connect(
            self.set_obj_attribute_from_parameter)

    def set_obj_attribute_from_parameter(self, p: Parameter, value):
        self.sigAttributeValueChanged.disconnect(self.set_parameter_value)

        try:
            self._obj.__setattr__(self._obj, self.key, value)
        except ValidationError as err:
            if (value is None) or pd.isna(value):
                b_none_allowed = p.opts.get(ParamOpts.KW.C_NULLABLE_VALUE)
                self._obj.__setattr__(self._obj, self.key, None)
                pass
            else:
                raise err

        print(f"Set '{self.key}' from parameter({id(p)}):",
              getattr(self._obj, self.key))
        self.sigAttributeValueChanged.connect(self.set_parameter_value)

    def set_parameter_value(self, link, key, value, b_block: bool = True,):
        print(f"Set parameter value '{key}'", value)
        if b_block:
            self.get_parameter_signal(self._parameter).disconnect(
                self.set_obj_attribute_from_parameter)
        self._parameter.setValue(value)
        if b_block:
            self.get_parameter_signal(self._parameter).connect(
                self.set_obj_attribute_from_parameter)

    @staticmethod
    def get_parameter_signal(parameter):
        if isinstance(parameter, ListParameter):
            return parameter.sigValueChanged
        else:
            return parameter.sigValueChanged
            # return parameter.sigValueChanging

    def attributeValueChanged(self, value):
        if ((value is None)
                and (self.parameter.opts.get(
                    ParamOpts.KW.C_NONE_MEANS_UNKNOWN, False) is True)):
            pass
        else:
            self.sigAttributeValueChanged.emit(self, self.key, value)


class ModelParameterLinks(Object2ObjectMap):

    class ContainerConfigClass(Int2ObjectMapConfig, frozen=True):
        allowed_types: Type[Parameter]

    class InvertedConfigClass(Int2ObjectMapConfig, frozen=True):
        allowed_types: Type[ObjectParameterLink]

    def __init__(self, model, group_parameter: GroupParameter | None = None,
                 **kwargs):
        self.model = model
        self.data: dict[int, Parameter] | None = None
        self.str_emitter_map: dict[str, ObjectParameterLink] = (
            ConfigurableDict.from_type(ObjectParameterLink))

        def set_attr(self_, key, value):
            try:
                setattr(self_, key, value)
            except ValidationError as err:
                raise err
            self.str_emitter_map[key].attributeValueChanged(value)

        # TODO:
        self.model.__setattr__ = set_attr
        super().__init__(**kwargs)

    def add_group_parameter(
            self, model, parameter: GroupParameter | None = None):
        # noinspection PyTypeChecker
        cs: list[Parameter] = parameter.children()
        for p in cs:
            if not isinstance(p, GroupParameter):
                self.add_parameter(model=model, param=p)

    def add_link(self, link: ObjectParameterLink):
        self[link] = link.parameter

    def add_parameter(self, model: BaseModel, param: Parameter):
        key = param.opts[ParamOpts.KW.C_MODEL_FIELD_NAME]
        self.add_link(
            ObjectParameterLink(key=key, parameter=param, obj=model))

    def __setitem__(self, link, parameter):
        super().__setitem__(link, parameter)
        self.str_emitter_map[link.key] = link


class ModelSignalRegister(Model2ObjectMap):

    class ContainerConfigClass(Int2ObjectMapConfig, frozen=True):
        allowed_types: Type[ModelParameterLinks]

    def __init__(self, **kwargs):
        self.data: dict[BaseModel, ModelParameterLinks] | None = None
        self.group_map: dict[BaseModel, GroupParameter] = (
            Model2ObjectMap.from_type(GroupParameter))
        super().__init__(**kwargs)

    def connect_parameter(self, model, parameter: Parameter):
        if model not in self:
            self[model] = ModelParameterLinks(model=model)
        self[model].add_parameter(parameter=parameter, obj=model)

    def connect_group_parameter(self, model, parameter: GroupParameter):
        if model not in self:
            self[model] = ModelParameterLinks(model=model)
            self.group_map[model] = parameter
        self[model].add_group_parameter(model=model, parameter=parameter)

    @property
    def connected_models(self):
        return self.refs

    def get_parameters_by_type(
        self, model_type: Type[BaseModel],
        ancestor: GroupParameter | BaseModel | None = None,
    ):
        return ParameterBuilder.get_parameters_by_type(
            model_type=model_type, signal_register=self,
            ancestor=ancestor)

    def move_parameters_by_type(
        self, model_type: Type[BaseModel],
        new_parent: GroupParameter | BaseModel,
        ancestor: GroupParameter | BaseModel | None = None,
    ):
        pars = self.get_parameters_by_type(
            model_type=model_type, ancestor=ancestor)
        if isinstance(new_parent, BaseModel):
            new_parent = self.group_map[new_parent]
        for p in pars:
            new_parent.addChild(p, autoIncrementName=True)
