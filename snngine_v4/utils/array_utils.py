from types import UnionType
from typing import get_args

import numpy as np
from numpydantic import NDArray, Shape
from numpydantic.exceptions import ShapeError, DtypeError
from pydantic.fields import FieldInfo

from snngine_v4.utils.field_utils import AnnotationType, extract_annotation


type Array2DF32 = NDArray[Shape["* x, * y"], np.float32]
type ArrayL3F32 = NDArray[Shape["3 x"], np.float32]


def b_is_array_annotation(ann: AnnotationType):
    if isinstance(ann, FieldInfo):
        ann = ann.annotation

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

