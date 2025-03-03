from __future__ import annotations

from pydantic import BeforeValidator, Field
from typing import Annotated, ClassVar

import numpy as np

from snngine_v4.utils.data_utils.validation.array_annotation import (
    ArrayInterfaces, i32_2D, i64_2D, f32_2D, Bool2D, i32_3D, f32_3D
)
from snngine_v4.utils.settings.config_model import ConfigModel


class FrameVector(ConfigModel):
    name: str
    default_scalar: int | float = 0
    # dtype: str = 'NONE'

    @staticmethod
    def validate_field(v):
        if isinstance(v, str):
            v = FrameVector(name=v)
        return v


FrameVectorType = Annotated[FrameVector,
                            BeforeValidator(FrameVector.validate_field)]


class DataFrameIndex(ConfigModel):

    def __len__(self):
        return len(self.model_keys())

    def to_list(self):
        return [getattr(self, k).name for k in self.model_keys()]


class TypedDataFrameBase(ConfigModel):

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

    # @classmethod
    # def _validate_model_after(cls, data: TypedDataFrameBase):
    #     super()._validate_model_after(data=data)
    def model_post_init(self, __context):
        super().model_post_init(__context)
        data = self
        if data.data.shape[1] == 0:
            if data.data.shape[0] != 1:
                raise NotImplementedError
            data.data = self.cls_zeroes(model=data)
        # return data

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

