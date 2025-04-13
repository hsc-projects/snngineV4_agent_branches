from typing import Callable

from pyqtgraph.dockarea import Dock

from snngine_v4.gui.common.docks import CustomPgDock, CustomPgDockArea
from snngine_v4.visualization.config_models.vispy_canvas_config import \
    VispyCanvasConfig
from snngine_v4.visualization.scenes.main_network_scene import EngineSceneCanvas
from snngine_v4.visualization.scenes.scene_manager import SceneManager


def pass_floating():
    pass


class ViewDock(CustomPgDock):

    WIDGET_CLASS: EngineSceneCanvas
    widget: Callable[..., EngineSceneCanvas]

    # def clear(self):
    #     self.widget().clear()


# class ViewArea(QtWidgets.QWidget):
class ViewArea(CustomPgDockArea):

    def __init__(self, scene_manager: SceneManager, parent=None):
        self.scene_manager = scene_manager
        super().__init__(parent)

    # noinspection PyPep8Naming
    def addDock(self, dock=None, position='bottom',
                relativeTo=None, **kwargs):

        canvas: EngineSceneCanvas | None = None
        if isinstance(dock, VispyCanvasConfig):

            model = dock

            canvas = self.scene_manager[model]
            canvas.set_current()

            name = model.Options.title
            dock = ViewDock(name=name, **kwargs)
            dock.float = pass_floating
            dock.addWidget(canvas.native)

        elif isinstance(dock, Dock):
            pass
        else:
            raise NotImplementedError

        dock = super().addDock(
            dock=dock, position=position,
            relativeTo=relativeTo, **kwargs)

        if canvas is not None:
            canvas._draw_scene()

        return dock
