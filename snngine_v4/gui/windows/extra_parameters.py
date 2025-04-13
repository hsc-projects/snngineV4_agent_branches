from typing import Callable

from pydantic import BaseModel
from pyqtgraph.dockarea import Dock, DockArea

from snngine_v4.gui.common.docks import CustomPgDock, CustomPgDockArea
from snngine_v4.gui.parameter_tree.engine_parameter_tree import \
    EngineParameterTree

from snngine_v4.utils.containers.mappings import (
    ObjectMapConfig,
    Object2ObjectMap,
)


class ParameterDock(CustomPgDock):

    WIDGET_CLASS: EngineParameterTree
    widget: Callable[..., EngineParameterTree]

    def clear(self):
        self.widget().clear()

    # def closeEvent(self, a0):
    #     self.widget().clear()
    #     super().closeEvent(a0)
    #
    # def close(self):
    #     self.widget().clear()
    #     super().close()

    def setVisible(self, visible):
        super().setVisible(visible)


class ParameterArea(CustomPgDockArea):

    def __init__(self, parent=None, temporary=False, home=None):
        super().__init__(parent=parent, temporary=temporary,
                         home=home)

    # noinspection PyPep8Naming
    def addDock(self, dock=None, position='bottom',
                relativeTo=None, closable=True, **kwargs) -> Dock:

        name = kwargs.pop('name', None)

        if (dock is None) or isinstance(dock, BaseModel):

            model = dock
            if name is None:
                name = model.__class__.__name__
            dock = EngineParameterTree(name=name, model=model, **kwargs)
            kwargs = {}

        if isinstance(dock, EngineParameterTree):
            widget = dock
            dock = ParameterDock(name=name, closable=closable, **kwargs)
            dock.addWidget(widget)
            self.dock_map[widget.settings_model] = dock

        dock = super().addDock(
            dock=dock, position=position,
            relativeTo=relativeTo, **kwargs)

        return dock

    def closeEvent(self, a0):
        docks = self.findAll()[1]
        for dock in docks.values():
            if isinstance(dock, ParameterDock):
                dock.clear()
        self.clear()
        self.docks.clear()
        self.dock_map.clear(b_force=True)
        super().closeEvent(a0)

    def close(self):
        self.clear()
        self.docks.clear()
        super().close()
