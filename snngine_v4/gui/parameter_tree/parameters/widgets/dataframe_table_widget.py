from __future__ import annotations

from enum import auto, IntEnum, unique
from typing import Callable, ClassVar, TYPE_CHECKING

from pyqtgraph import TableWidget
from pyqtgraph.dockarea import Dock
from qtpy import QtWidgets

from snngine_v4.gui.common.qobject_dicts import QWidgetDict

from snngine_v4.gui.parameter_tree.parameters.widgets.q_dataframe import \
    QDataFrame
from snngine_v4.gui.windows.main_window_base import MainEngineWindowBase
from snngine_v4.utils.containers.mappings import Object2ObjectMap

if TYPE_CHECKING:
    from snngine_v4.gui.parameter_tree.parameters.widgets.array_editor import (
        ArrayEditorArea,
    )


# noinspection PyPep8Naming
class QDataFrameUIWidgets(QWidgetDict):

    @unique
    class WidgetID(IntEnum):
        ADD_ROW = 0
        ADD_COLUMN = auto()
        EDITOR = auto()

    def __init__(self, qdf: QDataFrame,
                 b_connect: bool = True,
                 b_include_editor: bool = True
                 ):

        self.qdf: QDataFrame = qdf

        super().__init__()

        self._widget = QtWidgets.QWidget()
        self._widget.setLayout(QtWidgets.QHBoxLayout())
        self._widget.layout().setContentsMargins(0, 0, 0, 0)

        self[self.WidgetID.ADD_ROW] = QtWidgets.QPushButton('Add Row')
        self[self.WidgetID.ADD_COLUMN] = QtWidgets.QPushButton('Add Col')
        if b_include_editor:
            self[self.WidgetID.EDITOR] = QtWidgets.QPushButton('Editor')

        self._connected = False
        if b_connect is True:
            self.connect_widgets()

        if self.qdf.df is not None:
            self.updateTableWidgets()

    def addColClicked(self):
        self.qdf.addColumn()
        self.updateTableWidgets()

    def addRowClicked(self):
        self.qdf.addRow()
        self.updateTableWidgets()
    
    def connect_widgets(self):
        if self._connected is True:
            raise RuntimeError
        self._connected = True
        self[self.WidgetID.ADD_ROW].clicked.connect(self.addRowClicked)
        self[self.WidgetID.ADD_COLUMN].clicked.connect(self.addColClicked)
        if self.WidgetID.EDITOR in self:
            self[self.WidgetID.EDITOR].clicked.connect(self.editorClicked)
        self.qdf.sigChanged.connect(self.updateTableWidgets)

    def disconnect_widgets(self):
        if self._connected is False:
            raise RuntimeError
        self._connected = False
        self[self.WidgetID.ADD_ROW].clicked.disconnect(self.addRowClicked)
        self[self.WidgetID.ADD_COLUMN].clicked.disconnect(self.addColClicked)
        if self.WidgetID.EDITOR in self:
            self[self.WidgetID.EDITOR].clicked.disconnect(self.editorClicked)
        self.qdf.sigChanged.disconnect(self.updateTableWidgets)
    
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._widget.layout().addWidget(value)

    def editorClicked(self):
        w = self[self.WidgetID.EDITOR].window()
        if isinstance(w, MainEngineWindowBase):
            editor = w.arrayEditorDockWidget
            dock_area: ArrayEditorArea = editor.widget()
            if self.qdf not in dock_area.qdf_map:
                dock_area.addDock(self.qdf)
                if not editor.isVisible():
                    editor.show()
            else:
                wdg, dock = dock_area[self.qdf]
                if dock.parent() is None:
                    dock.label.show()
                    dock_area.addDock(dock)
                    if not editor.isVisible():
                        editor.show()
                else:
                    dock.close()
            if dock_area.count() == 0:
                editor.close()
        print()

    def updateTableWidgets(self):
        shape = self.qdf.as_array().shape

        add_row_enabled = (
                (len(self.qdf.df.columns) > 0)
                and (len(shape) > 1)
                and self.qdf.validator.validate_shape(
                    (shape[0] + 1, shape[1]))
        )
        self[self.WidgetID.ADD_ROW].setEnabled(add_row_enabled)

        add_col_enabled = (len(self.qdf.df.columns) > 0)
        if len(shape) == 1:
            next_shape = shape[0] + 1,
        else:
            next_shape = shape[0], shape[1] + 1
        add_col_enabled &= self.qdf.validator.validate_shape(next_shape)

        self[self.WidgetID.ADD_COLUMN].setEnabled(add_col_enabled)
    
    def widget(self):
        return self._widget
        

# noinspection PyPep8Naming
class QDataFrameTableWidget(TableWidget):
    sigChanged = None

    def __init__(
            self, qdf: QDataFrame, sortable=False, *args, **kwargs):

        self.qdf = qdf
        super().__init__(*args, sortable=sortable, **kwargs)

        self.editable = not self.qdf.readonly
        self.add_value = 0
        self.max_rows = 10
        self.max_cols = 10
        self.selected_item = None

        self.qdf.sigChanged.connect(self.onDataChange)
        self.qdf.sigColumnNamesChanged.connect(self.setColumnNames)
        self.qdf.sigColumnNamesChanged.emit(self.qdf.column_names)
        self.itemChanged.connect(self.onItemChange)

        self.itemSelectionChanged.connect(self.onItemSelectionChanged)
        self.itemPressed.connect(self.onItemPressed)
        self.onDataChange()

    def clear(self):
        super().clear()
        # self.setColumnNames(self.qdf.column_names)

    def appendData(self, data):
        super().appendData(data)
        self.setColumnNames(self.qdf.column_names)

    def make_ui_widgets(self,
                        b_include_editor: bool = True, ):
        widgets = QDataFrameUIWidgets(
            self.qdf, b_include_editor=b_include_editor)

        return widgets

    def onDataChange(self):
        self.itemChanged.disconnect(self.onItemChange)
        self.setData(self.qdf.value())
        self.itemChanged.connect(self.onItemChange)

    def onItemPressed(
            self, item: QtWidgets.QTableWidgetItem | None = None):
        self.selected_item = item
        return

    def onItemSelectionChanged(self):
        # if self.currentItem() != self.selected_item:
        self.selected_item = self.currentItem()
        return

    def onItemChange(self, row_or_item=-1, col=-1):
        if isinstance(row_or_item, QtWidgets.QTableWidgetItem):
            if col != -1:
                raise RuntimeError("col != -1")
            item = row_or_item
        else:
            item = self.item(row_or_item, col)

        if item == self.selected_item:
            self.qdf.update_from_item(item)

    def setColumnNames(self, names):
        if names:
            # self.setVerticalHeaderLabels(names)
            self.setHorizontalHeaderLabels(names)
            self.horizontalHeadersSet = True

    def value(self):
        return self.qdf.value()


class QDataFrameDockMap(Object2ObjectMap):
    ContainerConfigClass: ClassVar = (QDataFrame, Dock)


class QDataFrameTableMap(Object2ObjectMap):
    ContainerConfigClass: ClassVar = (QDataFrame, QDataFrameTableWidget)

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self.dock_map: QDataFrameDockMap | dict[QDataFrame, TableDock] = (
            QDataFrameDockMap())

    def add_dock(self, dock: TableDock):
        wdg = dock.widget().table
        self.dock_map[wdg.qdf] = dock
        self[wdg.qdf] = wdg

    def add_table_widget(self, wdg):
        if isinstance(wdg, InteractiveTableWidget):
            wdg = wdg.table
        elif isinstance(wdg, TableDock):
            wdg = wdg.widget().table
        self[wdg.qdf] = wdg


class InteractiveTableWidget(QtWidgets.QWidget):

    layout: Callable[[], QtWidgets.QGridLayout]

    def __init__(
            self,
            ui_widgets: QtWidgets.QWidget | QDataFrameUIWidgets,
            table_widget: QDataFrameTableWidget,
            *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.table = table_widget
        self.ui = ui_widgets
        if isinstance(ui_widgets, QWidgetDict):
            ui_widgets = ui_widgets.widget()
        self.setLayout(QtWidgets.QGridLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(ui_widgets, 0, 0)
        self.layout().addWidget(table_widget, 1, 0)
        ui_widgets.setMaximumHeight(24)
        ui_widgets.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Minimum,
        )
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
                b_include_editor=b_include_editor),
            table_widget=widget,
        )


class TableDock(Dock):

    def addWidget(self, widget, **kwargs):
        if len(self.widgets) == 0:
            super().addWidget(widget, **kwargs)
        else:
            raise PermissionError

    @classmethod
    def from_qdf(cls, qdf: QDataFrame, closable=True, **kwargs):
        widget = InteractiveTableWidget.from_qdf(
            qdf=qdf, b_include_editor=False)
        return cls(name=qdf.name, widget=widget,
                   closable=closable, **kwargs)

    def widget(self) -> InteractiveTableWidget:
        return self.widgets[0]
