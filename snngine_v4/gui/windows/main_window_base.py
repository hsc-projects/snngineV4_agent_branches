from __future__ import annotations

from enum import auto, IntEnum
from functools import cached_property
from typing import ClassVar, Type, TYPE_CHECKING

from qtpy import QtCore, QtWidgets

from snngine_v4.gui.common.qobject_dicts import QDockWidgetDict, QWidgetDict
from snngine_v4.gui.views.view_area import ViewArea

from snngine_v4.gui.windows.main_window_widgets import (
    ButtonsDockWidget,
    RightToolbar,
)
from snngine_v4.snngine_config import EngineConfig


from snngine_v4.snngine import SNNgine
from snngine_v4.visualization.scenes.main_network_scene import EngineSceneCanvas

if TYPE_CHECKING:
    from snngine_v4.gui.parameter_tree.engine_parameter_tree import (
        EngineParameterTree, QTree, EngineTreeDockWidget)
    from snngine_v4.gui.parameter_tree.parameters.widgets.table \
        .array_editor import ArrayEditorDockWidget
    from snngine_v4.gui.windows.extra_parameters import ParameterArea


class WindowTypes(IntEnum):
    MAIN = 0
    SETTINGS = auto()
    EXTRA_PARAMETERS = auto()
    SECONDARY_VIEWS = auto()


# noinspection PyPep8Naming
class MainEngineWindowBase(QtWidgets.QMainWindow):

    ACTIONS_DOCK_NAME: ClassVar[str] = 'Actions'
    ARRAYS_DOCK_NAME: ClassVar[str] = 'Array Editor'
    CONTROLS_DOCK_NAME: ClassVar[str] = 'Controls'

    PARAMETER_TREE_CLASS: ClassVar[Type[EngineParameterTree] | None]
    SETTINGS_DOCK_CLASS: ClassVar[Type[EngineTreeDockWidget] | None]

    def __init__(self, windows: QWidgetDict, engine: SNNgine,
                 b_verbose: bool = True):
        super().__init__()

        self.b_verbose = b_verbose

        self.setMenuBar(QtWidgets.QMenuBar())
        self.setCentralWidget(QtWidgets.QWidget(self))

        engine_config = engine.conf
        window_config = engine_config.app.windows.main
        self.resize(*window_config.size)

        self.centralWidget().setLayout(QtWidgets.QVBoxLayout())
        self.centralWidget().layout().setContentsMargins(0, 0, 0, 0)

        self.windows: dict[str, ViewArea] | QWidgetDict = windows

        self.right_toolbar = RightToolbar()
        self.addToolBar(
            QtCore.Qt.ToolBarArea.RightToolBarArea, self.right_toolbar)

        self.docks: dict[str, ButtonsDockWidget] | QDockWidgetDict = (
            QDockWidgetDict())

        self.engine = engine

        self.setup_dock_widgets()

        self.scene_tree: QTree = self.get_tree(EngineConfig.Slots.SCENES)
        self.constr_tree: QTree = self.get_tree(EngineConfig.Slots.CONSTR)
        self.network_tree: QTree = self.get_tree(EngineConfig.Slots.NETWORK)

        self.connect_to_engine()

        self.centralWidget().layout().addWidget(
            self.main_network_scene.native)

    @cached_property
    def arrayEditorDockWidget(self) -> ArrayEditorDockWidget:
        # noinspection PyTypeChecker
        return self.docks[self.ARRAYS_DOCK_NAME]

    def build(self):
        raise NotImplementedError

    def connect_to_engine(self):
        buttons_dock = self.docks[self.ACTIONS_DOCK_NAME]
        buttons_dock.build_button.clicked.connect(self.build)
        buttons_dock.test_button.clicked.connect(self.test_func)

        file_menu = self.menuBar().addMenu('&File')

        build_action = QtWidgets.QAction('&Build', self)
        file_menu.addAction(build_action)
        build_action.triggered.connect(self.build)

        settings_action = QtWidgets.QAction('&Settings', self)
        file_menu.addAction(settings_action)
        settings_action.triggered.connect(
            self.windows[WindowTypes.SETTINGS].show)

        extra_pars_wdg = self.windows[WindowTypes.EXTRA_PARAMETERS]
        extra_pars_action = QtWidgets.QAction('Show &Additional Parameters')
        file_menu.addAction(extra_pars_action)
        extra_pars_action.triggered.connect(extra_pars_wdg.show)
        self.windows.action_map[extra_pars_action] = extra_pars_wdg
        for action in self.windows.action_map.inv[extra_pars_wdg]:
            action.setEnabled(False)

        if WindowTypes.SECONDARY_VIEWS in self.windows:
            views_action = QtWidgets.QAction('Secondary &Views', self)
            file_menu.addAction(views_action)
            views_action.triggered.connect(
                self.windows[WindowTypes.SECONDARY_VIEWS].show)

    @cached_property
    def extraParametersWindow(self) -> ParameterArea:
        return self.windows[WindowTypes.EXTRA_PARAMETERS]

    def get_tree(self, slot) -> QTree:
        # noinspection PyTypeChecker
        return self.docks[slot.capitalize()].widget()

    @cached_property
    def main_network_scene(self):
        return self.engine.scene_manager[
            self.engine.conf.scenes.main]

    def make_settings_dock_widget(self, key) -> EngineTreeDockWidget:
        settings = getattr(self.engine.conf, key)
        tree = self.PARAMETER_TREE_CLASS(
            key.capitalize(), settings, showHeader=True,
            b_verbose=self.b_verbose)

        return self.SETTINGS_DOCK_CLASS(
            # pars=self.setting_trees[key].copy(),
            pars=tree,
            # name=key.capitalize()
        )

    def addLeftDockWidget(
            self, widget_or_key: str | QtWidgets.QWidget):
        if isinstance(widget_or_key, str):
            widget = self.make_settings_dock_widget(key=widget_or_key)
        else:
            widget = widget_or_key
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, widget)
        self.docks.add_widget(widget)
        return widget

    def setup_dock_widgets(self):

        options = self.dockOptions()
        options |= QtWidgets.QMainWindow.DockOption.VerticalTabs
        options |= QtWidgets.QMainWindow.DockOption.AllowNestedDocks

        self.setDockOptions(options)
        self.setCorner(QtCore.Qt.Corner.TopLeftCorner,
                       QtCore.Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setCorner(QtCore.Qt.Corner.BottomLeftCorner,
                       QtCore.Qt.DockWidgetArea.LeftDockWidgetArea)

        scenes = self.addLeftDockWidget(
            widget_or_key=EngineConfig.Slots.SCENES)
        construction = self.addLeftDockWidget(
            widget_or_key=EngineConfig.Slots.CONSTR)
        network = self.addLeftDockWidget(
            widget_or_key=EngineConfig.Slots.NETWORK)

        self.tabifyDockWidget(scenes, construction)
        self.tabifyDockWidget(construction, network)

        buttons = ButtonsDockWidget(name=self.ACTIONS_DOCK_NAME)
        # noinspection PyTypeChecker,PydanticTypeChecker
        self.addLeftDockWidget(buttons)

    @property
    def setting_trees(self) -> dict[str, QTree]:
        return self.windows[WindowTypes.SETTINGS].setting_trees

    def test_func(self):
        pass

    def toggleArrayEditorVisibility(self):
        if (editor := self.arrayEditorDockWidget).isVisible():
            editor.hide()
            editor.close()
        else:
            # print(editor.sizeHint())
            editor.show()
            # print(editor.sizeHint())
