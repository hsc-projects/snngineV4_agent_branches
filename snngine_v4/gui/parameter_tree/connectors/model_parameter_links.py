from __future__ import annotations

from typing import Callable, Iterable, Type

import pandas as pd
from pydantic import BaseModel, ValidationError
from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import GroupParameter, ListParameter

from qtpy import QtCore

from snngine_v4.gui.parameter_tree.connectors.object2object_links import (
    Object2ObjectLinks, ObjectSignal, LinkStateType, Object2ObjectLink,
)
from snngine_v4.gui.parameter_tree.parameters.multi_type_parameter import \
    MultiTypeParameter
from snngine_v4.utils.containers.super_maps import TypeSortedMap

from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


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
            self[link_type] = ObjectSignal(
                key=key,
                signal=self.get_parameter_signal(obj), obj=obj, **kwargs)

    def _default_call(self, *args, link_type: LinkStateType, **kwargs):
        match link_type:
            case LinkStateType.SOURCE2SINK:
                if args[0] != self.source:
                    raise AssertionError
                elif args[1] != self.source_key:
                    raise AssertionError
                value = args[2]
                print(f"Set parameter value '{self.source_key}'", value)
                self.sink.setValue(value)
            case LinkStateType.SINK2SOURCE:
                if args[0] != self.sink:
                    raise AssertionError
                value = self.sink.value()
                try:
                    # noinspection PyArgumentList
                    self.source.__setattr__(self.source, self.source_key, value)
                # except TypeError as err:
                #     if '__setattr__' in self.source.model_extra:
                #         self.source.__setattr__ = self.source.model_extra.pop(
                #             '__setattr__')
                #         self.source.__setattr__(self.source, self.source_key,
                #                                 value)
                #     else:
                #         raise err
                except ValidationError as err:
                    if (value is None) or pd.isna(value):
                        b_none_allowed = self.sink.opts.get(
                            ParamOpts.KW.C_NULLABLE_VALUE)
                        # noinspection PyArgumentList
                        self.source.__setattr__(
                            self.source, self.source_key, None)
                        pass
                    else:
                        raise err
                print(f"({self.source.__class__.__name__}, {id(self.source)}) "
                      f"Set '{self.source_key}' "
                      f"from parameter({id(self.sink)}):",
                      getattr(self.source, self.source_key))
            case _:
                raise TypeError(f"{link_type.name}")

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
            self[LinkStateType.SOURCE2SINK].signal.emit(
                self, self.source_key, value)


class ModelParameterLinks(Object2ObjectLinks):

    sub_maps: tuple = ((ObjectParameterLink, Parameter),
                       (str, ObjectParameterLink))

    __getitem__: Callable[[str | Type[str] | Type[ObjectParameterLink]],
                          dict[ObjectParameterLink, Parameter]
                          | dict[str, ObjectParameterLink]
                          | ObjectParameterLink | Parameter]

    def __init__(self, model, group_param=None, **kwargs):
        self.data: dict[int | BaseModel, Parameter] | None = None
        self.source: BaseModel | None = None
        self.sink: GroupParameter | None = None
        super().__init__(source=model, sink=group_param, **kwargs)

        self.prepare_object(
            obj=self.source, link_type=LinkStateType.SOURCE2SINK,
            debug_catch=ValidationError)
        if group_param is not None:
            self.add_parameter(group_param)

    def add_parameter(
            self, param: Parameter | GroupParameter):
        if (isinstance(param, GroupParameter)
                and (not isinstance(param, MultiTypeParameter))):
            # noinspection PyTypeChecker
            cs: list[Parameter] = param.children()
            for p in cs:
                if ((not isinstance(p, GroupParameter))
                        or isinstance(p, MultiTypeParameter)):
                    self.add_parameter(param=p)
        else:
            key = param.opts.get(ParamOpts.KW.C_MODEL_FIELD_NAME, None)
            link = ObjectParameterLink(
                key=key, parameter=param, obj=self.source)
            self[link] = link.sink

    def parameters(self) -> Iterable[Parameter]:
        return self[ObjectParameterLink].values()

    def __setitem__(self, link, parameter):
        TypeSortedMap.__setitem__(self, link, parameter)
        TypeSortedMap.__setitem__(self, link.source_key, link)
