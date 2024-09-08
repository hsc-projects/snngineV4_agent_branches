from vispy.scene import Grid, ViewBox, XYZAxis
from vispy.visuals.transforms import STTransform

from snngine_v4.config.graphics.scene_config import VispyCanvasConfig
from snngine_v4.visualization.scenes.engine_scene import EngineSceneCanvas
from snngine_v4.visualization.scenes.connectable_camera import \
    ConnectableTurntableCamera


class MainNetworkSceneCanvas(EngineSceneCanvas):

    def __init__(self, conf: VispyCanvasConfig,
                 app, name: str | None = None):
        super().__init__(conf, app, name=name)

        self.scene_view: ViewBox = self.central_widget.add_view(
            camera=ConnectableTurntableCamera(name='MainCamera')
        )

        self.grid: Grid = self.scene_view.add_grid()

        axis = XYZAxis(parent=self.scene_view.scene)
        axis.transform = STTransform()
        axis.transform.move((-0.1, -0.1, -0.1))
