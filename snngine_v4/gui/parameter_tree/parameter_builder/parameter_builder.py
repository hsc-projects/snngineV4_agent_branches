from __future__ import annotations

from types import GenericAlias, UnionType
from typing import (
    get_args, get_origin,
    Type,
    TYPE_CHECKING, TypeAliasType,
)


from pydantic import BaseModel

from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import (
    GroupParameter,
)

from snngine_v4.gui.parameter_tree.parameter_builder.options_builder import \
    OptionsBuilder

from snngine_v4.gui.parameter_tree.parameters.engine_group_parameter import \
    EngineGroupParameter
from snngine_v4.gui.parameter_tree.parameters.multi_type_parameter import \
    MultiTypeParameter
from snngine_v4.gui.parameter_tree.parameters.reference_parameter import \
    ReferenceParameter
from snngine_v4.utils.settings.settings_keywords import (
    BaseSettingsSlots,
)
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts

from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


if TYPE_CHECKING:

    from snngine_v4.gui.parameter_tree.connectors \
        .basemodel_signal_register import ModelSignalRegister


class ParameterBuilder:

    @classmethod
    def collect_extra_classes(
            cls, parent_par, collector_par, signal_register):
        if (v := collector_par.opts[
                k := ParamOpts.KW.C_B_COLLECT_EXTRA_CLASSES]) is False:
            raise PermissionError(f"{k}={v} for ({collector_par})")
        collector_model: XMLSettingsModel = signal_register.group_map.inv[
            collector_par]
        extra_classes = collector_model.EXTRA_CLASSES
        for cl in extra_classes:
            pars = cls.get_parameters_by_type(
                signal_register=signal_register,
                model_type=cl, ancestor=parent_par,
                excluded_ancestor=collector_par)
            for p in pars:
                parent: Parameter = p.parent()
                idx = parent.children().index(p)
                collector_par.addChild(p)
                p.insertChild(0, ReferenceParameter(
                    name='parent', ref=parent
                ))
                parent.insertChild(idx, ReferenceParameter(
                    name=p.name(), ref=p
                ))

    @classmethod
    def get_parameters_by_type(
        cls, model_type: Type[BaseModel],
        signal_register: ModelSignalRegister,
        ancestor: GroupParameter | BaseModel | None,
        excluded_ancestor: GroupParameter | BaseModel | None,
    ):
        res = []
        if isinstance(ancestor, BaseModel):
            ancestor = signal_register.group_map[ancestor]
        if isinstance(excluded_ancestor, BaseModel):
            excluded_ancestor = signal_register.group_map[excluded_ancestor]
        for model in signal_register.refs:
            if isinstance(model, model_type):
                p = signal_register.group_map[model]
                if ((ancestor is not None)
                        and (ancestor.childPath(p) is None)):
                    pass
                elif ((excluded_ancestor is not None)
                      and (excluded_ancestor.childPath(p) is not None)):
                    pass
                else:
                    res.append(p)
        return res

    @classmethod
    def make_par(cls, options: ParamOpts, signal_register):

        parameter_ = None

        if ((not isinstance(options.c_data_types, (GenericAlias,
                                                   UnionType,
                                                   TypeAliasType)))
                and issubclass(options.c_data_types, BaseModel)):
            if isinstance(options.value, dict):
                options.value = options.c_data_types(**options.value)

            parameter_ = cls.make_pars_from_model(
                model=options.value, name=options.name,
                signal_register=signal_register, title=options.title)

        if parameter_ is None:
            if isinstance(options.c_data_types, GenericAlias):
                parameter_ = cls._make_pars_from_iterable(
                    parameter_type=options.c_data_types,
                    model_value=options.value,
                    signal_register=signal_register, options=options)

            if parameter_ is None:
                if options.name == 'color':
                    pass
                parameter_ = Parameter.create(**options)

        if isinstance(parameter_, MultiTypeParameter):
            parameter_.build(signal_register=signal_register)
        return parameter_

    @classmethod
    def make_par_from_field(cls, parent_model: BaseModel, key, value,
                            signal_register,
                            **options):
        c_data_types = OptionsBuilder.get_parameter_type(
            parent_model, key)
        if key in parent_model.model_fields:
            fi = parent_model.model_fields[key]
            options = OptionsBuilder.from_field(
                fi=fi, c_data_types=c_data_types,
                c_model_field_name=key,
                value=value, **options)
        else:
            options = OptionsBuilder.from_annotation(
                ann=c_data_types,
                c_data_types=c_data_types,
                c_model_field_name=key,
                value=value, **options)

        return cls.make_par(options=options,
                            signal_register=signal_register)

    @classmethod
    def make_par_from_annotation(
            cls, ann: BaseModel, signal_register, **options):
        options = OptionsBuilder.from_annotation(
            ann=ann, **options)
        parameter_ = cls.make_par(
            options=options, signal_register=signal_register)
        return parameter_

    @classmethod
    def _make_pars_from_iterable(
            cls, parameter_type, model_value,
            signal_register, options):
        options = options.model_dump()
        options[ParamOpts.KW.C_COLLAPSED_CHILDREN] = True
        options[ParamOpts.KW.EXPANDED] = True
        group = EngineGroupParameter(**options)
        heritable_options = ParamOpts.heritable_options(**group.opts)

        iterable_type = get_origin(parameter_type)
        if iterable_type == tuple:
            args_ = get_args(parameter_type)
            for i, t in enumerate(args_):
                g_opts = OptionsBuilder.from_annotation(
                    ann=t,
                    name=str(i), c_data_types=t, type=None,
                    value=model_value[i] if model_value is not None else None,
                    **heritable_options)
                g_par = Parameter.create(**g_opts)
                group.addChild(g_par)
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

                        if issubclass(t, BaseModel):
                            name = model_value[i].__class__.__name__ + str(i)
                            g_par = cls.make_pars_from_model(
                                model=model_value[i],
                                name=name,
                                signal_register=signal_register)
                            pass
                            break
                        elif isinstance(v, t):
                            g_opts = OptionsBuilder.from_annotation(
                                name=str(i), c_data_types=t, type=None,
                                value=model_value[
                                    i] if model_value is not None else None,
                                ann=t, **heritable_options)
                            g_par = Parameter.create(**g_opts)
                            break

                    group.addChild(g_par)
        else:
            raise NotImplementedError(f"{iterable_type}")
        return group

    @classmethod
    def make_pars_from_model(cls, model,
                             signal_register: ModelSignalRegister,
                             **options):

        group = EngineGroupParameter.from_model(model=model, **options)
        heritable_options = ParamOpts.heritable_options(**group.opts)

        children = []
        n_children = 0
        n_numeric_children = 0
        if model is None:
            pass
        keys = list(model.model_fields.keys())

        if model.model_extra is not None:
            keys += list(model.model_extra.keys())

        for k in keys:
            if k not in [XMLSettingsModel.CLASS_NAME_KW]:

                par = cls.make_par_from_field(
                    parent_model=model, key=k,
                    value=getattr(model, k),
                    signal_register=signal_register,
                    **heritable_options)

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

        for c in group.children():
            if c.opts[ParamOpts.KW.C_B_COLLECT_EXTRA_CLASSES] is True:
                cls.collect_extra_classes(
                    parent_par=group, collector_par=c,
                    signal_register=signal_register)

        return group
