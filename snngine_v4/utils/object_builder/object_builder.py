from __future__ import annotations

from dataclasses import dataclass, field
from types import NoneType
from typing import ClassVar, Type

from pydantic import BaseModel

from snngine_v4.utils.containers.configurable_dict import (
    DefaultDictContainerConfig,
)
from snngine_v4.utils.containers.mappings import MappedDict, Object2KeyMap
from snngine_v4.utils.settings.settings_keywords import ParamOpts
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


@dataclass
class BuildResult:
    built: object
    model: BaseModel
    kwargs: dict = field(default_factory=dict)


class ContainerBuildResultConfig(DefaultDictContainerConfig, frozen=True):
    allowed_types: tuple[Type[BuildResult], Type[NoneType]] = (
        BuildResult, NoneType)


class ContainerBuildResult(MappedDict):

    CONTAINER_CONFIG_CLASS: ClassVar = ContainerBuildResultConfig

    def add_to_object_2_key_map(self, key, item):
        if ((item is not None) and (item.model is not None)
                and (self.object2key_map is not None)):
            self.object2key_map[item.model] = key

    @property
    def object_dict(self):
        return {(k, v.built if v is not None else None)
                for k, v in self.data.items()}


class ModelObjectBuilder:

    BUILDER_DEFAULT_MODEL_CLASS: ClassVar[Type[BaseModel]] = None
    DEFAULT_MODEL_CONTAINER_CLASS: ClassVar[Type[BaseModel]] = None

    BUILDER_DEFAULT_OBJECT_CLASS: ClassVar[Type] = None
    BUILDER_OBJECT_CLASS_MAP: ClassVar[dict[Type[BaseModel], Type]] = {}
    BUILDER_OBJECT_SUPERCLASS_MAP: ClassVar[dict[Type[BaseModel], Type]] = {}

    @classmethod
    def find_object_class(cls, model, b_ignore_default: bool,
                          b_raise: bool = True):
        object_class = None
        if model.__class__ not in cls.BUILDER_OBJECT_CLASS_MAP:
            for k, v in cls.BUILDER_OBJECT_SUPERCLASS_MAP.items():
                if issubclass(model.__class__, k):
                    object_class = v
                    break
        else:
            object_class = cls.BUILDER_OBJECT_CLASS_MAP[model.__class__]
        if object_class is None:
            if b_ignore_default is False:
                object_class = cls.BUILDER_DEFAULT_OBJECT_CLASS
            elif b_raise:
                raise ValueError('No object class found for model')
        return object_class

    @classmethod
    def make_object_kwargs(cls, model: BaseModel, **kwargs):
        object_kwargs = ParamOpts.pop_ui_options_keyword(
            model.model_dump(mode='python'))
        object_kwargs = XMLSettingsModel.pop_model__class__name_keyword(
            object_kwargs)
        object_kwargs.update(**kwargs)
        return object_kwargs

    @classmethod
    def get_model(cls, model: BaseModel | None):
        return model or cls.BUILDER_DEFAULT_MODEL_CLASS()

    @classmethod
    def make_object(cls, object_class, model, **object_kwargs):
        return object_class(**object_kwargs)

    @classmethod
    def cls_build_container(
            cls, model_container=None,
            b_replace_missing_by_default_model: bool = False,
            b_ignore_default_object_class: bool = True,
            b_raise_if_missing_model: bool = False,
            b_raise_if_missing_object_class: bool = False,
            special_kwargs=None,
            b_make_model_to_key_map: bool = True,
            **common_kwargs):

        if model_container is None:
            model_container = cls.DEFAULT_MODEL_CONTAINER_CLASS()

        if b_make_model_to_key_map:
            object2key_map = Object2KeyMap()
        else:
            object2key_map = None

        res = ContainerBuildResult(object2key_map=object2key_map)

        if special_kwargs is None:
            special_kwargs = {}

        if isinstance(model_container, dict):
            keys = model_container.keys()
            models = model_container.values()
        elif isinstance(model_container, BaseModel):
            keys = list(model_container.model_fields.keys())
            if model_container.model_extra is not None:
                keys += list(model_container.model_extra.keys())
            models = [getattr(model_container, k) for k in keys]
        elif hasattr(model_container, 'keys'):
            keys = model_container.keys()
            models = model_container.values()
        else:
            # noinspection PyTypeChecker
            keys = list(range(len(model_container)))
            models = model_container

        dct = ParamOpts.pop_ui_options_keyword(dict(zip(keys, models)))

        for key, model in dct.items():
            built = None
            if (model is None) and (b_replace_missing_by_default_model is True):
                model = cls.BUILDER_DEFAULT_OBJECT_CLASS()
            if b_raise_if_missing_model and model is None:
                raise ValueError('No object class found for model')
            if model is not None:
                object_class = cls.find_object_class(
                    model, b_ignore_default=b_ignore_default_object_class,
                    b_raise=b_raise_if_missing_object_class)
                if object_class is not None:
                    new_kwargs = special_kwargs.pop(key, {})
                    new_kwargs.update(common_kwargs)
                    built = cls.cls_build(
                        model=model, object_class=object_class,
                        b_ignore_default_object_class=True,
                        **new_kwargs
                    )
                else:
                    pass
            res[key] = built
        return res

    @classmethod
    def cls_build(cls, model: BaseModel = None, object_class=None,
                  b_ignore_default_object_class=False,
                  **kwargs):

        model = cls.get_model(model=model)

        if object_class is None:
            object_class = cls.find_object_class(
                model, b_ignore_default=b_ignore_default_object_class)

        object_kwargs = cls.make_object_kwargs(model, **kwargs)

        new = cls.make_object(object_class, model=model, **object_kwargs)

        return BuildResult(built=new, model=model, kwargs=object_kwargs)
