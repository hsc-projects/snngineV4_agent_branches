from __future__ import annotations

from copy import copy
from enum import Enum, IntEnum
from types import GenericAlias, NoneType, UnionType
from typing import (
    Annotated, Any, ClassVar, get_args, get_origin, Literal, Type,
    Union,
)

import numpy as np
import pandas as pd
from annotated_types import Ge, Gt, Le, Lt
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic.types import AnyType
from pydantic_core import PydanticUndefined
from typing_extensions import TypeAliasType

from .core_utils import type_assertion
from .interval_utils import make_interval


type AnnotationType = (FieldInfo | GenericAlias | UnionType
                       | Type | TypeAliasType)


def b_annotation_includes_basemodel(ann: AnnotationType,
                                    b_strict: bool) -> bool:
    return b_annotation_includes_type(
        ann=ann, type_=BaseModel, b_strict=b_strict)


def b_is_annotated(ann: AnnotationType, b_strict: bool = True):
    ann = extract_annotation(ann=ann)
    res = get_origin(ann) == Annotated
    if res or b_strict:
        return res
    if b_is_optional(ann):
        return any([b_is_annotated(x) for x in get_args(ann)])
    return False


def b_is_enum_annotation(ann: AnnotationType, b_strict: bool) -> bool:
    return b_annotation_includes_type(ann, Enum, b_strict=b_strict)


def b_is_int_annotation(ann: AnnotationType, b_strict: bool) -> bool:
    return b_annotation_includes_type(ann, int, b_strict=b_strict)


def b_is_intenum_annotation(ann: AnnotationType, b_strict: bool) -> bool:
    return b_annotation_includes_type(ann, IntEnum, b_strict=b_strict)


def b_is_literal_annotation(ann: AnnotationType, b_strict: bool = True):
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


def b_is_optional(ann: AnnotationType):
    ann = extract_annotation(ann=ann)
    res = (get_origin(ann) is Union) and (type(None) in get_args(ann))
    if res and (ann.__name__ != 'Optional'):
        raise RuntimeError
    return res


def b_is_union(ann: AnnotationType):
    ann = extract_annotation(ann=ann)
    return get_origin(ann) == Union


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

    if isinstance(ann, UnionType):
        if b_strict:
            return False
        res = any([b_annotation_includes_type(x, type_, b_strict=False)
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
    b_has_default = field_info.default is not PydanticUndefined
    if not b_has_default:
        return field_info.default_factory is not None
    return True


def extract_annotation(ann: AnnotationType):
    if isinstance(ann, FieldInfo):
        ann = ann.annotation
    if isinstance(ann, TypeAliasType):
        ann = ann.__value__
    return ann


def extract_annotations_from_annotation(
        ann: AnnotationType, b_strict: bool = True):
    ann = extract_annotation(ann)
    if b_strict:
        assert b_is_annotated(ann, b_strict=True)
        return get_args(ann)
    if b_is_optional(ann):
        for x in get_args(ann):
            if b_is_annotated(x, b_strict=True):
                return extract_annotations_from_annotation(x, True)
    raise TypeError(f"{ann}")


def extract_basemodel_from_annotation(ann: UnionType | Type,
                                      b_raise: bool = True,
                                      b_strict: bool = False):
    # if isinstance(ann, UnionType):
    #     return extract_basemodel_from_union(ann, b_raise=b_raise)
    # if b_annotation_includes_basemodel(ann, b_strict=True):
    #     return ann
    # if b_raise:
    #     raise ValueError("No BaseModel found")

    return extract_type_from_annotation(
        ann=ann, b_strict=b_strict, b_raise=b_raise, type_=BaseModel)


def extract_basemodels_from_annotation(
        ann: UnionType | Type, b_raise: bool = True, b_strict: bool = False):
    return extract_types_from_annotation(
        ann=ann, b_strict=b_strict, b_raise=b_raise, type_=BaseModel)


def extract_basemodel_from_iterable_annotation(
    ann: AnnotationType, b_raise: bool = True,
    allowed_union_alts: tuple[Type, ...] | Type[Undefined] = (NoneType, None)
):
    return extract_types_from_iterable_annotation(
        ann=ann, type_=BaseModel, b_raise=b_raise,
        allowed_union_alts=allowed_union_alts)

# def extract_basemodel_from_union(ann: UnionType, b_raise: bool = True,
#                                  b_strict: bool = False):
#     type_assertion(ann, UnionType)
#     for x in get_args(ann):
#         if b_annotation_includes_basemodel(x, b_strict=b_strict):
#             return x
#     if b_raise:
#         raise ValueError('No BaseModel found')


def extract_field_interval(field_: FieldInfo, default='inf'):
    if len(field_.metadata) == 0:
        return pd.Interval(-np.inf, np.inf) if (default == 'inf') else default
    metadata_types = [type(x) for x in field_.metadata]

    ge = None
    gt = None
    le = None
    lt = None

    metadata = copy(field_.metadata)

    if b_is_annotated(field_, b_strict=False):
        anns = extract_annotations_from_annotation(
            field_.annotation, b_strict=False)
        metadata += list(anns)
        metadata_types += [type(x) for x in anns]

    for i, metadata_type in enumerate(metadata_types):
        if metadata_type == Gt:
            gt = metadata[i].gt
        elif metadata_type == Ge:
            ge = metadata[i].ge
        elif metadata_type == Lt:
            lt = metadata[i].lt
        elif metadata_type == Le:
            le = metadata[i].le

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
    if b_is_literal_annotation(ann, True):
        return get_args(ann)
    else:
        raise RuntimeError
    # args = get_args(ann)
    # for arg in args:
    #     if b_is_literal_annotation(arg, False):
    #         return extract_literal_values(arg)


def extract_type_from_annotation(ann: AnnotationType, type_: Type,
                                 b_strict: bool = False,
                                 b_raise: bool = True, default=None):

    ann = extract_annotation(ann=ann)
    if ann == type_:
        return ann
    elif isinstance(ann, UnionType) or (get_origin(ann) == Union):
        if b_strict is True:
            return
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

    if ann in [Any, NoneType, type, AnyType]:
        return ann
    if get_origin(ann) != type:
        raise TypeError(f"{ann}, {get_origin(ann)}")
    res = get_args(ann)
    if len(res) != 1:
        raise NotImplementedError
    return res[0]


def extract_types_from_annotation(ann: AnnotationType, type_: Type,
                                  b_strict: bool = False,
                                  b_raise: bool = True):
    res = extract_type_from_annotation(ann=ann, b_strict=True, type_=type_,
                                       b_raise=False)
    if res is not None:
        return (res,)
    elif (isinstance(ann, UnionType) or (get_origin(ann) == Union)
          and (b_strict is False)):
        return extract_types_from_union(
            ann, type_=type_, b_raise=b_raise)


def extract_types_from_iterable_annotation(
    ann: AnnotationType, type_: Type, b_raise: bool = True,
    allowed_union_alts: tuple[Type, ...] | Type[Undefined] = (NoneType, None)
):
    orig = get_origin(ann)
    allowed_types = []
    if (allowed_union_alts is not Undefined) and (orig == UnionType):
        args = get_args(ann)
        for arg in args:
            if (arg_og := get_origin(arg)) in [list, tuple]:
                res = list(extract_types_from_iterable_annotation(
                    ann=arg, type_=type_, b_raise=False,
                    allowed_union_alts=Undefined,))
                allowed_types += res
            elif arg_og not in allowed_union_alts:
                raise NotImplementedError(f"{arg_og}")
        allowed_types = tuple(allowed_types)
    elif orig in [list, tuple]:
        for x in get_args(ann):
            if b_annotation_includes_type(x, type_=type_, b_strict=False):
                res = list(extract_types_from_annotation(
                    x, type_=type_, b_strict=False, b_raise=False))
                allowed_types += res
    else:
        raise NotImplementedError(f"{orig}")
    if (len(allowed_types) == 0) and b_raise:
        raise ValueError(f"No {type_} found")
    return allowed_types


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


def extract_types_from_union(ann: UnionType, type_: Type,
                             b_raise: bool = True):
    res = []
    type_assertion(ann, UnionType)
    for x in get_args(ann):
        if isinstance(x, GenericAlias):
            x_ = get_origin(x)
        else:
            x_ = x
        try:
            if issubclass(x_, type_):
                res.append(x)
        except TypeError:
            raise
    if (len(res) == 0) and b_raise:
        raise ValueError(f"No {type_} found")
    return tuple(res)


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


def model_keys(model):
    keys = list(model.model_fields.keys())
    if not isinstance(model, type) and (model.model_extra is not None):
        extra = list(model.model_extra.keys())
        if '__setattr__' in extra:
            extra.remove('__setattr__')
        keys += extra
    return keys


class Undefined:
    pass


type KeepUndefinedType = Type[Undefined] | None
