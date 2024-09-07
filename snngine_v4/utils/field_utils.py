from annotated_types import Ge, Gt, Le, Lt
from pydantic.fields import FieldInfo

from .interval_utils import make_interval


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


def get_field_type_str(field_: FieldInfo):
    return field_.annotation.__name__


def get_field_multiple_of(field_: FieldInfo):
    # noinspection PyProtectedMember
    if 'multiple_of' in field_._attributes_set:
        # noinspection PyProtectedMember
        return field_._attributes_set['multiple_of']


def get_field_json_schema_extra(field_: FieldInfo):
    if (hasattr(field_, 'json_schema_extra')
            and (field_.json_schema_extra is not None)):
        return field_.json_schema_extra
    return {}
