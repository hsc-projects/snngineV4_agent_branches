from qtpy import QtCore, QtWidgets

from snngine_v4.snngine_config import EngineConfig
from snngine_v4.gui.parameter_tree.engine_parameter_tree import \
    EngineParameterTree
from snngine_v4.gui.windows.settings_window import SettingsWindow


class MainEngineWindow(QtWidgets.QMainWindow):

    def __init__(self, engine_config: EngineConfig):
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

        self.settings_window = SettingsWindow(engine_config=engine_config)

        self.setCorner(QtCore.Qt.Corner.TopLeftCorner,
                       QtCore.Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setCorner(QtCore.Qt.Corner.BottomLeftCorner,
                       QtCore.Qt.DockWidgetArea.LeftDockWidgetArea)

        construction_pars = self.settings_window.setting_trees[
                EngineConfig.Slots.CONSTRUCTION].parameters
        self.construction_tree = EngineParameterTree.from_pars(
            pars=construction_pars
        )
        construction_tree_dock = self.construction_tree.set_q_dock_widget()
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea,
                           construction_tree_dock)

        self.setup_menu_bar()

    def setup_menu_bar(self):
        file_menu = self.menuBar().addMenu('&File')
        settings_action = QtWidgets.QAction('&Settings', self)
        file_menu.addAction(settings_action)
        settings_action.triggered.connect(self.settings_window.show)
