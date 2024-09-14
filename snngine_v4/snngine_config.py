from __future__ import annotations

from typing import ClassVar

from snngine_v4.utils.settings.settings_keywords import BaseSettingsSlots
from snngine_v4.utils.settings.xml_settings_base import (
    default_xml_model_config_dict,
    XMLSettingsConfigDict,
)
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel

from snngine_v4.config.app import EngineAppSettings
from snngine_v4.config.opengl import OpenGLSettings
from snngine_v4.config.scenes import SceneSettings
from snngine_v4.config.construction import NetworkConstructionConfig


class EngineConfig(XMLSettingsModel):

    class Slots:
        CONSTRUCTION: ClassVar[str] = 'construction'

    model_config: ClassVar[XMLSettingsConfigDict] = (
        default_xml_model_config_dict(
            f".snngine/{BaseSettingsSlots.SUB_SETTINGS_FILE_NAME_PATTERN}.xml"))

    app: EngineAppSettings
    open_gl: OpenGLSettings
    scenes: SceneSettings

    construction: NetworkConstructionConfig
