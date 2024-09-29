from pydantic import BaseModel

from qtpy import QtWidgets, QtCore

from snngine_v4.gui.common.qobject_dicts import QTreeWidgetDict
from snngine_v4.snngine_config import EngineConfig
from snngine_v4.gui.parameter_tree.engine_parameter_tree import \
    EngineParameterTree


class SettingsWindow(QtWidgets.QWidget):

    def __init__(self, engine_config: EngineConfig, parent=None):

        super().__init__(parent=parent)

        self.engine_config: EngineConfig = engine_config

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        self.toolbar = QtWidgets.QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setOrientation(QtCore.Qt.Orientation.Vertical)

        self.top_layout = QtWidgets.QHBoxLayout()
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.layout().addLayout(self.top_layout)

        self.setting_trees: (QTreeWidgetDict
                             | dict[str, EngineParameterTree]) = (
            QTreeWidgetDict())

        self.top_layout.addWidget(self.toolbar)
        self.options_layout = QtWidgets.QVBoxLayout()
        self.options_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.addLayout(self.options_layout)

        for k in engine_config.model_fields:
            self.add_settings(getattr(engine_config, k), name=k)

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

        self.save_btn.clicked.connect(self.engine_config.export)

    def add_settings(self, settings: BaseModel, name):

        tree: EngineParameterTree | QtWidgets.QTreeWidget = (
            EngineParameterTree(name, settings, showHeader=True))
        self.setting_trees.add_widget(tree)

        if len(self.setting_trees) > 1:
            tree.setVisible(False)
        self.options_layout.addWidget(tree)
        action_name = name.capitalize()
        if action_name.endswith('_gl'):
            action_name = action_name.replace('_gl', 'GL')
        action = QtWidgets.QAction(action_name, self)
        self.toolbar.addAction(action)
        action.triggered.connect(lambda: self.show_tree(name))

    def show_tree(self, name):
        for k, tree in self.setting_trees.items():
            tree.setVisible(k == name)
            if k == name:
                header: QtWidgets.QHeaderView = tree.header()
                mode = QtWidgets.QHeaderView.ResizeMode.ResizeToContents
                header.resizeSections(mode)
        return
