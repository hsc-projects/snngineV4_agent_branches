from __future__ import annotations

from enum import Enum
from types import NoneType, UnionType
from typing import Any, ClassVar, Type

import numpy as np
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings

from snngine_v4.utils.field_utils import (
    b_annotation_includes_type, b_field_has_default,
    b_is_int_annotation, b_is_literal_annotation,
    extract_field_interval,
    extract_literal_values, extract_type_from_annotation,
    get_field_json_schema_extra, get_field_multiple_of,
)
from snngine_v4.utils.interval_utils import limits_from_interval


class ParamOpts(BaseSettings, extra='allow'):

    """
    from pyqtgraph.parametertree.Parameter:

    =======================      ===============================================
    **Keyword Arguments:**
    name                         The name to give this Parameter. This is the
                                 name that will appear in the left-most column
                                 of a ParameterTree for this Parameter.
    value                        The value to initially assign to this
                                 Parameter.
    default                      The default value for this Parameter (most
                                 Parameters provide an option to
                                 'reset to default').
    children                     A list of children for this Parameter. Children
                                 may be given either as a Parameter instance or
                                 as a dictionary to pass to Parameter.create().
                                 In this way, it is possible to specify complex
                                 hierarchies of Parameters from a single nested
                                 data structure.
    readonly                     If True, the user will not be allowed to edit
                                 this Parameter. (default=False)
    enabled                      If False, any widget(s) for this parameter will
                                 appear disabled. (default=True)
    visible                      If False, the Parameter will not appear when
                                 displayed in a ParameterTree. (default=True)
    renamable                    If True, the user may rename this Parameter.
                                 (default=False)
    removable                    If True, the user may remove this Parameter.
                                 (default=False)
    expanded                     If True, the Parameter will initially be
                                 expanded in ParameterTrees: Its children will
                                 be visible. (default=True)
    syncExpanded                 If True, the `expanded` state of this Parameter
                                 is synchronized with all ParameterTrees it is
                                 displayed in. (default=False)
    title                        (str or None) If specified, then the parameter
                                 will be displayed to the user using this string
                                 as its name. However, the parameter will still
                                 be referred to internally using the *name*
                                 specified above. Note that this option is not
                                 compatible with renamable=True.
                                 (default=None; added in version 0.9.9)
    =======================      ===============================================
    """
    PREFIX_PATTERN_SEP: ClassVar[str] = ','
    CLASS_VAR_KEY: ClassVar[str] = 'parameter_ui_opts'

    class KW:

        TYPE: ClassVar[str] = 'type'

        MOVABLE: ClassVar[str] = 'movable'

        NAME: ClassVar[str] = 'name'
        VALUE: ClassVar[str] = 'value'
        DEFAULT: ClassVar[str] = 'default'
        CHILDREN: ClassVar[str] = 'children'
        READONLY: ClassVar[str] = 'readonly'
        ENABLED: ClassVar[str] = 'enabled'
        VISIBLE: ClassVar[str] = 'visible'
        RENAMABLE: ClassVar[str] = 'renamable'
        REMOVABLE: ClassVar[str] = 'removable'
        EXPANDED: ClassVar[str] = 'expanded'
        SYNC_EXPANDED: ClassVar[str] = 'syncExpanded'
        TITLE: ClassVar[str] = 'title'

        STEP: ClassVar[str] = 'step'
        SPAN: ClassVar[str] = 'span'
        BOUNDS: ClassVar[str] = 'bounds'
        DECIMALS: ClassVar[str] = 'decimals'
        DEC: ClassVar[str] = 'dec'
        LIMITS: ClassVar[str] = 'limits'
        PREFIX: ClassVar[str] = 'prefix'
        SI_PREFIX: ClassVar[str] = 'siPrefix'
        SUFFIX: ClassVar[str] = 'suffix'
        ENUM: ClassVar[str] = 'enum'
        DELAY: ClassVar[str] = 'delay'

        INT: ClassVar[str] = 'int'
        MIN: ClassVar[str] = 'min'
        MIN_STEP: ClassVar[str] = 'minStep'
        MAX: ClassVar[str] = 'max'

        # Custom
        C_GROUP_PREFIXES: ClassVar[str] = 'c_group_prefixes'
        C_MODEL_FIELD_NAME: ClassVar[str] = 'c_model_field_name'
        C_MODEL_FIELD_INFO: ClassVar[str] = 'c_model_field_info'
        C_NUMERIC_GROUP: ClassVar[str] = 'c_numeric_group'
        C_NULLABLE_VALUE: ClassVar[str] = 'c_nullable_value'
        C_COERCE_TO_LIMITS: ClassVar[str] = 'c_coerce_to_limits'
        C_VALUE_INTERVAL: ClassVar[str] = 'c_value_interval'
        C_AUTO_COLLAPSE: ClassVar[str] = 'c_auto_collapse'
        C_AUTO_EXPAND: ClassVar[str] = 'c_auto_expand'
        C_NONE_MEANS_UNKNOWN: ClassVar[str] = 'c_none_means_unknown'
        C_DATA_TYPES: ClassVar[str] = 'c_data_types'
        # C_VALUE_INTERVAL: ClassVar[str] = 'c_value_interval'

    # keep unset
    value: Any = None
    type: Any = None
    c_model_field_name: Any = None
    c_model_field_info: Any = None
    c_data_types: Any = None
    c_value_interval: Any = None
    step: Any = None
    limits: Any = None
    bounds: Any = None
    default: Any = None
    decimals: int = 3

    title: str | None = None
    delay: float = Field(default=0.1, gt=0)
    name: str | None = None
    enum: Type[Enum] | None = None
    expanded: bool = True
    readonly: bool | None = False
    movable: bool = False
    dropEnabled: bool = False
    renamable: bool = False
    compactHeight: bool = False
    prefix: str | list[str] = ''

    # custom
    c_numeric_group: bool = False
    c_nullable_value: bool = False
    c_group_prefixes: list[str] | None = None
    c_coerce_to_limits: bool = False
    c_auto_expand: bool = False
    c_auto_collapse: bool = False
    # c_group_singles: bool = False

    def keys(self):
        return set(self.model_fields.keys()).union(
            set(self.model_extra.keys()))

    def __contains__(self, item):
        return item in self.keys()

    @classmethod
    def from_field(cls, key, value,
                   parent_model, **options) -> ParamOpts:

        field_info = parent_model.model_fields[key]
        json_schema_extra = get_field_json_schema_extra(field_info)

        options.update(json_schema_extra)

        options = cls(**options)

        if options.c_data_types is None:
            raise AssertionError

        if key == 'scale_factor':
            pass

        options.c_model_field_info = field_info

        if options.name is None:
            options.name = key

        options.value = value

        if b_field_has_default(field_info=field_info):
            options.default = field_info.default

        if field_info.title:
            options.title = field_info.title

        if not isinstance(options.c_data_types, UnionType):
            options.type = options.c_data_types.__name__
        else:
            options.type = UnionType.__name__

        if options.c_data_types == Enum:
            # see pyqtgraphQtEnumParameter
            options.enum = extract_type_from_annotation(
                field_info.annotation, type_=Enum)

        options.c_nullable_value = (
            b_annotation_includes_type(
                field_info.annotation, type_=NoneType))

        options.c_model_field_name = key

        if options.c_group_prefixes is not None:
            if isinstance(options.c_group_prefixes, list):
                name = options.name
                if name in options.c_group_prefixes:
                    options.prefix = name + ': '

        if options.c_data_types in [float, int]:
            options.c_value_interval = extract_field_interval(field_info)
            multiple_of = get_field_multiple_of(field_info)

            if multiple_of is not None:
                options.step = multiple_of
            else:
                is_int = b_is_int_annotation(field_info.annotation, True)
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
                if b_is_literal_annotation(options.c_model_field_info,
                                           b_strict=False):
                    options.limits = extract_literal_values(
                        options.c_model_field_info.annotation)
                else:
                    raise ValueError
        return options

    @classmethod
    def from_model(cls, model: BaseModel, name_=None):

        opts = getattr(model, ParamOpts.CLASS_VAR_KEY, {})
        if opts is None:
            opts = {}
        elif isinstance(opts, BaseModel):
            opts = opts.model_dump(mode='python')

        opts = cls(**opts)
        if model.model_config.get('frozen', False) is True:
            opts.readonly = True

        if name_ is not None:
            opts.name = name_
        elif opts.name is None:
            opts.name = model.__class__.__name__

        return opts

    def get(self, item, default=None):
        return getattr(self, item, default)

    def __getitem__(self, item):
        return getattr(self, item)

    @classmethod
    def heritable_options(cls, **opts):
        res = {}
        for k in [ParamOpts.KW.READONLY,
                  ParamOpts.KW.RENAMABLE,
                  ParamOpts.KW.MOVABLE,
                  ParamOpts.KW.C_GROUP_PREFIXES,
                  ParamOpts.KW.C_NULLABLE_VALUE,
                  ParamOpts.KW.C_COERCE_TO_LIMITS,
                  ParamOpts.KW.DELAY,
                  ]:
            res[k] = opts[k]
        return res

    def __iter__(self):
        return iter(self.model_dump())

    def __len__(self):
        return len(self.keys())

    def model_dump(self, **kwargs):
        return super().model_dump(include=self.keys(), **kwargs)

    def __setitem__(self, key, value):
        setattr(self, key, value)
    # noinspection PyNestedDecorators

    @field_validator('c_group_prefixes', mode='before')
    @classmethod
    def validate_c_group_prefixes(cls, v):
        if v is None:
            v = []
        if isinstance(v, str):
            v = v.split(cls.PREFIX_PATTERN_SEP)
        return v


class FrozenParamOpts(ParamOpts, frozen=True):
    @classmethod
    def from_field(cls, **kwargs) -> FrozenParamOpts:
        return cls(**super().from_field(**kwargs))


def p_field(default, readonly=False, **kwargs):
    res = Field(
        default=default,
        json_schema_extra={
            ParamOpts.KW.READONLY: readonly,
        },
        **kwargs)
    return res
