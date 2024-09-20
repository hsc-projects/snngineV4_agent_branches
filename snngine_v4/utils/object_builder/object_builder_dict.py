from __future__ import annotations

from types import NoneType

from pydantic import BaseModel

from snngine_v4.utils.containers.mappings import (
    Model2ObjectMap, Int2ObjectMapConfig,
)
from snngine_v4.utils.object_builder.object_builder import ModelObjectBuilder


class BuilderDict(Model2ObjectMap, ModelObjectBuilder):

    def add_from_model(self: dict[str, object] | BuilderDict,
                       model, **kwargs):
        build_result = self.cls_build(model=model, **kwargs)
        self[model] = build_result.built

    def cls_make_container_conf(self, container_conf=None):
        if ((container_conf is None)
                and (self.ContainerConfigClass.default_allowed_types()
                     is None)):

            allowed_types = [NoneType]
            allowed_types += list(self.BUILDER_OBJECT_CLASS_MAP.values())
            allowed_types += list(self.BUILDER_OBJECT_SUPERCLASS_MAP.values())
            if self.BUILDER_DEFAULT_OBJECT_CLASS is not None:
                allowed_types.append(self.BUILDER_DEFAULT_OBJECT_CLASS)
            allowed_types = tuple(allowed_types)
            container_conf = Int2ObjectMapConfig(
                allowed_types=allowed_types
            )
        return container_conf or self.ContainerConfigClass()

    def update(self, m, **kwargs) -> None:
        if isinstance(m, BaseModel):
            build = self.cls_build_container(model_container=m)
            m = build.object_dict
        super().update(m, **kwargs)
