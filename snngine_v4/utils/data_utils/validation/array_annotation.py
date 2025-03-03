from __future__ import annotations

from types import UnionType
from typing import Any, get_args, get_origin, Type, Union

import numpy as np
from numpydantic import Shape
from numpydantic.exceptions import DtypeError, ShapeError

# noinspection PyUnresolvedReferences
from numpydantic.ndarray import NDArray, NDArrayMeta
from numpydantic.interface import NumpyInterface
from pydantic import BaseModel

# noinspection PyProtectedMember
from pydantic.fields import FieldInfo
from typing_extensions import TypeAliasType

from snngine_v4.utils.containers.mappings import (
    Int2ObjectMapConfig,
    Object2ObjectMap,
)
from snngine_v4.utils.core_utils import Singleton
from snngine_v4.utils.data_utils.validation.np_interface import (
    ExtendedNumpyJsonDict,
    TypedNumpyInterface,
)
from snngine_v4.utils.field_utils import (
    AnnotationType, as_annotation,
    fill_field_default,
)


class ArrayDtype2ObjectMap(Object2ObjectMap):

    class ContainerConfigClass(Int2ObjectMapConfig, frozen=True,
                               arbitrary_types_allowed=True):
        allowed_types: Type[NDArrayMeta]
        b_get_inv_allowed: bool = True


class ArrayDtype2InterfaceMap(ArrayDtype2ObjectMap):
    class InvertedConfigClass(Int2ObjectMapConfig, frozen=True):
        allowed_types: Type[NumpyInterface]


class ArrayDtype2PairMap(ArrayDtype2ObjectMap):
    class InvertedConfigClass(Int2ObjectMapConfig, frozen=True):
        allowed_types: Type[TypedNumpyInterface]


class ArrayInterfaces(metaclass=Singleton):

    def __init__(self):
        super().__init__()

        self.dtype_interface_map = ArrayDtype2InterfaceMap()
        self.dtype_pair_map = ArrayDtype2PairMap()

        self.D2 = TypedNumpyInterface(
            dtype=Any, shape=Shape['* x, * y'])

        self.D2_i32 = TypedNumpyInterface(
            dtype=np.int32, shape=Shape['* x, * y'])
        self.D2_f32 = TypedNumpyInterface(
            dtype=np.float32, shape=Shape['* x, * y'])

        self.rgb_a_f32 = TypedNumpyInterface(
            dtype=np.float32, shape=Shape['3-4'])
        self.ibo3 = TypedNumpyInterface(
            dtype=np.int32, shape=Shape['* x, 3'])
        self.vbo3 = TypedNumpyInterface(
            dtype=np.float32, shape=Shape['* x, 3'])
        self.vbo4 = TypedNumpyInterface(
            dtype=np.float32, shape=Shape['* x, 4'])

        self.rgb_u8 = TypedNumpyInterface(
            dtype=np.uint8, shape=Shape['3'])

    def __getitem__(self, item) -> NumpyInterface | NDArrayMeta:
        if isinstance(item, TypeAliasType):
            item = item.__value__
        return self.dtype_interface_map[item]

    def __setattr__(self, name: str, value: Any) -> None:

        if isinstance(value, TypedNumpyInterface):
            self.dtype_interface_map[value] = value.array_type
        if hasattr(self, name):
            raise AttributeError(f"{name} has already been set")
        super().__setattr__(name, value)

    def vbo_array_interface(self, y):
        return self[self.vbo_array_type(y)]

    def vbo_array_type(self, y):
        return self.array_2d_type(x='* x', y=y, dtype=np.float32)

    def ibo_array_type(self, y):
        return self.array_2d_type(x='* x', y=y, dtype=np.int32)

    def array_2d_type(self, x, y, dtype):
        shape = Shape[f'{x}, {y}']
        dt = NDArray[shape, dtype]
        if dt not in self.dtype_interface_map.values():
            v = TypedNumpyInterface(dtype=dtype, shape=shape,)
            self.dtype_interface_map[v] = v.array_type
        return dt

    def array_3d_type(self, x, y, z, dtype):
        shape = Shape[f'{x}, {y}, {z}']
        dt = NDArray[shape, dtype]
        if dt not in self.dtype_interface_map.values():
            v = TypedNumpyInterface(dtype=dtype, shape=shape,)
            self.dtype_interface_map[v] = v.array_type
        return dt


def b_includes_array_annotation(ann: AnnotationType):
    try:
        ann = as_annotation(ann)
    except (AttributeError, TypeError):
        pass
    if isinstance(ann, UnionType) or get_origin(ann) == Union:
        args = get_args(ann)
        for a in args:
            if b_is_array_annotation(a):
                return True
    else:
        return b_is_array_annotation(ann)


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


def fill_array_field_default(
        dct, model: Type[BaseModel] | BaseModel, key, **kwargs):
    fill_field_default(dct, model, key, **kwargs)
    if isinstance(dct[key], dict):
        dct[key] = ExtendedNumpyJsonDict.handle_input(dct[key])
    return dct[key]


type Bool2D = ArrayInterfaces().array_2d_type('* x', '* y', np.bool)
type i32_2D = ArrayInterfaces().array_2d_type('* x', '* y', np.int32)
type i32_3D = ArrayInterfaces().array_3d_type(
    '* x', '* y', '* z', np.int32)
type u32_2D = ArrayInterfaces().array_2d_type('* x', '* y', np.uint32)
type i64_2D = ArrayInterfaces().array_2d_type('* x', '* y', np.int64)
type f32_2D = ArrayInterfaces().array_2d_type('* x', '* y', np.float32)
type f32_3D = ArrayInterfaces().array_3d_type(
    '* x', '* y', '* z', np.float32)