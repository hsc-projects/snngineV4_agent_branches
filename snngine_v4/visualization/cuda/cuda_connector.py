from collections import UserDict
from typing import Callable, ClassVar, Iterable, Type

import numpy as np
import torch
from pydantic import BaseModel
from vispy.gloo import get_current_canvas
from vispy.visuals import MarkersVisual, Visual

from snngine_v4.utils.containers.mappings import (
    Int2ObjectMapConfig,
    Model2ObjectMap, Object2ObjectMap,
)
from snngine_v4.visualization.cuda.gl_interop.gl_tensor import (
    CudaRegister, GLTensorDict, GLVBOTensor,
)
from snngine_v4.visualization.scenes.main_network_scene import EngineSceneCanvas


class CudaVispyConnector(CudaRegister):

    @classmethod
    def get_buffer(cls, item: Visual | Model2ObjectMap, model: BaseModel = None):
        res = GLTensorDict()
        if isinstance(item, MarkersVisual):
            # noinspection PyUnresolvedReferences,PyProtectedMember
            gl_id = cls.gl_buffer_id(item._vbo.id)
            gl_tensor = GLVBOTensor(
                opengl_id=gl_id,
                shape=(len(model.pos), 14
                       # self._config.technical.vispy_scatter_plot_stride
                       ),
                device=0)
            res['vbo'] = gl_tensor
            print(gl_tensor)
        else:
            pass
            # raise NotImplementedError
        return res

    @classmethod
    def get_buffers(cls, item: Visual | Model2ObjectMap):

        if isinstance(item, EngineSceneCanvas):
            item.set_current()
            item._draw_scene()
            item = item.visual_node_dict
            res = Model2ObjectMap()
        else:
            raise NotImplementedError

        if isinstance(item, Model2ObjectMap):
            for k, v in item.items():
                model = item.inv[v]
                assert id(model) == k
                k = model
                buffs = cls.get_buffer(v, model)
                res[k] = buffs
        else:
            raise NotImplementedError
        return res

    @staticmethod
    def gl_buffer_id(glir_id):
        # noinspection PyProtectedMember
        return int(get_current_canvas().context.shared.parser._objects[glir_id]
                   .handle)
