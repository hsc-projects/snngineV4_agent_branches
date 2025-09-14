from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from snngine_v4.nn.construction.config_models.engine_element_config import \
    (EngineElementConfig, EngineElementConfigMixin)
from snngine_v4.utils.settings.ui_parameter_options import FrozenParamOpts
from snngine_v4.visualization.config_models.plotting.multi_line_plot import \
    (LinePlotConfigBase, MultiLinePlotConfig, MultiScatterPlotConfig)


class EngineMultiLinePlotConfig(MultiLinePlotConfig,
                                EngineElementConfigMixin):
    pass


class EngineMultiScatterPlotConfig(MultiScatterPlotConfig,
                                   EngineElementConfigMixin):
    pass


class CudaBackendPlotConfig(EngineElementConfig):
    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        expanded=False)

    voltage_plot: EngineMultiLinePlotConfig = Field(
        default_factory=lambda: EngineMultiLinePlotConfig(
            size_x=100
        ),
    )
    firings_scatter_plot: EngineMultiScatterPlotConfig = Field(
        default_factory=lambda: EngineMultiScatterPlotConfig(
            size_x=100
        ),
    )

    group_firings_plot: EngineMultiLinePlotConfig = Field(
        default_factory=lambda: EngineMultiLinePlotConfig(
            size_x=200
        ),
    )

    def plot_config_dict(self, **kwargs):
        return self.filtered_model_dict(
            type_filter=LinePlotConfigBase, **kwargs)

    def plot_config_values(self, **kwargs):
        return self.filtered_model_values(
            type_filter=LinePlotConfigBase, **kwargs)


class SimulatorOptions(EngineElementConfig):
    """

    """

    T: int = 1000
    plots: CudaBackendPlotConfig
