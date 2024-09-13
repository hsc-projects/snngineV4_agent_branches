from pyqtgraph.parametertree import registerParameterType
from pyqtgraph.parametertree.parameterTypes import QtEnumParameter


registerParameterType('Enum', QtEnumParameter, override=True)
