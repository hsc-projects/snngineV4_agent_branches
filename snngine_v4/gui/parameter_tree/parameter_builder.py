from __future__ import annotations

from enum import Enum
from types import GenericAlias, UnionType
from typing import (
    # _LiteralGenericAlias, _UnionGenericAlias,
    Annotated, get_args, get_origin, Literal,
    Type,
    TYPE_CHECKING, Union,
)


from pydantic import BaseModel

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

from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.utils.array_utils import (
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

    @classmethod
    def make_par(cls, parent_model: BaseModel, key, value, signal_register,
                 model_dict_value,
                 **options):

        parameter_ = None

        options = ParamOpts.from_field(
            parent_model=parent_model,
            c_data_types=cls.get_parameter_type(
                parent_model=parent_model, key=key),
            key=key, value=value, **options)

        if options.c_data_types in [float, int]:
            parameter_ = SpinBoxSliderParameter(**options)

        elif isinstance(options.c_data_types, GenericAlias):

            parameter_ = cls._make_pars_from_iterable(
                parameter_type=options.c_data_types, model_value=value,
                model_dict_value=model_dict_value,
                signal_register=signal_register, **options)

        if parameter_ is None:
            if key == 'color':
                pass
            parameter_ = Parameter.create(**options)

        return parameter_

    @classmethod
    def _par_from_item_from_iterable(
            cls, idx, par_type, model_value, **options):
        options = ParamOpts(**options)

        options.name = str(idx)
        options.type = par_type.__name__
        if model_value is not None:
            p_value = model_value[idx]
        else:
            p_value = None
        options.value = p_value
        options = options.model_dump(exclude_none=True)
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

        if name == 'seg':
            pass

        group = EngineGroupParameter.from_model(model=model, name=name)
        heritable_options = ParamOpts.heritable_options(**group.opts)

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
                        model_dict_value=v, **heritable_options)
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
