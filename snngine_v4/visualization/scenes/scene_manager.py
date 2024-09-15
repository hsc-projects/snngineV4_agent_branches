from typing import ClassVar

from vispy.scene import SceneCanvas

from snngine_v4.config.scenes import SceneSettings
from snngine_v4.utils.settings.object_builder import BuilderDict
from snngine_v4.visualization.config_models.canvas_config import (
    MainNetworkSceneConfig, VispyCanvasConfig,
)
from snngine_v4.visualization.scenes.main_network_scene import \
    MainNetworkSceneCanvas


class SceneManager(BuilderDict):

    BUILDER_DEFAULT_MODEL_CLASS: ClassVar = VispyCanvasConfig
    BUILDER_DEFAULT_OBJECT_CLASS: ClassVar = SceneCanvas
    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        MainNetworkSceneConfig: MainNetworkSceneCanvas
    }

    def __init__(self, scenes):
        self.data: dict[str, SceneCanvas] | None = None
        super().__init__()
        if isinstance(scenes, (list, SceneSettings)):
            self.add_scenes(scenes)

    def add_scene(self, scene: SceneCanvas | VispyCanvasConfig,
                  name=None, **kwargs):
        if isinstance(scene, VispyCanvasConfig):
            self.add_from_model(key=name, model=scene, **kwargs)
        self[name] = scene

    def add_scenes(self, scenes: SceneSettings | list):
        if isinstance(scenes, list):
            for s in scenes:
                self.add_scene(s)
        else:
            self.update(scenes)

    @classmethod
    def make_object(cls, object_class, **object_kwargs):

        wdg_opts = object_kwargs.pop(
            VispyCanvasConfig.Slots.CENTRAL_WIDGET_OPTIONS, {})

        scene: SceneCanvas = object_class(**object_kwargs)

        for k, v in wdg_opts.items():
            if k == 'border_width':
                k = '_border_width'
            setattr(scene.central_widget, k, v)
        return scene
