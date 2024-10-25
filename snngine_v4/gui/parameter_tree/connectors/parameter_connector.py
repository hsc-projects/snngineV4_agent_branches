from snngine_v4.gui.parameter_tree.connectors.model_signals_register import \
    ExtendedModelSignalsRegister
from snngine_v4.gui.parameter_tree.engine_parameter_tree import \
    EngineParameterTree
from snngine_v4.utils.containers.mappings import (
    Model2ObjectMap,
    Object2ObjectMap,
)


class ParameterConnector(Model2ObjectMap):

    def connect_tree(self, **kwargs):
        return self.cls_connect_tree(container=self, **kwargs)

    def connect_map(self, **kwargs):
        return self.cls_connect_map(container=self, **kwargs)

    @classmethod
    def cls_connect_map(cls, mapping: Object2ObjectMap,
                        signal_register: ExtendedModelSignalsRegister,
                        container=None):
        if container is None:
            container = cls.make_container()
        for model, obj in mapping.pairs():
            container[model] = (
                cls.connect_object(model, obj, signal_register))
        return container

    @classmethod
    def connect_object(cls, model, obj,
                       signal_register: ExtendedModelSignalsRegister):
        raise NotImplementedError

    @classmethod
    def cls_connect_tree(cls, tree: EngineParameterTree,
                         mapping,
                         container=None):
        if container is None:
            container = cls.make_container()

        return cls.cls_connect_map(
            mapping=mapping,
            signal_register=tree.signal_register,
            container=container
        )

    @classmethod
    def make_container(cls):
        return Model2ObjectMap(container_conf=cls.cls_make_container_conf())
