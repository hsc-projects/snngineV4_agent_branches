from pyqtgraph.parametertree import registerParameterType


from snngine_v4.gui.parameter_tree.parameters.tensor_parameter import \
    TensorParameter, TensorDictParameter
from snngine_v4.nn.config_models.reservoir.reservoir_flags import (
    LG2LGFlags,
    LG2LGProp, LGroupFlags,
    NeuronFlags,
)


registerParameterType(NeuronFlags.__name__, TensorDictParameter, override=True)
registerParameterType(LGroupFlags.__name__, TensorDictParameter, override=True)
registerParameterType(LG2LGFlags.__name__, TensorDictParameter, override=True)
registerParameterType(LG2LGProp.__name__, TensorDictParameter, override=True)
# registerParameterType(LG2LGFlags.__name__, TensorParameter, override=True)
