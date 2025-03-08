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


# noinspection PyPep8Naming
class SpatialNetwork(EngineElement):

    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        FiniteGridConfig: FiniteGrid,
        NetworkReservoirConfig: NetworkReservoir,
        NeuronStateModel: NeuronState,
    }

    config_model: NetworkConstructionConfig

    def __init__(self, model: NetworkConstructionConfig, device, **kwargs):

        self.data: dict[EngineElementConfig, EngineElement] | None = None

        super().__init__(build_model=model.elements,
                         device=device,
                         config_model=model,
                         node_tree=EngineNodes(root=model),
                         root_element=self,
                         )

        p = self[model.elements[1]].neuron_states.parent_element

        self.grid: FiniteGrid = self.add_build(self.config_model.grid)
