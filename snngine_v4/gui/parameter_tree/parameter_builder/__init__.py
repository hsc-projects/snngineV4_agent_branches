from enum import Enum
from types import NoneType, UnionType

from pyqtgraph.parametertree import registerParameterType
from pyqtgraph.parametertree.parameterTypes import QtEnumParameter

from snngine_v4.gui.parameter_tree.parameters.array_parameter import \
    ArrayParameter
from snngine_v4.gui.parameter_tree.parameters.color_type_parameter import \
    ColorTypeParameter
from snngine_v4.gui.parameter_tree.parameters.multi_type_parameter import \
    MultiTypeParameter
from snngine_v4.gui.parameter_tree.parameters.none_type_parameter import \
    NoneTypeParameter
from snngine_v4.gui.parameter_tree.parameters.spin_box_slider_parameter import \
    SpinBoxSliderParameter
from snngine_v4.visualization.config_models.vispy_visual_parameters import (
    ColorType, ColorTypeUnion,
)


registerParameterType(Enum.__name__, QtEnumParameter, override=True)
registerParameterType(NoneType.__name__, NoneTypeParameter, override=True)

registerParameterType(UnionType.__name__, MultiTypeParameter, override=True)
registerParameterType(int.__name__, SpinBoxSliderParameter, override=True)
registerParameterType(float.__name__, SpinBoxSliderParameter, override=True)
registerParameterType('NDArray', ArrayParameter, override=True)

registerParameterType(ColorTypeUnion.__name__,
                      ColorTypeParameter, override=True)
