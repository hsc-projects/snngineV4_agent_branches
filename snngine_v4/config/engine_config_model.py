from __future__ import annotations

from typing import ClassVar, Type

from snngine_v4.config.graphics.app_config_model import EngineAppConfig
from snngine_v4.utils.settings.settings_keywords import BaseSettingsSlots
from snngine_v4.utils.settings.xml_settings_base import (
    default_xml_model_config_dict,
    XMLSettingsConfigDict,
)
from snngine_v4.utils.settings.xml_settings import (
    XMLSettingsModel,
)

from snngine_v4.config.construction \
    .construction import NetworkConstructionSettings
from snngine_v4.config.graphics.opengl_config import OpenGLConfig
from snngine_v4.config.graphics.scene_config import SceneConfig


class EngineConfig(XMLSettingsModel):

    class Slots:
        CONSTRUCTION: ClassVar[str] = 'construction'

    model_config: ClassVar[XMLSettingsConfigDict] = (
        # default_xml_model_config_dict('.snngine/settings.xml'))
        default_xml_model_config_dict(
            f".snngine/{BaseSettingsSlots.SUB_SETTINGS_FILE_NAME_PATTERN}.xml"))

    app: EngineAppConfig

    open_gl: OpenGLConfig

    scenes: SceneConfig

    construction: NetworkConstructionSettings
