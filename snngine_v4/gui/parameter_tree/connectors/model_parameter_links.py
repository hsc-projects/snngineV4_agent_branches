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
from snngine_v4.utils.containers.mappings import (
    Object2ObjectMap,
)
from snngine_v4.utils.containers.super_maps import TypeSortedMap

from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


# noinspection PyPep8Naming
class ObjectParameterLink(Object2ObjectLink):

    source: BaseModel
    sink: Parameter

    def __init__(self, key, obj=None, parameter=None,
                 signal0=None, signal1=None,):
        super().__init__(obj0=obj, obj1=parameter, key0=key,
                         signal0=signal0, signal1=signal1,)

    def setup(self, link_type: LinkStateType, obj, key, signal=None, **kwargs):
        if link_type == LinkStateType.SOURCE2SINK:
            super().setup(link_type=link_type, key=key, obj=obj,
                          signal=signal, **kwargs)
        else:
            if signal is None:
                signal = ObjectSignal(
                    key=key,
                    signal=self.get_parameter_signal(obj), obj=obj, **kwargs)
            self[link_type] = signal

    def _default_call(self, *args, link_type: LinkStateType, **kwargs):

        match link_type:

            case LinkStateType.SOURCE2SINK:
                if args[0] != self.source:
                    raise AssertionError
                elif args[1] != self.source_key:
                    raise AssertionError
                value = args[2]
                msg = f">> parameter"
                value_str = str(value)

                self.sink.setValue(value)
            case LinkStateType.SINK2SOURCE:
                if args[0] != self.sink:  # assert expected parameter
                    raise AssertionError
                value = self.sink.value()
                if value is None:
                    pass
                try:
                    # noinspection PyArgumentList
                    # setattr(self.source, self.source_key, value)
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
                        # noinspection PyArgumentList
                        self.source.__setattr__(
                            self.source, self.source_key, value)
                        raise err
                value_str = str(getattr(self.source, self.source_key))
                msg = f"<< parameter"
            case _:
                raise TypeError(f"{link_type.name}")

        source_name = f"[{self.source.__class__.__name__}].{self.source_key}"

        if self.source_key == 'pos_origin':
            pass

        if value_str != '':
            value_str = ': ' + value_str
        sink_name = self.sink.name()
        if sink_name.lower() == self.source_key.lower():
            sink_name = ''
        else:
            sink_name = " '" + sink_name + "'"

        print(source_name, msg + sink_name, value_str)
        # print(f"[{id(self.source)}]", f"({id(self.sink)})")

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

    __getitem__: (
            Callable[[str | ObjectParameterLink],
                     ObjectParameterLink | Parameter]
            |
            Callable[[Type[str] | Type[ObjectParameterLink]],
                     Object2ObjectMap]
            # | dict[str, ObjectParameterLink]
            # | dict[ObjectParameterLink, Parameter]]
    )

    def __init__(self, model, group_param=None, ext_obj_attr_map=None,
                 allowed_keys=None,
                 **kwargs):
        self.data: dict[int | BaseModel, Parameter] | None = None
        self.source: BaseModel | None = None
        self.sink: GroupParameter | None = None

        # from snngine_v4.visualization.config_models.vispy_camera_configs
        # import \
        #     TurnTableCameraParameters
        # if isinstance(model, TurnTableCameraParameters):
        #     pass

        super().__init__(source=model, sink=group_param,
                         allowed_keys=allowed_keys,
                         ext_obj_attr_map=ext_obj_attr_map, **kwargs)

        self.prepare_object(
            obj=self.source, link_type=LinkStateType.SOURCE2SINK,
            debug_catch=ValidationError)
        if group_param is not None:
            self.add_parameter(group_param)

    def add_parameter(
            self, param: Parameter | GroupParameter):
        if (isinstance(param, GroupParameter)
                and (not isinstance(param, MultiTypeParameter))):
            # noinspection PyTypeChecker,PydanticTypeChecker
            cs: list[Parameter] = param.children()
            for p in cs:
                b_add_parameter = ((not isinstance(p, GroupParameter))
                                   # or isinstance(p, ArrayDictParameter)
                                   or isinstance(p, MultiTypeParameter))
                if b_add_parameter:
                    # if isinstance(p, ArrayDictParameter):
                    self.add_parameter(param=p)
        else:
            key = param.opts.get(ParamOpts.KW.C_MODEL_FIELD_NAME, None)
            if key is None:
                if not isinstance(param, ListParameter):
                    raise RuntimeError
                key = param.opts[ParamOpts.KW.NAME]
            if hasattr(self.source, key):
                if ((self.ext_obj_attr_map is not None)
                        and (key in self.ext_obj_attr_map)):
                    signal0 = self.ext_obj_attr_map[key]
                else:
                    signal0 = None
                link = ObjectParameterLink(
                    key=key, parameter=param,
                    signal0=signal0,
                    obj=self.source)
                self[link] = link.sink
            elif ((self.allowed_keys is not None)
                  and (key not in self.allowed_keys)):
                pass
            else:
                raise KeyError(f"{key}")

    @property
    def linked_keys(self):
        return self[str].refs

    def parameters(self) -> Iterable[Parameter]:
        return self[ObjectParameterLink].values()

    def __setitem__(self, link, parameter):
        TypeSortedMap.__setitem__(self, link, parameter)
        if self.ext_obj_attr_map:
            self.ext_obj_attr_map[link.source_key] = link
        else:
            TypeSortedMap.__setitem__(self, link.source_key, link)
