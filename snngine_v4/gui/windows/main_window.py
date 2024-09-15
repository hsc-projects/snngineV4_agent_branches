from enum import IntEnum

from qtpy import QtCore, QtWidgets, QtGui

from snngine_v4.gui.common.widget_dict import QDockWidgetDict, QWidgetDict
from snngine_v4.snngine import SNNgine
from snngine_v4.snngine_config import EngineConfig
from snngine_v4.gui.parameter_tree.engine_parameter_tree import \
    (
    EngineParameterTree, EngineTreeDockWidget,
)
from snngine_v4.gui.windows.settings_window import SettingsWindow


class WindowTypes(IntEnum):
    MAIN = 0
    SETTINGS = 1


class ButtonsDockWidget(QtWidgets.QDockWidget):

    def __init__(self, name = 'Buttons', parent=None, features=None, **kwargs):

        super().__init__(name, parent=parent, **kwargs)
        self.setObjectName(name)
        if features is None:
            features = (
                    QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
                    | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.setFeatures(features)
        self.setWidget(QtWidgets.QWidget())

        self.widget().setLayout(QtWidgets.QGridLayout())

        self.build_button = QtWidgets.QPushButton('Build')
        self.widget().layout().addWidget(self.build_button, 0, 0)


class MainEngineWindow(QtWidgets.QMainWindow):

    def __init__(self, engine: SNNgine):
        super().__init__()

        engine_config = engine.conf
        window_config = engine_config.app.windows.main
        self.resize(*window_config.size)

        self.setCentralWidget(QtWidgets.QWidget(self))
        self.centralWidget().setLayout(QtWidgets.QVBoxLayout())
        self.centralWidget().layout().setContentsMargins(0, 0, 0, 0)

        self.windows = QWidgetDict({
            WindowTypes.SETTINGS: SettingsWindow(engine_config=engine_config)
        })

        self._config_docks()

        construction_tree_dock = EngineTreeDockWidget(
            self.setting_trees[EngineConfig.Slots.CONSTRUCTION])

        buttons_docks = ButtonsDockWidget()
        buttons_docks.build_button.clicked.connect(engine.build)

        self.docks = QDockWidgetDict()
        self.docks.add_widget(construction_tree_dock)
        self.docks.add_widget(buttons_docks)

        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea,
                           construction_tree_dock)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea,
                           buttons_docks)

        self._set_menu_bar(engine=engine)

    def _config_docks(self):
        dock_options = self.dockOptions()
        dock_options |= QtWidgets.QMainWindow.DockOption.VerticalTabs
        dock_options |= QtWidgets.QMainWindow.DockOption.AllowNestedDocks
        self.setDockOptions(dock_options)
        self.setCorner(QtCore.Qt.Corner.TopLeftCorner,
                       QtCore.Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setCorner(QtCore.Qt.Corner.BottomLeftCorner,
                       QtCore.Qt.DockWidgetArea.LeftDockWidgetArea)

    @property
    def setting_trees(self) -> dict[str, EngineParameterTree]:
        return self.windows[WindowTypes.SETTINGS].setting_trees

    def _set_menu_bar(self, engine: SNNgine):
        self.setMenuBar(QtWidgets.QMenuBar())
        file_menu = self.menuBar().addMenu('&File')

        build_action = QtWidgets.QAction('&Build', self)
        file_menu.addAction(build_action)
        build_action.triggered.connect(engine.build)

        settings_action = QtWidgets.QAction('&Settings', self)
        file_menu.addAction(settings_action)
        settings_action.triggered.connect(
            self.windows[WindowTypes.SETTINGS].show)
