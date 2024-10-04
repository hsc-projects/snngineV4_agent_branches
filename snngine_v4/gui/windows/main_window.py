from typing import ClassVar

from qtpy import QtCore, QtWidgets

from snngine_v4.gui.common.qobject_dicts import QWidgetDict
from snngine_v4.gui.parameter_tree.connectors.basemodel_signal_register import \
    ModelSignalRegister
from snngine_v4.gui.parameter_tree.connectors.vispy_connector import \
    VispyConnector
from snngine_v4.gui.parameter_tree.parameters.widgets.array_editor import \
    ArrayEditorDockWidget
from snngine_v4.gui.windows.settings_window import SettingsWindow
from snngine_v4.snngine import SNNgine
from snngine_v4.gui.windows.main_window_base import (
    MainEngineWindowBase,
    WindowTypes,
)
from snngine_v4.snngine_config import EngineConfig
from snngine_v4.gui.parameter_tree.engine_parameter_tree import (
    EngineParameterTree, EngineTreeDockWidget,
)
from snngine_v4.visualization.config_models.vispy_camera_configs import \
    TurnTableCameraParameters
from snngine_v4.visualization.config_models.vispy_canvas_config import (
    VispyCanvasConfig
)


# noinspection PyPep8Naming
class MainEngineWindow(MainEngineWindowBase):

    SETTINGS_DOCK_CLASS: ClassVar = EngineTreeDockWidget

    def __init__(self, engine: SNNgine):

        windows = QWidgetDict({
            WindowTypes.SETTINGS: SettingsWindow(engine_config=engine.conf)
        })

        super().__init__(windows, engine=engine)

        scene_tree_dock = self.docks[EngineConfig.Slots.SCENES.capitalize()]
        self.scene_tree: EngineParameterTree = scene_tree_dock.widget()
        self.scene_tree.signal_register = (
            self.setting_trees[EngineConfig.Slots.SCENES].signal_register)

        self.update_connections()

    def build(self):
        self.engine.build()
        self.update_connections()

    def setup_dock_widgets(self):
        docks = super().setup_dock_widgets()
        array_dock = ArrayEditorDockWidget(name=self.ARRAYS_DOCK_NAME)
        self.addDockWidget(
            QtCore.Qt.DockWidgetArea.RightDockWidgetArea, array_dock)
        array_dock.close()
        docks.add_widgets(array_dock)

        show_array_editor_action = QtWidgets.QAction('A', self.right_toolbar)
        self.right_toolbar.addAction(show_array_editor_action)
        show_array_editor_action.triggered.connect(
            docks[self.ARRAYS_DOCK_NAME].toggleVisibility)

        return docks

    def update_connections(self):
        scene_tree: EngineParameterTree = self.scene_tree

        signal_register: ModelSignalRegister = scene_tree.signal_register
        models = signal_register.connected_models

        scene_manager = self.engine.scene_manager

        object2object_map = scene_manager.get_objects(models)

        VispyConnector.connect_map(
            object2object_map=object2object_map,
            signal_register=signal_register
        )

        scene_models: list[VispyCanvasConfig] = scene_manager.refs

        for sm in scene_models:
            if sm.Views:
                cam_pars = signal_register.get_parameters_by_type(
                    model_type=TurnTableCameraParameters,
                    ancestor=sm)
                roots = list(signal_register.group_map[sm.Cameras].items.keys())
                root = None
                for root in roots:
                    if root.treeWidget() == scene_tree:
                        break
                for p in cam_pars:
                    scene_tree.addParameters(p, root=root)
            signal_register

        return
