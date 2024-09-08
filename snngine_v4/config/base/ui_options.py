from typing import ClassVar

from pydantic_settings import BaseSettings


# class JSEKW:
#     """
#     'json_schema_extra' keywords
#     """
#     # ENUM: ClassVar[str] = 'enum'
#     B_READ_ONLY: ClassVar[str] = 'b_read_only'
#
#     SUFFIX: ClassVar[str] = 'suffix'


class PGParameterOptionKW:

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

    LIMITS: ClassVar[str] = 'limits'
    SUFFIX: ClassVar[str] = 'suffix'


class ParameterUIOpts(BaseSettings):
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
    UI_OPTIONS_KEYWORD: ClassVar[str] = 'ui_opts'

    title: str | None = None
    name: str | None = None
    expanded: bool = True
    readonly: bool = False
    movable: bool = False
    dropEnabled: bool = False
