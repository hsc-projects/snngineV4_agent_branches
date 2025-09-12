from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from snngine_v4.nn.construction.config_models.engine_element_config import (
    EngineElementConfig, EngineElementConfigMixin,
)
from snngine_v4.nn.construction.engine_element import EngineElement
from snngine_v4.utils.cuda_utils.tensor_dataframe import TensorSeries
from snngine_v4.utils.settings.ui_parameter_options import FrozenParamOpts
from snngine_v4.visualization.config_models.plotting.multi_line_plot import (
    MultiLinePlotConfig,
    MultiScatterPlotConfig, LinePlotConfigBase,
)


class EngineMultiLinePlotConfig(MultiLinePlotConfig,
                                EngineElementConfigMixin):
    pass


class EngineMultiScatterPlotConfig(MultiScatterPlotConfig,
                                   EngineElementConfigMixin):
    pass


class PlotElement(EngineElement):
    config_model: MultiLinePlotConfig

    map: TensorSeries

    def pos_vbo(self):
        return self.cuda_gl_dict['pos_vbo']

    # def set_tensor_attr(self):
    #     super().set_tensor_attr()
    #     # setattr(self, self.config_model.MAP_KW, self[self.config_model.map])


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

    def plot_config_dict(self, **kwargs):
        return self.filtered_model_dict(
            type_filter=LinePlotConfigBase, **kwargs)

    def plot_config_values(self, **kwargs):
        return self.filtered_model_values(
            type_filter=LinePlotConfigBase, **kwargs)


class CudaBackendPlotTensors(EngineElement):
    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        EngineMultiLinePlotConfig: PlotElement,
    }

    config_model: CudaBackendPlotConfig

