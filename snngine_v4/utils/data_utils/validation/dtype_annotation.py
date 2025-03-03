from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, ClassVar, Type

import annotated_types
import numpy as np
# noinspection PyUnresolvedReferences
from numpydantic.ndarray import NDArrayMeta
from pydantic import BeforeValidator


@dataclass(frozen=True)
class ValidateDType:

    dtype: Type
    coerced: Type | tuple[Type, ...] | None = None

    min_max: ClassVar[dict] = {}

    def __post_init__(self):
        if self.dtype is None:
            raise TypeError(self.dtype)
        if (np.issubdtype(self.dtype, np.integer)
                and (self.dtype not in self.min_max)):
            self.min_max[self.dtype] = (np.iinfo(self.dtype).min,
                                        np.iinfo(self.dtype).max)

    def __call__(self, x):

        if self.coerced and isinstance(x, self.coerced):
            x = self.dtype(x)
        b_is_int = (np.issubdtype(type(x), np.integer)
                    and np.issubdtype(self.dtype, np.integer))
        if b_is_int:
            min_max = self.min_max[self.dtype]
            if not min_max[0] <= x <= min_max[1]:
                raise ValueError(f"{x} is not in {min_max} ({self.dtype})")
            x = int(x)
        elif not np.issubdtype(type(x), self.dtype):
            raise TypeError(f"{type(x)} is not a {self.dtype}")
        return x


class DTypeBeforeValidatorMetaclass(type):
    def __new__(mcs, cls_name, bases, dct, dtype=None, coerced=None):
        # kwargs = {
        #     'func': ValidateDType(dtype=np.int32)
        # }
        if '__annotations__' not in dct:
            dct['__annotations__'] = {}
        if 'func' not in dct['__annotations__']:
            dct['__annotations__']['func'] = 'Any'
        if dtype is not None:
            dct['func'] = ValidateDType(dtype=dtype, coerced=coerced)
            dct['dtype'] = dtype
            dct['coerced'] = coerced
        new = super().__new__(mcs, cls_name, bases, dct)
        # new.func = func
        return new


@dataclass(frozen=True)
class DTypeBeforeValidator(BeforeValidator,
                           metaclass=DTypeBeforeValidatorMetaclass):
    func: Any = None
    dtype: Any = None
    coerced: Any = None

    def __post_init__(self):

        if self.func is None:
            object.__setattr__(self, "func",
                               ValidateDType(dtype=self.dtype,
                                             coerced=self.coerced))

        object.__setattr__(
            self, 'dtype', property(self.func.dtype).fget)
        object.__setattr__(
            self, 'coerced', property(self.func.coerced).fget)
        dtype = self.dtype
        if dtype is None:
            pass
        else:
            pass


@dataclass(frozen=True)
class Float32Validator(DTypeBeforeValidator,
                       dtype=np.float32, coerced=(int, float)):
    """"""


Float32 = Annotated[float, Float32Validator()]


def int_annotation(dtype):
    return Annotated[
        int, DTypeBeforeValidator(dtype=dtype),
        annotated_types.Ge(ValidateDType.min_max[dtype][0]),
        annotated_types.Le(ValidateDType.min_max[dtype][1])]


Int8 = int_annotation(np.int8)
Int32 = int_annotation(np.int32)
UInt8 = int_annotation(np.uint8)
UInt64 = int_annotation(np.uint64)
