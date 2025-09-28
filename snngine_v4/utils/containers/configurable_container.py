from __future__ import annotations

from collections import UserDict, UserList
from types import NoneType
from typing import Any, ClassVar, Type

from pydantic import field_validator
from pydantic.types import AnyType

from snngine_v4.utils.core_utils import filter_dict, filter_list
from snngine_v4.utils.field_utils import (
    extract_field_default, extract_type_from_type_annotation,
    b_field_has_default,
    Undefined,
)
from snngine_v4.utils.settings.config_model import ConfigModel


class ConfigurationError(Exception):
    pass


class ExtensionByDuplicateError(Exception):
    pass


class UndefinedDefaultError(Exception):
    pass


type ValidKeyType = tuple[Type, ...] | Type
type ValidValueType = tuple[Type | Any, ...] | Type | Any


class ContainerConfig(ConfigModel, frozen=True):
    allowed_types: ValidValueType = Any
    forbidden_types: ValidValueType = None
    allowed_key_types: ValidKeyType = NoneType
    b_duplicates_allowed: bool = False
    # b_duplicate_key_check_by_id: bool = False
    b_duplicate_value_check_by_id: bool = False
    b_replace_allowed: bool = False
    b_pop_allowed: bool = True
    b_clear_allowed: bool = False
    b_remove_by_id_allowed: bool = False

    class Slots:
        ALLOWED_TYPES: ClassVar[str] = 'allowed_types'
        B_POP_ALLOWED: ClassVar[str] = 'b_pop_allowed'

    @classmethod
    def b_int_allowed(cls, type_, forbidden_types=None):
        return cls.b_valid_object_type(
            1, type_, forbidden_types=forbidden_types)

    @classmethod
    def b_valid_object_type(cls, item, type_, forbidden_types=None):
        if (forbidden_types is not None) and isinstance(item, forbidden_types):
            return False

        if type_ in [(Any, ), (AnyType, )]:
            return True
        try:
            return isinstance(item, type_)
        except TypeError:
            return isinstance(item, type_)

    @classmethod
    def validate_value_type(cls, item, type_, forbidden_types=None):
        b_allowed_type = cls.b_valid_object_type(
            item, type_=type_, forbidden_types=forbidden_types)
        if b_allowed_type is False:
            raise TypeError(
                    f"Item must be of type {type_}."
                    f"Got {type(item).__name__} instead.")
        return item

    @classmethod
    def default_allowed_types(cls):
        return cls.model_fields[cls.Slots.ALLOWED_TYPES].default

    # noinspection PyNestedDecorators
    @field_validator('allowed_types',
                     'allowed_key_types', mode='after')
    @classmethod
    def type_validator(cls, v: ValidValueType | Type | Any) -> ValidValueType:
        if not isinstance(v, tuple):
            return v,
        return v

    @classmethod
    def _validate_model_before(cls, data: Any) -> Any:
        k = cls.Slots.ALLOWED_TYPES
        field = cls.model_fields[k]
        if (k not in data) and (not b_field_has_default(field)):
            v = extract_type_from_type_annotation(field.annotation)
            data[k] = v
        for k, v in data.items():
            if data[k] == Undefined:
                data[k] = extract_field_default((cls, k))
        return super()._validate_model_before(data)

    def model_post_init(self, __context):
        super().model_post_init(__context)
        data = self
        if (b_int_allowed := self.b_int_allowed(
                data.allowed_types, data.forbidden_types)
            and (data.b_duplicate_value_check_by_id
                 or data.b_remove_by_id_allowed)):
            # noinspection PyUnboundLocalVariable
            raise ConfigurationError(
                f"b_int_allowed={b_int_allowed} "
                f"and "
                f"\ndata.b_duplicate_value_check_by_id"
                f"={data.b_duplicate_value_check_by_id}"
                f"\ndata.b_remove_by_id_allowed"
                f"={data.b_remove_by_id_allowed}"
            )


class ConfigurableContainerBase:

    ContainerConfigClass: ClassVar[Type[ContainerConfig]] = ContainerConfig

    data: list | dict | Any

    def __init__(self, container_conf: ContainerConfig = None):
        self._container_conf: ContainerConfig = self.cls_make_container_conf(
            container_conf=container_conf)

    def assert_emptiness(self):
        if not self.is_empty:
            raise AssertionError("not empty")

    def b_valid_item(self, item):
        b_valid_type = self.b_valid_item_type(item)
        b_duplicated = self.b_duplicated_item(item)
        return b_valid_type and (not b_duplicated)

    def b_duplicated_item(self, item):
        return False

    def b_valid_item_type(self, item):
        return ContainerConfig.b_valid_object_type(
            item, self._container_conf.allowed_types,
            forbidden_types=self._container_conf.forbidden_types)

    def b_valid_key_type(self, key):
        return ContainerConfig.b_valid_object_type(
            key, self._container_conf.allowed_key_types)

    @classmethod
    def cls_make_container_conf(cls, container_conf=None,
                                default_cls=None, **kwargs):
        if container_conf:
            return container_conf
        if default_cls is None:
            default_cls = cls.ContainerConfigClass
        if isinstance(default_cls, tuple):
            cls_: Type[ContainerConfig] = default_cls[0]
            kwargs = {'allowed_types': default_cls[1]}
            if len(default_cls) == 3:
                kwargs['allowed_key_types'] = default_cls[2]
            return cls_(**kwargs)
        return default_cls(**kwargs)

    @classmethod
    def cls_validate_values(cls, items, type_, b_duplicate_check):
        if isinstance(items, dict):
            # keys = list(items.keys())
            items = list(items.values())
        if b_duplicate_check is True:
            try:
                item_set = list(set(items))
            except TypeError:
                item_set = list(set([id(item) for item in items]))
            if len(items) != len(item_set):
                raise ExtensionByDuplicateError("Items must be unique.")

        for item in items:
            ContainerConfig.validate_value_type(item, type_=type_)
        return items

    def __contains__(self, item):
        if ((not isinstance(item, int)) and
                self._container_conf.b_duplicate_value_check_by_id):
            return id(item) in self.data_ids
        return item in self.data

    @property
    def container_conf(self):
        return self._container_conf

    @property
    def data_ids(self):
        return [id(x) for x in self.data]

    def filter_dict(self, dict_: dict | UserDict, result_dict=None, b_pop=True):
        return filter_dict(
            dict_, include_type=self._container_conf.allowed_types,
            result_dict=result_dict, b_pop=b_pop)

    def filter_list(self, list_: list | UserList, result_list=None, b_pop=True):
        return filter_list(
            list_, type_=self._container_conf.allowed_types,
            result_list=result_list, b_pop=b_pop)

    @classmethod
    def from_type(cls, type_: Type, **kwargs):
        return cls(
            container_conf=ContainerConfig(allowed_types=type_, **kwargs))

    def get_valid_item_type(self, item, default=Undefined,
                            types_=None):
        if types_ is None:
            types_ = self._container_conf.allowed_types
        if type(item) in types_:
            return type(item)
        else:
            for t in types_:
                if isinstance(item, t):
                    return t
        if self.b_valid_item_type(item):
            raise ValueError("Unknown but valid type")
        if default is not Undefined:
            return default
        raise TypeError(f"{item}")

    @property
    def is_empty(self):
        return len(self.data) == 0

    def _validate_item(self, item):
        if self.b_valid_item_type(item) is False:
            raise TypeError(
                f"Item must be of type"
                f" {self._container_conf.allowed_types}."
                f"Got {type(item).__name__} instead.")
        elif ((not self._container_conf.b_duplicates_allowed) and
              self.b_duplicated_item(item)):
            raise ExtensionByDuplicateError(
                f"Duplicated item: {item} ({id(item)})")
        return self

    def validate_item(self, item):
        b_valid_item = self.b_valid_item(item)
        if b_valid_item is False:
            self._validate_item(item)
            raise AttributeError("Item must be valid.")
        return item

    def validate_items(self, items):
        if isinstance(items, dict):
            keys = list(items.keys())
            self.validate_keys(keys)
        return self.cls_validate_values(
            items=items, type_=self._container_conf.allowed_types,
            b_duplicate_check=not self._container_conf.b_duplicates_allowed)

    def validate_keys(self, keys):
        keys = self.cls_validate_values(
            items=keys, type_=self._container_conf.allowed_key_types,
            b_duplicate_check=True)
        return keys
