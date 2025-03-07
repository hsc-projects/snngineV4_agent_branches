from typing import ClassVar

from snngine_v4.geometry.grid.finite_grid import FiniteGrid
from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.nn.construction.config_models.neurons.neuron_state import \
    NeuronStateModel
from snngine_v4.nn.construction.config_models.nn_builder_config import \
    NetworkConstructionConfig
from snngine_v4.nn.construction.config_models.engine_element_config \
    import EngineElementConfig
from snngine_v4.nn.construction.config_models.reservoir.nn_reservoir_config \
    import NetworkReservoirConfig
from snngine_v4.nn.neuron_states import NeuronState

from snngine_v4.nn.spnn_reservoir import NetworkReservoir
from snngine_v4.nn.construction.engine_element import EngineElement, EngineNodes
from snngine_v4.utils.cuda_utils.tensor_dataframe import (
    TensorDataFrame,
    TensorSeries,
)
from snngine_v4.utils.cuda_utils.tensor_dict import TensorDict
from snngine_v4.utils.data_utils.dataframe_config import (
    SeriesBase,
    TypedDataFrameBase,
    TypedDataFrameBase3D,
)

# from snngine_v4.utils.object_builder.object_builder import \
#     ObjectInitializationType


# noinspection PyPep8Naming
class SpatialNetwork(EngineElement):

    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        FiniteGridConfig: FiniteGrid,
        NetworkReservoirConfig: NetworkReservoir,
        NeuronStateModel: NeuronState,
    }

    BUILDER_OBJECT_SUPERCLASS_MAP: ClassVar = {
        TypedDataFrameBase3D: TensorDict,  # Keep order (1/3)
        TypedDataFrameBase: TensorDataFrame,  # Keep order (2/3)
        SeriesBase: TensorSeries,  # Keep order (3/3)
        EngineElementConfig: EngineElement,
    }

    # OBJECT_INIT_SUPER_TYPES = {
    #     TypedDataFrameBase3D: ObjectInitializationType.MODEL,
    #     EngineElementConfig: ObjectInitializationType.MODEL,
    #     # NeuronStateModel: ObjectInitializationType.MODEL
    # }

    config_model: NetworkConstructionConfig

    def __init__(self, model: NetworkConstructionConfig, device, **kwargs):

        self.data: dict[EngineElementConfig, EngineElement] | None = None

        super().__init__(model=model.elements,
                         device=device,
                         config_model=model,
                         node_tree=EngineNodes(root=model),
                         root_element=self,
                         )

        p = self[model.elements[1]].neuron_states.parent_element

        self.grid: FiniteGrid = self.add_build(self.config_model.grid)
