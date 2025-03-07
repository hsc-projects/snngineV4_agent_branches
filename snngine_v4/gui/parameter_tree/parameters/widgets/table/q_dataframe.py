from copy import deepcopy
from enum import auto, IntEnum
from typing import ClassVar

import numpy as np
import pandas as pd
from numpydantic.interface import NumpyInterface
from pydantic_core import PydanticUndefined
# noinspection PyProtectedMember
from pyqtgraph.widgets.TableWidget import TableWidgetItem
from qtpy import QtCore, QtSql, QtWidgets

from snngine_v4.utils.core_utils import type_assertion
from snngine_v4.utils.data_utils.validation.np_interface \
    import TypedNumpyInterface


class DataChangeType(IntEnum):

    UNDEFINED = 0
    ROW_ADDED = auto()
    COLUMN_ADDED = auto()
    CELL_UPDATED = auto()
    COLUMN_VALUE_UPDATED = auto()
    INDEX_VALUE_UPDATED = auto()
    DATA_CHANGED = auto()
    SET_DATA = auto()
    SET_VALUE = auto()


# noinspection PyPep8Naming
class QDataFrame(QtSql.QSqlTableModel):

    sigChanged = QtCore.Signal(object, int, object)
    sigSetData = QtCore.Signal(object, int, object)

    sigColumnNamesChanged = QtCore.Signal(object)
    sigIndexNamesChanged = QtCore.Signal(object)

    BLOCK_SIGNAL_ROLE: ClassVar[int] = -1

    def __init__(self, name,
                 validator, value, default_value=PydanticUndefined,
                 readonly=False,
                 column_names=None,
                 index_names=None,
                 parent=None):

        super().__init__(parent)

        self.name = name
        self.readonly = readonly
        self.readonly = readonly
        self.validator = validator
        self._column_names = column_names
        self._index_names = index_names

        if default_value == PydanticUndefined:
            default_value = value
        self.default_value = default_value

        self.dataChanged.connect(self.onDataChanged)

        self._df: pd.DataFrame | pd.Series = None
        # if value is not None:
        self.setValue(value)

    def addRow(self, value=PydanticUndefined):
        if value == PydanticUndefined:
            value = 0

        if isinstance(self.df.index[-1], str):
            new_last_idx = f"new_{len(self.df)}"
            new_index = list(self.df.index) + [new_last_idx]
            if self._index_names is not None:
                self._index_names = new_index
        elif isinstance(self.df.index[-1], int):
            new_last_idx = len(self.df)
            if not isinstance(self.df.index, pd.RangeIndex):
                raise NotImplementedError
            new_index = pd.RangeIndex(len(self.df) + 1)

        else:
            raise NotImplementedError

        if new_last_idx in self.df.index:
            raise NotImplementedError

        new_df = pd.DataFrame(data=0,
                              dtype=self.validator.dtype,
                              columns=self.df.columns,
                              index=new_index)

        new_df.iloc[: len(self.df.index), :] = self.df
        new_df.iloc[len(self.df.index), :] = value

        self.setData(value=new_df, role=DataChangeType.ROW_ADDED)

        if self._index_names is not None:
            self.sigIndexNamesChanged.emit(self._index_names)

    def addColumn(self, value=PydanticUndefined, dtype=None):
        if (dtype is None) and isinstance(self.validator, NumpyInterface):
            dtype = self.validator.dtype
        else:
            dtype = self.df.values[:, -1].dtype

        new_values = np.zeros(len(self.df), dtype=dtype)
        if value != PydanticUndefined:
            new_values[:] = value

        new_col = len(self.df.columns)
        if new_col in self.df.columns:
            init_new_col = new_col
            i = 2
            while new_col in self.df.columns:
                new_col = f"f{init_new_col} ({i})"
        # new_df = deepcopy(self.df)
        self.df[new_col] = new_values
        self.setData(value=self.df, role=DataChangeType.COLUMN_ADDED)

    def appendData(self, data: pd.DataFrame, b_block_signal: bool = False):
        if len(data.shape) == 1:
            data = data[np.newaxis]
        elif len(data.shape) != 2:
            raise AssertionError
        new_df = pd.DataFrame(index=pd.RangeIndex(len(self.df) + len(data)),
                              columns=self.df.columns)
        new_df[:len(self.df)] = self.df[:]
        new_df[len(self.df):] = data
        if b_block_signal is False:
            self.sigChanged.emit(self, DataChangeType.ROW_ADDED,
                                 len(new_df) - len(self.df))

    def as_array(self, value=None):
        if value is None:
            value = self.df
        value = value.values
        if ((len(self.validator.shape.prepared_args) == 1)
                and (value.shape[0] == 1)):
            value = value.flatten()
        return value

    @staticmethod
    def as_df(array):
        if isinstance(array, tuple,) or len(array.shape) == 1:
            return pd.Series(array)
            # array = array[np.newaxis]
        return pd.DataFrame(array)

    @property
    def column_names(self):
        return self._column_names

    @column_names.setter
    def column_names(self, value):
        self._column_names = value
        self.sigColumnNamesChanged.emit(self._column_names)

    @property
    def index_names(self):
        return self._index_names

    @index_names.setter
    def index_names(self, value):
        self._index_names = value
        self.sigIndexNamesChanged.emit(self._index_names)

    @property
    def df(self) -> pd.DataFrame | pd.Series:
        return self._df

    @df.setter
    def df(self, value: pd.DataFrame):
        type_assertion(value, (pd.DataFrame, pd.Series))
        self.validate(value)
        self._df = deepcopy(value)
        if self.column_names is not None:
            self._df.columns = self.column_names
        if self.index_names is not None:
            self._df.index = self.index_names

    def insertRecord(self, row, record):
        if isinstance(self.df, pd.DataFrame):
            new_df = pd.DataFrame(index=pd.RangeIndex(len(self.df) + 1),
                                  columns=self.df.columns)
            new_df[:row] = self.df[:row]
            new_df[row] = record
            if row != (len(self.df) + 1):
                new_df[row + 1:] = new_df[row:]
            self.df = new_df
            self.sigChanged.emit(self, DataChangeType.ROW_ADDED, row)
        else:
            raise NotImplementedError

    def onDataChanged(self, topLeft=None, bottomRight=None, roles=None):
        self.sigChanged.emit(self, DataChangeType.DATA_CHANGED,
                             (topLeft, bottomRight, roles))

    def setColumnValue(self, value, column):
        col_idx = self._df.columns.get_loc(column)
        self._df.iloc[:, col_idx] = value
        self.sigChanged.emit(
            self, DataChangeType.COLUMN_VALUE_UPDATED, (col_idx, value))

    def setData(self, index=None, value=None, role=DataChangeType.SET_DATA):
        if not isinstance(value, (pd.DataFrame, pd.Series)):
            value = self.as_df(value)
        if (self._df is None) or (value.shape != self.df.shape):
            self.df = value
        else:
            self.validate(value)
            self._df[:] = value
        if role != self.BLOCK_SIGNAL_ROLE:
            self.sigChanged.emit(self, role, None)

    def setRowValue(self, value, row):
        row_idx = self._df.index.get_loc(row)
        self._df.iloc[row_idx, :] = value
        self.sigChanged.emit(
            self, DataChangeType.INDEX_VALUE_UPDATED, (row_idx, value))

    def setValue(self, value: np.ndarray, b_block_signal: bool = False):
        self.setData(value=value,
                     role=self.BLOCK_SIGNAL_ROLE
                     if b_block_signal is True else
                     DataChangeType.SET_VALUE)
        return self.value()

    def update_from_item(
            self, item: QtWidgets.QTableWidgetItem | TableWidgetItem):
        if isinstance(item, QtWidgets.QTableWidgetItem):
            value = item.value
            rc = item.row(), item.column()
            if self.df.ndim == 2:
                old_value = self.df.iloc[*rc]
            else:
                if rc[1] != 0:
                    raise RuntimeError
                old_value = self.df.iloc[rc[0]]
            if old_value != value:
                if self.df.ndim == 2:
                    self.df.iloc[*rc] = value
                else:
                    self.df.iloc[rc[0]] = value
                self.sigChanged.emit(self, DataChangeType.CELL_UPDATED,
                                     (rc[0], rc[1], value))

        else:
            raise NotImplementedError(str(item))

    def validate(self, value):
        if self.validator is None:
            pass
        elif isinstance(self.validator, NumpyInterface):
            if isinstance(value, pd.DataFrame):
                value = self.as_array(value)
            self.validator.validate(value)
        else:
            raise NotImplementedError(f"type({type(self.validator)})")

    def validation_check(self, value):
        if self.validator is None:
            pass
        elif isinstance(self.validator, NumpyInterface):
            if isinstance(value, pd.DataFrame):
                value = self.as_array(value)
            TypedNumpyInterface.cls_b_is_valid(self.validator, value)
        else:
            raise NotImplementedError(f"type({type(self.validator)})")

    def value(self):
        if self.df is not None:
            return self.as_array(self.df)
