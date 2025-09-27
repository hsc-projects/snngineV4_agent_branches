from pydantic import BaseModel
from vispy.scene import BaseCamera, SceneCanvas, ViewBox, VisualNode


from snngine_v4.utils.containers.mappings import Model2ObjectMap


class EngineSceneCanvas(SceneCanvas):

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)

        self.unfreeze()

        self.camera_dict: dict[BaseModel, BaseCamera] | Model2ObjectMap = (
            Model2ObjectMap.from_type(BaseCamera))
        self.view_dict: dict[BaseModel, ViewBox] | Model2ObjectMap = (
            Model2ObjectMap.from_type(ViewBox))
        self.visual_node_dict: dict[BaseModel, VisualNode] | Model2ObjectMap = (
            Model2ObjectMap.from_type(VisualNode))

        self.sub_visual_super_map: (dict[BaseModel, Model2ObjectMap]
                                    | Model2ObjectMap) = (
            Model2ObjectMap.from_type(Model2ObjectMap))

        self.model2model_map = Model2ObjectMap.from_type(BaseModel)

        self.freeze()

    def add_visual_node(self, node: VisualNode, view_box=None):
        node.parent = self.new_visual_node_parent(view_box=view_box)

    def new_visual_node_parent(self, view_box=None):
        if view_box is None:
            view_box = list(self.view_dict.values())[0]
        sc = view_box.scene
        return sc

    def find_sub_visual_map(self, model):
        obj = self.sub_visual_super_map.get(model)
        if obj is not None:
            return obj
        alt_model = self.model2model_map.get(model)
        if alt_model is not None:
            return self.sub_visual_super_map.get(alt_model)
        return None
