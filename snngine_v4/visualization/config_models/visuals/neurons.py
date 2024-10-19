from snngine_v4.nn.config_models.nn_reservoir_config import NetworkReservoir
from snngine_v4.visualization.config_models.visuals.markers import \
    MarkersVisualConfig


class NeuronMarkersVisualConfig(MarkersVisualConfig):

    reservoir: NetworkReservoir
