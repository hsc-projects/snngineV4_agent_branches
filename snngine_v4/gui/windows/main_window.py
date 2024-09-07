from qtpy import QtCore, QtWidgets

from snngine_v4.gui.parameter_tree.engine_parameter_tree import \
    EngineParameterTree


class MainEngineWindow(QtWidgets.QMainWindow):
    def __init__(self, settings):
        super().__init__()

        self.main = QtWidgets.QWidget(self)
        self.setCentralWidget(self.main)

        self.main.setLayout(QtWidgets.QVBoxLayout())
        self.main.layout().setContentsMargins(0, 0, 0, 0)
        self.splitter = QtWidgets.QSplitter()
        self.main.layout().addWidget(self.splitter)

        self.label0 = QtWidgets.QLabel('Label0')
        self.label1 = QtWidgets.QLabel('Label1')
        self.label2 = QtWidgets.QLabel('Label2')
        self.label3 = QtWidgets.QLabel('Label3')

        # self.splitter.addWidget(self.label0)
        # self.splitter.addWidget(self.label1)

        dock_options = self.dockOptions()
        dock_options |= QtWidgets.QMainWindow.DockOption.VerticalTabs
        dock_options |= QtWidgets.QMainWindow.DockOption.AllowNestedDocks
        # dock_options |= QtWidgets.QMainWindow.DockOption.ForceTabbedDocks

        self.setDockOptions(dock_options)
        self.setCorner(QtCore.Qt.Corner.TopLeftCorner,
                       QtCore.Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setCorner(QtCore.Qt.Corner.BottomLeftCorner,
                       QtCore.Qt.DockWidgetArea.LeftDockWidgetArea)

        construction_dock = QtWidgets.QDockWidget('Construction')
        construction_dock.setWidget(self.label2)
        construction_dock.setFeatures(
            QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(
            QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, construction_dock)

        wdg = QtWidgets.QWidget()
        wdg.setLayout(QtWidgets.QVBoxLayout())
        wdg.layout().addWidget(self.label3)
        simulation_dock = QtWidgets.QDockWidget('Simulation')
        simulation_dock.setWidget(wdg)
        simulation_dock.setFeatures(
            QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(
            QtCore.Qt.DockWidgetArea.LeftDockWidgetArea,
            simulation_dock)
        self.tabifyDockWidget(construction_dock, simulation_dock)

        self.tree = EngineParameterTree(settings)
        wdg.layout().addWidget(self.tree)
