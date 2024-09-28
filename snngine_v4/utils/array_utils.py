from __future__ import annotations

from dataclasses import dataclass, field
from types import UnionType
from typing import Annotated, Any, ClassVar, get_args, Type

import annotated_types
import numpy as np
from numpydantic import NDArray, Shape
from numpydantic.exceptions import ShapeError, DtypeError
from numpydantic.interface import NumpyInterface
# noinspection PyUnresolvedReferences
from numpydantic.ndarray import NDArrayMeta
from numpydantic.types import DtypeType, NDArrayType, ShapeType
from pydantic import BeforeValidator
from pydantic.fields import FieldInfo

from snngine_v4.utils.containers.mappings import (
    Int2ObjectMapConfig,
    Object2ObjectMap,
)
from snngine_v4.utils.core_utils import Singleton
from snngine_v4.utils.field_utils import AnnotationType, extract_annotation


class ArrayInterfaceMap(Object2ObjectMap):

    class ContainerConfigClass(Int2ObjectMapConfig, frozen=True,
                               arbitrary_types_allowed=True):
        allowed_types: Type[NDArrayMeta]

    class InvertedConfigClass(Int2ObjectMapConfig, frozen=True):
        allowed_types: Type[NumpyInterface]


@dataclass(frozen=True)
class ArrayInterfacePair:

    dtype: DtypeType
    shape: ShapeType

    interface: NumpyInterface = field(init=False)
    type: Type[NDArrayType] = field(init=False)

    def check_array(self, v: np.ndarray):
        return (self.interface.validate_dtype(v.dtype)
                and self.interface.validate_shape(v.shape))

    def __post_init__(self):

        object.__setattr__(self, 'interface', NumpyInterface(
                dtype=self.dtype, shape=self.shape))
        object.__setattr__(self, 'type', NDArray[
                self.shape, self.dtype])

        object.__setattr__(
            self, 'dtype', property(self.interface.dtype).fget)
        object.__setattr__(
            self, 'shape', property(self.interface.shape).fget)


class ArrayInterfaces(metaclass=Singleton):

    def __init__(self):
        super().__init__()
        self.interface_map = ArrayInterfaceMap()
        self.F32_D2 = ArrayInterfacePair(
            dtype=np.float32, shape=Shape['* x, * y'])

        self.rgb_a_f32 = ArrayInterfacePair(
            dtype=np.float32, shape=Shape['3-4'])
        self.rgb_u8 = ArrayInterfacePair(
            dtype=np.uint8, shape=Shape['3'])

    def __setattr__(self, name: str, value: Any) -> None:

        if isinstance(value, ArrayInterfacePair):
            self.interface_map[value.interface] = value.type
        if hasattr(self, name):
            raise AttributeError(f"{name} has already been set")
        super().__setattr__(name, value)


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
    def __new__(mcs, clsname, bases, dct, dtype=None, coerced=None):
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
        new = super().__new__(mcs, clsname, bases, dct)
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
class Int32Validator(DTypeBeforeValidator, dtype=np.int32):
    """"""


@dataclass(frozen=True)
class Float32Validator(DTypeBeforeValidator,
                       dtype=np.float32, coerced=(int, float)):
    """"""


Float32 = Annotated[float, Float32Validator()]


def int_annotation(dtype):
    return Annotated[int, DTypeBeforeValidator(dtype=dtype),
                    annotated_types.Ge(ValidateDType.min_max[dtype][0]),
                    annotated_types.Le(ValidateDType.min_max[dtype][1])]


Int8 = int_annotation(np.int8)
Int32 = int_annotation(np.int32)
UInt8 = int_annotation(np.uint8)


def b_is_array_annotation(ann: AnnotationType):
    if isinstance(ann, FieldInfo):
        ann = ann.annotation

    if isinstance(ann, NDArrayMeta):
        return True

    try:
        res = ann.__value__(0)
    except (ShapeError, DtypeError):
        return True
    except (AttributeError, TypeError):
        return False
    if isinstance(res, np.ndarray):
        return True
    raise TypeError(f"{res} is not a numpy array")


def b_includes_array_annotation(ann: AnnotationType):
    try:
        ann = extract_annotation(ann)
    except (AttributeError, TypeError):
        pass
    if isinstance(ann, UnionType):
        args = get_args(ann)
        for a in args:
            if b_is_array_annotation(a):
                return True
    else:
        return b_is_array_annotation(ann)


def convert_type_alias_type(ann: AnnotationType):
    if b_is_array_annotation(ann):
        return ann
    else:
        return ann.__value__
