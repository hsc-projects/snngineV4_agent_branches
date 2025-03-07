from typing import Callable, ClassVar

from pyqtgraph.dockarea import DockArea
from qtpy import QtWidgets

from snngine_v4.gui.common.docks import MainDockWidget
from snngine_v4.gui.parameter_tree.parameters.widgets.table \
    .df_table_widget_dock import (
        QDataFrameTableMap, TableDock
    )
from snngine_v4.gui.parameter_tree.parameters.widgets.table.q_dataframe import \
    QDataFrame


# noinspection PyPep8Naming
class ArrayEditorArea(DockArea):

    def __init__(self, parent=None, temporary=False, home=None):
        super().__init__(parent=parent, temporary=temporary, home=home)
        self.qdf_map = QDataFrameTableMap()

    def addDock(self, dock=None, position='bottom',
                relativeTo=None, **kwargs) -> TableDock:

        if isinstance(dock, QDataFrame):
            dock, kwargs = TableDock.from_qdf(qdf=dock, **kwargs), {}
            dock.sigClosed.connect(self.close_if_empty)
            self.qdf_map.add_dock(dock)
        if isinstance(dock, TableDock):
            dock.widget().ui.disconnect_widgets()
        dock = super().addDock(
            dock=dock, position=position,
            relativeTo=relativeTo, **kwargs)
        if isinstance(dock, TableDock):
            # dock.widget().ui.disconnect_widgets()
            dock.widget().ui.connect_widgets()
        return dock

    def __getitem__(self, key):
        return self.qdf_map[key], self.qdf_map.dock_map[key]

    def close_if_empty(self):
        if self.count() == 0:
            if isinstance(self.parent(), ArrayEditorDockWidget):
                self.parent().close()
            else:
                self.close()


# noinspection PyPep8Naming
class ArrayEditorDockWidget(MainDockWidget):

    DEFAULT_FEATURES: ClassVar = (
            QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable)

    widget: Callable[[], ArrayEditorArea]

    def __init__(self, name, parent=None,
                 features=None, **kwargs):
        super().__init__(name,
                         features=features, parent=parent, **kwargs)
        # noinspection PyTypeChecker
        self.setWidget(ArrayEditorArea())
        return
