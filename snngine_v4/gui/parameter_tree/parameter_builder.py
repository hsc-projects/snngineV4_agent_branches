from __future__ import annotations

import copy
from copy import deepcopy
from enum import Enum, IntEnum
from types import GenericAlias, UnionType
from typing import Type, TYPE_CHECKING

import numpy as np
import pandas as pd

from pydantic import BaseModel

from pyqtgraph.parametertree import Parameter
import typing_extensions
from pyqtgraph.parametertree.parameterTypes import GroupParameter

from snngine_v4.gui.parameter_tree.parameters.engine_group_parameter import \
    EngineGroupParameter
from snngine_v4.utils.core_utils import IntervalClosedType
from snngine_v4.utils.settings.settings_keywords import (
    BaseSettingsSlots, ParamOpts,
    PGParOption,
)
from snngine_v4.gui.parameter_tree.parameters.spin_box_slider_parameter import \
    SpinBoxSliderParameter

from snngine_v4.utils.field_utils import (
    b_is_int_annotation, get_field_interval,
    get_field_json_schema_extra, get_field_multiple_of,
    extract_type_from_annotation,
)
from snngine_v4.utils.interval_utils import (
    limits_from_interval,
    linspace_from_interval,
)
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel

if TYPE_CHECKING:
    from snngine_v4.gui.parameter_tree.connectors \
        .basemodel_signal_register import ModelSignalRegister


class ParameterBuilder:

    @classmethod
    def get_parameter_type(cls, parent_model: BaseModel, key):
        if key in parent_model.model_fields:
            field_ = parent_model.model_fields[key]
            parameter_type = field_.annotation
            if isinstance(parameter_type, UnionType):
                parameter_type = typing_extensions.get_args(field_.annotation)[0]
            elif issubclass(parameter_type, IntEnum):
                parameter_type = Enum
            return parameter_type
        elif key in parent_model.model_extra:
            model_value = getattr(parent_model, key)
            if (isinstance(model_value, dict)
                    and isinstance(parent_model, XMLSettingsModel)):
                model_type = parent_model.model_interpret_dict_type(
                    dct=model_value)
                if model_type:
                    return model_type
            return type(model_value)

    @classmethod
    def make_group_from_model(cls, model: BaseModel, name=None,
                              model_dict: dict[str, BaseModel] = None, ):

        parameter_ui_opts = getattr(model, ParamOpts.UI_OPTIONS_KEYWORD,
                                    {})
        if parameter_ui_opts is None:
            parameter_ui_opts = {}
        elif isinstance(parameter_ui_opts, BaseModel):
            parameter_ui_opts = parameter_ui_opts.model_dump()

        if PGParOption.RENAMABLE not in parameter_ui_opts:
            parameter_ui_opts[PGParOption.RENAMABLE] = False

        # noinspection PyTypedDict
        if model.model_config.get(BaseSettingsSlots.FROZEN, None):
            parameter_ui_opts[PGParOption.READONLY] = True

        ui_name = parameter_ui_opts.pop(PGParOption.NAME, None)
        if ui_name is not None:
            name = ui_name
        elif name is None:
            name = model.__class__.__name__

        if PGParOption.PREFIX in parameter_ui_opts:
            prefix_pattern = parameter_ui_opts[PGParOption.PREFIX]
            if isinstance(prefix_pattern, str):
                sep = ParamOpts.PREFIX_PATTERN_SEP
                prefix_pattern = prefix_pattern.split(sep)
                parameter_ui_opts[PGParOption.PREFIX] = prefix_pattern
        else:
            parameter_ui_opts[PGParOption.PREFIX] = []

        g = EngineGroupParameter(name=name, **parameter_ui_opts)
        return g

    @classmethod
    def make_par(cls, parent_model: BaseModel, key, value, signal_register,
                 model_dict_value,
                 **options):

        if key == 'fov':
            pass

        field_ = parent_model.model_fields[key]
        json_schema_extra = get_field_json_schema_extra(field_)

        if PGParOption.NAME not in options:
            options[PGParOption.NAME] = key

        options[PGParOption.VALUE] = value
        options.update(json_schema_extra)

        parameter_type = cls.get_parameter_type(
            parent_model=parent_model, key=key)

        options[PGParOption.TYPE] = parameter_type.__name__
        if parameter_type == Enum:
            options['enum'] = extract_type_from_annotation(
                field_.annotation, _type=Enum)

        parameter_ = None

        options[PGParOption.CUSTOM_MODEL_FIELD_NAME] = key

        if PGParOption.PREFIX in options:
            prefix = options[PGParOption.PREFIX]
            if isinstance(prefix, list):
                name = options[PGParOption.NAME]
                if name in prefix:
                    options[PGParOption.PREFIX] = name + ': '
                else:
                    options[PGParOption.PREFIX] = ''

        if parameter_type in [float, int]:
            if key == 'distance':
                pass
            parameter_ = cls._make_numeric_par(field_=field_, **options)

        elif isinstance(parameter_type, GenericAlias):

            parameter_ = cls._make_pars_from_iterable(
                parameter_type=parameter_type, model_value=value,
                model_dict_value=model_dict_value,
                signal_register=signal_register, **options)

        if parameter_ is None:
            parameter_ = Parameter.create(**options)

        # if ((signal_register is not None)
        #         and (BaseSettingsSlots.b_is_frozen(parent_model)
        #              is False)):
        #     signal_register.connect_parameter(
        #         parent_model, key=key, parameter=parameter_)

        return parameter_

    @classmethod
    def _make_numeric_par(cls, field_, **options):
        interval = get_field_interval(field_)
        multiple_of = get_field_multiple_of(field_)

        if multiple_of is not None:
            step_size = multiple_of
        else:
            is_int = b_is_int_annotation(field_.annotation, True)
            if is_int:
                step_size = options.get(PGParOption.STEP, 1)
            else:
                step_size = options.get(PGParOption.STEP, .01)
                options[PGParOption.DECIMALS] = 6
        options[PGParOption.STEP] = step_size
        if interval is not None:
            # interval = get_field_interval(field_)
            limits = limits_from_interval(interval, step_size=step_size)
            options[PGParOption.LIMITS] = limits
        if interval is not None:
            parameter_ = cls.make_slider_parameter(
                interval=interval, step_size=step_size,
                **options)
        else:
            parameter_ = Parameter.create(**options)
        return parameter_

    @classmethod
    def _par_from_item_from_iterable(
            cls, idx, par_type, model_value, **options):
        options = copy.copy(options)
        options[PGParOption.NAME] = str(idx)
        options[PGParOption.TYPE] = par_type.__name__
        if model_value is not None:
            p_value = model_value[idx]
        else:
            p_value = None
        options[PGParOption.VALUE] = p_value
        par = Parameter.create(**options)
        return par

    @classmethod
    def _make_pars_from_iterable(
            cls, parameter_type, model_value, model_dict_value,
            signal_register, **options):

        parameter_ = EngineGroupParameter(**options)
        iterable_type = typing_extensions.get_origin(parameter_type)

        if iterable_type == tuple:
            args_ = typing_extensions.get_args(parameter_type)
            for i, t in enumerate(args_):
                g_par = cls._par_from_item_from_iterable(
                    idx=i, par_type=t, model_value=model_value,
                    **options)
                parameter_.addChild(g_par)
        elif iterable_type == list:
            if model_value is None:
                pass
            else:

                t_args_ = typing_extensions.get_args(parameter_type)
                if len(t_args_) != 1:
                    raise NotImplementedError("len(t_args_) != 1")
                t_arg0 = t_args_[0]
                if isinstance(t_arg0, UnionType):
                    t_args = typing_extensions.get_args(t_arg0)
                else:
                    t_args = [t_arg0]

                for i, v in enumerate(model_value):
                    g_par = None
                    for t in t_args:

                        if (issubclass(t, BaseModel)
                                and isinstance(model_dict_value[i], dict)):
                            name = model_value[i].__class__.__name__ + str(i)
                            g_par = cls.make_pars_from_model(
                                model=model_value[i],
                                model_dict=model_dict_value[i], name=name,
                                signal_register=signal_register)
                            pass
                            break
                        elif isinstance(v, t):
                            g_par = cls._par_from_item_from_iterable(
                                idx=i, par_type=t, model_value=model_value,
                                **options)
                            break

                    parameter_.addChild(g_par)
        else:
            raise NotImplementedError(f"{iterable_type}")
        return parameter_

    @classmethod
    def make_slider_parameter(
            cls, interval: pd.Interval, name, value,
            step_size=None, span=None, **options):

        if span is None:
            if interval.length == np.inf:
                if step_size is None:
                    step_size = 1
                offset = 1000 * step_size

                if abs(value) * 9 < offset:
                    ref_value = 0
                else:
                    ref_value = value
                if interval.left == -np.inf:

                    if interval.right == np.inf:
                        interval = pd.Interval(ref_value - offset,
                                               ref_value + offset,
                                               closed='neither')
                    else:
                        if interval.closed in ['left', 'neither']:
                            closed: IntervalClosedType = 'left'
                        else:
                            closed = 'both'
                        interval = pd.Interval(ref_value - offset,
                                               interval.right,
                                               closed=closed)
                elif interval.right == np.inf:
                    if interval.closed in ['right', 'neither']:
                        closed: IntervalClosedType = 'right'
                    else:
                        closed = 'both'
                    interval = pd.Interval(interval.left, ref_value + offset,
                                           closed=closed)
            if step_size is None:
                n_steps_if_closed = 2001
            else:
                n_steps_if_closed = int(interval.length / step_size) + 1

            span = linspace_from_interval(interval=interval,
                                          n_steps_if_closed=n_steps_if_closed,
                                          b_change_n_steps_if_open=True)
        parameter_ = SpinBoxSliderParameter(
           name=name, value=value, span=span, **options)
        return parameter_

    @classmethod
    def make_pars_from_model(cls, model, model_dict,
                             signal_register: ModelSignalRegister = None,
                             name=None):

        group = cls.make_group_from_model(
            model=model, name=name, model_dict=model_dict)

        inherited_options = {
            PGParOption.READONLY: group.readonly(),
            PGParOption.RENAMABLE: group.opts.get(
                PGParOption.RENAMABLE, False),
            PGParOption.MOVABLE: group.opts.get(
                PGParOption.MOVABLE, False),
            PGParOption.PREFIX: group.opts.get(
                PGParOption.PREFIX, ''),
        }

        children = []
        n_children = 0
        n_numeric_children = 0

        for k, v in model_dict.items():
            if k not in [XMLSettingsModel.CLASS_NAME_KW]:

                model_value = getattr(model, k)
                p_type = cls.get_parameter_type(parent_model=model, key=k)

                if ((not isinstance(p_type, GenericAlias))
                        and issubclass(p_type, BaseModel)):

                    if isinstance(model_value, dict):
                        model_value = p_type(**model_value)

                    par = cls.make_pars_from_model(
                        model=model_value, model_dict=v, name=k,
                        signal_register=signal_register)
                else:
                    par = cls.make_par(
                        parent_model=model, key=k, value=model_value,
                        signal_register=signal_register,
                        model_dict_value=v,
                        **deepcopy(inherited_options))
                n_children += 1
                if par.opts[PGParOption.TYPE] in ['int', 'float']:
                    n_numeric_children += 1
                children.append(par)
                group.addChild(par)
        if ((signal_register is not None)
                and (BaseSettingsSlots.b_is_frozen(model)
                     is False)):
            signal_register.connect_group_parameter(
                model, parameter=group)
        return group

    @classmethod
    def get_parameters_by_type(
        cls, model_type: Type[BaseModel],
        signal_register: ModelSignalRegister,
        ancestor: GroupParameter | BaseModel | None,
    ):
        res = []
        if isinstance(ancestor, BaseModel):
            ancestor = signal_register.group_map[ancestor]
        for model in signal_register.refs:
            if isinstance(model, model_type):
                p = signal_register.group_map[model]
                if ((ancestor is not None)
                        and (ancestor.childPath(p) is None)):
                    pass
                else:
                    res.append(p)
        return res
