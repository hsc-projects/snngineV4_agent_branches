import torch

from snngine_v4.opengl.engine_visual_node import (
    EngineCompoundVisualNode,
    VispyObjectLocation,
)
from snngine_v4.opengl.visual_object_config_model import VisualObjectConfigModel


class CudaNodeMixin:
    pass


class EngineCompoundVisualCudaNode(EngineCompoundVisualNode):

    def __init__(self,
                 subvisuals: list,
                 visual_config: VisualObjectConfigModel = None,
                 vispy_location: VispyObjectLocation = None,
                 **kwargs):

        EngineCompoundVisualNode.__init__(
            self, visual_config=visual_config, vispy_location=vispy_location,
            subvisuals=subvisuals, **kwargs)

    def init_cuda_attributes(self, device: torch.device | None = None):
        if self.visual_config.cuda_attributes_initialized is True:
            raise RuntimeError('Cuda attributes already initialized')
        self._half_frozen_set_attr_and_ignore_none_value(
            self.DEVICE_ATTR, device)
        # self._cuda_device = device
        for x in self.cuda_children:
            if x._cuda_attributes_initialized is True:
                continue
            x.init_cuda_attributes(device)
        self._inner_init_cuda_attributes()
        self._cuda_attributes_initialized = True