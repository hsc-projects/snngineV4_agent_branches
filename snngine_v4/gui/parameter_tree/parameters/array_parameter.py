import numpy as np
import pandas as pd
from pyqtgraph import TableWidget
from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import WidgetParameterItem
from qtpy import QtCore, QtWidgets

from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


# noinspection PyPep8Naming
class DataFrameTable(TableWidget):
    sigChanged = QtCore.Signal(object)
    sigChanging = QtCore.Signal(object, object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.add_value = 0

        self.max_rows = 10
        self.max_cols = 10
        self.df: pd.DataFrame = pd.DataFrame()
        self.cellChanged.connect(self.onChange)
        self.itemChanged.connect(self.onChange)

    def addRow(self, vals):
        self.df.loc[len(self.df.index)] = vals
        self.setData(self.df)

    def addColumn(self, vals):
        new_col = len(self.df.columns)
        if new_col in self.df.columns:
            init_new_col = new_col
            i = 2
            while new_col in self.df.columns:
                new_col = f"f{init_new_col} ({i})"
        self.df[new_col] = vals
        self.setData(self.df)

    def appendData(self, data):
        if len(data.shape) != 2:
            raise AssertionError
        data = data[:min(data.shape[0], self.max_rows),
                    :min(data.shape[1], self.max_cols)]
        super().appendData(data)

    def clear(self):
        super().clear()
        self.df = pd.DataFrame()

    def onChange(self, row_or_item=-1, col=-1):
        if isinstance(row_or_item, QtWidgets.QTableWidgetItem):
            row = row_or_item.row()
            if col != -1:
                raise RuntimeError
            col = row_or_item.column()
        else:
            row = row_or_item
        self.sigChanged.emit(self)

    def setData(self, data: np.ndarray | pd.DataFrame):
        init_data = data
        if isinstance(data, pd.DataFrame):
            data = data.values
        super().setData(data)
        if isinstance(init_data, pd.DataFrame):
            self.df = init_data
        else:
            self.df = pd.DataFrame(data)

    def setValue(self, value: np.ndarray):
        self.setData(value)

    def value(self):
        return self.df.values


# noinspection PyPep8Naming
class ArrayParameterItem(WidgetParameterItem):

    def __init__(self, *args, **kwargs):
        # self.widget: DataFrameTable | QtWidgets.QTableWidget | None = None
        self.widget: DataFrameTable | None = None
        super().__init__(*args, **kwargs)

        self.addRowWidget = QtWidgets.QPushButton('Add Row')
        self.addRowWidget.clicked.connect(self.addRowClicked)
        self.layoutWidget.layout().insertWidget(
            self.layoutWidget.layout().count() - 2, self.addRowWidget)
        self.addRowWidget.setEnabled(False)

        self.addColWidget = QtWidgets.QPushButton('Add Col')
        self.addColWidget.clicked.connect(self.addColClicked)
        self.layoutWidget.layout().insertWidget(
            self.layoutWidget.layout().count() - 2, self.addColWidget)
        self.param.sigValueChanged.connect(self.updateTableWidgets)

    def valueChanged(self, param, val, force=False):
        super().valueChanged(param, val, force)

    def widgetValueChanged(self, ):
        super().widgetValueChanged()

    def addRowClicked(self,):
        vals = np.zeros(len(self.widget.df.columns))
        vals[:] = self.param.opts[ParamOpts.KW.C_ARRAY_DEFAULT_VALUE]
        self.widget.addRow(vals=vals)
        self.updateTableWidgets()

    def addColClicked(self,):
        vals = np.zeros(len(self.widget.df))
        vals[:] = self.param.opts[ParamOpts.KW.C_ARRAY_DEFAULT_VALUE]
        self.widget.addColumn(vals=vals)
        self.updateTableWidgets()

    def makeWidget(self):
        self.asSubItem = True
        table = DataFrameTable()
        table.setMaximumHeight(200)
        table.editable = not self.param.opts[ParamOpts.KW.READONLY]
        # table.editable = self.param.opts[ParamOpts.KW.READONLY]
        return table

    def updateTableWidgets(self):
        self.addRowWidget.setEnabled(len(self.widget.df.columns) > 0)


class ArrayParameter(Parameter):
    itemClass = ArrayParameterItem

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)