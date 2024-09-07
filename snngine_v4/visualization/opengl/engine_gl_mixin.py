from __future__ import annotations

from enum import IntEnum

from vispy.gloo import get_current_canvas
from vispy.util import Frozen

from snngine_v4.visualization.opengl.visual_config import (
    GLBufferType, VisualEngineObjectConfig,
)
from snngine_v4.utils.containers.configurable_dict import ConfigurableDict


class EngineGLMixin:

    def __init__(self: EngineGLMixin | Frozen,
                 visual_config: VisualEngineObjectConfig | None = None):

        frozen = hasattr(self, 'unfreeze')
        if frozen:
            self.unfreeze()
        self.gl_buffer_ids = ConfigurableDict.from_type(type_=int)

        if visual_config is None:
            visual_config = VisualEngineObjectConfig()
        self.visual_config = visual_config

        if frozen:
            self.freeze()

    @staticmethod
    def gl_buffer_id(glir_id):
        # noinspection PyProtectedMember
        return int(get_current_canvas().context.shared.parser._objects[glir_id]
                   .handle)

    def get_glir_id(self, buffer_type: GLBufferType | IntEnum | str):
        raise NotImplementedError

    def get_gl_buffer_id(self, buffer_type: GLBufferType | IntEnum | str):
        if isinstance(buffer_type, IntEnum):
            buffer_type = buffer_type.name
        if buffer_type not in self.gl_buffer_ids:
            glir_id = self.get_glir_id(buffer_type)
            self.gl_buffer_ids[buffer_type] = self.gl_buffer_id(
                glir_id=glir_id)
        return self.gl_buffer_ids[buffer_type]
