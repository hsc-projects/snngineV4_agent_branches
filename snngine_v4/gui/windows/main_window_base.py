from __future__ import annotations

from enum import IntEnum
from typing import ClassVar, Type, TYPE_CHECKING

from qtpy import QtCore, QtWidgets

from snngine_v4.gui.common.qobject_dicts import QDockWidgetDict, QWidgetDict

from snngine_v4.gui.windows.main_window_widgets import (
    ButtonsDockWidget,
    RightToolbar,
)
from snngine_v4.snngine_config import EngineConfig


from snngine_v4.snngine import SNNgine

if TYPE_CHECKING:
    from snngine_v4.gui.parameter_tree.engine_parameter_tree import (
        QTree, EngineTreeDockWidget,
    )
    from snngine_v4.gui.parameter_tree.parameters.widgets.table \
        .array_editor import ArrayEditorDockWidget


class WindowTypes(IntEnum):
    MAIN = 0
    SETTINGS = 1


# noinspection PyPep8Naming
class MainEngineWindowBase(QtWidgets.QMainWindow):

    BUTTONS_DOCK_NAME: ClassVar[str] = 'Buttons'
    ARRAYS_DOCK_NAME: ClassVar[str] = 'Array Editor'

    SETTINGS_DOCK_CLASS: ClassVar[Type[EngineTreeDockWidget]] = None

    def __init__(self, windows: QWidgetDict, engine: SNNgine):
        super().__init__()

        self.setMenuBar(QtWidgets.QMenuBar())
        self.setCentralWidget(QtWidgets.QWidget(self))

        engine_config = engine.conf
        window_config = engine_config.app.windows.main
        self.resize(*window_config.size)

        self.centralWidget().setLayout(QtWidgets.QVBoxLayout())
        self.centralWidget().layout().setContentsMargins(0, 0, 0, 0)

        self.windows = windows

        self.right_toolbar = RightToolbar()
        self.addToolBar(
            QtCore.Qt.ToolBarArea.RightToolBarArea, self.right_toolbar)

        self.docks: QDockWidgetDict = self.setup_dock_widgets()

        self.scene_tree: QTree = self.get_tree(EngineConfig.Slots.SCENES)
        self.constr_tree: QTree = self.get_tree(EngineConfig.Slots.CONSTR)
        self.network_tree: QTree = self.get_tree(EngineConfig.Slots.NETWORK)

        self.engine = engine
        self.connect_to_engine()

    @property
    def arrayEditorDockWidget(self) -> ArrayEditorDockWidget:
        return self.docks[self.ARRAYS_DOCK_NAME]

    def build(self):
        raise NotImplementedError

    def connect_to_engine(self):
        buttons_dock = self.docks[self.BUTTONS_DOCK_NAME]
        buttons_dock.build_button.clicked.connect(self.build)

        file_menu = self.menuBar().addMenu('&File')

        build_action = QtWidgets.QAction('&Build', self)
        file_menu.addAction(build_action)
        build_action.triggered.connect(self.build)

        settings_action = QtWidgets.QAction('&Settings', self)
        file_menu.addAction(settings_action)
        settings_action.triggered.connect(
            self.windows[WindowTypes.SETTINGS].show)

    def get_tree(self, slot) -> QTree:
        return self.docks[slot.capitalize()].widget()

    def make_settings_dock_widget(self, key) -> EngineTreeDockWidget:
        return self.SETTINGS_DOCK_CLASS(
            pars=self.setting_trees[key].copy(),
            name=key.capitalize())

    def setup_dock_widgets(self):

        docks = QDockWidgetDict()
        options = self.dockOptions()
        options |= QtWidgets.QMainWindow.DockOption.VerticalTabs
        options |= QtWidgets.QMainWindow.DockOption.AllowNestedDocks

        self.setDockOptions(options)
        self.setCorner(QtCore.Qt.Corner.TopLeftCorner,
                       QtCore.Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setCorner(QtCore.Qt.Corner.BottomLeftCorner,
                       QtCore.Qt.DockWidgetArea.LeftDockWidgetArea)

        construction = self.make_settings_dock_widget(
            key=EngineConfig.Slots.CONSTR)
        scenes = self.make_settings_dock_widget(
            key=EngineConfig.Slots.SCENES)
        network = self.make_settings_dock_widget(
            key=EngineConfig.Slots.NETWORK)

        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea,
                           scenes)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea,
                           construction)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea,
                           network)
        self.tabifyDockWidget(scenes, construction)
        self.tabifyDockWidget(construction, network)

        # construction.raise_()

        buttons = ButtonsDockWidget(name=self.BUTTONS_DOCK_NAME)
        self.addDockWidget(
            QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, buttons)

        # noinspection PyTypeChecker
        docks.add_widgets(construction, scenes, network, buttons)

        return docks

    @property
    def setting_trees(self) -> dict[str, QTree]:
        return self.windows[WindowTypes.SETTINGS].setting_trees

    def toggleArrayEditorVisibility(self):
        if (editor := self.arrayEditorDockWidget).isVisible():
            editor.hide()
            editor.close()
        else:
            # print(editor.sizeHint())
            editor.show()
            # print(editor.sizeHint())
