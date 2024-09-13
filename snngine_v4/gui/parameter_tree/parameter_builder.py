from enum import Enum, IntEnum
from types import GenericAlias, UnionType

import numpy as np
import pandas as pd
from pydantic import BaseModel
import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.parametertree import Parameter
import typing_extensions

from snngine_v4.utils.settings.settings_keywords import (
    BaseSettingsSlots, ParameterUIOpts,
    PGParameterOptionKW,
)
from snngine_v4.gui.parameter_tree.parameters.spin_box_slider_parameter import \
    SpinBoxSliderParameter
from snngine_v4.gui.parameter_tree.signal_register import SignalMapRegister
from snngine_v4.utils.field_utils import (
    get_field_interval,
    get_field_json_schema_extra, get_field_multiple_of,
    get_type_from_annotation,
)
from snngine_v4.utils.interval_utils import linspace_from_interval


class ParameterBuilder:

    @classmethod
    def get_parameter_type(cls, parent_model: BaseModel, key):
        field_ = parent_model.model_fields[key]
        parameter_type = field_.annotation
        if isinstance(parameter_type, UnionType):
            parameter_type = typing_extensions.get_args(field_.annotation)[0]
        if issubclass(parameter_type, IntEnum):
            parameter_type = Enum
        return parameter_type

    @classmethod
    def make_par(cls, parent_model: BaseModel, key, value, **options):
        field_ = parent_model.model_fields[key]
        json_schema_extra = get_field_json_schema_extra(field_)

        if PGParameterOptionKW.NAME not in options:
            options[PGParameterOptionKW.NAME] = key

        options[PGParameterOptionKW.VALUE] = value
        options.update(json_schema_extra)

        parameter_type = cls.get_parameter_type(
            parent_model=parent_model, key=key)

        options[PGParameterOptionKW.TYPE] = parameter_type.__name__
        if parameter_type == Enum:
            options['enum'] = get_type_from_annotation(
                field_.annotation, _type=Enum)

        parameter_ = None

        if parameter_type in [float, int]:
            interval = get_field_interval(field_)
            multiple_of = get_field_multiple_of(field_)
            if (interval is not None) and (interval.length < np.inf):
                parameter_ = cls.make_slider_parameter(
                    interval=interval, value=value,
                    multiple_of=multiple_of,
                    **options)

        elif isinstance(parameter_type, GenericAlias):
            parameter_ = pTypes.GroupParameter(**options)
            args_ = typing_extensions.get_args(parameter_type)
            for i, t in enumerate(args_):
                options[PGParameterOptionKW.NAME] = str(i)
                options[PGParameterOptionKW.TYPE] = t.__name__
                if value is not None:
                    p_value = value[i]
                else:
                    p_value = None
                options[PGParameterOptionKW.VALUE] = p_value
                g_par = Parameter.create(**options)
                parameter_.addChild(g_par)

        # if parameter_ is None:
        #     # try:
        #     if issubclass(parameter_type, IntEnum):
        #         if PGParameterOptionKW.LIMITS not in options:
        #             # noinspection PyProtectedMember
        #             options[PGParameterOptionKW.LIMITS] = (
        #                 parameter_type._member_names_)
        #             options[PGParameterOptionKW.TYPE] = 'list'
        #         parameter_ = Parameter.create(**options)
        #     # except Exception as e:
        #     #     pass
        if parameter_ is None:
            parameter_ = Parameter.create(**options)
        return parameter_

    @classmethod
    def make_slider_parameter(
            cls, interval: pd.Interval, name, value,
            multiple_of=None, span=None, **options):
        if span is None:
            if multiple_of is None:
                n_steps_if_closed = 101
            else:
                n_steps_if_closed = int(interval.length / multiple_of) + 1
            span = linspace_from_interval(interval=interval,
                                          n_steps_if_closed=n_steps_if_closed,
                                          b_change_n_steps_if_open=True)
        parameter_ = SpinBoxSliderParameter(
            name=name, value=value, span=span, **options)
        return parameter_

    @classmethod
    def make_group(cls, model: BaseModel, name=None,
                   model_dict: dict[str, BaseModel] = None,):

        ui_opts = model_dict.get(ParameterUIOpts.UI_OPTIONS_KEYWORD, {})

        # noinspection PyTypedDict
        if model.model_config.get(BaseSettingsSlots.FROZEN, None):
            ui_opts[PGParameterOptionKW.READONLY] = True

        name = ui_opts.pop(PGParameterOptionKW.NAME,
                           model.__class__.__name__)
        if name is None:
            name = model.__class__.__name__

        g = pTypes.GroupParameter(name=name, **ui_opts)
        return g

    @classmethod
    def make_pars(cls, model, model_dict,
                  signal_register: SignalMapRegister = None,
                  name=None):

        group = cls.make_group(
            model, name=name, model_dict=model_dict)

        inherited_options = {
            PGParameterOptionKW.READONLY: group.readonly(),
            PGParameterOptionKW.RENAMABLE: group.opts.get(
                PGParameterOptionKW.RENAMABLE, True),
            PGParameterOptionKW.MOVABLE: group.opts.get(
                PGParameterOptionKW.MOVABLE, False),
        }

        for k, v in model_dict.items():
            if k not in [ParameterUIOpts.UI_OPTIONS_KEYWORD]:

                model_value = getattr(model, k)

                p_type = cls.get_parameter_type(parent_model=model, key=k)

                if ((not isinstance(p_type, GenericAlias))
                        and issubclass(p_type, BaseModel)):
                    par = cls.make_pars(
                        model=model_value, model_dict=v, name=k,
                        signal_register=signal_register)
                else:
                    par = cls.make_par(
                        parent_model=model, key=k, value=model_value,
                        **inherited_options)
                    if ((signal_register is not None)
                            and (BaseSettingsSlots.b_is_frozen(model)
                                 is False)):
                        signal_register.connect_parameter(
                            model, key_=k, parameter=par)
                group.addChild(par)
        return group
