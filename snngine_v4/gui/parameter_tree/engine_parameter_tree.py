from __future__ import annotations

from pydantic import BaseModel
from pyqtgraph.parametertree import Parameter, ParameterTree
from qtpy import QtCore, QtWidgets

from snngine_v4.gui.parameter_tree.parameter_builder import ParameterBuilder
from snngine_v4.gui.parameter_tree.connectors.basemodel_signal_register \
    import ModelSignalRegister


class EngineParameterTree(ParameterTree):

    # noinspection PyPep8Naming
    def __init__(self,
                 name: str,
                 model: BaseModel = None,
                 parent=None, showHeader=True):

        super().__init__(parent=parent, showHeader=showHeader)
        self.setObjectName(name)

        self._settings_model = model
        self.signal_register = ModelSignalRegister()
        if model is not None:
            settings_model_dict = self._settings_model.model_dump()
            self.parameters = self.add_parameters_from_model(
                self._settings_model, model_dict=settings_model_dict)

        self._dock_widget = None

        header: QtWidgets.QHeaderView = self.header()
        mode = QtWidgets.QHeaderView.ResizeMode.Interactive
        header.setSectionResizeMode(mode)

    # noinspection PyPep8Naming
    def addParameters(self, param, root=None, depth=0, showTop=True):
        super().addParameters(param, root=root, depth=depth, showTop=showTop)

        header: QtWidgets.QHeaderView = self.header()
        mode = QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        header.resizeSections(mode)
        # header.resizeSection(0, 15)

    def add_parameters_from_model(self, model: BaseModel, model_dict=None):
        if model_dict is None:
            model_dict = model.model_dump()
        pars = ParameterBuilder.make_pars_from_model(
            model=model, model_dict=model_dict,
            signal_register=self.signal_register)
        self.addParameters(pars)
        return pars

    # noinspection PyPep8Naming
    @classmethod
    def from_pars(cls, pars: Parameter | EngineParameterTree,
                  name=None,
                  root=None, depth=0, showTop=False, model=None
                  ) -> EngineParameterTree:
        if isinstance(pars, EngineParameterTree):
            if name is None:
                name = pars.objectName()
            pars = pars.parameters
        tree = cls(name=name)
        tree.addParameters(pars, root=root, depth=depth, showTop=showTop)
        tree.settings_model = model
        return tree

    @property
    def dock_widget(self):
        return self._dock_widget

    @dock_widget.setter
    def dock_widget(self, value):
        if self._dock_widget is not None:
            raise AttributeError("dock_widget already set")
        self._dock_widget = value

    @property
    def settings_model(self):
        return self._settings_model

    @settings_model.setter
    def settings_model(self, value):
        if self._settings_model is not None:
            raise AttributeError("settings_model already set")
        self._settings_model = value

    def set_q_dock_widget(self, name=None, features=None):
        if self._dock_widget is not None:
            raise PermissionError

        dock = QtWidgets.QDockWidget(name)
        dock.setWidget(self)

        self._dock_widget = dock
        return self._dock_widget

    def sizeHint(self):
        hint = super().sizeHint()
        return QtCore.QSize(hint.width() + 100, hint.height() + 20)


class EngineTreeDockWidget(QtWidgets.QDockWidget):

    count: int = 0

    def __init__(self, pars: Parameter | EngineParameterTree,
                 name=None, parent=None,
                 features=None, **kwargs):

        count = self.__class__.count
        self.__class__.count += 1

        if not isinstance(pars, QtWidgets.QTreeWidget):
            pars: EngineParameterTree | QtWidgets.QTreeWidget = (
                EngineParameterTree.from_pars(pars))

        if (name is None) or (name == ''):
            name = pars.objectName()
            if name == '':
                name = self.__class__.__name__ + str(count)
        super().__init__(name, parent=parent, **kwargs)
        self.setObjectName(name)
        pars.dock_widget = self
        self.setWidget(pars)

        if features is None:
            features = (
                    QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
                    | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.setFeatures(features)
