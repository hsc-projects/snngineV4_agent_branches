from __future__ import annotations

from functools import cached_property
from typing import ClassVar

from pydantic import Field

from snngine_v4.nn.construction.config_models.engine_element_config import \
    (
    EngineElementConfig, EngineElementConfigMixin,
)
from snngine_v4.nn.construction.engine_element import EngineElement
from snngine_v4.utils.cuda_utils.tensor_dataframe import TensorSeries
from snngine_v4.utils.settings.ui_parameter_options import FrozenParamOpts
from snngine_v4.visualization.config_models.plotting.multi_line_plot import (
    MultiPlotConfig,
    PlotConfig,
)


class EngineMultiPlotConfig(MultiPlotConfig, EngineElementConfigMixin):
    pass



class PlotElement(EngineElement):
    config_model: MultiPlotConfig

    map: TensorSeries

    def pos_vbo(self):
        return self.cuda_gl_dict['pos_vbo']


    def set_tensor_attr(self):
        super().set_tensor_attr()
        setattr(self, self.config_model.MAP_KW, self[self.config_model.map])


class CudaBackendPlotConfig(EngineElementConfig):

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        expanded=False)

    current_plot: EngineMultiPlotConfig = Field(
        default_factory=lambda: EngineMultiPlotConfig(
            size_x=100
        ),
    )

    voltage_plot: EngineMultiPlotConfig = Field(
        default_factory=lambda: EngineMultiPlotConfig(
            size_x=100
        ),
    )

    def plot_config_dict(self, **kwargs):
        return self.filtered_model_dict(type_filter=PlotConfig, **kwargs)

    def plot_config_values(self, **kwargs):
        return self.filtered_model_values(type_filter=PlotConfig, **kwargs)


class CudaBackendPlotTensors(EngineElement):

    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        MultiPlotConfig: PlotElement,
    }

    config_model: CudaBackendPlotConfig

