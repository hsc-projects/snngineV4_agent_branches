from __future__ import annotations

from typing import Callable, ClassVar, TYPE_CHECKING

from snngine_v4.construction.engine_element import EngineElement
from snngine_v4.nn.sim.gpu_plots import (
    CudaBackendPlotTensors, )
from snngine_v4.nn.sim.sim_parameters import (CudaBackendPlotConfig,
                                              SimulatorOptions)
from snngine_v4.nn.sim.simulation import Simulation, SimulationModel

from snngine_v4.nn.spnn_reservoir import NetworkReservoir
from snngine_v4.utils.containers.mappings import (
    Object2ObjectMap,
)


if TYPE_CHECKING:
    from snngine_v4.nn.spnn import GetNetworkElementType, SpatialNetwork


class Simulator(EngineElement):
    """

    """

    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        CudaBackendPlotConfig: CudaBackendPlotTensors,
        SimulationModel: Simulation
    }

    parent_element: Callable[..., SpatialNetwork]
    root_element: SpatialNetwork

    config: SimulatorOptions

    plots: CudaBackendPlotTensors

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.backends = Object2ObjectMap()

    def make_simulation_instance(self, element: NetworkReservoir):
        if self.b_cuda_backend_available is False:
            return None

        simulation = self.add_build(model=SimulationModel(),
                                    element=element,
                                    parent_model=self.config)

        return simulation

    def add_simulation(self, element: GetNetworkElementType):
        element = self.root_element.get_network_element(element)
        self.backends[element] = self.make_simulation_instance(element=element)

    def run_sim(self, element):
        element = self.root_element.get_network_element(element)

