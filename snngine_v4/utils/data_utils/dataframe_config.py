from __future__ import annotations

import pandas as pd
from pydantic import Field
from typing import Any, ClassVar

import numpy as np

from snngine_v4.utils.data_utils.index_config import IndexConfig, RowOrColumn
from snngine_v4.utils.data_utils.validation.array_annotation import (
    ArrayInterfaces, Bool2D,
    i32_1D, i32_2D, i32_3D,
    i64_1D, i64_2D,
    f32_1D, f32_2D, f32_3D,
)
from snngine_v4.utils.field_utils import Undefined
from snngine_v4.utils.settings.config_model import ConfigModel


class SeriesModel(ConfigModel):

    class Slots:
        INDEX: ClassVar[str] = "index"
        DATA: ClassVar[str] = "data"
        INIT_LENGTH: ClassVar[str] = "init_length"

        SHAPE: ClassVar[str] = "shape"
        D_TYPE: ClassVar[str] = "dtype"

    index: IndexConfig | i64_1D | None = Field(default=None, repr=False)
    # index: IndexConfig = Field(default=None, repr=False)

    init_length: ClassVar[int] = 1
    data: i64_1D = Field(repr=False)
    b_nullable: bool = Field(default=False, repr=False, frozen=True)

    @classmethod
    def _apply_index_value(cls, data, i, value, dim):
        if isinstance(data, (pd.Series, pd.DataFrame)):
            data = data.values
        if dim <= 0:
            data[i] = value
        elif dim == 1:
            data[:, i] = value
        elif dim == 2:
            data[:, :, i] = value
        elif isinstance(i, tuple):
            raise NotImplementedError
        else:
            raise ValueError("dim must be <= 2")

    def apply_property(
            self, data=None, idx_attr=RowOrColumn.Slots.SCALAR_VALUE,
            dim=0, b_skip_na=True, index=None):
        if index is None:
            index = self.index
        if isinstance(index, IndexConfig):
            if data is None:
                data = self.data
            for i, k in enumerate(index.model_keys()):
                value = getattr(getattr(index, k), idx_attr)
                if (not b_skip_na) or pd.notna(value):
                    self._apply_index_value(data, i, value, dim=dim)

    def apply_index_init_values(self, data=None, b_skip_na=True, **kwargs):
        self.apply_property(
            data=data, b_skip_na=b_skip_na,
            idx_attr=RowOrColumn.Slots.INIT_SCALAR_VALUE, **kwargs)

    def as_tuple(self):
        return tuple(self.data)

    @classmethod
    def cls_n_indices(cls, model: SeriesModel):
        if model.index is not None:
            n_indices = len(model.index)
        else:
            n_indices = model.init_length
        return n_indices

    @classmethod
    def cls_zeroes(cls, model: SeriesModel, n_indices=None, **kwargs):
        if n_indices is None:
            n_indices = cls.cls_n_indices(model)
        return np.zeros(n_indices, dtype=model.data.dtype, **kwargs)

    @classmethod
    def cls_validate_data(cls, model, data, **kwargs):
        raise NotImplementedError

    @classmethod
    def from_tuple(cls, value, **kwargs):
        new = cls(**kwargs)
        new.data = np.array(value, dtype=new.data.dtype)
        return new

    def __len__(self):
        if self.index is None:
            return self.data.shape[0]
        return len(self.index)

    def _model_post_init(self, __context):
        if self.data.shape[0] == 0:
            self.data = self.zeroes()
        if self.index is not None:
            if len(self.index) != self.data.shape[0]:
                raise ValueError("len(self.index) != self.data.shape[0]")

    def model_post_init(self, __context):
        super().model_post_init(__context)
        self._model_post_init(__context)

    def prod(self):
        return self.data.cumprod()[-1]

    def validate_data(self, data, **kwargs):
        return self.cls_validate_data(model=self, data=data, **kwargs)

    def zeroes(self, n_indices=None, **kwargs):
        return self.cls_zeroes(model=self, n_indices=n_indices, **kwargs)

    @classmethod
    def _validate_model_before(
            cls, data: Any) -> Any:
        if isinstance(data, (np.ndarray,)):
            data = {cls.Slots.DATA: data}
        elif isinstance(data, pd.Series):
            data = {cls.Slots.DATA: data.values,
                    cls.Slots.INDEX: list(data.index)}
        res = super()._validate_model_before(data=data)
        return res


class SeriesI32(SeriesModel):
    data: i32_1D = Field(
        default_factory=lambda: np.array([], dtype=np.int32),
        repr=True)


class SeriesF32(SeriesModel):
    data: f32_1D = Field(
        default_factory=lambda: np.array([], dtype=np.float32),
        repr=True)


class TypedDataFrameModel(SeriesModel):
    class Slots(SeriesModel.Slots):
        COLUMNS: ClassVar[str] = "columns"

    index: list[str] | None = Field(default=None, repr=False)
    columns: list[str] | None = Field(default=None, repr=False)
    data: i64_2D = Field(repr=False)

    @classmethod
    def _apply_column_value(cls, data, i, value):
        data.iloc[:, i] = value

    def apply_column_property(
            self, data=None, idx_attr=RowOrColumn.Slots.SCALAR_VALUE,
            index=None, dim=1, **kwargs):
        self.apply_property(data=data, idx_attr=idx_attr, dim=dim,
                            index=index, **kwargs)

    @classmethod
    def cls_shape(cls, model: TypedDataFrameModel, n_indices=None, n_cols=None):
        if n_cols is None:
            if model.columns is not None:
                n_cols = len(model.columns)
            else:
                n_cols = model.init_length
        if n_indices is None:
            n_indices = cls.cls_n_indices(model=model)
        if n_cols is Undefined:
            return n_indices
        return n_indices, n_cols

    @classmethod
    def cls_zeroes(cls, model: TypedDataFrameModel,
                   n_indices=None, n_cols=None, **kwargs):
        shape = cls.cls_shape(model=model, n_indices=n_indices, n_cols=n_cols)
        return np.zeros(shape, dtype=model.data.dtype, **kwargs)

    @classmethod
    def from_tuple(cls, value):
        raise NotImplementedError

    def _model_post_init(self, __context):
        if self.data.shape[1] == 0:
            if self.data.shape[0] != 1:
                raise NotImplementedError
            self.data = self.zeroes()

    def zeroes(self, n_indices=None, n_cols=None, **kwargs):
        return self.cls_zeroes(
            model=self, n_indices=n_indices, n_cols=n_cols, **kwargs)


class DataFrameI32(TypedDataFrameModel):
    data: i32_2D = Field(
        default_factory=lambda: np.array([[]], dtype=np.int32),
        repr=False)


class DataFrameF32(TypedDataFrameModel):
    data: f32_2D = Field(
        default_factory=lambda: np.array([[]], dtype=np.float32),
        repr=False)


class DataFrameBool(TypedDataFrameModel):
    data: Bool2D = Field(
        default_factory=lambda: np.array([[]], dtype=np.bool),
        repr=False)


class TypedDataFrameBase3D(TypedDataFrameModel):
    index: IndexConfig

    @classmethod
    def cls_shape(
            cls, model: TypedDataFrameBase3D, n_indices=None, n_cols=None):
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
        return ArrayInterfaces().make_type(
            '* x', '* y', dtype=self.data.dtype)

    @classmethod
    def _validate_model_before(
            cls, data: Any) -> Any:
        if isinstance(data, dict):
            pass
        res = super()._validate_model_before(data=data)
        return res


class DataFrameI32D3(TypedDataFrameBase3D):
    data: i32_3D = Field(
        default_factory=lambda: np.array([[[]]], dtype=np.int32),
        repr=False)


class DataFrameF32D3(TypedDataFrameBase3D):
    data: f32_3D = Field(
        default_factory=lambda: np.array([[[]]], dtype=np.float32),
        repr=False)

