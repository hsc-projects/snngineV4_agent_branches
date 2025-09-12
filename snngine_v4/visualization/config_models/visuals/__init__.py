from snngine_v4.geometry.grid_config import FiniteGridConfig

from snngine_v4.visualization.config_models.visuals.lines import (
    LineConnectType,
    LineVisualConfig,
)
from snngine_v4.visualization.config_models.visuals.markers import \
    MarkersVisualConfig

from snngine_v4.nn.construction.config_models.spnn_config \
    import NetworkReservoirConfig

type VisualConfig = (FiniteGridConfig | LineVisualConfig | MarkersVisualConfig
                     | NetworkReservoirConfig)
