from typing import Callable, ClassVar

from qtpy import QtWidgets

from snngine_v4.gui.common.docks import CustomPgDockArea, MainDockWidget
from snngine_v4.gui.parameters.widgets.table.df_table_widget_dock import (
        QDataFrameTableMap, TableDock
    )
from snngine_v4.gui.parameters.widgets.table.q_dataframe import \
    QDataFrame


# noinspection PyPep8Naming
class ArrayEditorArea(CustomPgDockArea):

    dock_map: QDataFrameTableMap

    def __init__(self, parent=None, temporary=False, home=None):
        super().__init__(parent=parent, temporary=temporary,
                         dock_map=QDataFrameTableMap(),
                         home=home)

    def addDock(self, dock=None, position='bottom',
                relativeTo=None, **kwargs) -> TableDock:

        if isinstance(dock, QDataFrame):
            dock, kwargs = TableDock.from_qdf(qdf=dock, **kwargs), {}
            dock.sigClosed.connect(self.close_if_empty)
            self.dock_map.add_dock(dock)
        if isinstance(dock, TableDock):
            dock.widget().ui.disconnect_widgets()
        dock = super().addDock(
            dock=dock, position=position,
            relativeTo=relativeTo, **kwargs)
        if isinstance(dock, TableDock):
            # dock.widget().ui.disconnect_widgets()
            dock.widget().ui.connect_widgets()
        return dock

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
