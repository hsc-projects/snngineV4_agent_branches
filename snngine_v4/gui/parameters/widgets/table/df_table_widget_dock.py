from __future__ import annotations

from typing import Callable, ClassVar

from pyqtgraph.dockarea import Dock
from qtpy import QtWidgets

from snngine_v4.gui.common.docks import CustomPgDock
from snngine_v4.gui.parameters.widgets.table.df_table_widget \
    import (
        QDataFrameTableWidget, QDataFrameUIWidgets,
    )
from snngine_v4.gui.parameters.widgets.table.q_dataframe import \
    QDataFrame
from snngine_v4.utils.containers.mappings import Object2ObjectMap


class QDataFrameDockMap(Object2ObjectMap):
    ContainerConfigClass: ClassVar = (QDataFrame, Dock)


class QDataFrameTableMap(Object2ObjectMap):
    ContainerConfigClass: ClassVar = (QDataFrame, QDataFrameTableWidget)

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self.docks: QDataFrameDockMap | dict[QDataFrame, TableDock] = (
            QDataFrameDockMap())

    def add_dock(self, dock: TableDock):
        wdg = dock.widget().table
        self.docks[wdg.qdf] = dock
        self[wdg.qdf] = wdg

    def add_table_widget(self, wdg):
        if isinstance(wdg, InteractiveTableWidget):
            wdg = wdg.table
        elif isinstance(wdg, TableDock):
            wdg = wdg.widget().table
        self[wdg.qdf] = wdg


class InteractiveTableWidget(QtWidgets.QWidget):

    layout: Callable[[], QtWidgets.QGridLayout]

    def __init__(self, ui_widgets: QtWidgets.QWidget | QDataFrameUIWidgets,
                 table_widget: QDataFrameTableWidget, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.table: QDataFrameTableWidget = table_widget
        self.ui: QDataFrameUIWidgets = ui_widgets

        ui_widget = ui_widgets.widget()
        self.setLayout(QtWidgets.QGridLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(ui_widget, 0, 0)
        self.layout().addWidget(table_widget, 1, 0)
        ui_widget.setMaximumHeight(
            26 * (self.ui.layout_row + 1 * int(self.ui.layout_col > 0)))
        ui_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Minimum,
        )
        # noinspection PyUnresolvedReferences
        table_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

    @classmethod
    def from_qdf(cls, qdf: QDataFrame,
                 b_include_editor: bool = True
                 ):
        widget = QDataFrameTableWidget(qdf)
        return cls(
            ui_widgets=widget.make_ui_widgets(
                b_include_editor=b_include_editor,
            ),
            table_widget=widget,
        )


class TableDock(CustomPgDock):

    WIDGET_CLASS: InteractiveTableWidget
    widget: Callable[..., InteractiveTableWidget]

    @classmethod
    def from_qdf(cls, qdf: QDataFrame, closable=True, **kwargs):
        widget = InteractiveTableWidget.from_qdf(
            qdf=qdf, b_include_editor=False)
        shape = 'x'.join([str(x) for x in qdf.df.shape])
        dock_name = qdf.name + f" ({shape})"
        return cls(name=dock_name, widget=widget,
                   closable=closable, **kwargs)
