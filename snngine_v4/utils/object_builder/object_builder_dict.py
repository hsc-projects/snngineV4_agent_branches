from __future__ import annotations

from types import NoneType

from pydantic import BaseModel

from snngine_v4.utils.containers.configurable_dict import \
    DefaultDictContainerConfig
from snngine_v4.utils.containers.mappings import MappedDict, Object2KeyMap
from snngine_v4.utils.object_builder.object_builder import ModelObjectBuilder


class BuilderDict(MappedDict, ModelObjectBuilder):

    def __init__(
        self, initdict_or_model=None,
        object2key_map=None,
        container_conf: DefaultDictContainerConfig | None = None
    ):
        if ((container_conf is None)
                and (self.CONTAINER_CONFIG_CLASS == DefaultDictContainerConfig)):

            allowed_types = [NoneType]
            allowed_types += list(self.BUILDER_OBJECT_CLASS_MAP.values())
            allowed_types += list(self.BUILDER_OBJECT_SUPERCLASS_MAP.values())
            if self.BUILDER_DEFAULT_OBJECT_CLASS is not None:
                allowed_types.append(self.BUILDER_DEFAULT_OBJECT_CLASS)
            allowed_types = tuple(allowed_types)
            container_conf = DefaultDictContainerConfig(
                allowed_types=allowed_types
            )

        if object2key_map is None:
            object2key_map = Object2KeyMap()

        super().__init__(object2key_map=object2key_map,
                         container_conf=container_conf)
        if initdict_or_model is not None:
            self.update(initdict_or_model)

    def add_from_model(self: dict[str, object] | BuilderDict,
                       key, model, **kwargs):
        build_result = self.cls_build(model=model, **kwargs)
        item = build_result.built
        model = build_result.model
        self.object2key_map[model] = key
        self[key] = item

    def __getitem__(self, key):
        if isinstance(key, BaseModel) and (self.object2key_map is not None):
            return self.data[self.object2key_map[key]]
        return self.data[key]

    def update(self, m, **kwargs) -> None:

        if isinstance(m, BaseModel):
            built_container = self.cls_build_container(
                model_container=m)
            super().update(built_container.object_dict)
            self.object2key_map.update(built_container.object2key_map)
        else:
            super().update(m, **kwargs)
