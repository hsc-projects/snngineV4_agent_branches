from __future__ import annotations

from types import NoneType
from typing import Type

from pydantic import BaseModel

from snngine_v4.utils.containers.mappings import (
    Model2ObjectMap, Int2ObjectMapConfig,
)
from snngine_v4.utils.core_utils import type_assertion
from snngine_v4.utils.object_builder.object_builder import (
    ContainerBuildResult,
    ModelObjectBuilder,
)


class BuilderDict(Model2ObjectMap, ModelObjectBuilder):

    def __init__(self, model_container=None, build_kwargs=None, **kwargs):
        super().__init__(**kwargs)
        if model_container is not None:
            if build_kwargs is not None:
                build_res = self.cls_build_container(
                    model_container=model_container, **build_kwargs)
                self.update(build_res)
            else:
                self.update(model_container)

    def add_build(self: dict[BaseModel, object] | BuilderDict,
                  model, **kwargs):
        build_result = self.cls_build_obj(model=model, **kwargs).built
        self[model] = build_result
        return build_result

    @classmethod
    def cls_make_container_conf(
            cls, container_conf=None,
            default_cls: Type[Int2ObjectMapConfig] = None, **kwargs):

        if default_cls is None:
            default_cls = cls.ContainerConfigClass

        if ((container_conf is None)
                and (default_cls.default_allowed_types()
                     is None)):

            allowed_types = [NoneType]
            allowed_types += list(cls.BUILDER_OBJECT_CLASS_MAP.values())
            allowed_types += list(cls.BUILDER_OBJECT_SUPERCLASS_MAP.values())
            if cls.BUILDER_DEFAULT_OBJECT_CLASS is not None:
                allowed_types.append(cls.BUILDER_DEFAULT_OBJECT_CLASS)
            allowed_types = tuple(allowed_types)
            container_conf = Int2ObjectMapConfig(
                allowed_types=allowed_types, **kwargs
            )
        return container_conf or default_cls()

    def build(self, m=None, **kwargs):
        self.clear()
        self.update(m=m, **kwargs)

    def get_built_objects(self, *models, container=None,
                          b_assert_key_exists=True):
        return self.make_subset(*models,
                                subset_container=container,
                                b_assert_key_exists=b_assert_key_exists)

    def update(self, m=None, **kwargs) -> None:
        type_assertion(m, (BaseModel, list, NoneType, Model2ObjectMap,
                           ContainerBuildResult))
        if isinstance(m, (BaseModel, list)):
            m = self.cls_build_container(model_container=m).object_dict
        if isinstance(m, ContainerBuildResult):
            m = m.object_dict
        super().update(m, **kwargs)
