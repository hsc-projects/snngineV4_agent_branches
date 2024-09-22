from __future__ import annotations

from typing import ClassVar

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class ParamOpts(BaseSettings, frozen=True):

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

    class KW:

        ParamOpts: ClassVar[str] = 'parameter_ui_opts'

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
        SUFFIX: ClassVar[str] = 'suffix'
        ENUM: ClassVar[str] = 'enum'
        DELAY: ClassVar[str] = 'delay'

        # Custom
        C_MODEL_FIELD_NAME: ClassVar[str] = 'c_model_field_name'
        C_NUMERIC_GROUP: ClassVar[str] = 'c_numeric_group'
        C_NULLABLE_VALUE: ClassVar[str] = 'c_nullable_value'
        C_COERCE_TO_LIMITS: ClassVar[str] = 'c_coerce_to_limits'
        C_VALUE_INTERVAL: ClassVar[str] = 'c_value_interval'
        C_AUTO_COLLAPSE: ClassVar[str] = 'c_auto_collapse'
        C_AUTO_EXPAND: ClassVar[str] = 'c_auto_expand'
        C_NONE_MEANS_UNKNOWN: ClassVar[str] = 'c_none_means_unknown'
        C_DATA_TYPES: ClassVar[str] = 'c_data_types'
        # C_VALUE_INTERVAL: ClassVar[str] = 'c_value_interval'

    title: str | None = None
    delay: float = Field(default=0.1, gt=0)
    name: str | None = None
    expanded: bool = True
    readonly: bool | None = False
    movable: bool = False
    dropEnabled: bool = False
    renamable: bool = False
    prefix: str = ''

    # custom
    c_numeric_group: bool = False
    c_coerce_to_limits: bool = False
    c_auto_expand: bool = False
    c_auto_collapse: bool = False
    # c_group_singles: bool = False

    # noinspection PyNestedDecorators
    @field_validator('prefix', mode='before')
    @classmethod
    def convert_none(cls, v):
        if v is None:
            v = ''
        return v


def p_field(default, readonly=False, **kwargs):
    res = Field(
        default=default,
        json_schema_extra={
            ParamOpts.KW.READONLY: readonly,
        },
        **kwargs)
    return res
