from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.nn.config_models.nn_reservoir_config import NetworkReservoir
from snngine_v4.visualization.config_models.visuals.lines import \
    LineVisualConfig
from snngine_v4.visualization.config_models.visuals.markers import \
    MarkersVisualConfig

type VisualConfig = (FiniteGridConfig | LineVisualConfig | MarkersVisualConfig
                     | NetworkReservoir)

