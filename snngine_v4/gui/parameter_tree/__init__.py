from pyqtgraph.parametertree import (
    registerParameterType,
)
from pyqtgraph.parametertree.parameterTypes import (
    QtEnumParameter,
    SimpleParameter, StrParameterItem,
)

from snngine_v4.utils.settings.settings_keywords import PGParOption


class NoneTypeParameter(SimpleParameter):

    def __init__(self, **opts):
        opts[PGParOption.READONLY] = True
        opts[PGParOption.REMOVABLE] = True
        super().__init__(**opts)

    @property
    def itemClass(self):
        return StrParameterItem


registerParameterType('Enum', QtEnumParameter, override=True)
registerParameterType('NoneType', NoneTypeParameter, override=True)
