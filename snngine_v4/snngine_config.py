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
from snngine_v4.config.construction import EngineConstructionConfig


class EngineConfig(XMLSettingsModel):

    class Slots:
        CONSTRUCTION: ClassVar[str] = 'construction'
        SCENES: ClassVar[str] = 'scenes'

    model_config: ClassVar[XMLSettingsConfigDict] = (
        default_xml_model_config_dict(
            xml_file=f".snngine"
                     f"/{BaseSettingsSlots.SUB_SETTINGS_FILE_NAME_PATTERN}.xml"))

    app: EngineAppSettings
    open_gl: OpenGLSettings
    scenes: SceneSettings

    construction: EngineConstructionConfig

    @classmethod
    def _xml_file_paths(cls):
        # noinspection PyTypedDict
        fn = cls.model_config[BaseSettingsSlots.XML_FILE]

        sub_setting_pat = BaseSettingsSlots.SUB_SETTINGS_FILE_NAME_PATTERN
        if (fn is not None) and (sub_setting_pat in fn):
            xml_files = []
            for k in cls.model_fields:
                if k not in [cls.Slots.CONSTRUCTION, cls.Slots.SCENES]:
                    xml_files.append(fn.replace(sub_setting_pat, k))
        else:
            xml_files = fn
        return xml_files

    # def _export_submodels(self, conv, fn, sub_setting_pattern):
    #     for k in self.model_fields:
    #         if k != self.Slots.CONSTRUCTION:
    #             sub_model = getattr(self, k)
    #             conv.to_xml_file(
    #                 data={k: sub_model.model_dump(mode='json')},
    #                 fn=fn.replace(sub_setting_pattern, k))
