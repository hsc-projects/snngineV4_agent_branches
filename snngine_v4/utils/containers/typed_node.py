from __future__ import annotations

import warnings
from collections import UserList
from copy import copy
from enum import IntEnum
from functools import cached_property
from typing import Type

from snngine_v4.utils.containers.configurable_list import (
    ConfigurableList,
)
from snngine_v4.utils.core_utils import get_intenum_member


class TreeDir(IntEnum):
    ASCENDING = 0
    DESCENDING = 1


class TreeNode:

    container_class: Type[list] = list
    cls_max_search_depth: int = 100

    def __init__(self, parent_node: TreeNode = None,
                 children_nodes: list[TreeNode] | None = None):

        self._parent_node: TreeNode | None = None
        self._children_nodes: list[TreeNode] | ConfigurableList | None = (
            self.make_node_container(children_nodes))

        self.parent_node = parent_node

    def __iter__(self):
        return iter(self._children_nodes)

    def __repr__(self):
        return f'{self.__class__.__name__}({self._parent_node})'

    def __contains__(self, item):
        return item in self._children_nodes

    def add_children_node(self, node: TreeNode):
        self._children_nodes.append(node)
        if node.parent_node is not self:
            node.parent_node = self
        return node

    @property
    def b_has_children_nodes(self):
        return len(self._children_nodes) > 0

    @property
    def b_has_parent_node(self):
        return self._parent_node is not None

    def check_depth(self, depth):
        if depth == self.max_search_depth_warning:
            warnings.warn(
                f'Warning: search depth exceeds '
                f'{self.max_search_depth_warning}.',
                stacklevel=2)
        if depth >= self.max_search_depth:
            raise RuntimeError

    @property
    def children_nodes(self):
        return self._children_nodes

    @children_nodes.setter
    def children_nodes(self, new_children_nodes):
        self._children_nodes.clear()
        self._children_nodes.extend(new_children_nodes)
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
                      ) -> list[TreeNode]:
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
            self.check_depth(i)
            i += 1
        return node_list

    def make_node_container(self, *nodes, **kwargs):
        if len(nodes) == 1 and nodes[0] is None:
            nodes = ()
        return self.container_class(*nodes, **kwargs)

    @cached_property
    def max_search_depth(self):
        return max(self.cls_max_search_depth, 2)

    @cached_property
    def max_search_depth_warning(self):
        return self.max_search_depth // 2

    @property
    def node_generation(self):
        generation = 0
        node = self
        i = 0
        while node.b_has_parent_node:
            generation += 1
            node = node.parent_node
            self.check_depth(i)
            i += 1

        return generation

    def node_rank(self):
        if self._parent_node is not None:
            return self._parent_node.children_nodes.index(self)
        else:
            return None

    @property
    def parent_node(self) -> TreeNode:
        return self._parent_node

    @parent_node.setter
    def parent_node(self, parent_node):
        """
           Set the parent node of the current node.
        """
        # if parent_node is not None:
        #     parent_node = self.validate_item(parent_node)
        # if self.b_has_parent_node and (parent_node != self._parent_node):
        #     if self._container_conf.b_freeze_parent is True:
        #         raise AttributeError(
        #             'Cannot change parent node of frozen node.')
        #     self._parent_node = parent_node
        # elif (not self.b_has_parent_node) and (parent_node is not None):
        #     self._parent_node = parent_node
        if self.b_has_parent_node:
            self.parent_node.remove_child_node(self)
        self._parent_node = parent_node
        if (parent_node is not None) and (self not in parent_node):
            parent_node.add_children_node(self)


    def remove_child_node(self, node):
        node.parent_node = None
        self._children_nodes.remove(node)
        return node

    def remove_child_nodes(self, *nodes):
        if len(nodes) == 0:
            nodes = self.children_nodes
        for n in nodes:
            self.remove_child_node(n)

    def root_node(self):
        if not self.b_has_parent_node:
            return self
        else:
            return self._parent_node.root_node()

    @property
    def sibling_nodes(self):
        if self.b_has_parent_node:
            siblings = copy(self._parent_node.children_nodes)
            if isinstance(siblings, UserList):
                siblings = siblings.data
            siblings.remove(self)
            return siblings
        else:
            return []
