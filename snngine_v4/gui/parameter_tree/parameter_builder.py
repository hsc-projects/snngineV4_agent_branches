from __future__ import annotations

import copy
from copy import deepcopy
from enum import Enum, IntEnum
from types import GenericAlias, NoneType, UnionType
from typing import (
    # _LiteralGenericAlias, _UnionGenericAlias,
    _UnionGenericAlias, Annotated, get_args, get_origin, Literal,
    Type,
    TYPE_CHECKING, Union,
)

import numpy as np
from numpydantic import NDArray, Shape

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import GroupParameter
from typing_extensions import TypeAliasType

from snngine_v4.gui.parameter_tree.parameters.engine_group_parameter import \
    EngineGroupParameter
from snngine_v4.utils.settings.settings_keywords import (
    BaseSettingsSlots,
)
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts
from snngine_v4.gui.parameter_tree.parameters.spin_box_slider_parameter import \
    SpinBoxSliderParameter

from snngine_v4.utils.field_utils import (
    b_annotation_includes_type,
    b_is_literal_annotation, extract_literal_values,
    get_field_json_schema_extra,
    extract_type_from_annotation, b_field_has_default,
)
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.utils.array_utils import (
    Array2DF32,
    b_includes_array_annotation, convert_type_alias_type,
)


if TYPE_CHECKING:

    from snngine_v4.gui.parameter_tree.connectors \
        .basemodel_signal_register import ModelSignalRegister


class ParameterBuilder:

    @classmethod
    def get_parameter_type_from_annotation(cls, annotation,):

        b_array_type_checked = False

        if isinstance(annotation, TypeAliasType):
            if b_includes_array_annotation(annotation):
                return convert_type_alias_type(annotation)
            else:
                annotation = annotation.__value__
            b_array_type_checked = True

        try:
            if isinstance(annotation, UnionType):
                if ((not b_array_type_checked)
                        and b_includes_array_annotation(annotation)):
                    return annotation
                args = get_args(annotation)
                args0 = args[0]
                return args0
            elif issubclass(annotation, Enum):
                return Enum
        except TypeError:
            origin = get_origin(annotation)
            if origin == Union:
                new_annotation = get_args(annotation)[0]
                return cls.get_parameter_type_from_annotation(
                    new_annotation
                )
            elif origin == Literal:
                return list
            elif origin == Annotated:
                args = get_args(annotation)
                args0 = args[0]
                pass
            raise

        return annotation

    @classmethod
    def get_parameter_type(cls, parent_model: BaseModel, key):

        if key == 'color':
            pass

        if key in parent_model.model_fields:
            return cls.get_parameter_type_from_annotation(
                parent_model.model_fields[key].annotation)
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
    def make_group_from_model(
        cls, model: BaseModel, name=None,
        model_dict: dict[str, BaseModel] = None,
    ) -> EngineGroupParameter | GroupParameter:

        parameter_ui_opts = getattr(model, ParamOpts.KW.ParamOpts, {})
        if parameter_ui_opts is None:
            parameter_ui_opts = {}
        elif isinstance(parameter_ui_opts, BaseModel):
            parameter_ui_opts = parameter_ui_opts.model_dump()

        if ParamOpts.KW.RENAMABLE not in parameter_ui_opts:
            parameter_ui_opts[ParamOpts.KW.RENAMABLE] = False

        # noinspection PyTypedDict
        if model.model_config.get(BaseSettingsSlots.FROZEN, None):
            parameter_ui_opts[ParamOpts.KW.READONLY] = True

        ui_name = parameter_ui_opts.pop(ParamOpts.KW.NAME, None)
        if ui_name is not None:
            name = ui_name
        elif name is None:
            name = model.__class__.__name__

        if ParamOpts.KW.PREFIX in parameter_ui_opts:
            prefix_pattern = parameter_ui_opts[ParamOpts.KW.PREFIX]
            if isinstance(prefix_pattern, str):
                sep = ParamOpts.PREFIX_PATTERN_SEP
                prefix_pattern = prefix_pattern.split(sep)
                parameter_ui_opts[ParamOpts.KW.PREFIX] = prefix_pattern
        else:
            parameter_ui_opts[ParamOpts.KW.PREFIX] = []

        g = EngineGroupParameter(name=name, **parameter_ui_opts)
        return g

    @classmethod
    def make_par(cls, parent_model: BaseModel, key, value, signal_register,
                 model_dict_value,
                 **options):

        if key == 'color':
            pass

        field_ = parent_model.model_fields[key]
        json_schema_extra = get_field_json_schema_extra(field_)

        if ParamOpts.KW.NAME not in options:
            options[ParamOpts.KW.NAME] = key

        options[ParamOpts.KW.VALUE] = value

        if b_field_has_default(field_info=field_):
            options[ParamOpts.KW.DEFAULT] = field_.default

        options.update(json_schema_extra)

        parameter_type = cls.get_parameter_type(
            parent_model=parent_model, key=key)

        options[ParamOpts.KW.C_DATA_TYPES] = parameter_type
        if not isinstance(parameter_type, UnionType):
            parameter_type_name = parameter_type.__name__
        else:
            parameter_type_name = UnionType.__name__

        options[ParamOpts.KW.TYPE] = parameter_type_name
        if parameter_type == Enum:
            # see pyqtgraphQtEnumParameter
            options[ParamOpts.KW.ENUM] = extract_type_from_annotation(
                field_.annotation, type_=Enum)

        options[ParamOpts.KW.C_NULLABLE_VALUE] = (
            b_annotation_includes_type(
                field_.annotation, type_=NoneType))

        parameter_ = None

        options[ParamOpts.KW.C_MODEL_FIELD_NAME] = key

        if ParamOpts.KW.PREFIX in options:
            prefix = options[ParamOpts.KW.PREFIX]
            if isinstance(prefix, list):
                name = options[ParamOpts.KW.NAME]
                if name in prefix:
                    options[ParamOpts.KW.PREFIX] = name + ': '
                else:
                    options[ParamOpts.KW.PREFIX] = ''

        if parameter_type in [float, int]:
            # if key == 'distance':
            #     pass
            parameter_ = cls._make_numeric_par(field_=field_, **options)

        elif isinstance(parameter_type, GenericAlias):

            parameter_ = cls._make_pars_from_iterable(
                parameter_type=parameter_type, model_value=value,
                model_dict_value=model_dict_value,
                signal_register=signal_register, **options)

        if parameter_type == list:
            if ParamOpts.KW.LIMITS not in options:
                if b_is_literal_annotation(field_, b_strict=False):
                    options[ParamOpts.KW.LIMITS] = extract_literal_values(
                        field_.annotation)
                else:
                    raise ValueError

        if parameter_ is None:
            if key == 'color':
                pass
            parameter_ = Parameter.create(**options)

        return parameter_

    @classmethod
    def _make_numeric_par(cls, field_: FieldInfo, **options):
        return SpinBoxSliderParameter.from_field(
            field=field_, **options)
        # if options[ParamOpts.KW.C_MODEL_FIELD_NAME] == 'distance':
        #     pass
        #
        # if (options[ParamOpts.KW.C_NULLABLE_VALUE] and
        #         options.get(ParamOpts.KW.DEFAULT) is None):
        #     options[ParamOpts.KW.DEFAULT] = np.nan
        # interval = extract_field_interval(field_)
        # multiple_of = get_field_multiple_of(field_)
        #
        # if multiple_of is not None:
        #     step_size = multiple_of
        # else:
        #     is_int = b_is_int_annotation(field_.annotation, True)
        #     if is_int:
        #         step_size = options.get(ParamOpts.KW.STEP, 1)
        #     else:
        #         step_size = options.get(ParamOpts.KW.STEP, .01)
        #         options[ParamOpts.KW.DECIMALS] = 6
        #
        # options[ParamOpts.KW.STEP] = step_size
        #
        # # if True:
        # if interval is not None:
        #     # interval = get_field_interval(field_)
        #     limits = limits_from_interval(interval, step_size=step_size)
        #     options[ParamOpts.KW.LIMITS] = limits
        # else:
        #     pass
        # # if interval is not None:
        # if True:
        #     parameter_ = SpinBoxSliderParameter.from_interval(
        #         interval=interval, **options)
        # else:
        #     parameter_ = Parameter.create(**options)
        # return parameter_

    @classmethod
    def _par_from_item_from_iterable(
            cls, idx, par_type, model_value, **options):
        options = copy.copy(options)
        options[ParamOpts.KW.NAME] = str(idx)
        options[ParamOpts.KW.TYPE] = par_type.__name__
        if model_value is not None:
            p_value = model_value[idx]
        else:
            p_value = None
        options[ParamOpts.KW.VALUE] = p_value
        par = Parameter.create(**options)
        return par

    @classmethod
    def _make_pars_from_iterable(
            cls, parameter_type, model_value, model_dict_value,
            signal_register, **options):

        parameter_ = EngineGroupParameter(**options)
        iterable_type = get_origin(parameter_type)

        if iterable_type == tuple:
            args_ = get_args(parameter_type)
            for i, t in enumerate(args_):
                g_par = cls._par_from_item_from_iterable(
                    idx=i, par_type=t, model_value=model_value,
                    **options)
                parameter_.addChild(g_par)
        elif iterable_type == list:
            if model_value is None:
                pass
            else:

                t_args_ = get_args(parameter_type)
                if len(t_args_) != 1:
                    raise NotImplementedError("len(t_args_) != 1")
                t_arg0 = t_args_[0]
                if isinstance(t_arg0, UnionType):
                    t_args = get_args(t_arg0)
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
    def make_pars_from_model(cls, model, model_dict,
                             signal_register: ModelSignalRegister = None,
                             name=None):

        if name == 'color':
            pass

        group = cls.make_group_from_model(
            model=model, name=name, model_dict=model_dict)

        inherited_options = {
            ParamOpts.KW.READONLY: group.readonly(),
            ParamOpts.KW.RENAMABLE: group.opts.get(
                ParamOpts.KW.RENAMABLE, False),
            ParamOpts.KW.MOVABLE: group.opts.get(
                ParamOpts.KW.MOVABLE, False),
            ParamOpts.KW.PREFIX: group.opts.get(
                ParamOpts.KW.PREFIX, ''),
            ParamOpts.KW.C_NULLABLE_VALUE: group.opts.get(
                ParamOpts.KW.C_NULLABLE_VALUE, False),
            ParamOpts.KW.C_COERCE_TO_LIMITS: group.opts.get(
                ParamOpts.KW.C_COERCE_TO_LIMITS, False),
            ParamOpts.KW.DELAY: group.opts.get(
                ParamOpts.KW.DELAY, 0.1),
        }

        children = []
        n_children = 0
        n_numeric_children = 0

        for k, v in model_dict.items():
            if k not in [XMLSettingsModel.CLASS_NAME_KW]:

                model_value = getattr(model, k)
                p_type = cls.get_parameter_type(parent_model=model, key=k)

                if k == 'color':
                    pass

                if ((not isinstance(p_type, (GenericAlias, UnionType)))
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
                if par.opts[ParamOpts.KW.TYPE] in ['int', 'float']:
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
