from typing import ClassVar

from snngine_v4.nn.config_models.nn_builder_config import \
    NetworkConstructionConfig
from snngine_v4.utils.settings.ui_parameter_options import FrozenParamOpts
from snngine_v4.utils.settings.xml_settings import (
    XMLSettingsContainerModel,
)


class EngineConstructionConfig(XMLSettingsContainerModel):

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        expanded=True,
        c_auto_collapse=True,
        c_collapsed_children=False,
    )

    network: NetworkConstructionConfig | None = None
