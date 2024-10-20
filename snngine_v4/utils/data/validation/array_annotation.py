from __future__ import annotations

from types import UnionType
from typing import Any, get_args, get_origin, Type, Union

import numpy as np
from numpydantic import Shape
from numpydantic.exceptions import DtypeError, ShapeError

# noinspection PyUnresolvedReferences
from numpydantic.ndarray import NDArrayMeta
from numpydantic.interface import NumpyInterface

# noinspection PyProtectedMember
from pydantic.fields import FieldInfo
from typing_extensions import TypeAliasType

from snngine_v4.utils.containers.mappings import (
    Int2ObjectMapConfig,
    Object2ObjectMap,
)
from snngine_v4.utils.core_utils import Singleton
from snngine_v4.utils.data.validation.np_interface import TypedNumpyInterface
from snngine_v4.utils.field_utils import AnnotationType, extract_annotation


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


def b_includes_array_annotation(ann: AnnotationType):
    try:
        ann = extract_annotation(ann)
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
