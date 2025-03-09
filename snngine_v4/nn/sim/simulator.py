from typing import ClassVar

from snngine_v4.nn.construction.engine_element import EngineElement
from snngine_v4.nn.sim.gpu_plots import (
    CudaBackendPlotConfig,
    CudaBackendPlotTensors,
)
from snngine_v4.utils.settings.config_model import ConfigModel


class SimulatorOptions(ConfigModel):

    T: int = 1000

    plots: CudaBackendPlotConfig


class Simulator(EngineElement):

    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        CudaBackendPlotConfig: CudaBackendPlotTensors,
    }
