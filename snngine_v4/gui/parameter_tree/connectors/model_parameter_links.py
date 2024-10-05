from __future__ import annotations

import pandas as pd
from pydantic import BaseModel, ValidationError
from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import GroupParameter, ListParameter

from qtpy import QtCore

from snngine_v4.gui.parameter_tree.connectors.object2object_links import \
    (
    LinkState, LinkStateType, Object2ObjectLink, SetAttributeEmitterBase,
)
from snngine_v4.gui.parameter_tree.parameters.multi_type_parameter import \
    MultiTypeParameter
from snngine_v4.utils.containers.super_maps import TypeSortedMap

from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


# class ObjectParameterLink(SetAttributeEmitterBase):
#
#     def __init__(self, key, obj=None, parameter=None, parent=None):
#         super().__init__(key=key, parent=parent)
#         self._obj = obj
#         self._parameter_connected = False
#         self._attribute_connected = False
#         self._parameter = None
#         self.parameter = parameter
#         self.connect_attribute()
#
#     def connect_attribute(self, b_raise: bool = True):
#         if (self._attribute_connected is True) and (b_raise is True):
#             raise RuntimeError
#         self._attribute_connected = True
#         self.sigAttributeValueChanged.connect(self.set_parameter_value)
#
#     def connect_parameter(self, b_raise: bool = True):
#         if (self._parameter_connected is True) and (b_raise is True):
#             raise RuntimeError
#         self._parameter_connected = True
#         self.get_parameter_signal(self._parameter).connect(
#             self.set_obj_attribute_from_parameter)
#
#     def disconnect_attribute(self, b_raise: bool = True):
#         if (self._attribute_connected is False) and (b_raise is True):
#             raise RuntimeError
#         self._attribute_connected = False
#         self.sigAttributeValueChanged.disconnect(self.set_parameter_value)
#
#     def disconnect_parameter(self, b_raise: bool = True):
#         if (self._parameter_connected is False) and (b_raise is True):
#             raise RuntimeError
#         self._parameter_connected = False
#         self.get_parameter_signal(self._parameter).disconnect(
#             self.set_obj_attribute_from_parameter)
#
#     @property
#     def obj(self):
#         return self._obj
#
#     @obj.setter
#     def obj(self, value):
#         if self._obj is not None:
#             raise AttributeError("obj already set")
#         self._obj = value
#
#     @property
#     def parameter(self):
#         return self._parameter
#
#     @parameter.setter
#     def parameter(self, value):
#         if self._parameter is not None:
#             raise AttributeError("parameter already set")
#         self._parameter = value
#         self.connect_parameter()
#
#     def set_obj_attribute_from_parameter(self, p: Parameter, value):
#         self.disconnect_attribute()
#
#         try:
#             self._obj.__setattr__(self._obj, self.key, value)
#         except ValidationError as err:
#             if (value is None) or pd.isna(value):
#                 b_none_allowed = p.opts.get(ParamOpts.KW.C_NULLABLE_VALUE)
#                 self._obj.__setattr__(self._obj, self.key, None)
#                 pass
#             else:
#                 raise err
#
#         print(f"Set '{self.key}' from parameter({id(p)}):",
#               getattr(self._obj, self.key))
#         self.connect_attribute()
#
#     def set_parameter_value(self, link, key, value, b_block: bool = True,):
#         print(f"Set parameter value '{key}'", value)
#         if b_block:
#             self.disconnect_parameter()
#         self._parameter.setValue(value)
#         if b_block:
#             self.connect_parameter()
#
#     @staticmethod
#     def get_parameter_signal(parameter) -> QtCore.Signal:
#         if isinstance(parameter, ListParameter):
#             return parameter.sigValueChanged
#         else:
#             return parameter.sigValueChanged
#             # return parameter.sigValueChanging
#
#     def attributeValueChanged(self, value):
#         if ((value is None)
#                 and (self.parameter.opts.get(
#                     ParamOpts.KW.C_NONE_MEANS_UNKNOWN, False) is True)):
#             pass
#         else:
#             self.sigAttributeValueChanged.emit(self, self.key, value)


# noinspection PyPep8Naming
class ObjectParameterLink(Object2ObjectLink):

    source: BaseModel
    sink: Parameter

    def __init__(self, key, obj=None, parameter=None):
        super().__init__(obj0=obj, obj1=parameter, key0=key)

    def setup(self, link_type: LinkStateType, obj, key, **kwargs):
        if link_type == LinkStateType.SOURCE2SINK:
            super().setup(link_type=link_type, key=key, obj=obj, **kwargs)
        else:
            self[link_type] = LinkState(
                signal=self.get_parameter_signal(obj), obj=obj, **kwargs)

    @property
    def key(self):
        return self[LinkStateType.SOURCE2SINK].key

    def _default_call(self, *args, link_type: LinkStateType, **kwargs):
        match link_type:
            case LinkStateType.SOURCE2SINK:
                if args[0] != self:
                    raise AssertionError
                elif args[1] != self.key:
                    raise AssertionError
                value = args[2]
                print(f"Set parameter value '{self.key}'", value)
                self.sink.setValue(value)
            case LinkStateType.SINK2SOURCE:
                if args[0] != self.sink:
                    raise AssertionError
                value = self.sink.value()
                try:
                    self.source.__setattr__(self.source, self.key, value)
                except ValidationError as err:
                    if (value is None) or pd.isna(value):
                        b_none_allowed = self.sink.opts.get(
                            ParamOpts.KW.C_NULLABLE_VALUE)
                        self.source.__setattr__(self.source, self.key, None)
                        pass
                    else:
                        raise err
                print(f"Set '{self.key}' from parameter({id(self.sink)}):",
                      getattr(self.source, self.key))

    @staticmethod
    def get_parameter_signal(parameter) -> QtCore.Signal:
        if isinstance(parameter, ListParameter):
            return parameter.sigValueChanged
        else:
            return parameter.sigValueChanged
            # return parameter.sigValueChanging

    def attributeValueChanged(self, value):
        if ((value is None)
                and (self.sink.opts.get(
                    ParamOpts.KW.C_NONE_MEANS_UNKNOWN, False) is True)):
            pass
        else:
            self[LinkStateType.SOURCE2SINK].signal.emit(self, self.key, value)


class ModelParameterLinks(TypeSortedMap):

    sub_maps: tuple = ((ObjectParameterLink, Parameter),
                       (str, ObjectParameterLink))

    # __getitem__: Callable[str, ObjectParameterLink | Parameter]

    def __init__(self, model, **kwargs):
        self.model = model
        self.data: dict[int, Parameter] | None = None

        def set_attr(self_, key, value):
            try:
                setattr(self_, key, value)
            except ValidationError as err:
                raise err
            self[key].attributeValueChanged(value)

        # TODO:
        self.model.__setattr__ = set_attr
        super().__init__(**kwargs)

    def add_group_parameter(
            self, model, parameter: GroupParameter | None = None):
        # noinspection PyTypeChecker
        cs: list[Parameter] = parameter.children()
        for p in cs:

            if ((not isinstance(p, GroupParameter))
                    or isinstance(p, MultiTypeParameter)):
                self.add_parameter(model=model, param=p)

    def add_link(self, link: ObjectParameterLink):
        self[link] = link.sink

    def add_parameter(self, model: BaseModel, param: Parameter):
        key = param.opts[ParamOpts.KW.C_MODEL_FIELD_NAME]
        self.add_link(
            ObjectParameterLink(key=key, parameter=param, obj=model))

    def clear(self, b_force: bool = False):

        for link in self[str].values():
            link: ObjectParameterLink
            link.disconnect_attribute(b_raise=True)
        super().clear(b_force=b_force,)

    def __setitem__(self, link, parameter):
        super().__setitem__(link, parameter)
        super().__setitem__(link.key, link)
