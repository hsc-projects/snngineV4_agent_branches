from enum import Enum
from types import NoneType, UnionType
from typing import Union

from pyqtgraph.parametertree import registerParameterType
from pyqtgraph.parametertree.parameterTypes import (
    QtEnumParameter,
)

from snngine_v4.gui.parameters.none_type_parameter import (
    NoneTypeParameter, UndefinedTypeParameter,
)

from snngine_v4.gui.parameters.spin_box_slider_parameter import \
    SpinBoxSliderParameter
from snngine_v4.gui.parameters.array.array_parameter import (
    ArrayParameter,
)
from snngine_v4.gui.parameters.custom_list import \
    CustomListParameter
from snngine_v4.gui.parameters.multi_type_parameter import \
    MultiTypeParameter
from snngine_v4.gui.parameters.color_type_parameter import \
    ColorTypeParameter


from snngine_v4.gui.parameters.index_parameter import \
    IndexParameter
from snngine_v4.gui.parameters.array.tensor_parameter import (
    TensorDictParameter,
    TensorParameter,
)
from snngine_v4.utils.data_utils.dataframe_config import (
    SeriesModel,
    TypedDataFrameBase3D,
)
from snngine_v4.utils.data_utils.index_config import (
    InconsistentType,
    IndexConfig
)
from snngine_v4.visualization.config_models.visuals.parameters import (
    ColorTypeUnion, RGBAColorTypeUnion
)
from snngine_v4.utils.list_parameter_model import ListParameterModel
from snngine_v4.gui.parameters.linker_parameter import LinkerParameter

# noinspection DuplicatedCode
registerParameterType(Enum.__name__, QtEnumParameter, override=True)
registerParameterType(NoneType.__name__, NoneTypeParameter, override=True)
registerParameterType(InconsistentType.__name__, UndefinedTypeParameter,
                      override=True)

registerParameterType(UnionType.__name__, MultiTypeParameter, override=True)
registerParameterType(Union.__name__, MultiTypeParameter, override=True)
registerParameterType(int.__name__, SpinBoxSliderParameter, override=True)
registerParameterType(float.__name__, SpinBoxSliderParameter, override=True)

registerParameterType(ColorTypeUnion.__name__,
                      ColorTypeParameter, override=True)
registerParameterType(RGBAColorTypeUnion.__name__,
                      ColorTypeParameter, override=True)

registerParameterType('NDArray', ArrayParameter, override=True)

# noinspection DuplicatedCode
registerParameterType(ListParameterModel.__name__,
                      CustomListParameter, override=True)
registerParameterType(SeriesModel.__name__,
                      TensorParameter, override=True)
registerParameterType(TypedDataFrameBase3D.__name__,
                      TensorDictParameter, override=True)

registerParameterType(IndexConfig.__name__, IndexParameter, override=True)
# registerParameterType(RowOrColumn.__name__, IndexParameter, override=True)
# registerParameterType(Row.__name__, IndexParameter, override=True)
# registerParameterType(Column.__name__, IndexParameter, override=True)
registerParameterType(LinkerParameter.REGISTER_KW, LinkerParameter,
                      override=True)
