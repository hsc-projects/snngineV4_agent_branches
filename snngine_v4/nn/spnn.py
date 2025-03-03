from typing import ClassVar

from snngine_v4.geometry.grid.finite_grid import FiniteGrid
from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.nn.config_models.nn_builder_config import \
    NetworkConstructionConfig
from snngine_v4.nn.config_models.nn_element_config import EngineElementConfig
from snngine_v4.nn.config_models.reservoir.nn_reservoir_config import \
    NetworkReservoirConfig


from snngine_v4.nn.spnn_reservoir import NetworkReservoir
from snngine_v4.nn.engine_element import EngineElement
from snngine_v4.utils.object_builder.object_builder import \
    ObjectInitializationType
from snngine_v4.utils.object_builder.object_builder_dict import BuilderDict


# noinspection PyPep8Naming
class SpatialNetwork(BuilderDict):

    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        FiniteGridConfig: FiniteGrid,
        NetworkReservoirConfig: NetworkReservoir,}

    BUILDER_OBJECT_SUPERCLASS_MAP: ClassVar = {
        EngineElementConfig: EngineElement,}

    OBJECT_INIT_SUPER_TYPES = {
        EngineElementConfig: ObjectInitializationType.MODEL}

    def __init__(self, model: NetworkConstructionConfig, device, **kwargs):

        self.model: NetworkConstructionConfig = model
        self.data: dict[EngineElementConfig, EngineElement] | None = None
        self.device = device

        super().__init__(model_container=self.model.elements,
                         build_kwargs={'device': self.device})

        self.grid: FiniteGrid = self.add_build(self.model.grid)

