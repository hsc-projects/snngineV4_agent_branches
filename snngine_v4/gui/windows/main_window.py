from typing import ClassVar

from qtpy import QtCore, QtWidgets


from snngine_v4.gui.common.qobject_dicts import QWidgetDict
from snngine_v4.gui.linker_tree.linker_tree import LinkerTree

from snngine_v4.gui.parameter_tree.parameters.widgets.table \
    .array_editor import ArrayEditorDockWidget
from snngine_v4.gui.selector_tree.engine_selector_tree import EngineSelectorTree
from snngine_v4.gui.views.view_area import ViewArea
from snngine_v4.gui.windows.extra_parameters import ParameterArea
from snngine_v4.gui.windows.settings_window import SettingsWindow

from snngine_v4.snngine import SNNgine
from snngine_v4.gui.windows.main_window_base import (
    MainEngineWindowBase,
    WindowTypes,
)
from snngine_v4.gui.parameter_tree.engine_parameter_tree import (
    EngineParameterTree, EngineTreeDockWidget,
)
from snngine_v4.snngine_config import EngineConfig


# noinspection PyPep8Naming
class MainEngineWindow(MainEngineWindowBase):

    PARAMETER_TREE_CLASS: ClassVar = EngineParameterTree
    SETTINGS_DOCK_CLASS: ClassVar = EngineTreeDockWidget

    def __init__(self, engine: SNNgine, b_show: bool = True):

        sec_views = ViewArea(scene_manager=engine.scene_manager)

        windows = QWidgetDict({
            WindowTypes.SETTINGS: SettingsWindow(engine_config=engine.conf),
            WindowTypes.EXTRA_PARAMETERS: ParameterArea(),
            WindowTypes.SECONDARY_VIEWS: sec_views
        })

        sec_views.resize(QtCore.QSize(640, 480))

        self.selection_tree = EngineSelectorTree()
        self.selection_tree_dock: EngineTreeDockWidget | None = None

        super().__init__(windows, engine=engine)

        if b_show:
            self.show()

    def construct_network(self):
        self.engine.build(
            scene_tree=self.scene_tree,
            network_tree=self.network_tree,
            selector_tree=self.selection_tree
        )

    def setup_dock_widgets(self):
        super().setup_dock_widgets()

        array_dock = ArrayEditorDockWidget(name=self.ARRAYS_DOCK_NAME)
        self.addRightDockWidget('A', array_dock)

        controls_tree = LinkerTree(name=self.CONTROLS_DOCK_NAME)

        features = (
            QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable)
        controls_dock = EngineTreeDockWidget(
            pars=controls_tree,
            features=features)
        self.addRightDockWidget('C', controls_dock)

        self.selection_tree_dock = self.SETTINGS_DOCK_CLASS(
            pars=self.selection_tree)

        self.addLeftDockWidget(self.selection_tree_dock)

        self.tabifyDockWidget(
            self.docks[EngineConfig.Slots.BUILT.capitalize()],
            self.selection_tree_dock)

    def test_func(self, ):
        # self.engine.run_sim(10)
        self.selection_tree.add_selector_box_visual(None)
