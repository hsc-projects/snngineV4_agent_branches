from __future__ import annotations

from pydantic import Field

from snngine_v4.utils.settings.xml_settings import (
    XMLSettingsContainerModel,
    XMLSettingsModel,
)


class CompoundVisualNodeConfig(XMLSettingsContainerModel):
    # EXTRA_CLASSES: ClassVar[Type[XMLSettingsModel]] = [VispyViewBoxConfig]

    initialization: XMLSettingsModel
    visuals: list[XMLSettingsModel] | None = None


class SubVisualsConfig(XMLSettingsModel):
    sub_visuals: list[XMLSettingsModel] = Field(default_factory=list)
