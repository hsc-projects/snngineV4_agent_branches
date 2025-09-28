from pyqtgraph.parametertree.parameterTypes import GroupParameter

from snngine_v4.gui.parameter_trees.connectors.model_signals_register import \
    ExtendedModelSignalsRegister
from snngine_v4.gui.parameter_trees.connectors.parameter_connector import \
    ParameterConnector
from snngine_v4.gui.parameter_trees.engine_parameter_tree import \
    EngineParameterTree
from snngine_v4.gui.parameters import (
    TensorDictParameter,
    TensorParameter,
)
from snngine_v4.construction.engine_element import EngineElement
from snngine_v4.construction.nn_builder import NetworkBuilder
from snngine_v4.nn.spnn import SpatialNetwork
from snngine_v4.utils.containers.mappings import Object2ObjectMap


class TensorConnector(ParameterConnector):
    # noinspection PyUnreachableCode
    @classmethod
    def connect_object(cls, model: EngineElement,
                       obj: GroupParameter,
                       signal_register: ExtendedModelSignalsRegister,
                       **kwargs):
        res = {}
        for c in obj.childs:
            if isinstance(c, (TensorParameter, TensorDictParameter)):
                name = c.name()
                tensor = model.tensor_dict[c.name()]
                if isinstance(c, TensorParameter):
                    c.tensor = tensor
                elif isinstance(c, TensorDictParameter):
                    c: TensorDictParameter
                    c.set_tensor(tensor)
                else:
                    raise TypeError(f"type(c) == {type(c)}")
                res[name] = tensor
        return res

    @classmethod
    def cls_connect_tree(cls, tree: EngineParameterTree,
                         network_manager: NetworkBuilder,
                         container=None,
                         **kwargs):
        sr = tree.signal_register
        network_model = network_manager.container_model.network
        network: SpatialNetwork = network_manager[network_model]
        mapping = cls.make_container()

        def expand_mapping(elt: EngineElement):
            for m in elt.children_models:
                mapping[elt[m]] = sr.get_group(m)
                expand_mapping(elt[m])
        expand_mapping(network)
        return super().cls_connect_tree(tree, mapping, container, **kwargs)

    @classmethod
    def make_container(cls):
        return Object2ObjectMap(container_conf=cls.cls_make_container_conf())
