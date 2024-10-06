from __future__ import annotations

from functools import cached_property
from typing import Callable, Type

from pydantic import BaseModel
from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import GroupParameter

from snngine_v4.gui.parameter_tree.connectors.model_parameter_links import \
    ModelParameterLinks
from snngine_v4.utils.containers.mappings import (
    Int2ObjectMapConfig, Model2ObjectMap,
)
from snngine_v4.utils.containers.node_map import (
    ModelTree, NodeTree,
    NodeTreeConfig, NodeTreeMap,
)
from snngine_v4.utils.field_utils import model_keys


class ModelSignalRegister(Model2ObjectMap):

    class ContainerConfigClass(Int2ObjectMapConfig, frozen=True):
        allowed_types: Type[ModelParameterLinks]
        b_clear_allowed: bool = True

    values: Callable[[], list[ModelParameterLinks]]
    __getitem__: Callable[[BaseModel], ModelParameterLinks]

    def __init__(self, node_tree_map=None, **kwargs):
        self.data: dict[BaseModel, ModelParameterLinks] | None = None
        self.group_map: dict[BaseModel, GroupParameter] | Model2ObjectMap = (
            Model2ObjectMap.from_type(GroupParameter))
        self.model2model_map = Model2ObjectMap.from_type(BaseModel)
        self.model2nodetree_map: NodeTreeMap | None = (
                node_tree_map or NodeTreeMap())
        super().__init__(**kwargs)

    def actualize_node_tree_map(
            self, key_model, value_links: ModelParameterLinks = None):
        if key_model not in self.model2model_map.values():
            node_tree = self.main_node_tree
            if key_model not in node_tree:
                if value_links.sink.parent() is not None:
                    raise AssertionError
                else:
                    node_tree.add_free_element(key_model)
        else:
            pass
            # raise RuntimeError
            # self.node_tree_map[key_model] = node_tree

    def clear(self, b_force: bool = False, b_clear_inv: bool = True):
        for v in self.values():
            v.clear(b_force=self.container_conf.b_clear_allowed or b_force)
        super().clear(b_force=b_force, b_clear_inv=b_clear_inv)
        self.group_map.clear(b_force=True)

    @property
    def connected_models(self):
        return self.refs

    def __setitem__(self, model, value):
        if isinstance(value, GroupParameter):
            value = ModelParameterLinks(model=model, group_param=value)
        super().__setitem__(model, value)
        self.group_map[model] = self[model].sink
        self.actualize_node_tree_map(model, self[model])

    @cached_property
    def main_node_tree(self) -> NodeTree:
        return ModelTree(
            container_conf=NodeTreeConfig(b_free_nodes_allowed=True))

    def make_model2model_links(self, model0: BaseModel, model1: BaseModel,
                               node_tree=None):
        self.model2model_map[model0] = model1
        self[model1] = ModelParameterLinks(model=model1, sink=self[model0])
        if node_tree is None:
            node_tree = NodeTree(root=model1)
        elif model1 not in NodeTree:
            raise AssertionError
        self.model2nodetree_map[model1] = node_tree

        keys0 = model_keys(model0)
        for k0 in keys0:
            v0 = getattr(model0, k0)
            if isinstance(v0, BaseModel):
                self.make_model2model_links(
                    v0, getattr(model1, k0), node_tree=node_tree)
