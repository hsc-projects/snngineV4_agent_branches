from pydantic import BaseModel
from vispy.scene import BaseCamera, SceneCanvas, ViewBox, VisualNode

from snngine_v4.utils.containers.configurable_dict import ConfigurableDict
from snngine_v4.utils.containers.mappings import Model2ObjectMap


class EngineSceneCanvas(SceneCanvas):

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)

        self.unfreeze()

        self.camera_dict: dict[BaseModel, BaseCamera] = (
            Model2ObjectMap.from_type(BaseCamera))
        self.view_dict: dict[BaseModel, ViewBox] = (
            Model2ObjectMap.from_type(ViewBox))
        self.visual_node_dict: dict[BaseModel, ViewBox] = (
            Model2ObjectMap.from_type(VisualNode))

        self.freeze()

    def add_visual_node(self, node: VisualNode, view_box=None):
        node.parent = self.new_visual_node_parent(view_box=view_box)

    def new_visual_node_parent(self, view_box=None):
        if view_box is None:
            view_box = list(self.view_dict.values())[0]
        return view_box.scene
