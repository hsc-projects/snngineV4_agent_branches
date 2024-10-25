# from __future__ import annotations
#
# import torch
#
# from snngine_v4.visualization.opengl.engine_compound_visual import (
#     EngineCompoundVisualNode,
# )
# from snngine_v4.visualization.opengl.visual_config import (
#     EngineObjectKeys, VispyObjectLocation, VisualEngineObjectConfig,
# )
# from snngine_v4.utils.containers.typed_node import (
#     TreeNode,
#     TypedTreeNodeConfig,
# )
# from snngine_v4.config.settings_model import BaseSettingsModel
#
#
# class CudaObjectConfig(BaseSettingsModel):
#     cuda_attributes_initialized: bool | None = None
#     device: int | None = None
#
#
# class CudaNodeAttribute(TreeNode):
#
#     def __init__(self, node_object: CudaNode,
#                  parent_node: CudaNodeAttribute = None,
#                  children_nodes: list[CudaNodeAttribute] | None = None,
#                  container_conf: TypedTreeNodeConfig = None,):
#         self._node_object: CudaNode | None = None
#         super().__init__(node_object=node_object,
#                          parent_node=parent_node,
#                          children_nodes=children_nodes,
#                          container_conf=container_conf)
#
#
# class CudaNode:
#     def __init__(self, cuda_config: CudaObjectConfig):
#         self._cuda_node: CudaNodeAttribute = CudaNodeAttribute(self)
#         self._cuda_config: CudaObjectConfig = cuda_config
#
#     def make_cuda_node(self):
#         parent_node = None
#         if hasattr(self, EngineObjectKeys.PARENT_NODE_KEY):
#             parent = getattr(self, EngineObjectKeys.PARENT_NODE_KEY)
#             if isinstance(parent, CudaNode):
#                 parent_node = parent.cuda_node
#
#         children_nodes = []
#         if hasattr(self, EngineObjectKeys.CHILDREN_NODE_KEY):
#             nodes = getattr(self, EngineObjectKeys.CHILDREN_NODE_KEY)
#             for node in nodes:
#                 if isinstance(node, CudaNode):
#                     children_nodes.append(node.cuda_node)
#
#         return CudaNodeAttribute(self, parent_node=parent_node,
#                                  children_nodes=children_nodes)
#
#     @property
#     def cuda_children(self):
#         return self._cuda_node.children_nodes
#
#     @property
#     def cuda_config(self):
#         return self._cuda_config
#
#     @property
#     def cuda_node(self):
#         return self._cuda_node
#
#     def init_cuda_attributes(self, device: torch.device | None = None):
#         if self._cuda_config.cuda_attributes_initialized is True:
#             raise RuntimeError('Cuda attributes already initialized')
#         if self._cuda_config.device is None:
#             self._cuda_config.device = device
#         elif device is not None:  # and device != self._cuda_config.device:
#             raise AssertionError('Device attribute already initialized')
#         for x in self.cuda_children:
#             # if x.cuda_config.cuda_attributes_initialized is True:
#             #     continue
#             x.init_cuda_attributes(device)
#         self._inner_init_cuda_attributes()
#         self._cuda_config.cuda_attributes_initialized = True
#
#     def _inner_init_cuda_attributes(self):
#         pass
#
#
# class EngineCompoundVisualCudaNode(EngineCompoundVisualNode, CudaNode):
#
#     def __init__(self: EngineCompoundVisualCudaNode,
#                  subvisuals: list,
#                  cuda_config: CudaObjectConfig = None,
#                  visual_config: VisualEngineObjectConfig = None,
#                  vispy_location: VispyObjectLocation = None,
#                  **kwargs):
#         self._parent: EngineCompoundVisualCudaNode | None = None
#         super().__init__(
#             visual_config=visual_config, vispy_location=vispy_location,
#             subvisuals=subvisuals, **kwargs)
#
#         CudaNode.__init__(self, cuda_config=cuda_config)
