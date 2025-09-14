from __future__ import annotations

from copy import copy
from functools import cached_property
from types import NoneType
from typing import Type

from pydantic import BaseModel

from snngine_v4.utils.containers.mappings import (
    Model2ObjectMap, ObjectMapConfig,
)
from snngine_v4.utils.containers.node_map import ModelTree
from snngine_v4.utils.core_utils import type_assertion
from snngine_v4.utils.object_builder.object_builder import (
    ContainerBuildResult,
    ModelObjectBuilder,
)


class BuilderDict(Model2ObjectMap, ModelObjectBuilder):

    def __init__(self, model_container=None, build_kwargs=None,
                 node_tree: ModelTree = None,
                 **kwargs):
        self.node_tree: ModelTree = node_tree
        super().__init__(**kwargs)
        if model_container is not None:
            if build_kwargs is None:
                build_kwargs = self.default_build_kwargs
            if build_kwargs is not None:
                build_res = self.cls_build_container(
                    model_container=model_container, **build_kwargs).object_dict
                self.update(build_res)
            else:
                self.update(model_container)

    def add_build(self: dict[BaseModel, object] | BuilderDict,
                  model,
                  b_default_build_kwargs: bool = True,
                  parent_model=None,
                  **kwargs):

        if ((b_default_build_kwargs is True)
                and isinstance(defaults := self.default_build_kwargs, dict)):
            kwargs_ = copy(defaults)
            kwargs_.update(kwargs)
        else:
            kwargs_ = kwargs

        build_result = self.cls_build_obj(model=model, **kwargs_).built
        self[model] = build_result

        if (self.node_tree is not None) and (parent_model is not None):
            self.node_tree.add_element(model, parent=parent_model)

        return build_result

    @cached_property
    def default_build_kwargs(self):
        return None

    @classmethod
    def cls_make_container_conf(
            cls, container_conf=None,
            default_cls: Type[ObjectMapConfig] = None, **kwargs):

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
            container_conf = ObjectMapConfig(
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
