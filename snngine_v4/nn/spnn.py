from functools import cached_property
from typing import ClassVar

from snngine_v4.geometry.grid.finite_grid import FiniteGrid
from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.nn.construction.config_models.neurons.neuron_state import \
    NeuronStateModel
from snngine_v4.nn.construction.config_models.spnn_config import \
    SpatialNetworkConfig
from snngine_v4.nn.construction.config_models.engine_element_config \
    import EngineElementConfig
from snngine_v4.nn.construction.config_models.reservoir.nn_reservoir_config \
    import NetworkReservoirConfig
from snngine_v4.nn.neuron_states import NeuronState
from snngine_v4.nn.sim.simulator import Simulator
from snngine_v4.nn.sim.sim_parameters import SimulatorOptions

from snngine_v4.nn.spnn_reservoir import NetworkReservoir
from snngine_v4.nn.construction.engine_element import EngineElement, EngineNodes


type GetNetworkElementType = (int | EngineElementConfig
                              | EngineElement | NetworkReservoirConfig)
type NetworkElementType = NetworkReservoir | EngineElement


# noinspection PyPep8Naming
class SpatialNetwork(EngineElement):
    """

    """

    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        FiniteGridConfig: FiniteGrid,
        NetworkReservoirConfig: NetworkReservoir,
        NeuronStateModel: NeuronState,
        SimulatorOptions: Simulator,
    }

    config_model: SpatialNetworkConfig

    def __init__(self, model: SpatialNetworkConfig, device, **kwargs):

        self.data: dict[EngineElementConfig, EngineElement] | None = None

        node_tree = EngineNodes(root=model)

        super().__init__(build_model=model.elements,
                         device=device,
                         config_model=model,
                         node_tree=node_tree,
                         root_element=self,
                         )

        for elt_conf in self.config_model.elements:
            elt = self[elt_conf]
            if isinstance(elt, NetworkReservoir):
                elt.fill_tensors()

        p = self.get_network_element(0).neuron_states.parent_element()
        self.add_build(self.config_model.grid,
                       parent_model=self.config_model,
                       b_default_build_kwargs=False)
        self.add_build(self.config_model.simulator,
                       parent_model=self.config_model)

    # @cached_property
    # def engine_build_kwargs(self):
    #     return {
    #         CudaKeywords.DEVICE: self.device,
    #         self.NODE_TREE_KW: self.node_tree,
    #         self.ROOT_ELEMENT_KW: self,
    #         self.PARENT_ELEMENT_KW: self,
    #     }

    def configure_simulator(self, element: GetNetworkElementType):
        self.simulator.add_simulation(
            element=self.get_network_element(element))

    def get_network_element(
            self, index_or_model: GetNetworkElementType) -> NetworkElementType:
        if isinstance(index_or_model, int):
            index_or_model = self.config_model.elements[index_or_model]
        elif isinstance(index_or_model, EngineElement):
            return index_or_model
        return self[index_or_model]

    @cached_property
    def grid(self) -> FiniteGrid:
        return self[self.config_model.grid]

    @cached_property
    def simulator(self) -> Simulator:
        return self[self.config_model.simulator]
