from __future__ import annotations

from typing import ClassVar

from pydantic import Field, model_validator

from snngine_v4.utils.data_utils.validation.dtype_annotation import Float32
from snngine_v4.utils.settings.config_model import ConfigModel


type InconsistentType = str


class RowOrColumn(ConfigModel):

    class Slots:
        NAME: ClassVar[str] = "name"
        SCALAR_VALUE: ClassVar[str] = "scalar_value"
        INIT_SCALAR_VALUE: ClassVar[str] = "init_scalar_value"

    name: str = Field(default='', repr=False)
    init_scalar_value: int | float | None = Field(
        default=None, repr=False)
    scalar_value: int | float | InconsistentType | None = Field(
        default=None, repr=False)
    # dtype: str = 'NONE'

    @model_validator(mode='before')
    def validate_model(cls, v):
        if isinstance(v, str):
            v = {cls.Slots.NAME: v}
        elif isinstance(v, int | float):
            v = {cls.Slots.INIT_SCALAR_VALUE: v}
        return v


class Column(RowOrColumn):
    pass


class Row(RowOrColumn):
    pass


class RowF32(RowOrColumn):
    init_scalar_value: Float32 | None = Field(default=0, repr=False)
    scalar_value: Float32 | None = Field(default=0, repr=False)


class IndexConfig(ConfigModel):

    def __len__(self):
        return len(self.model_keys())

    def to_list(self):
        return [getattr(self, k).name for k in self.model_keys()]

    def model_post_init(self, __context):
        super().model_post_init(__context)
        for k in self.model_keys():
            vec_def = getattr(self, k)
            if isinstance(vec_def, RowOrColumn) and (vec_def.name == ''):
                vec_def.name = k
