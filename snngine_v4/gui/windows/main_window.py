from qtpy import QtCore, QtWidgets

from snngine_v4.config.engine_config_model import EngineConfig
from snngine_v4.gui.parameter_tree.engine_parameter_tree import \
    EngineParameterTree
from snngine_v4.gui.windows.settings_window import SettingsWindow


class MainEngineWindow(QtWidgets.QMainWindow):

    def __init__(self, settings: EngineConfig):
        super().__init__()

        self.main = QtWidgets.QWidget(self)
        self.setCentralWidget(self.main)

        self.setMenuBar(QtWidgets.QMenuBar())

        self.main.setLayout(QtWidgets.QVBoxLayout())
        self.main.layout().setContentsMargins(0, 0, 0, 0)

        dock_options = self.dockOptions()
        dock_options |= QtWidgets.QMainWindow.DockOption.VerticalTabs
        dock_options |= QtWidgets.QMainWindow.DockOption.AllowNestedDocks
        self.setDockOptions(dock_options)

        self.settings_window = SettingsWindow(settings=settings)

        self.setCorner(QtCore.Qt.Corner.TopLeftCorner,
                       QtCore.Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setCorner(QtCore.Qt.Corner.BottomLeftCorner,
                       QtCore.Qt.DockWidgetArea.LeftDockWidgetArea)

        self.construction_tree = EngineParameterTree(settings.construction)
        construction_tree_dock = self.construction_tree.set_q_dock_widget()
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea,
                           construction_tree_dock)

        self.setup_menu_bar()


    def setup_menu_bar(self):
        file_menu = self.menuBar().addMenu('&File')
        settings_action = QtWidgets.QAction('&Settings', self)
        file_menu.addAction(settings_action)
        settings_action.triggered.connect(self.settings_window.show)
