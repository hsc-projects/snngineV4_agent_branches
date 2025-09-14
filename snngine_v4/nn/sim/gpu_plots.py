from __future__ import annotations

from functools import cached_property
from typing import ClassVar

from snngine_v4.gui.parameter_tree.cuda_connector import GLBufferTypes
from snngine_v4.nn.construction.engine_element import EngineElement
from snngine_v4.nn.sim.sim_parameters import (CudaBackendPlotConfig,
                                              EngineMultiLinePlotConfig,
                                              EngineMultiScatterPlotConfig)
from snngine_v4.utils.cuda_utils.tensor_dataframe import TensorSeries
from snngine_v4.visualization.config_models.plotting.multi_line_plot import (
    MultiLinePlotConfig,
)
from snngine_v4.visualization.cuda.gl_interop.gl_tensor import GLBufferTensor


class PlotElement(EngineElement):
    config_model: MultiLinePlotConfig

    map: TensorSeries

    @cached_property
    def pos_vbo(self) -> GLBufferTensor:
        return self.cuda_gl_dict[GLBufferTypes.POS_VBO.name]

    # def set_tensor_attr(self):
    #     super().set_tensor_attr()
    #     # setattr(self, self.config_model.MAP_KW, self[self.config_model.map])


class CudaBackendPlotTensors(EngineElement):
    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        EngineMultiLinePlotConfig: PlotElement,
        EngineMultiScatterPlotConfig: PlotElement,
    }

    config_model: CudaBackendPlotConfig

