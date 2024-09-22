from enum import Enum, IntEnum
from types import GenericAlias, UnionType
from typing import (
    Any, ClassVar, get_args, get_origin, Literal, Type,
    Union,
)

import numpy as np
import pandas as pd
from annotated_types import Ge, Gt, Le, Lt
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined
from typing_extensions import TypeAliasType

from .core_utils import type_assertion
from .interval_utils import make_interval


type AnnotationType = (FieldInfo | GenericAlias | UnionType
                       | Type | TypeAliasType)


def b_annotation_includes_basemodel(ann: AnnotationType) -> bool:
    return b_annotation_includes_type(ann=ann, type_=BaseModel)


def b_is_enum_annotation(ann: AnnotationType, b_strict: bool) -> bool:
    return b_annotation_includes_type(ann, Enum, b_strict=b_strict)


def b_is_int_annotation(ann: AnnotationType, b_strict: bool) -> bool:
    return b_annotation_includes_type(ann, int, b_strict=b_strict)


def b_is_intenum_annotation(ann: AnnotationType, b_strict: bool) -> bool:
    return b_annotation_includes_type(ann, IntEnum, b_strict=b_strict)


def b_is_literal_annotation(ann: AnnotationType, b_strict: bool):
    ann = extract_annotation(ann=ann)
    b_literal = get_origin(ann) == Literal
    if (b_strict is True) or (b_literal is True):
        return b_literal
    args = get_args(ann)
    if len(args) == 0:
        return False
    for arg in args:
        if b_is_literal_annotation(arg, False):
            return True
    return False


def b_annotation_includes_instance(
        ann: AnnotationType, type_: Type, b_strict=False) -> bool:

    ann = extract_annotation(ann=ann)

    if isinstance(ann, GenericAlias):
        ann = get_origin(ann)

    if b_strict and isinstance(ann, UnionType):
        return False

    if isinstance(ann, UnionType):
        res = any([b_annotation_includes_instance(x, type_)
                   for x in get_args(ann)])
        return res
    try:
        # noinspection PyTypeChecker
        return isinstance(ann, type_)
    except TypeError:
        pass
    return False


def b_annotation_includes_type(ann: AnnotationType, type_: Type,
                               b_strict=False) -> bool:

    ann = extract_annotation(ann=ann)

    if isinstance(ann, GenericAlias):
        ann = get_origin(ann)

    if b_strict and isinstance(ann, UnionType):
        return False

    if isinstance(ann, UnionType):
        res = any([b_annotation_includes_type(x, type_)
                   for x in get_args(ann)])
        return res
    try:
        # noinspection PyTypeChecker
        return issubclass(ann, type_)
    except TypeError:
        pass
    return False


def b_is_float_annotation(ann: AnnotationType, b_strict: bool) -> bool:
    return b_annotation_includes_type(ann, float, b_strict=b_strict)


def b_is_str_annotation(ann: AnnotationType, b_strict: bool) -> bool:
    return b_annotation_includes_type(ann, float, b_strict=b_strict)


def b_field_has_default(field_info: FieldInfo) -> bool:
    b_as_default = field_info.default != PydanticUndefined
    if not b_as_default:
        return field_info.default_factory is not None
    return True


def extract_annotation(ann: AnnotationType):
    if isinstance(ann, FieldInfo):
        ann = ann.annotation
    if isinstance(ann, TypeAliasType):
        ann = ann.__value__
    return ann


def extract_basemodel_from_annotation(ann: UnionType | Type,
                                      b_raise: bool = True):
    if isinstance(ann, UnionType):
        return extract_basemodel_from_union(ann, b_raise=b_raise)
    if b_annotation_includes_basemodel(ann):
        return ann
    if b_raise:
        raise ValueError("No BaseModel found")


def extract_basemodel_from_union(ann: UnionType, b_raise: bool = True):
    type_assertion(ann, UnionType)
    for x in get_args(ann):
        if b_annotation_includes_basemodel(x):
            return x
    if b_raise:
        raise ValueError('No BaseModel found')


def extract_field_interval(field_: FieldInfo, default='inf'):
    if len(field_.metadata) == 0:
        return pd.Interval(-np.inf, np.inf) if (default == 'inf') else default
    metadata_types = [type(x) for x in field_.metadata]

    ge = None
    gt = None
    le = None
    lt = None

    for i, metadata_type in enumerate(metadata_types):
        if metadata_type == Gt:
            gt = field_.metadata[i].gt
        elif metadata_type == Ge:
            ge = field_.metadata[i].ge
        elif metadata_type == Lt:
            lt = field_.metadata[i].lt
        elif metadata_type == Le:
            le = field_.metadata[i].le

    interval = make_interval(ge=ge, gt=gt, lt=lt, le=le)
    return interval


def extract_field_values_by_type(model: BaseModel, type_: Type):
    res = {}
    keys = list(model.model_fields) + list(model.model_extra.keys())
    for k in keys:
        if isinstance(v := getattr(model, k), type_):
            res[k] = v
    return res


def extract_literal_values(ann: AnnotationType):
    ann = extract_annotation(ann=ann)
    if get_origin(ann) == Literal:
        return get_args(ann)
    args = get_args(ann)
    for arg in args:
        if b_is_literal_annotation(arg, False):
            return extract_literal_values(arg)


def extract_type_from_annotation(ann: AnnotationType, type_: Type,
                                 b_strict: bool = False,
                                 b_raise: bool = True, default=None):

    ann = extract_annotation(ann=ann)
    if ann == type_:
        return ann
    elif (isinstance(ann, UnionType) or (get_origin(ann) == Union)
          and (b_strict is False)):
        return extract_type_from_union(
            ann, type_=type_, b_raise=b_raise)
    elif isinstance(ann, GenericAlias):
        res = get_origin(ann)
        if issubclass(res, type_):
            return res
    try:
        if issubclass(ann, type_):
            return ann
    except TypeError:
        raise
    if b_raise:
        raise ValueError(f"No {type_} found")
    return default


def extract_type_from_type_annotation(ann: AnnotationType) -> Type | None:
    ann = extract_annotation(ann)
    if get_origin(ann) != type:
        raise TypeError(f"{ann}")
    res = get_args(ann)
    if len(res) != 1:
        raise NotImplementedError
    return res[0]


def extract_type_from_union(ann: UnionType, type_: Type,
                            b_raise: bool = True, default=None):
    # type_assertion(ann, (UnionType, _UnionGenericAlias))
    type_assertion(ann, UnionType)
    for x in get_args(ann):
        if isinstance(x, GenericAlias):
            x_ = get_origin(x)
        else:
            x_ = x
        try:
            if issubclass(x_, type_):
                return x
        except TypeError:
            raise
    if b_raise:
        raise ValueError(f"No {type_} found")
    return default


class FieldInfoSlots:
    MULTIPLE_OF: ClassVar[str] = 'multiple_of'
    DEFAULT: ClassVar[str] = 'default'
    DEFAULT_FACTORY: ClassVar[str] = 'DEFAULT_FACTORY'
    JSON_SCHEMA_EXTRA: ClassVar[str] = 'json_schema_extra'


def get_field_info_value(field: FieldInfo, key: str, default=None):
    if key == FieldInfoSlots.MULTIPLE_OF:
        return get_field_multiple_of(field)
    elif (hasattr(FieldInfoSlots, key.upper())
          and isinstance(getattr(FieldInfoSlots, key.upper()), str)):
        if hasattr(field, key):
            return getattr(field, key)
        return default
    else:
        raise NotImplementedError(key)


def get_field_json_schema_extra(field: FieldInfo, default=dict) -> dict | Any:
    if (hasattr(field, FieldInfoSlots.JSON_SCHEMA_EXTRA)
            and (field.json_schema_extra is not None)):
        return field.json_schema_extra
    if default == dict:
        return {}
    return default


def get_field_multiple_of(field: FieldInfo, default=None):
    # noinspection PyProtectedMember
    if FieldInfoSlots.MULTIPLE_OF in field._attributes_set:
        # noinspection PyProtectedMember
        return field._attributes_set[FieldInfoSlots.MULTIPLE_OF]
    return default
