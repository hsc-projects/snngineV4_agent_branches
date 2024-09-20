from typing import ClassVar

from pydantic import BaseModel
from vispy.scene import BaseCamera, SceneCanvas, ViewBox

from snngine_v4.config.scenes import SceneSettings
from snngine_v4.utils.containers.mappings import (
    Model2ObjectMap,
    Object2ObjectMap,
)
from snngine_v4.utils.object_builder.object_builder_dict import BuilderDict
from snngine_v4.visualization.config_models.vispy_camera_configs import \
    TurnTableCameraParameters
from snngine_v4.visualization.config_models.vispy_canvas_config import (
    VispyCanvasConfig, VispyViewBoxConfig,
)
from snngine_v4.visualization.config_models.visual_configs import \
    LineVisualConfig
from snngine_v4.visualization.scenes.event_camera import \
    EventTurntableCamera
from snngine_v4.visualization.scenes.main_network_scene import EngineSceneCanvas
from snngine_v4.visualization.visual_builder import VispyVisualManager


class SceneManager(BuilderDict):

    BUILDER_DEFAULT_MODEL_CLASS: ClassVar = VispyCanvasConfig
    BUILDER_DEFAULT_OBJECT_CLASS: ClassVar = EngineSceneCanvas
    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        VispyCanvasConfig: EngineSceneCanvas
    }

    def __init__(self, scenes):
        self.data: dict[BaseModel, EngineSceneCanvas] | None = None
        super().__init__()
        if isinstance(scenes, (list, SceneSettings)):
            self.update(scenes)

    def get_objects(self, model_list):
        res = Model2ObjectMap()
        for model in model_list:
            if isinstance(model, VispyCanvasConfig):
                res[model] = self[model]
            elif isinstance(model, TurnTableCameraParameters):
                for scene in self.values():
                    if model in scene.camera_dict:
                        res[model] = scene.camera_dict[model]
            elif isinstance(model, LineVisualConfig):
                for scene in self.values():
                    if model in scene.visual_node_dict:
                        res[model] = scene.visual_node_dict[model]
        return res

    @classmethod
    def _make_camera(cls, **kwargs) -> BaseCamera:

        camera = EventTurntableCamera(**kwargs)

        return camera

    @classmethod
    def make_object(cls, object_class, model, **object_kwargs):

        scene_opts = object_kwargs.pop(
            VispyCanvasConfig.Slots.OPTIONS, {})

        wdg_opts = scene_opts.pop(
            VispyCanvasConfig.Slots.CENTRAL_WIDGET_OPTIONS, {})

        visuals = object_kwargs.pop(
            VispyCanvasConfig.Slots.VISUALS, None)
        views = object_kwargs.pop(
            VispyCanvasConfig.Slots.VIEWS, {})

        scene: EngineSceneCanvas = super().make_object(
            object_class=object_class,
            model=model,
            **scene_opts,)

        for k, v in wdg_opts.items():
            if k == 'border_width':
                k = '_border_width'
            setattr(scene.central_widget, k, v)

        for k, view_config in views.items():
            views_model = getattr(model, VispyCanvasConfig.Slots.VIEWS)
            view_model = getattr(views_model, k)
            camera_model = getattr(view_model, 'camera')
            view_config: VispyViewBoxConfig | dict
            camera = cls._make_camera(**view_config.pop('camera'))
            view = scene.view_dict[view_model] = ViewBox(
                camera=camera, **view_config)
            scene.central_widget.add_widget(view)
            scene.camera_dict[camera_model] = camera

        if visuals is not None:
            visuals = getattr(model, VispyCanvasConfig.Slots.VISUALS)
            parent = scene.new_visual_node_parent()
            visual_dict = VispyVisualManager.cls_build_container(
                visuals, parent=parent
            )
            scene.visual_node_dict.update(visual_dict.object_dict)
        return scene
