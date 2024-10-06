from typing import Any, Callable, ClassVar, Type

from pydantic import BaseModel

from snngine_v4.utils.containers.configurable_list import (
    ConfigurableList,
    ConfigurableListConfig,
)
from snngine_v4.utils.containers.mappings import (
    Int2ObjectMapConfig,
    Object2ObjectMap,
)
from snngine_v4.utils.containers.typed_node import TreeDir, TreeNode
from snngine_v4.utils.field_utils import model_keys


class NodeTreeConfig(Int2ObjectMapConfig):
    b_get_inv_allowed: bool = True
    allowed_types: Type = TreeNode
    b_freeze_parent: bool = False
    b_free_nodes_allowed: bool = False
    b_root_frozen: bool = True

class FreeElementListConfig(ConfigurableListConfig):
    b_remove_allowed: bool = True


class NodeTree(Object2ObjectMap):

    ContainerConfigClass: ClassVar = NodeTreeConfig
    FreeElementListConfigClass: ClassVar[Type[FreeElementListConfig]] = (
        FreeElementListConfig)

    container_conf: NodeTreeConfig
    _container_conf: NodeTreeConfig
    __getitem__: Callable[[Any], TreeNode]

    def __init__(self, root=None, free_nodes_config=None,
                 container_conf: NodeTreeConfig | None = None):
        super().__init__(container_conf=container_conf)

        self.free_elements = ConfigurableList(
            free_nodes_config or self.FreeElementListConfigClass(
                allowed_types=self.inv.container_conf.allowed_types))

        self._root = None
        if root is not None:
            self.root = root

    def __getitem__(self, key):
        if key is None:
            raise KeyError('None')
        return super().__getitem__(key)

    def __setitem__(self, key, value):
        if value is None:
            value = TreeNode(parent_node=None)
        super().__setitem__(key, value)
        if (value.parent_node is None) and (key is not self._root):
            self.free_elements.append(self.inv[value])

    # noinspection PyPep8Naming
    @property
    def NodeClass(self):
        cls = self.container_conf.allowed_types
        if isinstance(cls, tuple):
            if len(cls) != 1:
                raise TypeError("Node classes must have exactly one class")
            cls = cls[0]
        return cls

    def b_valid_item(self, item):
        return super().b_valid_item(item) and self.b_valid_parent(item)

    def b_valid_parent(self, item: TreeNode):
        if self._root is not None:
            if ((item.parent_node is None)
                    and (not self._container_conf.b_free_nodes_allowed)
                    and (item is not self.root_node)):
                return False
            elif ((item.parent_node is not None)
                  and (item.parent_node not in self.inv)):
                return False
        return True

    def add_element(self, element, parent=None):
        if parent is None:
            parent = self.root
        parent_node = self[parent]
        node = TreeNode(parent_node=parent_node)
        self[element] = node
        return self

    def add_elements(self, *elements, parent=None):
        for e in elements:
            self.add_element(e, parent=parent)
        return self

    def add_free_element(self, element):
        print(element.__class__.__name__, id(element))

        self[element] = None
        return self

    def b_has_children(self, element):
        return self[element].b_has_children_nodes

    def b_has_parent(self, element):
        return self[element].b_has_parent_node

    def b_is_free(self, element):
        res = ((element is not self._root)
                and (element in self)
                and (self[element].parent_node is None))
        if res and element not in self.free_elements:
            raise RuntimeError
        return res

    def children(self, element):
        nodes = self[element].children_nodes
        return [self[x] for x in nodes]

    def descendants(self, element):
        nodes = self[element].descendant_nodes()
        return [self[x] for x in nodes]

    def lineage(self, element, order: TreeDir = TreeDir.DESCENDING
                ) -> list[TreeNode]:
        nodes = self[element].lineage_nodes(order=order)
        return [self[x] for x in nodes]

    def generation(self, element):
        return self[element].node_generation

    def make_node(self, parent):
        return self.NodeClass(parent)

    def parent(self, element):
        if element is self._root:
            raise ValueError("Root Node")
        parent_node = self[element].parent_node
        if parent_node is not None:
            return self[parent_node]

    def pop(self, element):
        node = self[element]
        self.parent(element).remove_child_node(node)
        self[element].remove_child_nodes()
        return super().pop(element)

    def rank(self, element):
        return self[element].node_rank()

    @property
    def root(self):
        return self._root

    @root.setter
    def root(self, value):
        root = self._root
        if root is not None:
            if self._container_conf.b_root_frozen is True:
                raise PermissionError("root already set")

        self[value] = self.make_node(parent=None)
        self._root = value
        if root is not None:
            self.set_parent(root, self._root)

    @property
    def root_node(self):
        return self[self._root]

    def set_parent(self, element, parent):
        """
        Set the parent node of the current node.
        """
        if element is self._root:
            raise PermissionError("cannot set parent of root element")
        child_node = self[element]

        parent_node = self[parent] if parent else None
        if (self.b_has_parent(element)
                and (self._container_conf.b_freeze_parent is True)):
            raise PermissionError("frozen parent node.")
        child_node.parent_node = parent_node
        if (parent_node is not None) and self.b_is_free(element):
            self.free_elements.remove(element)
        self.validate_parent(child_node)
        if parent_node is None:
            self.free_elements.append(child_node)
        return self

    def siblings(self, element):
        nodes = self[element].sibling_nodes
        return [self[x] for x in nodes]

    def _validate_item(self, item: TreeNode):
        return super()._validate_item(item).validate_parent(item)

    def validate_parent(self, item):
        if not self.b_valid_parent(item):
            if self._root is not None:
                if ((item.parent_node is None)
                    and (self._container_conf.b_free_nodes_allowed is False)):
                    raise PermissionError("free nodes are not allowed.")
                elif item.parent_node is not None:
                    if item.parent_node not in self.inv:
                        raise PermissionError("foreign nodes are not allowed.")
        return self


class NodeTreeMapConfig(NodeTreeConfig):
    b_get_inv_allowed: bool = True
    allowed_types: Type = NodeTree
    b_duplicates_allowed: bool = True


class NodeTreeMap(Object2ObjectMap):

    ContainerConfigClass: ClassVar = NodeTreeMapConfig
    __getitem__: Callable[[Any], NodeTree]

    def __init__(self):
        super().__init__()


class ModelTree(NodeTree):
    __getitem__: Callable[[BaseModel], TreeNode]

    def __setitem__(self, model: BaseModel, value, ):
        super().__setitem__(model, value)
        for k in model_keys(model):
            v = getattr(model, k)
            if isinstance(v, BaseModel):
                if (v in self) and self.b_is_free(v):
                    self.set_parent(v, model)
                else:
                    self.add_element(v, parent=model)
