from copy import deepcopy
from typing import ClassVar, Type

from pydantic import BaseModel


from snngine_v4.config.construction import EngineConstructionConfig
from snngine_v4.nn.construction.config_models.spnn_config import \
    SpatialNetworkConfig
from snngine_v4.nn.spnn import SpatialNetwork
from snngine_v4.utils.containers.mappings import ObjectMapConfig
from snngine_v4.utils.field_utils import model_keys
from snngine_v4.utils.object_builder.object_builder import \
    ObjectInitializationType

from snngine_v4.utils.object_builder.object_builder_dict import BuilderDict
from snngine_v4.utils.settings.settings_keywords import BaseModelSlots


class NetworkBuilder(BuilderDict):

    class ContainerConfigClass(ObjectMapConfig):
        b_clear_allowed: bool = True

    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        # FiniteGridConfig: FiniteGrid,
        SpatialNetworkConfig: SpatialNetwork
    }

    OBJECT_INIT_SUPER_TYPES = {
        SpatialNetworkConfig: ObjectInitializationType.MODEL_AND_KWARGS
    }

    def __init__(
        self, container_model: EngineConstructionConfig,
        build_model: EngineConstructionConfig = None, **kwargs
    ):

        super().__init__(**kwargs)
        self.container_model_class: Type[EngineConstructionConfig] | None = None
        self.container_model = container_model

        if build_model is not None:
            self.update(build_model)

    def clear(self, b_force: bool = False, b_clear_inv: bool = True):
        super().clear(b_force=b_force, b_clear_inv=b_clear_inv)
        self.container_model_class = self.container_model.__class__
        del self.container_model

    def build(self, m=None, **kwargs):
        super().build(**kwargs)
        if isinstance(m, BaseModel):
            m2 = deepcopy(m)
            m3 = m2.model_dump()
            self.container_model = self.container_model_class(**m3)
            super().update(self.container_model)
            keys = model_keys(self.container_model,
                              exclude=BaseModelSlots.CLASS__NAME)
            for k in keys:
                v = getattr(self.container_model, k)
                if v not in self:
                    if isinstance(v, (list, tuple)):
                        if not all([(x in self) for x in v]):
                            raise AssertionError
                    else:
                        raise AssertionError
        elif m is not None:
            self.update(m)
        return
