from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings


class PGParOption:

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

    # Custom
    CUSTOM_FIELD_NAME: ClassVar[str] = 'c_field_name'
    CUSTOM_NUMERIC_GROUP: ClassVar[str] = 'c_numeric'


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
    UI_OPTIONS_KEYWORD: ClassVar[str] = 'parameter_ui_opts'
    PREFIX_PATTERN_SEP: ClassVar[str] = ','
    XYZ_PREFIX_PATTERN: ClassVar[str] = '{XYZ}'

    title: str | None = None
    name: str | None = None
    expanded: bool = True
    readonly: bool = False
    movable: bool = False
    dropEnabled: bool = False
    renamable: bool = False
    prefix: str = ''

    # custom
    c_numeric: bool = False

    # noinspection PyNestedDecorators
    @field_validator('prefix', mode='before')
    @classmethod
    def convert_none(cls, v):
        if v is None:
            v = ''
        return v

    @classmethod
    def pop_ui_options_keyword(cls, dct: dict, b_recursive: bool = True):
        key_list = list(dct.keys())
        for k in key_list:
            if k == cls.UI_OPTIONS_KEYWORD:
                dct.pop(cls.UI_OPTIONS_KEYWORD)
            elif b_recursive and isinstance(dct[k], dict):
                dct[k] = cls.pop_ui_options_keyword(dct[k], b_recursive=True)
        return dct


class InternalOpts(BaseSettings, frozen=True):
    class Slots:
        TECHNICAL: ClassVar[str] = 'technical'


class BaseSettingsSlots:

    FROZEN: ClassVar[str] = 'frozen'

    XML_FILE: ClassVar[str] = 'xml_file'

    SUB_SETTINGS_FILE_NAME_PATTERN: ClassVar[str] = '{sub_settings}'

    @classmethod
    def b_is_frozen(cls, model: BaseModel) -> bool:
        # noinspection PyTypedDict
        return model.model_config.get(
            cls.FROZEN, False)
