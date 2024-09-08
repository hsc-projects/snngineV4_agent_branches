from pydantic import BaseModel
from qtpy import QtGui, QtWidgets, QtCore

from snngine_v4.config.engine_config_model import EngineConfig
from snngine_v4.gui.parameter_tree.engine_parameter_tree import \
    EngineParameterTree
from snngine_v4.utils.containers.configurable_dict import ConfigurableDict


class SettingsWindow(QtWidgets.QWidget):

    def __init__(self, settings: EngineConfig, parent=None):

        super().__init__(parent=parent)

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        self.toolbar = QtWidgets.QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setOrientation(QtCore.Qt.Orientation.Vertical)

        self.top_layout = QtWidgets.QHBoxLayout()
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.layout().addLayout(self.top_layout)

        self.setting_trees = ConfigurableDict.from_type(EngineParameterTree)

        self.top_layout.addWidget(self.toolbar)
        self.options_layout = QtWidgets.QVBoxLayout()
        self.options_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.addLayout(self.options_layout)

        self.add_settings(settings.app_config)
        self.add_settings(settings.open_gl_config)

        btn_wdgs = QtWidgets.QWidget()
        btn_wdgs.setLayout(QtWidgets.QHBoxLayout())
        self.save_btn = QtWidgets.QPushButton("Save")
        self.apply_btn = QtWidgets.QPushButton("Apply")
        self.restart = QtWidgets.QPushButton("Restart")
        btn_wdgs.layout().addWidget(self.save_btn)
        btn_wdgs.layout().addWidget(self.apply_btn)
        btn_wdgs.layout().addWidget(self.restart)
        btn_wdgs.layout().setContentsMargins(2, 2, 2, 2)
        btn_wdgs.layout().setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.layout().addWidget(btn_wdgs)

    def show_tree(self, name):
        for k, tree in self.setting_trees.items():
            tree.setVisible(k == name)
        return

    def add_settings(self, settings: BaseModel, name=None):
        tree: EngineParameterTree | QtWidgets.QTreeWidget = (
            EngineParameterTree(settings, showHeader=False))
        if name is None:
            name = tree.settings_model.__class__.__name__
        self.setting_trees[name] = tree
        if len(self.setting_trees) > 1:
            tree.setVisible(False)
        self.options_layout.addWidget(tree)
        action = QtWidgets.QAction(name, self)
        self.toolbar.addAction(action)
        action.triggered.connect(lambda: self.show_tree(name))
