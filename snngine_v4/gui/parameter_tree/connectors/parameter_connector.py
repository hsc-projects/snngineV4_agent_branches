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
                        container=None, **kwargs):
        if container is None:
            container = cls.make_container()
        for model, obj in mapping.pairs():
            container[model] = (
                cls.connect_object(model=model, obj=obj,
                                   signal_register=signal_register,  **kwargs))
        return container

    @classmethod
    def connect_object(cls, model, obj,
                       signal_register: ExtendedModelSignalsRegister,
                       **kwargs):
        raise NotImplementedError

    @classmethod
    def cls_connect_tree(cls, tree: EngineParameterTree,
                         mapping,
                         container=None, **kwargs):
        if container is None:
            container = cls.make_container()

        return cls.cls_connect_map(
            mapping=mapping,
            signal_register=tree.signal_register,
            container=container, **kwargs
        )

    @classmethod
    def make_container(cls):
        return Model2ObjectMap(container_conf=cls.cls_make_container_conf())
