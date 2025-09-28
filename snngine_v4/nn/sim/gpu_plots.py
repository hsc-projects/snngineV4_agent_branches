from __future__ import annotations

from functools import cached_property
from typing import ClassVar

import torch

from snngine_v4.gui.parameter_trees.cuda_connector import GLBufferTypes
from snngine_v4.construction.engine_element import EngineElement
from snngine_v4.nn.sim.sim_parameters import (CudaBackendPlotConfig,
                                              EngineMultiLinePlotConfig,
                                              EngineMultiScatterPlotConfig)
from snngine_v4.utils.cuda_utils.tensor_dataframe import TensorSeries
from snngine_v4.visualization.config_models.plotting.multi_line_plot import (
    MultiLinePlotConfig,
)
from snngine_v4.visualization.cuda.gl_interop.gl_tensor import GLBufferTensor


class PlotElement(EngineElement):
    config: MultiLinePlotConfig

    map: TensorSeries

    @cached_property
    def pos_vbo_gl(self) -> GLBufferTensor:
        return self.cuda_gl_dict.str2gl[GLBufferTypes.POS_VBO.name]

    @cached_property
    def pos_vbo(self) -> torch.Tensor:
        return self.cuda_gl_dict[GLBufferTypes.POS_VBO.name]

    # def set_tensor_attr(self):
    #     super().set_tensor_attr()
    #     # setattr(self, self.config.MAP_KW, self[self.config.map])


class CudaBackendPlotTensors(EngineElement):
    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        EngineMultiLinePlotConfig: PlotElement,
        EngineMultiScatterPlotConfig: PlotElement,
    }

    config: CudaBackendPlotConfig

