from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, ClassVar, Type

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings


def c_group_prefixes_validator(
        v: Type[Enum] | str | list[str], sep=',') -> list[str]:
    if v is None:
        v = []
    elif isinstance(v, str):
        v = v.split(sep)
    elif not isinstance(v, list):
        v = v._member_names_
    return v


GroupPrefixesType = Annotated[
    list[str], BeforeValidator(c_group_prefixes_validator)]


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

        ADD_TEXT: ClassVar[str] = 'addText'

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
        C_REQUIRES_REBUILD: ClassVar[str] = 'c_requires_rebuild'
        C_INITIAL_TYPE: ClassVar[str] = 'c_initial_type'
        C_ARRAY_INTERFACE: ClassVar[str] = 'c_array_interface'
        C_ARRAY_DEFAULT_VALUE: ClassVar[str] = 'c_array_default_value'
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
    c_group_prefixes: GroupPrefixesType = None
    c_coerce_to_limits: bool = False
    c_auto_expand: bool = False
    c_auto_collapse: bool = False
    c_requires_rebuild: bool = False
    c_array_default_value: float | int = 0

    def __contains__(self, item):
        return item in self.keys()

    def get(self, item, default=None):
        return getattr(self, item, default)

    def keys(self):
        return set(self.model_fields.keys()).union(
            set(self.model_extra.keys()))

    def items(self):
        return ((k, getattr(self, k)) for k in self.keys())

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

    def update(self, m=None, **kwargs):
        if m is not None:
            for k, v in m.items():
                setattr(self, k, v)
        for k, v in kwargs.items():
            setattr(self, k, v)


class FrozenParamOpts(ParamOpts, frozen=True):
    """"""


def p_field(default, readonly=False, **kwargs):
    res = Field(
        default=default,
        json_schema_extra={
            ParamOpts.KW.READONLY: readonly,
        },
        **kwargs)
    return res
