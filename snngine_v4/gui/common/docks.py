from typing import ClassVar

from pyqtgraph.dockarea import Dock
from qtpy import QtWidgets

from snngine_v4.utils.core_utils import type_assertion


class MainDockWidget(QtWidgets.QDockWidget):

    DEFAULT_FEATURES: ClassVar = (
            QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable)

    def __init__(self, name, parent=None, features=None, **kwargs):
        super().__init__(name, parent=parent, **kwargs)
        if features is None:
            features = self.DEFAULT_FEATURES
        self.setFeatures(features)
        self.setObjectName(name)

    def close(self):
        self.widget().hide()
        super().close()

    def toggleVisibility(self):
        if self.isVisible():
            self.close()
        else:
            self.show()

    def show(self):
        super().show()
        self.widget().show()


class CustomPgDock(Dock):

    WIDGET_CLASS: ClassVar = None
    max_widgets: ClassVar = 1

    def addWidget(self, widget, **kwargs):
        if self.WIDGET_CLASS is not None:
            type_assertion(widget, self.WIDGET_CLASS)
        if ((self.max_widgets is not None)
                and (len(self.widgets) >= self.max_widgets)):
            raise PermissionError
        super().addWidget(widget, **kwargs)

    def widget(self) -> QtWidgets.QWidget:
        if self.max_widgets == 1:
            w = self.widgets[0]
            return w
        else:
            raise ValueError