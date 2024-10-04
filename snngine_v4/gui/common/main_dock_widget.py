from typing import ClassVar

from qtpy import QtWidgets


class MainDockWidget(QtWidgets.QDockWidget):

    DEFAULT_FEATURES: ClassVar = (
            QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable)

    def __init__(self, name=None, parent=None,
                 features=None, **kwargs):
        super().__init__(name, parent=parent, **kwargs)
        if features is None:
            features = self.DEFAULT_FEATURES
        self.setFeatures(features)
        self.setObjectName(name)
