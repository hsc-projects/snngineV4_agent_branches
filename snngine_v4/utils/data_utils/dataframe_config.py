from __future__ import annotations

from pydantic import Field
from typing import ClassVar

import numpy as np

from snngine_v4.utils.data_utils.validation.array_annotation import (
    ArrayInterfaces, i32_2D, i64_2D, f32_2D, Bool2D, i32_3D, f32_3D
)
from snngine_v4.utils.field_utils import model_keys
from snngine_v4.utils.settings.settings_keywords import BaseModelSlots
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


class DataFrameIndex(XMLSettingsModel):

    def __len__(self):
        return len(model_keys(self, exclude=BaseModelSlots.CLASS__NAME))

    def to_list(self):
        return [getattr(self, k) for k in model_keys(
            self, exclude=BaseModelSlots.CLASS__NAME)]

    @classmethod
    def _validate_model_after(
            cls, data: DataFrameIndex) -> DataFrameIndex:
        data = super()._validate_model_after(data=data)
        cols = data.to_list()
        for col in cols:
            if not isinstance(col, str):
                raise TypeError(f"Column {col} is not a string")
        return data


class TypedDataFrameBase(XMLSettingsModel):

    class Slots:
        COLUMNS: ClassVar[str] = "columns"
        DATA: ClassVar[str] = "data"

        INIT_LENGTH: ClassVar[str] = "init_length"
        D_TYPE: ClassVar[str] = "dtype"

    index: list[str] | None = None
    columns: list[str] | None = None
    init_length: ClassVar[int] = 1
    data: i64_2D = Field(repr=False)

    @classmethod
    def cls_shape(cls, model: TypedDataFrameBase, n_indices=None, n_cols=None):
        if n_cols is None:
            if model.columns is not None:
                n_cols = len(model.columns)
            else:
                n_cols = model.init_length
        if n_indices is None:
            if model.index is not None:
                n_indices = len(model.index)
            else:
                n_indices = model.init_length
        return n_indices, n_cols

    @classmethod
    def cls_zeroes(cls, model: TypedDataFrameBase,
                   n_indices=None, n_cols=None):
        shape = cls.cls_shape(model=model, n_indices=n_indices, n_cols=n_cols)
        return np.zeros(shape, dtype=model.data.dtype)

    @classmethod
    def cls_validate_data(cls, model, data, **kwargs):
        raise NotImplementedError

    def validate_data(self, data, **kwargs):
        return self.cls_validate_data(model=self, data=data, **kwargs)

    @classmethod
    def _validate_model_after(cls, data: TypedDataFrameBase):
        super()._validate_model_after(data=data)
        if data.data.shape[1] == 0:
            if data.data.shape[0] != 1:
                raise NotImplementedError
            data.data = cls.cls_zeroes(model=data)
        return data

    def zeroes(self, n_indices=None, n_cols=None):
        return self.cls_zeroes(model=self, n_indices=n_indices, n_cols=n_cols)


class DataFrameI32(TypedDataFrameBase):
    data: i32_2D = Field(
        default_factory=lambda: np.array([[]], dtype=np.int32),
        repr=False)


class DataFrameF32(TypedDataFrameBase):
    data: f32_2D = Field(
        default_factory=lambda: np.array([[]], dtype=np.float32),
        repr=False)


class DataFrameBool(TypedDataFrameBase):
    data: Bool2D = Field(
        default_factory=lambda: np.array([[]], dtype=np.bool),
        repr=False)


class TypedDataFrameBase3D(TypedDataFrameBase):
    index: DataFrameIndex

    @classmethod
    def cls_shape(cls, model: TypedDataFrameBase3D,
                  n_indices=None, n_cols=None):
        shape_2d = super().cls_shape(
            model=model, n_indices=n_indices, n_cols=n_cols)
        return shape_2d[0], shape_2d[1], shape_2d[1]

    def __getitem__(self, item):
        if not isinstance(item, int):
            item = self.index.to_list().index(item)
        return self.data[item]

    def items(self):
        res = []
        for i, idx_name in enumerate(self.index.to_list()):
            res.append((idx_name, self.data[i]))
        return res

    def item_validation_interface(self):
        return ArrayInterfaces().array_2d_type(
            '* x', '* y', dtype=self.data.dtype)


class DataFrameI32D3(TypedDataFrameBase3D):
    data: i32_3D = Field(
        default_factory=lambda: np.array([[[]]], dtype=np.int32),
        repr=False)


class DataFrameF32D3(TypedDataFrameBase3D):
    data: f32_3D = Field(
        default_factory=lambda: np.array([[[]]], dtype=np.float32),
        repr=False)

