from vispy.scene import Grid, SceneCanvas, ViewBox, XYZAxis
from vispy.visuals.transforms import STTransform

from snngine_v4.visualization.scenes.connectable_camera import \
    ConnectableTurntableCamera


class MainNetworkSceneCanvas(SceneCanvas):

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)

        self.unfreeze()
        self.scene_view: ViewBox = self.central_widget.add_view(
            camera=ConnectableTurntableCamera(name='MainCamera')
        )

        self.display_grid: Grid = self.scene_view.add_grid()

        axis = XYZAxis(parent=self.scene_view.scene)
        axis.transform = STTransform()
        axis.transform.move((-0.1, -0.1, -0.1))
        self.freeze()
