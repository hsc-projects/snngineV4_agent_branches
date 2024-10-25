from copy import deepcopy
from typing import ClassVar, Type

from pydantic import BaseModel

from snngine_v4.config.construction import EngineConstructionConfig
from snngine_v4.geometry.grid.finite_grid import FiniteGrid
from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.utils.containers.mappings import Int2ObjectMapConfig
from snngine_v4.utils.field_utils import model_keys

from snngine_v4.utils.object_builder.object_builder_dict import BuilderDict
from snngine_v4.utils.settings.settings_keywords import BaseModelSlots
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


class NetworkManager(BuilderDict):

    class ContainerConfigClass(Int2ObjectMapConfig):
        b_clear_allowed: bool = True

    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        FiniteGridConfig: FiniteGrid
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

    def update(self, m=None, **kwargs) -> None:
        if isinstance(m, BaseModel):
            self.container_model = self.container_model_class(
                **deepcopy(m).model_dump())
            model = self.container_model
            keys = model_keys(model, exclude=BaseModelSlots.CLASS__NAME)
            build = self.cls_build_container(model_container=model)
            m_ = build.object_dict
            super().update(m_, **kwargs)
            for k in keys:
                v = getattr(model, k)
                if v not in self:
                    if isinstance(v, (list, tuple)):
                        if not all([(x in self) for x in v]):
                            raise AssertionError
                    else:
                        raise AssertionError

        else:
            super().update(m, **kwargs)

        return
