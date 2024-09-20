from snngine_v4.gui.parameter_tree.connectors.basemodel_signal_register import \
    ModelSignalRegister
from snngine_v4.utils.containers.mappings import Object2ObjectMap


class ParameterConnector:

    @classmethod
    def connect_map(cls, object2object_map: Object2ObjectMap,
                    signal_register: ModelSignalRegister):
        for model, obj in object2object_map.pairs():
            cls.connect_object(model, obj, signal_register)

    @classmethod
    def connect_object(cls, model, obj,
                       signal_register: ModelSignalRegister):
        raise NotImplementedError
