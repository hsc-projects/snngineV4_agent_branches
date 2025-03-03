from __future__ import annotations

from pydantic import Field

from snngine_v4.utils.settings.config_model import (
    ConfigContainerModel,
    ConfigModel,
)


class CompoundVisualNodeConfig(ConfigContainerModel):
    # EXTRA_CLASSES: ClassVar[Type[XMLSettingsModel]] = [VispyViewBoxConfig]

    initialization: ConfigModel
    visuals: list[ConfigModel] | None = None


class SubVisualsConfig(ConfigModel):
    sub_visuals: list[ConfigModel] = Field(default_factory=list)
