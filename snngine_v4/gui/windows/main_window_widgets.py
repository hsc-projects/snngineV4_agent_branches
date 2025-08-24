from typing import Callable

from qtpy import QtCore, QtWidgets

from snngine_v4.gui.common.docks import MainDockWidget


class ButtonsDockWidget(MainDockWidget):

    def __init__(self, name, parent=None, features=None, **kwargs):
        super().__init__(name, parent=parent,
                         features=features, **kwargs)
        self.setWidget(QtWidgets.QWidget())
        widget_layout = QtWidgets.QGridLayout()
        self.widget().setLayout(widget_layout)

        self.build_button = QtWidgets.QPushButton('Build')
        widget_layout.addWidget(self.build_button, 0, 0)

        self.test_button = QtWidgets.QPushButton('[Test]')
        widget_layout.addWidget(self.test_button, 0, 1)


class RightToolbar(QtWidgets.QToolBar):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(False)
        self.setVisible(False)
        self.setAllowedAreas(QtCore.Qt.ToolBarArea.RightToolBarArea)
        self.setOrientation(QtCore.Qt.Orientation.Vertical)

    def addAction(self, action):
        if not self.isVisible():
            self.setVisible(True)
        super().addAction(action)
