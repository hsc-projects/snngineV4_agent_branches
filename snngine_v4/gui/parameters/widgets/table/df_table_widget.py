from __future__ import annotations

from enum import auto, IntEnum
from typing import Callable, TYPE_CHECKING

import numpy as np
import pandas as pd

from pyqtgraph import TableWidget
from pyqtgraph.widgets.TableWidget import TableWidgetItem
from qtpy import QtWidgets, QtCore

from snngine_v4.gui.common.qobject_dicts import QWidgetDict
from snngine_v4.gui.parameters.widgets.custom_spin_box import \
    CustomSpinBox

from snngine_v4.gui.parameters.widgets.table.q_dataframe import \
    QDataFrame

from snngine_v4.gui.windows.main_window_base import MainEngineWindowBase

if TYPE_CHECKING:
    from snngine_v4.gui.parameters.widgets.table.array_editor import (
            ArrayEditorArea,
        )


class IndexSpinBox(CustomSpinBox):
    def __init__(self, parent=None, **kwargs):

        kwargs.setdefault('value', 0)
        kwargs.setdefault('int', True)
        kwargs.setdefault('min', 0)
        kwargs.setdefault('delay', .1)

        super().__init__(parent, **kwargs)


class UIEmitter(QtCore.QObject):
    sigRowRangeChanged = QtCore.Signal(int, int)
    sigColRangeChanged = QtCore.Signal(int, int)


# noinspection PyPep8Naming
class QDataFrameUIWidgets(QWidgetDict):

    # @unique
    class WidgetID(IntEnum):
        ADD_ROW = 0
        ADD_COLUMN = auto()
        EDITOR = auto()

        ROW_LABEL = auto()
        MIN_ROW = auto()
        MAX_ROW = auto()

        COL_LABEL = auto()
        MIN_COL = auto()
        MAX_COL = auto()

    __getitem__: Callable[[], QtWidgets.QPushButton | IndexSpinBox]

    def __init__(self, qdf: QDataFrame,
                 b_connect: bool = True,
                 b_include_editor: bool = True,
                 n_layout_cols=3
                 ):

        self.qdf: QDataFrame = qdf

        self.emitter: UIEmitter | None = None
        emitter = UIEmitter(parent=None)
        super().__init__(emitter=emitter)
        self.sigRowRangeChanged = self.emitter.sigRowRangeChanged
        self.sigColRangeChanged = self.emitter.sigColRangeChanged

        self._widget = QtWidgets.QWidget()
        self._widget.setLayout(QtWidgets.QGridLayout())
        self._widget.layout().setContentsMargins(0, 0, 0, 0)
        self.layout_row = 0
        self.layout_col = 0
        self.n_layout_cols = n_layout_cols

        if b_include_editor:
            self[self.WidgetID.ADD_ROW] = QtWidgets.QPushButton('Add Row')
            self[self.WidgetID.ADD_COLUMN] = QtWidgets.QPushButton('Add Col')
            self[self.WidgetID.EDITOR] = QtWidgets.QPushButton('Editor')
            self.make_row_widgets()
            self.make_col_widgets()
        else:
            self.n_layout_cols += 1
            # self.layout_col += 1
            # if self.layout_col >= self.n_layout_cols:
            #     self.layout_col = 0
            #     self.layout_row += 1
            self.make_row_widgets()
            self[self.WidgetID.ADD_ROW] = QtWidgets.QPushButton('  +  ')
            self.make_col_widgets()
            self[self.WidgetID.ADD_COLUMN] = QtWidgets.QPushButton('  +  ')

        self._connected = False
        if b_connect is True:
            self.connect_widgets()

        if self.qdf.df is not None:
            self.updateTableWidgets()

    def make_row_widgets(self):
        self[self.WidgetID.ROW_LABEL] = QtWidgets.QLabel('Rows')
        self[self.WidgetID.MIN_ROW] = IndexSpinBox(value=0)
        self[self.WidgetID.MAX_ROW] = IndexSpinBox(value=100)

    def make_col_widgets(self):
        self[self.WidgetID.COL_LABEL] = QtWidgets.QLabel('Columns')
        self[self.WidgetID.MIN_COL] = IndexSpinBox(value=0)
        self[self.WidgetID.MAX_COL] = IndexSpinBox(value=8)

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

        self[self.WidgetID.MIN_ROW].sigValueChanged.connect(
            self.rowRangeUpdated)
        self[self.WidgetID.MAX_ROW].sigValueChanged.connect(
            self.rowRangeUpdated)
        self.rowRangeUpdated(self[self.WidgetID.MIN_ROW])
        self.rowRangeUpdated(self[self.WidgetID.MAX_ROW])

        self[self.WidgetID.MIN_COL].sigValueChanged.connect(
            self.colRangeUpdated)
        self[self.WidgetID.MAX_COL].sigValueChanged.connect(
            self.colRangeUpdated)
        self.colRangeUpdated(self[self.WidgetID.MIN_COL])
        self.colRangeUpdated(self[self.WidgetID.MAX_COL])

        self.qdf.sigChanged.connect(self.updateTableWidgets)

    def range_update(self, k_min, k_max, wdg, signal):
        if wdg is not None:
            if wdg == self[k_min]:
                self[k_max].setMinimum(self[k_min].value(), )
            elif wdg == self[k_max]:
                self[k_min].setMaximum(self[k_max].value(), )
            else:
                raise RuntimeError
        min_value, max_value = self[k_min].value(), self[k_max].value()
        signal.emit(min_value, max_value)

    def rowRangeUpdated(self, wdg: CustomSpinBox = None):
        self.range_update(self.WidgetID.MIN_ROW, self.WidgetID.MAX_ROW, wdg,
                          self.sigRowRangeChanged)

    def colRangeUpdated(self, wdg: CustomSpinBox = None):
        self.range_update(self.WidgetID.MIN_COL, self.WidgetID.MAX_COL, wdg,
                          self.sigColRangeChanged)

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
        self._widget.layout().addWidget(value, self.layout_row, self.layout_col)
        self.layout_col += 1
        if self.layout_col >= self.n_layout_cols:
            self.layout_col = 0
            self.layout_row += 1

    def editorClicked(self):
        w = self[self.WidgetID.EDITOR].window()
        if isinstance(w, MainEngineWindowBase):
            editor = w.arrayEditorDockWidget
            dock_area: ArrayEditorArea = editor.widget()
            if self.qdf not in dock_area.dock_map:
                dock_area.addDock(self.qdf)
                if not editor.isVisible():
                    editor.show()
            else:
                dock = dock_area.dock_map.docks[self.qdf]
                if dock.parent() is None:
                    dock.label.show()
                    dock_area.addDock(dock)
                    if not editor.isVisible():
                        editor.show()
                else:
                    dock.close()
            if dock_area.count() == 0:
                editor.close()

    def updateTableWidgets(self, *args, **kwargs):
        shape = self.qdf.as_array().shape

        add_row_enabled = (
                (len(shape) > 1)
                and (len(self.qdf.df.columns) > 0)
                and self.qdf.validator.validate_shape(
                    (shape[0] + 1, shape[1]))
        )
        self[self.WidgetID.ADD_ROW].setEnabled(add_row_enabled)

        if isinstance(self.qdf.df, pd.DataFrame):
            add_col_enabled = (len(self.qdf.df.columns) > 0)
            if len(shape) == 1:
                next_shape = shape[0] + 1,
            else:
                next_shape = shape[0], shape[1] + 1
            add_col_enabled &= self.qdf.validator.validate_shape(next_shape)
        else:
            add_col_enabled = False

        self[self.WidgetID.ADD_COLUMN].setEnabled(add_col_enabled)

        self[self.WidgetID.MAX_ROW].setOpts(max=len(self.qdf.df) - 1)
    
    def widget(self):
        return self._widget
        

class CustomTableWidgetItem(TableWidgetItem):

    def textChanged(self):

        if self._blockValueChange:
            return

        if isinstance(self.value, (bool, np.bool)):
            if self.text() in ['False', 'false', '0']:
                self._blockValueChange = True
                try:
                    self._text = ''
                    self.setText(self._text)
                finally:
                    self._blockValueChange = False

        super().textChanged()
        if isinstance(self.value, (bool, np.bool)):
            self._updateText()


# noinspection PyPep8Naming
class QDataFrameTableWidget(TableWidget):
    sigChanged = None

    # self.itemClass = TableWidgetItem

    def __init__(
            self, qdf: QDataFrame, sortable=False, *args, **kwargs):

        self.qdf: QDataFrame = qdf
        super().__init__(*args, sortable=sortable, **kwargs)
        self.itemClass = CustomTableWidgetItem

        self.editable = not self.qdf.readonly

        self.row_range: pd.Interval = pd.Interval(
            0, 100, closed='both')

        self.col_range: pd.Interval = pd.Interval(
            0, 6, closed='both')

        self.selected_item = None

        self.qdf.sigChanged.connect(self.onDataChange)
        self.qdf.sigColumnNamesChanged.connect(self.setHorizontalHeaderLabels)
        self.qdf.sigColumnNamesChanged.emit(self.qdf.column_names)
        self.qdf.sigIndexNamesChanged.connect(self.setVerticalHeaderLabels)
        if ((self.qdf.index_names is not None)
                and isinstance(self.qdf.index_names[0], str)):
            self.qdf.sigIndexNamesChanged.emit(self.qdf.index_names)
        self.itemChanged.connect(self.onItemChange)

        self.itemSelectionChanged.connect(self.onItemSelectionChanged)
        self.itemPressed.connect(self.onItemPressed)
        self.onDataChange()

    def appendData(self, data):
        data = self.applyRange(data)
        super().appendData(data)
        self.setHorizontalHeaderLabels(self.qdf.column_names)
        self.setVerticalHeaderLabels(self.qdf.index_names)

    def applyRange(self, data: np.ndarray):

        if isinstance(data, np.ndarray):

            if data.ndim not in [1, 2]:
                raise NotImplementedError

            n_rows = data.shape[0]
            if n_rows <= self.row_range.left:
                self.clear()
                return
            else:
                min_row = self.row_range.left
                max_row = self.row_range.right
                if max_row >= n_rows:
                    max_row = n_rows - 1
                data = data[min_row:max_row + 1]

                if data.ndim >= 2:

                    n_cols = data.shape[1]
                    if n_cols <= self.col_range.left:
                        self.clear()
                        return
                    else:
                        min_col = self.col_range.left
                        max_col = self.col_range.right
                        if max_col >= n_cols:
                            max_col = n_cols - 1
                        data = data[:, min_col:max_col + 1]

        else:
            raise NotImplementedError

        return data

    def clear(self):
        super().clear()
        # self.setColumnNames(self.qdf.column_names)

    def make_ui_widgets(self,
                        b_include_editor: bool = True,
                        b_connect: bool = True, **kwargs):
        widgets = QDataFrameUIWidgets(
            self.qdf, b_include_editor=b_include_editor, **kwargs)

        if b_connect is True:
            widgets.sigRowRangeChanged.connect(self.setRowRange)
            widgets.rowRangeUpdated()
            widgets.sigColRangeChanged.connect(self.setColRange)
            widgets.colRangeUpdated()

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

    def setHorizontalHeaderLabels(self, labels: list | None):
        if labels and (len(labels) > self.col_range.left):
            labels = labels[min(self.col_range.left, len(labels) - 1)
                            : min(self.col_range.right + 1, len(labels))]
            super().setHorizontalHeaderLabels(labels)
            # self.horizontalHeadersSet = True
        else:
            labels = pd.RangeIndex(
                self.col_range.left,
                self.col_range.right + 1).values.astype(str)
            super().setHorizontalHeaderLabels(labels)

    def setVerticalHeaderLabels(self, labels: list | None):
        if labels and (len(labels) > self.row_range.left):
            labels = labels[min(self.row_range.left, len(labels) - 1)
                            : min(self.row_range.right + 1, len(labels))]
            super().setVerticalHeaderLabels(labels)
            # self.verticalHeadersSet = True
        else:
            labels = pd.RangeIndex(
                self.row_range.left,
                self.row_range.right + 1).values.astype(str)
            super().setVerticalHeaderLabels(labels)

    def setColRange(self, min_col: int, max_col: int):
        self.col_range = pd.Interval(min_col, max_col, closed='both')
        self.onDataChange()

    def setRowRange(self, min_row: int, max_row: int):
        self.row_range = pd.Interval(min_row, max_row, closed='both')
        self.onDataChange()

    def setData(self, data):
        super().setData(data)

    def value(self):
        return self.qdf.value()


# class QDataFrameTableTreeWidget(QPushButton):
#     def __init__(self, qdf: QDataFrame, text='Editor'):
#
#         self.qdf = qdf
#         super().__init__(text)
