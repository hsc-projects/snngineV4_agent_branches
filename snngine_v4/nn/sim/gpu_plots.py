from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from snngine_v4.nn.construction.config_models.engine_element_config import \
    EngineElementConfig
from snngine_v4.nn.construction.engine_element import EngineElement
from snngine_v4.visualization.config_models.plotting.multi_line_plot import (
    MultiPlotConfig,
    PlotConfig,
)


class PlotElement(EngineElement):
    config_model: MultiPlotConfig


class CudaBackendPlotTensors(EngineElement):

    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        MultiPlotConfig: PlotElement,
    }

    config_model: CudaBackendPlotConfig


class CudaBackendPlotConfig(EngineElementConfig):

    current_plot_config: MultiPlotConfig = Field(
        default_factory=lambda: MultiPlotConfig(
            size_x=100
        ),
    )

    voltage_plot_config: MultiPlotConfig = Field(
        default_factory=lambda: MultiPlotConfig(
            size_x=100
        ),
    )

    def plot_config_dict(self, **kwargs):
        return self.filtered_model_dict(type_filter=PlotConfig, **kwargs)

    def plot_config_values(self, **kwargs):
        return self.filtered_model_values(type_filter=PlotConfig, **kwargs)
