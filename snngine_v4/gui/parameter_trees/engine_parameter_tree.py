from __future__ import annotations

from typing import Callable

from pydantic import BaseModel
from pyqtgraph.parametertree import Parameter, ParameterTree
from qtpy import QtCore, QtWidgets

from snngine_v4.gui.common.docks import MainDockWidget
from snngine_v4.gui.parameter_trees.parameter_builder.parameter_builder import (
    ParameterBuilder
)
from snngine_v4.gui.parameter_trees.connectors.model_signals_register \
    import ExtendedModelSignalsRegister
from snngine_v4.utils.core_utils import type_assertion
from snngine_v4.utils.field_utils import Undefined


# noinspection PyPep8Naming
class EngineParameterTree(ParameterTree):

    # noinspection PyPep8Naming
    def __init__(self,
                 name: str = None,
                 model: BaseModel = None,
                 parent=None, showHeader=True,
                 signal_register: ExtendedModelSignalsRegister = None,
                 b_verbose: bool = True,
                 **kwargs):

        if name is None:
            name = self.__class__.__name__

        if b_verbose:
            print('New EngineParameterTree:', name)

        super().__init__(parent=parent, showHeader=showHeader)
        self.setObjectName(name)

        self._settings_model = model
        self.signal_register = signal_register or ExtendedModelSignalsRegister()
        self.parameters = None
        if model is not None:
            self.set_parameters_from_model(
                model=self._settings_model, **kwargs)

        self._dock_widget = None

        header: QtWidgets.QHeaderView = self.header()
        mode = QtWidgets.QHeaderView.ResizeMode.Interactive
        header.setSectionResizeMode(mode)

    def addParameters(self, param, root=None, depth=0, showTop=True):

        if isinstance(root, Parameter):
            for item in root.items:
                if item.treeWidget() is self:
                    root = item
                    break
        if isinstance(root, Parameter):
            raise TypeError
        super().addParameters(param, root=root, depth=depth, showTop=showTop)

        header: QtWidgets.QHeaderView = self.header()
        mode = QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        header.resizeSections(mode)

    def add_parameters_from_model(
        self, model: BaseModel, root=None, depth=0, showTop=True,
        signal_register=None, exclude_keys=None, **options
    ):
        if signal_register is None:
            signal_register = self.signal_register
        elif signal_register is Undefined:
            signal_register = None

        pars = ParameterBuilder.make_pars_from_model(
            model=model, signal_register=signal_register,
            exclude_keys=exclude_keys, **options)
        self.addParameters(pars, root=root, depth=depth, showTop=showTop)
        return pars

    def add_parameters_from_linked_model(
        self, model0: BaseModel, model1: BaseModel,
            signal_register=None, exclude_keys=None, **options
    ):
        if signal_register is None:
            signal_register = self.signal_register
        signal_register.add_linked_model(model0=model0, model1=model1)
        new_pars = self.add_parameters_from_model(
            model=model1,
            root=signal_register.get_group(
                signal_register.model2model_map.inv[model1]),
            signal_register=signal_register,
            exclude_keys=exclude_keys, **options
        )
        if signal_register.get_model(new_pars) is not model1:
            raise AssertionError
        return new_pars

    def clear(self):
        super().clear()
        if self._settings_model is not None:
            self.remove(self._settings_model)
            self._settings_model = None
        self.parameters = None

    def copy(self, **kwargs):
        return self.__class__.from_pars(
            signal_register=self.signal_register,
            pars=self.parameters,
            model=self._settings_model, **kwargs)

    @classmethod
    def from_pars(cls, pars: Parameter | EngineParameterTree,
                  name=None, signal_register=None,
                  root=None, depth=0, showTop=False, model=None
                  ) -> EngineParameterTree:
        if isinstance(pars, EngineParameterTree):
            if name is None:
                name = pars.objectName()
            pars = pars.parameters
        tree = cls(name=name, signal_register=signal_register)
        tree.addParameters(pars, root=root, depth=depth, showTop=showTop)
        tree.settings_model = model
        return tree

    def list_all_parameters(self, item=None) -> list[Parameter]:
        res = []
        items = self.listAllItems(item=item)
        for item in items:
            if hasattr(item, 'param'):
                res.append(item.param)
        return res

    def remove(self, model):
        group = self.signal_register.disconnect_model(model)
        group_parent: Parameter = group.parent()
        if group_parent is not None:
            group_parent.removeChild(group)
            del group
        return model

    def resize_header_sections_to_content(self,):
        self.header().resizeSections(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

    def set_parameters_from_model(self, model, **kwargs):
        self.parameters = self.add_parameters_from_model(
            model=model, **kwargs)

    @property
    def settings_model(self):
        return self._settings_model

    @settings_model.setter
    def settings_model(self, value):
        if self._settings_model is not None:
            raise AttributeError("settings_model already set")
        type_assertion(value, BaseModel)
        self._settings_model = value

    def sizeHint(self) -> QtCore.QSize:
        hint = super().sizeHint()
        return QtCore.QSize(hint.width() + 100, hint.height() + 20)


class EngineTreeDockWidget(MainDockWidget):

    count: int = 0

    widget: Callable[[], EngineParameterTree]

    def __init__(self, pars: Parameter | EngineParameterTree,
                 name=None, parent=None, features=None, **kwargs):

        count = self.__class__.count
        self.__class__.count += 1

        if not isinstance(pars, QtWidgets.QTreeWidget):
            pars: EngineParameterTree | QtWidgets.QTreeWidget = (
                EngineParameterTree.from_pars(pars))

        if (name is None) or (name == ''):
            name = pars.objectName()
            if name == '':
                name = self.__class__.__name__ + str(count)

        super().__init__(name, parent=parent, features=features, **kwargs)
        self.setWidget(pars)


type QTree = EngineParameterTree | QtWidgets.QTreeWidget
