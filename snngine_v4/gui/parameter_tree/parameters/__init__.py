from pyqtgraph.parametertree import (
    registerParameterType,
)
from pyqtgraph.parametertree.parameterTypes import (
    QtEnumParameter,
)

from snngine_v4.gui.parameter_tree.parameters.none_type_parameter import (
    NoneTypeParameter)


registerParameterType('Enum', QtEnumParameter, override=True)
registerParameterType('NoneType', NoneTypeParameter, override=True)
