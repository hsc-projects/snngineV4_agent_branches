from __future__ import annotations

import warnings
from collections import UserList
from enum import IntEnum
from typing import ClassVar, Type


from snngine_v4.utils.containers.configurable_container import (
    ConfigurableContainerBase, ContainerConfig,
)
from snngine_v4.utils.containers.configurable_list import (
    ConfigurableList,
    ConfigurableListConfig,
)
from snngine_v4.utils.core_utils import get_intenum_member


class TreeDir(IntEnum):
    ASCENDING = 0
    DESCENDING = 1


class TypedTreeNodeConfig(ContainerConfig, frozen=True):

    b_freeze_parent: bool = False
    search_warning_depth: int | None = 100
    children_container_config: ConfigurableListConfig | None = None

    def children_container_class(
            self, **kwargs) -> Type[list] | Type[ConfigurableList]:
        if self.children_container_config is None:
            if self.allowed_types is None:
                return list
            else:
                return ConfigurableList.class_from_type(
                    type_=self.allowed_types, **kwargs)
        else:
            kwargs_ = self.children_container_config.model_dump(mode='python')
            kwargs_.update(kwargs)
            return ConfigurableList.class_from_type(**kwargs_)


class TypedTreeNode(ConfigurableContainerBase):

    ContainerConfigClass: ClassVar[Type[TypedTreeNodeConfig]] = (
        TypedTreeNodeConfig)

    def __init__(self, parent_node: TypedTreeNode = None,
                 children_nodes: list[TypedTreeNode] | None = None,
                 container_conf: TypedTreeNodeConfig = None,
                 node_object=None,
                 ):
        self._container_conf: TypedTreeNodeConfig | None = None
        self._node_object = node_object
        if container_conf is None:
            container_conf = self.ContainerConfigClass(
                allowed_types=self.__class__)
        super().__init__(container_conf=container_conf)

        self._parent_node: TypedTreeNode | None = None
        self._children_nodes: list[TypedTreeNode] | ConfigurableList | None = \
            None

        self.parent_node = parent_node
        self.children_nodes = self.make_node_list(children_nodes)

    def __iter__(self):
        return iter(self._children_nodes)

    def __repr__(self):
        return f'{self.__class__.__name__}({self._parent_node})'

    def __contains__(self, item):
        return item in self._children_nodes

    def add_children_node(self, node: TypedTreeNode):
        self._children_nodes.append(node)
        node.parent_node = self
        return node

    @property
    def b_has_children_nodes(self):
        return len(self._children_nodes) > 0

    @property
    def b_has_parent_node(self):
        return self._parent_node is not None

    @property
    def children_nodes(self):
        return self._children_nodes

    @property
    def children_node_objects(self):
        return [x._node_object for x in self.children_nodes]

    @children_nodes.setter
    def children_nodes(self, new_children_nodes):
        new_children_nodes = self.validate_items(new_children_nodes)
        self._children_nodes = self.validate_items(new_children_nodes)
        for node in new_children_nodes:
            node.parent_node = self

    def descendant_nodes(self):
        # noinspection PyCallingNonCallable
        node_list = []
        for child in self._children_nodes:
            node_list.append(child)
            node_list += child.descendants()
        return node_list

    def lineage_nodes(self, order: TreeDir = TreeDir.DESCENDING
                      ) -> list[TypedTreeNode]:
        order = get_intenum_member(order, TreeDir)
        # noinspection PyCallingNonCallable
        node_list = [self]
        node = self
        i = 0
        while node.parent_node is not None:
            if order == TreeDir.ASCENDING:
                node_list.append(node.parent_node)
            elif order == TreeDir.DESCENDING:
                node_list.insert(0, node.parent_node)
            else:
                raise NotImplementedError
            node = node.parent_node
            if i == self._container_conf.search_warning_depth:
                self.warning_search_depth(i)
            i += 1
        return node_list

    def make_node_list(self, nodes=None, **kwargs):
        container_class = self._container_conf.children_container_class(
            **kwargs)
        if nodes is None:
            return container_class()
        return container_class(nodes)

    @property
    def node_generation(self):
        generation = 0
        node = self
        i = 0
        while node.b_has_parent_node:
            generation += 1
            node = node.parent_node
            if i >= self._container_conf.sea:
                self.warning_search_depth(i)
            i += 1

        return generation

    @property
    def node_object(self):
        return self._node_object

    def node_rank(self):
        if self._parent_node is not None:
            return self._parent_node.children_nodes.index(self)
        else:
            return None

    @property
    def parent_node(self):
        return self._parent_node

    @parent_node.setter
    def parent_node(self, parent_node):
        """
           Set the parent node of the current node.
        """
        if parent_node is not None:
            parent_node = self.validate_item(parent_node)
        if self.b_has_parent_node and (parent_node != self._parent_node):
            if self._container_conf.b_freeze_parent is True:
                raise AttributeError(
                    'Cannot change parent node of frozen node.')
            self._parent_node = parent_node
        elif (not self.b_has_parent_node) and (parent_node is not None):
            self._parent_node = parent_node
        if (parent_node is not None) and (self not in parent_node):
            parent_node.add_children_node(self)

    def remove_node(self, node):
        self._children_nodes.remove(node)
        node._parent_node = None
        return node

    def root_node(self):
        if not self.b_has_parent_node:
            return self
        else:
            return self._parent_node.root_node()

    @property
    def sibling_nodes(self):
        if self.b_has_parent_node:
            siblings = self._parent_node.children_nodes.data
            if isinstance(siblings, UserList):
                siblings = siblings.data
            siblings.remove(self)
            return siblings
        else:
            return []

    def warning_search_depth(self, i):
        if i >= self._container_conf.search_warning_depth:
            warnings.warn(f'Warning: search depth exceeds '
                          f'{self._container_conf.search_warning_depth}.',
                          stacklevel=2)
        return i + 1
