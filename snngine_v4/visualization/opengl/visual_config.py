# from __future__ import annotations
#
# from enum import auto, IntEnum
# from typing import ClassVar, NamedTuple
#
# from PySide6.QtWidgets import QMainWindow
# from vispy.scene import SceneCanvas, ViewBox
#
# from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
#
#
# class EngineObjectKeys:
#
#     ENGINE_LOCATION_KEY = 'vispy_location'
#     UNFREEZE: ClassVar[str] = 'unfreeze'
#     MODIFIER_ARROWS_KEY = 'modifier_arrows'
#
#     PARENT_NODE_KEY: ClassVar[str] = "parent"
#     CHILDREN_NODE_KEY: ClassVar[str] = "children"
#
#     CUDA_NODE_KEY: ClassVar[str] = "cuda_node"
#
#
# class GLBufferType(IntEnum):
#     INDEX = 0
#     POS = auto()
#     COLOR = auto()
#     NORMALS = auto()
#
#
# class VisualEngineObjectConfig(XMLSettingsModel):
#     name: str | None = None
#     interactive: bool | None = None
#
#
# class VispyObjectLocation(NamedTuple):
#
#     view: ViewBox | None
#     scene: SceneCanvas | None
#     window: QMainWindow | None
#
#     def set_current(self):
#         self.scene.set_current()
#
#     def add(self, obj):
#         self.view.add(obj)
#         # noinspection PyProtectedMember
#         self.scene._draw_scene()
