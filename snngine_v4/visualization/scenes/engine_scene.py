from vispy.app import Application
from vispy.scene import SceneCanvas

from snngine_v4.config.graphics.scene_config import VispyCanvasConfig


class EngineSceneCanvas(SceneCanvas):

    def __init__(self, conf: VispyCanvasConfig,
                 app: Application):

        conf = conf or VispyCanvasConfig()

        super().__init__(**conf.model_dump(mode='python'), app=app)
        self.central_widget.margin = 5
        self.unfreeze()

    @property
    def name(self):
        return self.title
