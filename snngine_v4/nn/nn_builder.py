from typing import ClassVar

from snngine_v4.geometry.grid.finite_grid import FiniteGrid
from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.nn.config_models.nn_builder_config import \
    NetworkConstructionConfig

from snngine_v4.utils.settings.object_builder import (
    BuilderDict,
)


class NetworkBuilder(BuilderDict):

    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        FiniteGridConfig: FiniteGrid
    }

    def __init__(self, model: NetworkConstructionConfig = None,
                 b_initial_build: bool = True):

        super().__init__()

        if (b_initial_build is True) and (model is not None):
            self.update(model)

    def update(self, m, **kwargs) -> None:
        self.destroy()
        super().update(m, **kwargs)

        data = self.data

        return

    def destroy(self):
        del self.data
        del self.model2key_map
        self.data = {}
        self.model2key_map = {}
