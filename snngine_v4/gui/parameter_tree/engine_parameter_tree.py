from pydantic import BaseModel
from pyqtgraph.parametertree import ParameterTree
from qtpy import QtCore, QtWidgets

from snngine_v4.gui.parameter_tree.parameter_builder import ParameterBuilder
from snngine_v4.gui.parameter_tree.signal_register import SignalMapRegister


class EngineParameterTree(ParameterTree):

    # noinspection PyPep8Naming
    def __init__(self, model: BaseModel,
                 parent=None, showHeader=True):

        super().__init__(parent=parent, showHeader=showHeader)

        self.settings_model = model
        settings_model_dict = self.settings_model.model_dump()
        self.signal_register = SignalMapRegister()
        self.parameters = self.add_parameters_from_model(
            self.settings_model, model_dict=settings_model_dict)

        self._q_dock_widget = None

    def add_parameters_from_model(self, model: BaseModel, model_dict=None):
        if model_dict is None:
            model_dict = model.model_dump()
        pars = ParameterBuilder.make_pars(
            model=model, model_dict=model_dict,
            signal_register=self.signal_register)
        self.addParameters(pars)
        return pars

    def sizeHint(self):
        hint = super().sizeHint()
        return QtCore.QSize(hint.width(), hint.height() + 20)

    @property
    def q_dock_widget(self):
        return self._q_dock_widget

    def set_q_dock_widget(self, name=None, features=None):
        if self._q_dock_widget is not None:
            raise PermissionError

        if name is None:
            name = self.settings_model.__class__.__name__

        dock = QtWidgets.QDockWidget(name)
        dock.setWidget(self)
        if features is None:
            features = (
                QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
                | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable)
        dock.setFeatures(features)
        self._q_dock_widget = dock
        return self._q_dock_widget
