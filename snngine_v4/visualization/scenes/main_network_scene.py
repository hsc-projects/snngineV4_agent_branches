from pydantic import BaseModel
from vispy.scene import BaseCamera, SceneCanvas, ViewBox, VisualNode

from snngine_v4.utils.containers.configurable_dict import ConfigurableDict
from snngine_v4.utils.containers.mappings import (
    MappedDict, Object2KeyMap,
    Object2ObjectMap,
)


class EngineSceneCanvas(SceneCanvas):

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)

        self.unfreeze()

        self.camera_dict: dict[BaseModel, BaseCamera] = (
            Object2ObjectMap.from_types(BaseModel, BaseCamera))
        self.view_dict: dict[str, ViewBox] = (
            ConfigurableDict.from_type(ViewBox))
        self.visual_node_dict = MappedDict.from_type(VisualNode)
        self.visual_node_dict.object2key_map = Object2KeyMap()

        self.freeze()

    def add_visual_node(self, node: VisualNode, view_box=None):
        node.parent = self.new_visual_node_parent(view_box=view_box)

    def new_visual_node_parent(self, view_box=None):
        if view_box is None:
            view_box = list(self.view_dict.values())[0]
        return view_box.scene
