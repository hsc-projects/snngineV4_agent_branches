from __future__ import annotations

from copy import copy
from enum import Enum
from types import NoneType, UnionType
from typing import (
    Annotated, get_args, get_origin, Literal, TypeAliasType,
    Union,
)

import numpy as np
import pandas as pd
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from snngine_v4.utils.array_utils import (
    b_includes_array_annotation,
    convert_type_alias_type,
)
from snngine_v4.utils.field_utils import (
    b_annotation_includes_type, b_field_has_default,
    b_is_int_annotation, b_is_literal_annotation, extract_field_interval,
    extract_literal_values, extract_type_from_annotation,
    get_field_json_schema_extra,
    get_field_multiple_of,
)
from snngine_v4.utils.interval_utils import limits_from_interval
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


class OptionsBuilder:

    @classmethod
    def get_parameter_type_from_annotation(cls, ann, ):

        b_array_type_checked = False

        if isinstance(ann, TypeAliasType):
            if b_includes_array_annotation(ann):
                return convert_type_alias_type(ann)
            else:
                ann = ann.__value__
            b_array_type_checked = True

        try:
            if isinstance(ann, UnionType):
                args = get_args(ann)
                if ((len(args) == 2) and (NoneType in args)
                        and ((b_float := (float in args)) or (int in args))):
                    return float if b_float else int
                return ann
                # if ((not b_array_type_checked)
                #         and b_includes_array_annotation(annotation)):
                #     return annotation
                # args = get_args(annotation)
                # args0 = args[0]
                # return args0
            elif issubclass(ann, Enum):
                return Enum
        except TypeError:
            origin = get_origin(ann)
            if origin == Union:
                new_annotation = get_args(ann)[0]
                return cls.get_parameter_type_from_annotation(
                    new_annotation
                )
            elif origin == Literal:
                return list
            elif origin == Annotated:
                args = get_args(ann)
                args0 = args[0]
                pass
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
                model_type = parent_model.model_interpret_dict_type(
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

        if options.c_data_types is None:
            options.c_data_types = cls.get_parameter_type_from_annotation(
                ann=ann)

        if options.type is None:
            if not isinstance(options.c_data_types, UnionType):
                options.type = options.c_data_types.__name__
            else:
                options.type = UnionType.__name__

        if options.c_data_types == Enum:
            # see pyqtgraphQtEnumParameter
            options.enum = extract_type_from_annotation(
                ann, type_=Enum)

        options.c_nullable_value = (
            b_annotation_includes_type(ann, type_=NoneType))

        if options.c_group_prefixes is not None:
            if isinstance(options.c_group_prefixes, list):
                name = options.name
                if name in options.c_group_prefixes:
                    options.prefix = name + ': '

        if options.c_data_types in [float, int]:

            if options.c_value_interval is None:
                options.c_value_interval = pd.Interval(-np.inf, np.inf)

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
                if b_is_literal_annotation(ann, b_strict=False):
                    options.limits = extract_literal_values(ann)
                else:
                    raise ValueError
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

        if opts.name is None:
            opts.name = model.__class__.__name__

        return opts
