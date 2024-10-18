from typing import get_origin, Type
from snngine_v4.gui.parameter_tree.connectors.object2vispy_object_link import \
    (
    VispyLinks, VispyObject,
)
from snngine_v4.utils.containers.mappings import (
    Int2ObjectMapConfig,
    Model2ObjectMap,
)


class VispySignalsRegister(Model2ObjectMap):

    class ContainerConfigClass(Int2ObjectMapConfig, frozen=True):
        allowed_types: Type[VispyObject]
        b_clear_allowed: bool = True

    def __setitem__(self, model, value):
        if isinstance(value, get_origin(VispyObject)):
            value = VispyLinks(model=model, vispy_obj=value)
        super().__setitem__(model, value)
