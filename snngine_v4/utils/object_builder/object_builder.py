from __future__ import annotations

from dataclasses import dataclass, field
from enum import auto, Enum, IntEnum
from types import NoneType
from typing import ClassVar, Type

from pydantic import BaseModel

from snngine_v4.utils.containers.mappings import (
    Model2ObjectMap, ObjectMapConfig,
)
from snngine_v4.utils.class_mixer import ClassMixer
from snngine_v4.utils.field_utils import model_keys
from snngine_v4.utils.settings.settings_keywords import BaseModelSlots


@dataclass
class BuildResult:
    built: object
    model: BaseModel
    kwargs: dict = field(default_factory=dict)


class ContainerBuildResultConfig(ObjectMapConfig, frozen=True):
    allowed_types: tuple[Type[BuildResult], Type[NoneType]] = (
        BuildResult, NoneType)


class ContainerBuildResult(Model2ObjectMap):
    """"""
    ContainerConfigClass: ClassVar = ContainerBuildResultConfig

    @property
    def object_dict(self):
        res = Model2ObjectMap()
        for k, v in self.pairs():
            if v is not None:
                v = v.built
            if v is not None:
                res[k] = v
        return res


class ObjectInitializationType(IntEnum):
    KWARGS = 0
    MODEL = auto()
    MODEL_AND_KWARGS = auto()


class MissingClassDefinitionError(Exception):
    """Raised when a class definition is missing"""


class ModelObjectBuilder:
    """"""
    b_enum_to_values: ClassVar[bool] = True

    BUILDER_DEFAULT_MODEL_CLASS: ClassVar[Type[BaseModel] | None] = None
    DEFAULT_MODEL_CONTAINER_CLASS: ClassVar[Type[BaseModel] | None] = None

    BUILDER_DEFAULT_OBJECT_CLASS: ClassVar[Type | None] = None
    BUILDER_OBJECT_CLASS_MAP: ClassVar[dict[Type[BaseModel], Type]] = {}
    BUILDER_OBJECT_SUPERCLASS_MAP: ClassVar[dict[Type[BaseModel], Type]] = {}
    BUILDER_OBJECT_CLASS_MIXER: ClassVar[Type[ClassMixer] | None] = None

    DEFAULT_OBJECT_INIT_TYPE: ObjectInitializationType = (
        ObjectInitializationType.KWARGS)

    OBJECT_INIT_TYPES: ClassVar[
        dict[Type[BaseModel], ObjectInitializationType]] = {}
    OBJECT_INIT_SUPER_TYPES: ClassVar[
        dict[Type[BaseModel], ObjectInitializationType]] = {}

    @classmethod
    def cls_build_container(
            cls, model_container,
            b_replace_missing_by_default_model: bool = False,
            b_ignore_default_object_class: bool = True,
            b_raise_if_missing_model: bool = False,
            b_raise_if_missing_object_class: bool = False,
            special_kwargs=None,
            **common_kwargs) -> ContainerBuildResult:

        if model_container is None:
            model_container = cls.DEFAULT_MODEL_CONTAINER_CLASS()

        res = ContainerBuildResult()

        if special_kwargs is None:
            special_kwargs = {}

        if isinstance(model_container, dict):
            keys = model_container.keys()
            models = model_container.values()
        elif isinstance(model_container, BaseModel):
            keys = model_keys(
                model=model_container,
                exclude=BaseModelSlots.CLASS__NAME)
            keys = [k for k in keys
                    if isinstance(getattr(model_container, k), BaseModel)]
            models = [getattr(model_container, k) for k in keys]
        elif hasattr(model_container, 'keys'):
            keys = model_container.keys()
            models = model_container.values()
        else:
            # noinspection PyTypeChecker,PydanticTypeChecker
            keys = list(range(len(model_container)))
            models = model_container

        dct = dict(zip(keys, models))
        dct = BaseModelSlots.pop_class__name_kw(dct)

        for key, model in dct.items():

            if isinstance(model, list):
                model_container_ = [x for x in model
                                    if isinstance(x, BaseModel)]
                if len(model_container_) > 0:
                    built_ = cls.cls_build_container(
                        model_container=model_container_,
                        b_replace_missing_by_default_model=
                        b_replace_missing_by_default_model,
                        b_ignore_default_object_class=
                        b_ignore_default_object_class,
                        b_raise_if_missing_model=b_raise_if_missing_model,
                        b_raise_if_missing_object_class=
                        b_raise_if_missing_object_class,
                        special_kwargs=special_kwargs.pop(key, {}),
                        **common_kwargs
                    )
                    res.update(built_)
            else:
                new_kwargs = {}
                new_kwargs.update(common_kwargs)
                new_kwargs.update(special_kwargs.pop(key, {}))
                built = cls.cls_build_obj(
                    model=model, object_class=None,
                    b_replace_missing_by_default_model=
                    b_replace_missing_by_default_model,
                    b_ignore_default_object_class=
                    b_ignore_default_object_class,
                    b_raise_if_missing_model=b_raise_if_missing_model,
                    b_raise_if_missing_object_class=
                    b_raise_if_missing_object_class,
                    **common_kwargs
                )
                res[model] = built
        return res

    @staticmethod
    def find_class_value(class_, class_dct: dict, super_dct=None,
                         default=None):
        if (object_class := class_dct.get(class_, None)) is not None:
            return object_class
        elif (object_class is None) and (super_dct is not None):
            for k, v in super_dct.items():
                if issubclass(class_, k):
                    return v
        if default is not None:
            return default
        else:
            name_list = ', '.join([x.__name__ for x in class_dct.keys()])
            raise MissingClassDefinitionError(
                f"{class_.__name__} is not in [{name_list}]")

    @classmethod
    def find_object_class(cls, model, b_ignore_default: bool,
                          b_raise: bool = True):
        try:
            object_class = cls.find_class_value(
                model.__class__, cls.BUILDER_OBJECT_CLASS_MAP,
                super_dct=cls.BUILDER_OBJECT_SUPERCLASS_MAP,
                default=cls.BUILDER_DEFAULT_OBJECT_CLASS
                if (b_ignore_default is False) else None)
        except MissingClassDefinitionError as error:
            if b_raise:
                raise error
            if cls.BUILDER_OBJECT_CLASS_MIXER is not None:
                raise error
            object_class = None

        if cls.BUILDER_OBJECT_CLASS_MIXER is not None:
            key_class = object_class
            object_class = cls.BUILDER_OBJECT_CLASS_MIXER()[key_class]
        return object_class

    @classmethod
    def make_object_kwargs(cls, object_class, model: BaseModel, **kwargs):
        object_kwargs = model.model_dump(mode='python')
        object_kwargs = BaseModelSlots.pop_class__name_kw(object_kwargs)
        # object_kwargs.update(**kwargs)

        if cls.b_enum_to_values is True:
            for k, v in object_kwargs.items():
                if isinstance(v, Enum):
                    object_kwargs[k] = v.value

        object_init_type = cls.find_class_value(
            model.__class__,
            class_dct=cls.OBJECT_INIT_TYPES,
            super_dct=cls.OBJECT_INIT_SUPER_TYPES,
            default=cls.DEFAULT_OBJECT_INIT_TYPE)

        match object_init_type:
            case ObjectInitializationType.KWARGS:
                pass
            case ObjectInitializationType.MODEL:
                object_kwargs = {'model': model}
            case ObjectInitializationType.MODEL_AND_KWARGS:
                object_kwargs['model'] = model
            case _:
                raise NotImplementedError(
                    f"object_init_type={object_init_type.name}")

        object_kwargs.update(**kwargs)

        return object_kwargs

    @classmethod
    def get_model(cls, model: BaseModel | None):
        if model is None:
            return cls.BUILDER_DEFAULT_MODEL_CLASS()
        return model

    @classmethod
    def make_object(cls, object_class, object_model, **object_kwargs):
        return object_class(**object_kwargs)

    @classmethod
    def cls_build_obj(cls, model: BaseModel = None, object_class=None,
                      b_replace_missing_by_default_model: bool = False,
                      b_ignore_default_object_class: bool = True,
                      b_raise_if_missing_model: bool = False,
                      b_raise_if_missing_object_class: bool = False,
                      **kwargs):

        if ((model is None)
                and (b_replace_missing_by_default_model is True)):
            model = cls.BUILDER_DEFAULT_OBJECT_CLASS()
        if b_raise_if_missing_model and model is None:
            raise ValueError('No object class found for model')
        if model is not None:
            object_class = cls.find_object_class(
                model, b_ignore_default=b_ignore_default_object_class,
                b_raise=b_raise_if_missing_object_class)
            if object_class is not None:

                model = cls.get_model(model=model)

                if object_class is None:
                    object_class,  = cls.find_object_class(
                        model, b_ignore_default=b_ignore_default_object_class)

                object_kwargs = cls.make_object_kwargs(
                    object_class, model, **kwargs)
                new = cls.make_object(object_class, model, **object_kwargs)

                return BuildResult(built=new, model=model, kwargs=object_kwargs)
        return BuildResult(built=None, model=model, kwargs=kwargs)
