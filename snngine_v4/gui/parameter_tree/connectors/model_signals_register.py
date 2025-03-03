from __future__ import annotations

from functools import cached_property
from typing import Callable, Type

from pydantic import BaseModel
from pyqtgraph.parametertree.parameterTypes import GroupParameter

from snngine_v4.gui.parameter_tree.connectors.model_parameter_links import \
    ModelParameterLinks
from snngine_v4.utils.containers.mappings import (
    Int2ObjectMapConfig, Model2ObjectMap,
)
from snngine_v4.utils.containers.node_map import (
    ModelTree, NodeTree,
    NodeTreeConfig, Object2NodeTreeMap,
)
from snngine_v4.utils.field_utils import model_keys
from snngine_v4.utils.settings.settings_keywords import BaseModelSlots


class ModelSignalsRegister(Model2ObjectMap):

    class ContainerConfigClass(Int2ObjectMapConfig, frozen=True):
        allowed_types: Type[ModelParameterLinks]
        b_clear_allowed: bool = True

    values: Callable[[], list[ModelParameterLinks]]
    __getitem__: Callable[[BaseModel], ModelParameterLinks]

    def __init__(self, **kwargs):
        self.data: dict[BaseModel, ModelParameterLinks] | None = None
        self.group_map: dict[BaseModel, GroupParameter] | Model2ObjectMap = (
            Model2ObjectMap.from_type(GroupParameter))
        super().__init__(**kwargs)

    def actualize_node_tree_map(
            self, key_model, value_links: ModelParameterLinks = None):
        if key_model not in self.node_tree:
            if value_links.sink.parent() is not None:
                raise AssertionError
            else:
                self.node_tree.add_free_element(key_model)

    def clear(self, b_force: bool = False, b_clear_inv: bool = True):
        for v in self.values():
            v.clear(b_force=self.container_conf.b_clear_allowed or b_force)
        super().clear(b_force=b_force, b_clear_inv=b_clear_inv)
        self.group_map.clear(b_force=True)
        self.node_tree.clear(b_force=True)

    @property
    def connected_models(self):
        return self.refs

    def get_group(self, model):
        res = self[model].sink
        if res != self.group_map[model]:
            raise RuntimeError
        return res

    def get_model(self, group):
        res = self.group_map.inv[group]
        if res != self[res].source:
            raise RuntimeError
        return res

    @cached_property
    def node_tree(self) -> NodeTree:
        return ModelTree(
            container_conf=NodeTreeConfig(b_free_nodes_allowed=True))

    def __setitem__(self, model, value):
        if isinstance(value, GroupParameter):
            value = ModelParameterLinks(
                model=model, group_param=value,
                ext_obj_attr_map=None)
            self.group_map[model] = value.sink
        super().__setitem__(model, value)
        self.actualize_node_tree_map(model, self[model])


class ExtendedModelSignalsRegister(ModelSignalsRegister):

    def __init__(self, node_tree_map=None, **kwargs):
        self.model2model_map = Model2ObjectMap.from_type(BaseModel)
        self.extensions_map = ModelSignalsRegister()
        self.model2nodetree_map: Object2NodeTreeMap | None = (
                node_tree_map or Object2NodeTreeMap())
        super().__init__(**kwargs)

    def actualize_node_tree_map(
            self, key_model, value_links: ModelParameterLinks = None):
        if key_model not in self.model2model_map.values():
            super().actualize_node_tree_map(key_model, value_links)
            if key_model not in self.model2nodetree_map:
                self.model2nodetree_map[key_model] = self.node_tree
        else:
            pass

    def add_linked_model_pars(self, model, group):
        """Add additional parameters for linked model"""

        value = ModelParameterLinks(
            model=model, group_param=group,
            ext_obj_attr_map=self[model][str])
        self.extensions_map.group_map[model] = value.sink

        self.extensions_map[model] = value

        return

    def add_linked_model(self, model0: BaseModel, model1: BaseModel,
                         node_tree=None, group0=None):
        """
        New linked model has been created but not yet additional
        parameters
        """
        self.model2model_map[model0] = model1

        self[model1] = ModelParameterLinks(
            allowed_keys=model_keys(
                model1, exclude=BaseModelSlots.CLASS__NAME),
            model=model1, group_param=group0 or self.get_group(model0))

        if node_tree is None:
            node_tree = ModelTree(root=model1)
        elif model1 not in node_tree:
            raise AssertionError
        self.model2nodetree_map[model1] = node_tree

        keys0 = model_keys(model0, b_include_computed=False)
        for k0 in keys0:
            v0 = getattr(model0, k0)
            if isinstance(v0, BaseModel):
                if hasattr(model1, k0):
                    self.add_linked_model(
                        v0, getattr(model1, k0), node_tree=node_tree,)
        return node_tree

    def clear(self, b_force: bool = False, b_clear_inv: bool = True):
        for v in self.values():
            v.clear(b_force=self.container_conf.b_clear_allowed or b_force)
        super().clear(b_force=b_force, b_clear_inv=b_clear_inv)
        self.model2model_map.clear(b_force=True)
        self.model2nodetree_map.clear(b_force=True)
        self.extensions_map.clear(b_force=True)

    def get_group(self, model):
        try:
            return super().get_group(model)
        except KeyError:
            return self.extensions_map.get_group(model)

    def get_model(self, group):
        try:
            return super().get_model(group)
        except KeyError:
            return self.extensions_map.get_model(group)
