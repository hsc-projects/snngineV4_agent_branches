from typing import Callable, ClassVar

from pydantic import BaseModel
from vispy.scene import ViewBox
from vispy.visuals import CompoundVisual

from snngine_v4.geometry.grid.finite_grid_config import FiniteGridConfig
from snngine_v4.utils.containers.mappings import (
    Model2ObjectMap,
)
from snngine_v4.utils.object_builder.object_builder import (BuildResult,
                                                            ModelObjectBuilder)

from snngine_v4.utils.object_builder.object_builder_dict import BuilderDict
from snngine_v4.visualization.config_models.vispy_camera_configs import (
    CameraCenter, PanZoomCameraParameters, TurnTableCameraParameters,
)
from snngine_v4.visualization.config_models.vispy_canvas_config import (
    VispyCanvasConfig, VispyViewBoxConfig,
)
from snngine_v4.visualization.config_models.visuals import (
    LineVisualConfig, MarkersVisualConfig
)

from snngine_v4.visualization.scenes.event_camera import (
    EventPanZoomCamera, EventTurntableCamera,
)
from snngine_v4.visualization.scenes.main_network_scene import (
    EngineSceneCanvas)
from snngine_v4.visualization.visual_builder import VispyVisualBuilder


from snngine_v4.nn.config_models.spnn_config \
    import NetworkReservoirConfig


type VisualConfigType = (
        FiniteGridConfig | LineVisualConfig | MarkersVisualConfig
        | NetworkReservoirConfig)


class CameraBuilder(ModelObjectBuilder):
    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        PanZoomCameraParameters: EventPanZoomCamera,
        TurnTableCameraParameters: EventTurntableCamera,
    }

    @classmethod
    def make_object(cls, object_class, object_model, **object_kwargs):

        if isinstance(center := object_kwargs.get('center'), dict):
            object_kwargs['center'] = CameraCenter(**center)

        return super().make_object(
            object_class=object_class, object_model=object_model,
            **object_kwargs)


class VispyMap(Model2ObjectMap):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model2model_map = Model2ObjectMap.from_type(BaseModel)
        self.sub_visual_super_map: (dict[BaseModel, Model2ObjectMap]
                                    | Model2ObjectMap) = (
            Model2ObjectMap.from_type(Model2ObjectMap))


class SceneManager(BuilderDict):

    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        VispyCanvasConfig: EngineSceneCanvas
    }

    data: dict[BaseModel, EngineSceneCanvas] | None
    __getitem__: Callable[[str | BaseModel], EngineSceneCanvas]

    def __init__(self, model_container, app=None, **kwargs):
        super().__init__(model_container=model_container,
                         build_kwargs=dict(app=app),
                         **kwargs)

    def build_visuals(self, visuals, scene, **kwargs):
        if isinstance(scene, BaseModel):
            scene = self[scene]
        return self.cls_build_visuals(visuals, scene=scene, **kwargs)

    @classmethod
    def cls_build_visuals(cls, visuals, scene, **kwargs):
        scene.set_current()
        parent = scene.new_visual_node_parent()
        built_visuals_dict = VispyVisualBuilder.cls_build_container(
            visuals, parent=parent,
            sub_visual_super_map=scene.sub_visual_super_map, **kwargs)
        scene.visual_node_dict.update(built_visuals_dict.object_dict)

        for model in built_visuals_dict.refs:
            build_res: BuildResult = built_visuals_dict[model]
            if build_res.model != model:
                scene.model2model_map[model] = build_res.model

        # scene._draw_scene()
        return built_visuals_dict

    def draw_scene(self, scene_model):
        self[scene_model]._draw_scene()

    def find_object(self, model):

        if isinstance(model, VisualConfigType.__value__):
            for scene in self.values():
                scene: EngineSceneCanvas
                obj = scene.visual_node_dict.get(model)
                if obj is not None:
                    return scene, obj
            return None
        elif isinstance(model, VispyCanvasConfig):
            return self[model]
        elif isinstance(model, TurnTableCameraParameters):
            for scene in self.values():
                scene: EngineSceneCanvas
                obj = scene.camera_dict.get(model)
                if obj is not None:
                    return scene, obj
            return None
        else:
            return None

    def get_built_objects(self, *models, container: VispyMap = None,
                          b_assert_key_exists=True) -> VispyMap:
        if container is None:
            container = VispyMap()
        for m in models:
            scene = None
            alt_model = None
            obj = self.find_object(m)
            if isinstance(obj, tuple):
                scene = obj[0]
                obj = obj[1]
            if obj is not None:
                if scene is not None:
                    alt_model = scene.model2model_map.get(m)
                    if alt_model is not None:
                        container.model2model_map[m] = alt_model
                        # m = alt_model
                container[m] = obj
                if isinstance(obj, CompoundVisual):
                    if alt_model is not None:
                        m = alt_model
                    container.sub_visual_super_map[m] = (
                        scene.find_sub_visual_map(m))

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
    def make_object(cls, object_class, object_model, **object_kwargs):

        scene_opts = object_kwargs.pop(
            VispyCanvasConfig.Slots.OPTIONS, {})
        scene_opts['app'] = object_kwargs.pop('app', None)

        wdg_opts = scene_opts.pop(
            VispyCanvasConfig.Slots.CENTRAL_WIDGET_OPTIONS, {})

        visuals = object_kwargs.pop(
            VispyCanvasConfig.Slots.VISUALS, None)
        views = object_kwargs.pop(
            VispyCanvasConfig.Slots.VIEWS, {})

        scene: EngineSceneCanvas = super().make_object(
            object_class=object_class, object_model=object_model,
            **scene_opts,)

        for k, v in wdg_opts.items():
            if k == 'border_width':
                k = '_border_width'
            setattr(scene.central_widget, k, v)

        for k, view_config in views.items():
            views_model = getattr(object_model, VispyCanvasConfig.Slots.VIEWS)
            view_model = getattr(views_model, k)
            camera_model = getattr(view_model, 'camera')
            view_config: VispyViewBoxConfig | dict
            # camera = cls._make_camera(**view_config.pop('camera'))
            camera = CameraBuilder.cls_build_obj(model=camera_model).built
            view_config['camera'] = camera
            view = scene.view_dict[view_model] = ViewBox(**view_config)
            scene.central_widget.add_widget(view)
            scene.camera_dict[camera_model] = camera

        if visuals is not None:
            cls.cls_build_visuals(
                getattr(object_model, VispyCanvasConfig.Slots.VISUALS), scene)
        return scene

    def set_current(self, scene_model):
        self[scene_model].set_current()
