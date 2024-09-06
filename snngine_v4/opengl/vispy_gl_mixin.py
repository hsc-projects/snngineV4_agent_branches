from __future__ import annotations

from enum import auto, IntEnum

from vispy.gloo import get_current_canvas
from vispy.util import Frozen

from snngine_v4.opengl.visual_object_config_model import VisualObjectConfigModel
from snngine_v4.utils.containers.configurable_dict import ConfigurableDict


class GLBufferType(IntEnum):
    INDEX = 0
    POS = auto()
    COLOR = auto()
    NORMALS = auto()


class VispyGLMixin:

    def __init__(self: VispyGLMixin | Frozen,
                 visual_config: VisualObjectConfigModel | None = None):

        frozen = hasattr(self, 'unfreeze')
        if frozen:
            self.unfreeze()
        self.gl_buffer_ids = ConfigurableDict.from_type(type_=int)

        if visual_config is None:
            visual_config = VisualObjectConfigModel()
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
