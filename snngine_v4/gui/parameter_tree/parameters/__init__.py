from enum import Enum
from types import NoneType, UnionType

from pyqtgraph.parametertree import (
    registerParameterType,
)
from pyqtgraph.parametertree.parameterTypes import (
    QtEnumParameter,
)

from snngine_v4.gui.parameter_tree.parameters.multi_type_parameter import \
    MultiTypeParameter
from snngine_v4.gui.parameter_tree.parameters.none_type_parameter import (
    NoneTypeParameter)


registerParameterType(Enum.__name__, QtEnumParameter, override=True)
registerParameterType(NoneType.__name__, NoneTypeParameter, override=True)

registerParameterType(UnionType.__name__, MultiTypeParameter, override=True)
registerParameterType('NDArray', MultiTypeParameter, override=True)
