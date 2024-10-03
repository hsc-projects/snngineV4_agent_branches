from copy import deepcopy
from typing import ClassVar

import numpy as np
import pandas as pd
from numpydantic.interface import NumpyInterface
from pydantic_core import PydanticUndefined
# noinspection PyProtectedMember
from pyqtgraph.widgets.TableWidget import TableWidgetItem
from qtpy import QtCore, QtSql, QtWidgets

from snngine_v4.data.validation.array_annotation import TypedNumpyInterface


# noinspection PyPep8Naming
class QDataFrame(QtSql.QSqlTableModel):

    sigChanged = QtCore.Signal(object)

    BLOCK_SIGNAL_ROLE: ClassVar[int] = -1

    def __init__(self, validator, value, default_value=PydanticUndefined,
                 parent=None):

        super().__init__(parent)

        self.validator = validator
        if default_value == PydanticUndefined:
            default_value = self.validator.dtype(0)
        self.default_value = default_value
        self.dataChanged.connect(self.emitSigChanged)
        self._df = None

        self.setValue(value)

    def addRow(self, vals=PydanticUndefined):
        if vals == PydanticUndefined:
            vals = self.default_value
        new_df = pd.DataFrame(
            dtype=self.validator.dtype,
            columns=self.df.columns,
            index=pd.RangeIndex(len(self.df) + 1))
        new_df.loc[: len(self.df.index)] = self.df
        new_df.loc[len(self.df.index), :] = vals
        self.setData(value=new_df)

    def addColumn(self, vals=PydanticUndefined, dtype=None):
        if vals == PydanticUndefined:
            vals = self.default_value

        if (dtype is None) and isinstance(self.validator, NumpyInterface):
            dtype = self.validator.dtype
            vals = dtype(vals)
        new_col = len(self.df.columns)
        if new_col in self.df.columns:
            init_new_col = new_col
            i = 2
            while new_col in self.df.columns:
                new_col = f"f{init_new_col} ({i})"
        new_df = deepcopy(self.df)
        new_df[new_col] = vals
        self.setData(value=new_df)

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
            self.sigChanged.emit(self)

    def emitSigChanged(self, *args, **kwargs):
        self.sigChanged.emit(self)

    def insertRecord(self, row, record):
        new_df = pd.DataFrame(index=pd.RangeIndex(len(self.df) + 1),
                              columns=self.df.columns)
        new_df[:row] = self.df[:row]
        new_df[row] = record
        if row != (len(self.df) + 1):
            new_df[row + 1:] = new_df[row:]
        self.df = new_df
        self.sigChanged.emit(self)

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
        if len(array.shape) == 1:
            array = array[np.newaxis]
        return pd.DataFrame(array)

    @property
    def df(self):
        return self._df

    @df.setter
    def df(self, value: pd.DataFrame):
        if not isinstance(value, pd.DataFrame):
            raise TypeError(type(value))
        self.validate(value)
        self._df = deepcopy(value)

    def setData(self, index=None, value=None, role=None):
        if not isinstance(value, pd.DataFrame):
            value = self.as_df(value)
        if (self.df is None) or (value.shape != self.df.shape):
            self.df = value
        else:
            self.validate(value)
            self.df[:] = value
        if role != self.BLOCK_SIGNAL_ROLE:
            self.sigChanged.emit(self)

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

    def setValue(self, value: np.ndarray, b_block_signal: bool = False):
        self.setData(value=value,
                     role=self.BLOCK_SIGNAL_ROLE
                     if b_block_signal is True else None)
        return self.value()

    def update(self, item: QtWidgets.QTableWidgetItem | TableWidgetItem):
        if isinstance(item, QtWidgets.QTableWidgetItem):
            value = item.value
            rc = item.row(), item.column()
            old_value = self.df.iloc[*rc]
            if old_value != value:
                self.df.iloc[*rc] = value
                self.sigChanged.emit(self)

        else:
            raise NotImplementedError(str(item))

    def value(self):
        if self.df is not None:
            return self.as_array(self.df)
