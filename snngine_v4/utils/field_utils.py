from types import GenericAlias, UnionType
from typing import ClassVar, Type

from annotated_types import Ge, Gt, Le, Lt
from pydantic import BaseModel
from pydantic.fields import FieldInfo
import typing_extensions
from pydantic_core import PydanticUndefined

from .core_utils import type_assertion
from .interval_utils import make_interval


class FieldInfoSlots:
    MULTIPLE_OF: ClassVar[str] = 'multiple_of'

    DEFAULT: ClassVar[str] = 'default'
    DEFAULT_FACTORY: ClassVar[str] = 'DEFAULT_FACTORY'


def get_field_interval(field_: FieldInfo):
    if len(field_.metadata) == 0:
        return
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


def get_field_annotation(field_: FieldInfo):
    return


def get_field_info_value(field_: FieldInfo, key: str):
    if key == FieldInfoSlots.MULTIPLE_OF:
        return get_field_multiple_of(field_)
    elif (hasattr(FieldInfoSlots, key.upper())
          and isinstance(getattr(FieldInfoSlots, key.upper()), str)):
        if hasattr(field_, key):
            return getattr(field_, key)
        return None
    else:
        raise NotImplementedError(key)


def get_basemodel_from_union(annotation: UnionType, b_raise: bool = True):
    type_assertion(annotation, UnionType)
    for x in typing_extensions.get_args(annotation):
        if is_basemodel_annotation(x):
            return x
    if b_raise:
        raise ValueError('No BaseModel found')


def get_type_from_union(annotation: UnionType, _type: Type,
                        b_raise: bool = True):
    type_assertion(annotation, UnionType)
    for x in typing_extensions.get_args(annotation):
        if isinstance(x, GenericAlias):
            x_ = typing_extensions.get_origin(x)
        else:
            x_ = x
        if issubclass(x_, _type):
            return x
    if b_raise:
        raise ValueError(f"No {_type} found")


def extract_basemodel_from_annotation(annotation: UnionType | Type,
                                      b_raise: bool = True):
    if isinstance(annotation, UnionType):
        return get_basemodel_from_union(annotation, b_raise=b_raise)
    if is_basemodel_annotation(annotation):
        return annotation
    if b_raise:
        raise ValueError("No BaseModel found")


def extract_field_values_by_type(model: BaseModel, type_: Type):
    res = {}
    keys = list(model.model_fields) + list(model.model_extra.keys())
    for k in keys:
        if isinstance(v := getattr(model, k), type_):
            res[k] = v
    return res


def extract_type_from_type_annotation(
        annotation
):
    if typing_extensions.get_origin(annotation) != type:
        raise TypeError(f"{annotation}")
    res = typing_extensions.get_args(annotation)
    if len(res) != 1:
        raise NotImplementedError
    return res[0]


def extract_type_from_annotation(
        annotation: UnionType | Type, _type: Type, b_raise: bool = True
):

    if annotation == _type:
        return annotation
    elif isinstance(annotation, UnionType):
        return get_type_from_union(
            annotation, _type=_type, b_raise=b_raise)
    elif isinstance(annotation, GenericAlias):
        res = typing_extensions.get_origin(annotation)
        if issubclass(res, _type):
            return res
    elif issubclass(annotation, _type):
        return annotation
    if b_raise:
        raise ValueError(f"No {_type} found")


def get_field_multiple_of(field_: FieldInfo):
    # noinspection PyProtectedMember
    if FieldInfoSlots.MULTIPLE_OF in field_._attributes_set:
        # noinspection PyProtectedMember
        return field_._attributes_set[FieldInfoSlots.MULTIPLE_OF]


def get_field_json_schema_extra(field_: FieldInfo):
    if (hasattr(field_, 'json_schema_extra')
            and (field_.json_schema_extra is not None)):
        return field_.json_schema_extra
    return {}


def has_basemodel_annotation(field_info: FieldInfo) -> bool:
    # noinspection PyTypeChecker
    return is_basemodel_annotation(field_info.annotation)


def has_default(field_info: FieldInfo) -> bool:
    b_as_default = field_info.default != PydanticUndefined
    if not b_as_default:
        return field_info.default_factory is not None
    return True


def b_is_float_annotation(annotation):
    return b_annotation_includes_type(annotation, float)


def b_is_int_annotation(annotation, b_strict: bool):
    if b_strict and isinstance(annotation, UnionType):
        return False
    return b_annotation_includes_type(annotation, int)


def b_annotation_includes_type(
        ann: GenericAlias | UnionType | Type, _type: Type) -> bool:

    if isinstance(ann, GenericAlias):
        ann = typing_extensions.get_origin(ann)

    if isinstance(ann, UnionType):
        res = any([b_annotation_includes_type(x, _type)
                   for x in typing_extensions.get_args(ann)])
        return res
    try:
        # noinspection PyTypeChecker
        return issubclass(ann, _type)
    except TypeError:
        return False


def is_basemodel_annotation(ann: GenericAlias | UnionType | Type) -> bool:
    return b_annotation_includes_type(ann, _type=BaseModel)
