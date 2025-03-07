from __future__ import annotations

from collections import UserDict, UserList
from dataclasses import is_dataclass
from enum import Enum

from typing import Literal, Union


class PostInitCaller(type):
    def __call__(cls, *args, **kwargs):
        obj = type.__call__(cls, *args, **kwargs)
        if not is_dataclass(obj):
            obj.__post_init__()
        return obj


class FrozenPostInitCaller(object, metaclass=PostInitCaller):

    __isfrozen = False
    __isfrozendataclass = None

    def __setattr__(self, key, value):
        if self.__isfrozen and not hasattr(self, key):
            raise AttributeError('%r is not an attribute of class %s. Call '
                                 '"unfreeze()" to allow addition of new '
                                 'attributes' % (key, self))
        object.__setattr__(self, key, value)

    def freeze(self):
        """Freeze the object so that only existing properties can be set"""
        if self.__isfrozen is True:
            raise AttributeError('%r is already frozen' % self)
        self.__isfrozen = True

    def unfreeze(self):
        """Unfreeze the object so that additional properties can be added"""
        if self.__isfrozen is False:
            raise AttributeError('%r is already unfrozen' % self)
        self.__isfrozen = False

    def __post_init__(self):
        # noinspection PyUnresolvedReferences
        object.__setattr__(
            self, f"_{FrozenPostInitCaller.__name__}__isfrozendataclass",
            is_dataclass(self) and (self.__dataclass_params__.frozen is True)
        )
        if self.__isfrozendataclass is False:
            self.freeze()

    @classmethod
    def _isfrozen_attr_key(cls):
        return f"_{FrozenPostInitCaller.__name__}__isfrozen"


def is_in_enum(value, enum_class):
    try:
        get_intenum_member(value, enum_class)
        return True
    except (ValueError, KeyError):
        return False


def get_intenum_member(value, enum_class,
                       b_allow_upper: bool = False):
    if isinstance(value, enum_class):
        return value
    elif isinstance(value, int):
        return enum_class(value)
    elif isinstance(value, str):
        if b_allow_upper is False:
            return enum_class[value]
        else:
            try:
                return enum_class[value]
            except KeyError:
                return enum_class[value.upper()]
    raise TypeError(f'Expected ({enum_class}, {int}, {str}), '
                    f'got {type(value).__name__}.')


def pop_enum_keys(dct, enum_class):
    res = {}
    if len(dct) < len(enum_class):
        pop_keys = []
        for k in dct:
            if is_in_enum(k, enum_class):
                # if k.name in model_dict:
                pop_keys.append(k)
        for k in pop_keys:
            res[k] = dct.pop(k)
    else:
        for x in enum_class:
            if x.name in dct:
                res[x.name] = dct.pop(x.name)
    return res


def type_assertion(item, _type):
    if not isinstance(item, _type):
        raise TypeError(f'Expected {_type}, got {item}')


IntervalLeftRight = Literal["left", "right"]
IntervalClosedType = Union[IntervalLeftRight, Literal["both", "neither"]]


class ConvertingEnum(Enum):

    @classmethod
    def mapping(cls):
        raise NotImplementedError

    @classmethod
    def convert_dict(cls, dct, mapping=None):
        if mapping is None:
            mapping = cls.mapping()
        for i, k in enumerate(cls._member_names_):
            if k in dct:
                raise KeyError(f"Key {k} already exists in dictionary")
            elif k in mapping:
                dct[k] = dct.pop(mapping[k])
        return dct

    @classmethod
    def convert_model(cls, model, mapping=None):
        if mapping is None:
            mapping = cls.mapping()
        res = {}
        for i, k in enumerate(cls._member_names_):
            if k in mapping:
                res[k] = model[mapping[k]]
        return res


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(
                *args, **kwargs)
        return cls._instances[cls]


def filter_dict(
        dct: dict, include_type, result_dict: UserDict | dict = None,
        b_pop: bool = True) -> dict:

    if result_dict is None:
        result_dict = {}

    valid_keys = []
    for k, v in dct.items():
        if isinstance(v, include_type):
            valid_keys.append(k)

    for k in valid_keys:
        if b_pop is True:
            result_dict[k] = dct.pop(k)
        else:
            result_dict[k] = dct[k]
    return result_dict


def filter_list(
        list_: list, type_,
        b_pop: bool = True,
        result_list: list | UserList | None = None):
    if result_list is None:
        result_list = []
    if b_pop is True:
        offset = 0
        for i in range(len(list_)):
            if isinstance(list_[i - offset], type_):
                result_list.append(list_.pop(i - offset))
                offset += 1
    else:
        for i in range(len(list_)):
            if isinstance(list_[i], type_):
                result_list.append(list_[i])
    return result_list
