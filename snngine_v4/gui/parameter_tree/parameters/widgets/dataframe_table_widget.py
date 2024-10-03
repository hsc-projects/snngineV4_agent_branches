from copy import deepcopy

import numpy as np
import pandas as pd
from numpydantic.interface import NumpyInterface
from pyqtgraph import TableWidget
from qtpy import QtCore, QtWidgets

from snngine_v4.data.validation.array_annotation import TypedNumpyInterface
from snngine_v4.gui.parameter_tree.parameters.widgets.q_dataframe import \
    QDataFrame


# noinspection PyPep8Naming
class QDataFrameTableWidget(TableWidget):
    sigChanged = QtCore.Signal(object)
    sigChanging = QtCore.Signal(object, object)

    def __init__(
            self, data: QDataFrame, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.qdf = data

        self.add_value = 0
        self.max_rows = 10
        self.max_cols = 10
        self.selected_item = None
        # self.cellChanged.connect(self.onCellChange)
        # self.cellChanged.connect(self.onChange)
        self.itemChanged.connect(self.onChange)
        self.itemSelectionChanged.connect(self.onItemSelectionChanged)
        self.itemPressed.connect(self.onItemPressed)

    def onChange(self, row_or_item=-1, col=-1, b_block_signal=True):
        if isinstance(row_or_item, QtWidgets.QTableWidgetItem):
            item = row_or_item
            row = row_or_item.row()
            if col != -1:
                raise RuntimeError
            col = row_or_item.column()
        else:
            row = row_or_item
            item = self.item(row, col)

        if item == self.selected_item:
            self.qdf.update(item)
        if b_block_signal is False:
            self.sigChanged.emit(self)

    def onItemPressed(
            self, item: QtWidgets.QTableWidgetItem | None = None):
        self.selected_item = item
        return

    def onItemSelectionChanged(self):
        # if self.currentItem() != self.selected_item:
        self.selected_item = self.currentItem()
        return

    def setValue(self, value):
        value = self.qdf.as_df(value).values
        self.setData(value)

    def value(self):
        return self.qdf.value()
