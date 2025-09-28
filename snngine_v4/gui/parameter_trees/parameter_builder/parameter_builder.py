from __future__ import annotations

from copy import deepcopy
from types import GenericAlias, NoneType, UnionType
from typing import (
    get_args, get_origin,
    Type,
    TYPE_CHECKING, TypeAliasType,
)


from pydantic import BaseModel

from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.Parameter import PARAM_TYPES
from pyqtgraph.parametertree.parameterTypes import (
    GroupParameter,
)

from snngine_v4.gui.parameter_trees.parameter_builder.options_builder import \
    OptionsBuilder

from snngine_v4.gui.parameters.common.engine_group_parameter import EngineGroupParameter
from snngine_v4.gui.parameters import \
    MultiTypeParameter
from snngine_v4.gui.parameters.reference_parameter import \
    ReferenceParameter
from snngine_v4.utils.data_utils.dataframe_config import (
    SeriesModel, TypedDataFrameBase3D,
)
from snngine_v4.utils.data_utils.index_config import IndexConfig
from snngine_v4.utils.field_utils import (
    b_is_annotated, b_is_optional,
    model_keys,
)
from snngine_v4.utils.list_parameter_model import ListParameterModel
from snngine_v4.utils.settings.settings_keywords import (
    BaseModelSlots, BaseSettingsSlots,
)
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts

if TYPE_CHECKING:

    from snngine_v4.gui.parameter_trees.connectors \
        .model_signals_register import ExtendedModelSignalsRegister


class ParameterBuilder:

    @classmethod
    def collect_extra_classes(
            cls, parent_par, collector_par, signal_register):
        if (v := collector_par.opts[
                k := ParamOpts.KW.C_B_COLLECT_EXTRA_CLASSES]) is False:
            raise PermissionError(f"{k}={v} for ({collector_par})")
        collector_model = signal_register.group_map.inv[
            collector_par]
        extra_classes = getattr(
            collector_model, BaseModelSlots.EXTRA_CLASSES, [])
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
        signal_register: ExtendedModelSignalsRegister,
        ancestor: GroupParameter | BaseModel | None,
        excluded_ancestor: GroupParameter | BaseModel | None,
    ):
        res = []
        if isinstance(ancestor, BaseModel):
            ancestor = signal_register.get_group(ancestor)
        if isinstance(excluded_ancestor, BaseModel):
            excluded_ancestor = signal_register.get_group(excluded_ancestor)
        for model in signal_register.refs:
            if isinstance(model, model_type):
                p = signal_register.get_group(model)
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
    def make_par(cls, options: ParamOpts, signal_register,
                 exclude_keys=None,
                 parent_model=None):

        parameter_ = None

        if ((not isinstance(options.c_data_types, (GenericAlias,
                                                   UnionType,
                                                   TypeAliasType)))
                and (not b_is_optional(options.c_data_types))
                and issubclass(options.c_data_types, BaseModel)):
            if isinstance(options.value, dict):
                options.value = options.c_data_types(**options.value)

            b_not_index = not isinstance(options.value, IndexConfig)
            b_not_tdf = not isinstance(options.value, SeriesModel)

            heritable_opts = ParamOpts.heritable_options(
                b_raise=True, **options)

            if ((options.value.__class__.__name__ not in PARAM_TYPES)
                    and b_not_tdf and b_not_index):

                parameter_ = cls.make_pars_from_model(
                    model=options.value, name=options.name,
                    parent_model=parent_model,
                    exclude_keys=exclude_keys,
                    signal_register=signal_register, title=options.title,
                    **heritable_opts)
            else:
                if b_not_tdf and b_not_index:
                    type_ = options.value.__class__.__name__
                else:
                    if isinstance(options.value, TypedDataFrameBase3D):
                        type_ = TypedDataFrameBase3D.__name__
                    elif isinstance(options.value, SeriesModel):
                        type_ = SeriesModel.__name__
                    # elif isinstance(options.value, RowOrColumn):
                    elif isinstance(options.value, IndexConfig):
                        type_ = IndexConfig.__name__
                    else:
                        raise TypeError(type(options.value))

                # heritable_opts = ParamOpts.heritable_options(**options)
                if options.c_data_types == ListParameterModel:
                    heritable_opts[ParamOpts.KW.LIMITS] = options.value.limits
                    heritable_opts[ParamOpts.KW.VALUE] = options.value.value

                parameter_ = Parameter.create(
                    name=options.name,
                    parent_model=parent_model, model=options.value,
                    type=type_,
                    signal_register=signal_register,
                    title=options.title,
                    exclude_keys=exclude_keys,
                    **heritable_opts)

                if isinstance(options.value, BaseModel):
                    signal_register.parameter_map[options.value] = parameter_

        if parameter_ is None:
            if (isinstance(options.c_data_types, GenericAlias)
                    or (options.c_data_types in [tuple])):
                parameter_ = cls._make_pars_from_iterable(
                    parameter_type=options.c_data_types,
                    model_value=options.value,
                    signal_register=signal_register, options=options)

            if parameter_ is None:
                if options.name == 'color':
                    pass
                if options.c_data_types == ListParameterModel:
                    pass
                parameter_ = Parameter.create(**options)

        if isinstance(parameter_, MultiTypeParameter):
            parameter_.build(signal_register=signal_register)
        return parameter_

    @classmethod
    def make_par_from_field(cls, parent_model: BaseModel, key, value,
                            signal_register, m=None, exclude_keys=None,
                            **options):

        if m is not None:
            m = deepcopy(m)
            m.update(options)
            options = m
        else:
            pass

        c_data_types = OptionsBuilder.get_parameter_type(
            parent_model, key)
        if key in parent_model.model_fields:
            fi = parent_model.model_fields[key]
            options = OptionsBuilder.from_field(
                fi=fi, c_data_types=c_data_types, c_model_field_name=key,
                value=value, **options)
        else:
            options = OptionsBuilder.from_annotation(
                ann=c_data_types, c_data_types=c_data_types,
                c_model_field_name=key, value=value, **options)

        return cls.make_par(options=options,
                            signal_register=signal_register,
                            exclude_keys=exclude_keys,
                            parent_model=parent_model)

    @classmethod
    def make_par_from_annotation(
            cls, ann: BaseModel, signal_register, **options):
        options = OptionsBuilder.from_annotation(ann=ann, **options)
        parameter_ = cls.make_par(
            options=options, signal_register=signal_register)
        return parameter_

    @classmethod
    def _make_pars_from_iterable(
            cls, parameter_type, model_value,
            signal_register, options):
        # tmp_value = options.value
        # options.value = None
        options = options.model_dump()
        # options[ParamOpts.KW.VALUE] = tmp_value
        options[ParamOpts.KW.C_COLLAPSED_CHILDREN] = True
        options[ParamOpts.KW.EXPANDED] = True
        group = EngineGroupParameter(**options)
        heritable_options = ParamOpts.heritable_options(
            b_raise=True, **group.opts)
        if parameter_type in [tuple]:
            iterable_type = parameter_type
        else:
            iterable_type = get_origin(parameter_type)
        if iterable_type == tuple:
            args_ = get_args(parameter_type)
            for i, t in enumerate(args_):
                value = model_value[i] if model_value is not None else None
                g_opts = OptionsBuilder.from_annotation(
                    ann=t,
                    name=str(i), c_data_types=t, type=None,
                    value=value,
                    **heritable_options)
                if g_opts.value is None:
                    pass
                g_par = Parameter.create(**g_opts)
                group.addChild(g_par)
        elif iterable_type == list:
            if model_value is None:
                pass
            else:
                if parameter_type in [tuple]:
                    t_args = set([type(x)for x in model_value])
                else:
                    t_args_ = get_args(parameter_type)
                    if len(t_args_) != 1:
                        raise NotImplementedError(
                            f"len(t_args_) = {len(t_args_)} != 1")
                    t_arg0 = t_args_[0]
                    if isinstance(t_arg0, UnionType):
                        t_args = get_args(t_arg0)
                    else:
                        t_args = [t_arg0]

                for i, v in enumerate(model_value):
                    g_par = None
                    for t in t_args:

                        t_0 = get_args(t)[0] if b_is_annotated(t) else t

                        if issubclass(t_0, BaseModel) and isinstance(v, t_0):
                            name = model_value[i].__class__.__name__ + str(i)
                            g_par = cls.make_pars_from_model(
                                model=model_value[i],
                                name=name,
                                signal_register=signal_register,
                                **heritable_options)
                            pass
                            break
                        elif isinstance(v, t_0):
                            value = (model_value[i] if model_value is not None
                                     else None)
                            g_opts = OptionsBuilder.from_annotation(
                                name=str(i), c_data_types=t_0, type=None,
                                value=value, ann=t, **heritable_options)
                            if (t_0 != NoneType) and (g_opts.value is None):
                                pass
                            g_par = Parameter.create(**g_opts)
                            break

                    group.addChild(g_par)
        else:
            raise NotImplementedError(f"{iterable_type}")
        return group

    @staticmethod
    def interpret_exclude_keys(exclude_keys):
        if isinstance(exclude_keys, str):
            exclude_keys = [exclude_keys]
        if isinstance(exclude_keys, dict):
            exclude_keys_dct = exclude_keys
            default_exclude_key = exclude_keys_dct.pop(None, None)
            exclude_keys = list(exclude_keys.keys())
        else:
            if exclude_keys is None:
                exclude_keys = []
            exclude_keys_dct = {}
            default_exclude_key = None
        exclude_keys += [BaseModelSlots.CLASS__NAME]

        return exclude_keys, exclude_keys_dct, default_exclude_key

    @classmethod
    def make_pars_from_model(
            cls, model, signal_register: ExtendedModelSignalsRegister,
            exclude_keys=None, parent_model=None,
            group=None,
            b_raise_if_missing_heritable_opts=True,
            **options):

        if signal_register is not None:
            if signal_register.node_tree.root is None:
                signal_register.node_tree.root = model
        if group is None:
            group = EngineGroupParameter.from_model(
                model=model, parent_model=parent_model,
                **options)
        heritable_options = ParamOpts.heritable_options(
            b_raise=b_raise_if_missing_heritable_opts, **group.opts)

        exclude_keys, excl_k_dct, dft_excl_k = cls.interpret_exclude_keys(
            exclude_keys
        )

        children = []
        n_children = 0
        n_numeric_children = 0
        if model is None:
            pass
        keys = model_keys(model, exclude=set(exclude_keys),
                          b_include_computed=False)
        for k in keys:
            # if k == 'map':
            #     pass
            param_model = getattr(model, k)
            par = cls.make_par_from_field(
                parent_model=model, key=k,
                value=param_model,
                signal_register=signal_register,
                exclude_keys=excl_k_dct.get(k, dft_excl_k),
                **heritable_options)

            n_children += 1
            if par.opts[ParamOpts.KW.TYPE] in ['int', 'float']:
                n_numeric_children += 1
            children.append(par)
            group.addChild(par)

        if ((signal_register is not None)
                and (BaseSettingsSlots.b_is_frozen(model) is False)):
            if model in signal_register.model2model_map.inv:
                # signal_register.group_map[model] = group
                signal_register.add_linked_model_pars(model, group)
            else:
                signal_register[model] = group

        for c in group.children():
            if c.opts.get(ParamOpts.KW.C_B_COLLECT_EXTRA_CLASSES) is True:
                cls.collect_extra_classes(
                    parent_par=group, collector_par=c,
                    signal_register=signal_register)

        return group
