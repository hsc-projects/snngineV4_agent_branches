from __future__ import annotations

from types import NoneType
from typing import Type

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from snngine_v4.utils.containers.mappings import (
    Model2ObjectMap, Int2ObjectMapConfig,
)
from snngine_v4.utils.object_builder.object_builder import ModelObjectBuilder


class BuilderDict(Model2ObjectMap, ModelObjectBuilder):

    def add_from_model(self: dict[str, object] | BuilderDict,
                       model, **kwargs):
        build_result = self.cls_build(model=model, **kwargs)
        self[model] = build_result.built

    @classmethod
    def cls_make_container_conf(
            cls, container_conf=None,
            default_cls: Type[Int2ObjectMapConfig] = PydanticUndefined):

        if default_cls == PydanticUndefined:
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
                allowed_types=allowed_types
            )
        return container_conf or default_cls()

    def build(self, m=None, **kwargs):
        self.clear()
        self.update(m=m, **kwargs)

    def update(self, m=None, **kwargs) -> None:
        if isinstance(m, BaseModel):
            build = self.cls_build_container(model_container=m)
            m = build.object_dict
        super().update(m, **kwargs)
