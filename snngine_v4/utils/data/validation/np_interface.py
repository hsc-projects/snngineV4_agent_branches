from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Type

import numpy as np
from numpydantic import NDArray
from numpydantic.interface import NumpyInterface
from numpydantic.interface.numpy import ENABLED, NumpyJsonDict
from numpydantic.types import DtypeType, NDArrayType, ShapeType
from pydantic import field_validator


NumpyInterface.enabled = lambda: False


class ExtendedNumpyJsonDict(NumpyJsonDict):
    """
    JSON-able roundtrip representation of numpy array
    """

    # noinspection PyNestedDecorators
    @field_validator('type', 'dtype', mode='before')
    @classmethod
    def validate_str(cls, v: str) -> str:
        if isinstance(v, np.str_):
            v = str(v)
        return v


@dataclass(frozen=True)
class TypedNumpyInterface(NumpyInterface):

    shape: ShapeType
    dtype: DtypeType
    # interface: NumpyInterface = field(init=False)
    array_type: Type[NDArrayType] | tuple[Type[NDArrayType]] = field(init=False)

    json_model = ExtendedNumpyJsonDict

    def array(self, *arg, **kwargs):
        res = np.array(*arg, dtype=self.dtype, **kwargs)
        self.validate(res)
        return res

    def b_is_valid(self, array: np.ndarray, array_type=None):
        return self.cls_b_is_valid(self, array, array_type=array_type)

    def b_is_valid_np(self, array: np.ndarray):
        return self.cls_b_is_valid(self, array, array_type=np.ndarray)

    @classmethod
    def check(cls, array: Any) -> bool:
        """
        Check that this is in fact a numpy ndarray or something that can be
        coerced to one
        """
        if array is None:
            return False

        if isinstance(array, np.ndarray):
            return True
        elif isinstance(array, dict):
            return ExtendedNumpyJsonDict.is_valid(array)
        else:
            try:
                _ = np.array(array)
                return True
            except Exception:
                return False

    @classmethod
    def cls_b_is_valid(
            cls, interface, array: np.ndarray, array_type=None):

        if (array_type is not None) and not isinstance(array, array_type):
            return False

        array = interface.before_validation(array)

        dtype = interface.get_dtype(array)
        dtype_valid = interface.validate_dtype(dtype)
        # array = self.after_validate_dtype(array)
        shape = interface.get_shape(array)
        shape_valid = interface.validate_shape(shape)
        # array = self.after_validation(array)
        return dtype_valid and shape_valid

    @classmethod
    def enabled(cls):
        return ENABLED

    def __post_init__(self):
        object.__setattr__(self, 'array_type', NDArray[
                self.shape, self.dtype])


TypedNumpyInterface.__name__ = NumpyInterface.__name__

