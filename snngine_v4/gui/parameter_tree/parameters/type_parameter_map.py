from types import GenericAlias
from typing import (
    _AnnotatedAlias, _LiteralGenericAlias, Annotated, Any,
    Literal, NewType, Type,
)

from pyqtgraph.parametertree import Parameter
from typing_extensions import TypeAliasType

from snngine_v4.utils.containers.super_maps import (
    TypeSortedMap,
)


ParameterValueType = NewType('ParameterValue', Any)


# noinspection PyPep8Naming
class MultiTypeParameterMap(TypeSortedMap):

    sub_maps: tuple = ((str, Parameter),
                       (type | GenericAlias | TypeAliasType
                        | _LiteralGenericAlias | _AnnotatedAlias
                        # | Type[Annotated]
                        ,
                        Parameter))

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        super().__setitem__(value.name(), value)
