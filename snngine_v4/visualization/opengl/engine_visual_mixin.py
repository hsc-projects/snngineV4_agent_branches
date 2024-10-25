# from __future__ import annotations
#
# from vispy.scene import Node
# from vispy.util import Frozen
#
# from snngine_v4.visualization.opengl.engine_gl_mixin import EngineGLMixin
# from snngine_v4.visualization.opengl.visual_config import (
#     VispyObjectLocation, VisualEngineObjectConfig, EngineObjectKeys,
# )
# from snngine_v4.utils.core_utils import PostInitCaller
#
#
# class EngineVisualMixin(EngineGLMixin, metaclass=PostInitCaller):
#
#     def __new__(cls, *arg, **kwargs):
#         print(f'Creating a new {cls.__name__} object...')
#         vispy_location: VispyObjectLocation = kwargs[
#             EngineObjectKeys.ENGINE_LOCATION_KEY]
#         vispy_location.set_current()
#         obj = object.__new__(cls)
#         return obj
#
#     def __init__(self,
#                  visual_config: VisualEngineObjectConfig,
#                  vispy_location: VispyObjectLocation = None):
#         self.vispy_location = vispy_location
#         super().__init__(visual_config=visual_config)
#
#     def __post_init__(self: EngineVisualMixin | Frozen | Node):
#         b_replace = False
#         p = None
#         if self.parent is not None:
#             b_replace = True
#             p = self.parent
#         self.vispy_location.add(self)
#         if b_replace is True:
#             self.parent = p
#         self.freeze()
