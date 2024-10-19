from __future__ import annotations

from copy import copy
from enum import Enum
from types import NoneType, UnionType
from typing import (
    Annotated, get_args, get_origin, Literal, Optional, TypeAliasType,
    Union, _LiteralGenericAlias
)

import numpy as np
import pandas as pd
from pydantic import BaseModel
from pydantic_core import PydanticUndefined
from pyqtgraph.parametertree.Parameter import PARAM_TYPES

from snngine_v4.data.validation.array_annotation import b_is_array_annotation

from snngine_v4.utils.field_utils import (
    AnnotationType, b_annotation_includes_type, b_field_has_default,
    b_is_annotated, b_is_int_annotation, b_is_literal_annotation, b_is_optional,
    b_is_union, extract_field_interval,
    extract_literal_values, extract_type_from_annotation,
    get_field_json_schema_extra,
    get_field_multiple_of,
)
from snngine_v4.utils.interval_utils import limits_from_interval
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.geometry.spatial_pars import Ax3D, PositionVBO
from snngine_v4.visualization.config_models.visuals.parameters import (
    ColorVBO, RGBAEnum,
)


class OptionsBuilder:

    @staticmethod
    def convert_type_alias_type(ann: AnnotationType):
        if b_is_array_annotation(ann):
            return ann
        else:
            return ann.__value__

    @classmethod
    def get_parameter_type_from_annotation(cls, ann, ):

        if isinstance(ann, TypeAliasType):
            if ann.__name__ in PARAM_TYPES:
                return ann
            if b_is_array_annotation(ann):
                if isinstance(ann, TypeAliasType):
                    return ann.__value__
                return ann
            ann = cls.convert_type_alias_type(ann)
        Optional
        try:
            if isinstance(ann, UnionType) or b_is_optional(ann):
                args = get_args(ann)
                if (len(args) == 2) and (NoneType in args):
                    if (b_float := (float in args)) or (int in args):
                        return float if b_float else int
                    elif b_is_annotated(ann, b_strict=False):
                        for arg in args:
                            if ((arg != NoneType)
                                    and (arg.__origin__ in [int, float])):
                                return arg.__origin__
                return ann
            elif issubclass(ann, Enum):
                return Enum
        except TypeError:
            if b_is_literal_annotation(ann=ann, b_strict=True):
                return list
            elif b_is_union(ann):
                pass
            elif b_is_annotated(ann):
                return ann.__origin__
            raise
        return ann

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
                model_type = parent_model.model_interpret_extra_dict_type(
                    dct=model_value)
                if model_type:
                    return model_type
            return type(model_value)

    @classmethod
    def from_field(cls,
                   fi, value=PydanticUndefined,
                   m: ParamOpts | None = None,
                   **options) -> ParamOpts:

        if m is not None:
            m.update(options)
            options = m
        else:
            options = ParamOpts(**options)

        json_schema_extra = get_field_json_schema_extra(fi)
        options.update(json_schema_extra)

        if options.c_model_field_name == 'scale_factor':
            pass

        options.c_model_field_info = fi

        if options.name is None:
            options.name = options.c_model_field_name

        b_has_default = b_field_has_default(field_info=fi)
        if b_has_default:
            options.default = fi.default

        if (value is PydanticUndefined) and b_has_default:
            value = options.default
        options.value = value

        if fi.title:
            options.title = fi.title

        if options.c_data_types in [float, int]:
            options.c_value_interval = extract_field_interval(fi)
            options.step = get_field_multiple_of(fi)

        return cls.from_annotation(ann=fi.annotation, m=options)

    @classmethod
    def from_annotation(
            cls, ann, m: ParamOpts | None = None, **options) -> ParamOpts:

        if m is not None:
            m = copy(m)
            m.update(options)
            options = m
        else:
            options = ParamOpts(**options)

        options.c_annotation = ann

        if ann == PositionVBO:
            options.c_column_name_s = Ax3D._member_names_
        elif ann == ColorVBO:
            options.c_column_name_s = RGBAEnum._member_names_
        else:
            options.c_column_name_s = None

        if options.c_data_types is None:
            options.c_data_types = cls.get_parameter_type_from_annotation(
                ann=ann)

        if options.type is None:
            if not isinstance(options.c_data_types, UnionType):
                options.type = options.c_data_types.__name__
            else:
                options.type = UnionType.__name__

        if options.type == 'Optional':
            options.type = UnionType.__name__

        if options.c_data_types == Enum:
            # see pyqtgraphQtEnumParameter
            options.enum = extract_type_from_annotation(
                ann, type_=Enum)

        options.c_nullable_value = (
            b_is_optional(ann) or
            b_annotation_includes_type(ann, type_=NoneType))

        if (options.name is None) and (options.c_model_field_name is not None):
            options.name = options.c_model_field_name

        if options.c_group_prefixes is not None:
            if isinstance(options.c_group_prefixes, list):
                name = options.name
                if name in options.c_group_prefixes:
                    options.prefix = name + ': '

        if options.c_data_types in [float, int]:

            if options.c_value_interval is None:
                if options.c_model_field_info is not None:
                    options.c_value_interval = extract_field_interval(
                        options.c_model_field_info)
                else:
                    options.c_value_interval = pd.Interval(-np.inf, np.inf)

            if options.step is None:
                if options.c_model_field_info is not None:
                    options.step = get_field_multiple_of(
                        options.c_model_field_info)
                if options.step is None:
                    is_int = b_is_int_annotation(ann, True)
                    if options.step is None:
                        if is_int:
                            options.step = 1
                        else:
                            options.step = .01
                            options.decimals = 6

            if (options.c_nullable_value and
                    options.default is None):
                options.default = np.nan

            bounds = limits_from_interval(
                options.c_value_interval, step_size=options.step)
            options.bounds = bounds

        if options.c_data_types == list:
            if options.limits is None:
                if b_is_literal_annotation(ann, b_strict=True):
                    options.limits = extract_literal_values(ann)
                else:
                    # pass
                    raise ValueError

        if options.c_b_group_default_button is None:
            options.c_b_group_default_button = True
        if options.expanded is None:
            options.expanded = True
        return options

    @classmethod
    def from_model(cls, model: BaseModel, **kwargs):

        opts = getattr(model, ParamOpts.CLASS_VAR_KEY, {})
        if opts is None:
            opts = {}
        elif isinstance(opts, BaseModel):
            opts = opts.model_dump(mode='python')

        opts = ParamOpts(**opts)
        opts.update(kwargs)

        if not hasattr(model, 'model_config'):
            pass

        if model.model_config.get('frozen', False) is True:
            opts.readonly = True

        if opts.name == 'main':
            pass
        if opts.name is None:
            if opts.c_b_group_default_button is None:
                opts.c_b_group_default_button = False
            opts.name = model.__class__.__name__
        if opts.c_b_group_default_button is None:
            opts.c_b_group_default_button = True
        if opts.expanded is None:
            opts.expanded = True
        return opts
