from typing import ClassVar

from pydantic import BaseModel
from vispy.scene import BaseCamera, ViewBox

from snngine_v4.config.scenes import SceneSettings
from snngine_v4.utils.containers.mappings import (
    Model2ObjectMap,
)

from snngine_v4.utils.object_builder.object_builder_dict import BuilderDict
from snngine_v4.visualization.config_models.vispy_camera_configs import (
    CameraCenter, TurnTableCameraParameters,
)
from snngine_v4.visualization.config_models.vispy_canvas_config import (
    VispyCanvasConfig, VispyViewBoxConfig,
)
from snngine_v4.visualization.config_models.visuals import VisualConfig
from snngine_v4.visualization.scenes.event_camera import \
    EventTurntableCamera
from snngine_v4.visualization.scenes.main_network_scene import EngineSceneCanvas
from snngine_v4.visualization.visual_builder import VispyVisualBuilder


# class Object2SceneMap(SurjectiveMap):
#     ContainerConfigClass: ClassVar = (Visual, EngineSceneCanvas)


class SceneManager(BuilderDict):

    # VISUAL_BUILDER_KW: ClassVar = 'visual_builder'
    BUILDER_DEFAULT_MODEL_CLASS: ClassVar = VispyCanvasConfig
    BUILDER_DEFAULT_OBJECT_CLASS: ClassVar = EngineSceneCanvas
    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        VispyCanvasConfig: EngineSceneCanvas
    }

    def __init__(self, scenes, **kwargs):
        self.data: dict[BaseModel, EngineSceneCanvas] | None = None
        # self.visual_builder = VispyVisualBuilder()
        # self.obj2scene_map: dict[BaseModel, Object2SceneMap] =
        super().__init__(**kwargs)
        if isinstance(scenes, (list, SceneSettings)):
            self.update(scenes)

    def build_visuals(self, visuals, scene):
        if isinstance(scene, BaseModel):
            scene = self[scene]
        return self.cls_build_visuals(visuals, scene=scene)

    @classmethod
    def cls_build_visuals(cls, visuals, scene):
        parent = scene.new_visual_node_parent()
        visual_dict = VispyVisualBuilder.cls_build_container(
            visuals, parent=parent
        )
        scene.visual_node_dict.update(visual_dict.object_dict)
        return visual_dict

    def get_built_objects(self, *models, container=None,
                          b_assert_key_exists=True):
        if container is None:
            container = Model2ObjectMap()
        for k in models:
            try:
                if isinstance(k, VispyCanvasConfig):
                    container[k] = self[k]
                elif isinstance(k, TurnTableCameraParameters):
                    for scene in self.values():
                        if k in scene.camera_dict:
                            container[k] = scene.camera_dict[k]
                elif isinstance(k, VisualConfig.__value__):
                    for scene in self.values():
                        if k in scene.visual_node_dict:
                            container[k] = scene.visual_node_dict[k]
            except KeyError as error:
                if b_assert_key_exists:
                    raise error
        return container

    def get_visual_nodes(self, *models, container=None):
        if container is None:
            container = Model2ObjectMap()
        for scene in self.values():
            for model in scene.visual_node_dict.refs:
                if (len(models) == 0) or (model in models):
                    container[model] = scene.visual_node_dict[model]
        return container

    @classmethod
    def _make_camera(cls, **kwargs) -> BaseCamera:

        if 'center' in kwargs:
            kwargs['center'] = CameraCenter(**kwargs['center'])

        camera = EventTurntableCamera(**kwargs)
        if not camera.name:
            camera.name = 'camera'
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
        # visual_builder = object_kwargs.pop(
        #     cls.VISUAL_BUILDER_KW, None)

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
            cls.cls_build_visuals(
                getattr(model, VispyCanvasConfig.Slots.VISUALS), scene)
        return scene

    # def __setitem__(self, key, value):
    #     super().__setitem__(key, value)
    #     self.

