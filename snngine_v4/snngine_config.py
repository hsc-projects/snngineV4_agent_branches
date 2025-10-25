from __future__ import annotations

import os.path
from typing import ClassVar

from pydantic import Field

from snngine_v4.nn.config_models.spnn_config import \
    SpatialNetworkConfig
from snngine_v4.nn.config_models.reservoir.nn_reservoir_config \
    import NetworkReservoirConfig
from snngine_v4.utils.settings.settings_keywords import BaseSettingsSlots
from snngine_v4.utils.settings.xml_converter.xml_settings_source import (
    default_xml_model_config_dict,
    XMLSettingsConfigDict,
)
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel

from snngine_v4.config.app import EngineAppSettings
from snngine_v4.config.devices import DeviceSettings
from snngine_v4.config.scenes import SceneSettings
from snngine_v4.config.template import (
    EngineConstructionConfig,
)


class EngineConfig(XMLSettingsModel):

    class Slots:
        TEMPLATE: ClassVar[str] = 'template'
        SCENES: ClassVar[str] = 'scenes'
        BUILT: ClassVar[str] = 'built'

    model_config: ClassVar[XMLSettingsConfigDict] = (
        default_xml_model_config_dict(
            xml_file=f".snngine/"
                     f"{BaseSettingsSlots.SUB_SETTINGS_FILE_NAME_PATTERN}"
                     f"{BaseSettingsSlots.XML_FILE_ENDING}"))

    app: EngineAppSettings

    devices: DeviceSettings

    scenes: SceneSettings
    template: EngineConstructionConfig = Field(
        default_factory=lambda:  EngineConstructionConfig(
            network=SpatialNetworkConfig(
                device=1,
                elements=[
                    # EngineElementConfig(),
                    NetworkReservoirConfig(),
                    # EngineElementConfig(),
                ])))

    built: EngineConstructionConfig

    def settings_directory(self) -> str | None:
        # noinspection PyTypedDict
        fn = self.model_config[BaseSettingsSlots.XML_FILE]
        dn = os.path.dirname(fn)
        return dn

    @classmethod
    def _xml_file_paths(cls):
        # noinspection PyTypedDict
        fn = cls.model_config[BaseSettingsSlots.XML_FILE]

        sub_setting_pat = BaseSettingsSlots.SUB_SETTINGS_FILE_NAME_PATTERN
        if (fn is not None) and (sub_setting_pat in fn):
            xml_files = []
            for k in cls.model_fields:
                if k not in [
                    # cls.Slots.CONSTR,
                    cls.Slots.SCENES
                ]:
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


if __name__ == '__main__':
    from pprint import pprint
    pprint(EngineConfig().model_dump())
