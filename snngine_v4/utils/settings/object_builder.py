from __future__ import annotations

from dataclasses import dataclass, field
from types import NoneType
from typing import ClassVar, Type

from pydantic import BaseModel

from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict, DefaultDictContainerConfig,
)
from snngine_v4.utils.settings.settings_keywords import ParamOpts


class Model2StringMapConfig(DefaultDictContainerConfig, frozen=True):
    allowed_key_types: Type[int] = int
    allowed_types: Type[str] = str
    b_duplicates_allowed: bool = False
    b_replace_allowed: bool = False
    b_pop_allowed: bool = False


class Model2StringMap(ConfigurableDict):
    DICT_CONFIG_CLASS: ClassVar = Model2StringMapConfig

    def __init__(self, **kwargs):
        self.refs = []
        super().__init__(**kwargs)

    def __getitem__(self, item):
        if not isinstance(item, int):
            item = id(item)
        return self.data[item]

    def __setitem__(self, key, value):
        if not isinstance(key, int):
            key = id(key)
        self.refs.append(key)
        super().__setitem__(key, value)

    def __contains__(self, key):
        return key in list(self.keys())


@dataclass
class BuildResult:
    built: object
    model: BaseModel
    kwargs: dict = field(default_factory=dict)


class ContainerBuildResultConfig(DefaultDictContainerConfig, frozen=True):
    allowed_types: tuple[Type[BuildResult], Type[NoneType]] = (
        BuildResult, NoneType)


class ModeledDict(ConfigurableDict):

    def __init__(self, initdict=None, model2key_map=None, container_conf=None):
        self.model2key_map = model2key_map
        super().__init__(initdict=initdict, container_conf=container_conf)

    def __getitem__(self, key):
        if isinstance(key, BaseModel) and (self.model2key_map is not None):
            return self.data[self.model2key_map[key]]
        return self.data[key]

    def add_to_model_2_key_map(self, key, item):
        pass

    def __setitem__(self, key, item: BuildResult):
        if self.model2key_map is not None:
            self.add_to_model_2_key_map(key, item)
        super().__setitem__(key, item)


class ContainerBuildResult(ModeledDict):

    DICT_CONFIG_CLASS: ClassVar = ContainerBuildResultConfig

    def add_to_model_2_key_map(self, key, item):
        if ((item is not None) and (item.model is not None)
                and (self.model2key_map is not None)):
            self.model2key_map[item.model] = key

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
        object_kwargs.update(**kwargs)
        return object_kwargs

    @classmethod
    def make_object(cls, object_class, **object_kwargs):
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
            model2key_map = Model2StringMap()
        else:
            model2key_map = None

        res = ContainerBuildResult(model2key_map=model2key_map)

        if special_kwargs is None:
            special_kwargs = {}

        if isinstance(model_container, dict):
            keys = model_container.keys()
            models = model_container.values()
        elif isinstance(model_container, BaseModel):
            keys = model_container.model_fields.keys()
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
            res[key] = built
        return res

    @classmethod
    def cls_build(cls, model: BaseModel = None, object_class=None,
                  b_ignore_default_object_class=False,
                  **kwargs):

        model = model or cls.BUILDER_DEFAULT_MODEL_CLASS()

        if object_class is None:
            object_class = cls.find_object_class(
                model, b_ignore_default=b_ignore_default_object_class)

        object_kwargs = cls.make_object_kwargs(model, **kwargs)

        new = cls.make_object(object_class, **object_kwargs)

        return BuildResult(built=new, model=model, kwargs=object_kwargs)


class BuilderDict(ModeledDict, ModelObjectBuilder):

    def __init__(
        self, initdict_or_model=None,
        model2key_map=None,
        container_conf: DefaultDictContainerConfig | None = None
    ):
        if ((container_conf is None)
                and (self.DICT_CONFIG_CLASS == DefaultDictContainerConfig)):

            allowed_types = [NoneType]
            allowed_types += list(self.BUILDER_OBJECT_CLASS_MAP.values())
            allowed_types += list(self.BUILDER_OBJECT_SUPERCLASS_MAP.values())
            if self.BUILDER_DEFAULT_OBJECT_CLASS is not None:
                allowed_types.append(self.BUILDER_DEFAULT_OBJECT_CLASS)
            allowed_types = tuple(allowed_types)
            container_conf = DefaultDictContainerConfig(
                allowed_types=allowed_types
            )

        if model2key_map is None:
            model2key_map = Model2StringMap()

        super().__init__(model2key_map=model2key_map,
                         container_conf=container_conf)
        if initdict_or_model is not None:
            self.update(initdict_or_model)

    def add_from_model(self, key, model, **kwargs):
        self: dict[str, object] | BuilderDict
        build_result = self.cls_build(model=model, **kwargs)
        item = build_result.built
        model = build_result.model
        self.model2key_map[model] = key
        self[key] = item

    def update(self, m, **kwargs) -> None:

        if isinstance(m, BaseModel):
            built_container = self.cls_build_container(
                model_container=m)
            super().update(built_container.object_dict)
            self.model2key_map.update(built_container.model2key_map)
        else:
            super().update(m, **kwargs)
