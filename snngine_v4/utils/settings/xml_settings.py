from __future__ import annotations

from typing import Any, ClassVar

from pydantic_settings import BaseSettings

from snngine_v4.utils.settings.config_model_base import (
    # BaseModelMixin,
    ConfigModelMixin, ModelDumpTypes,
)
from snngine_v4.utils.settings.ui_parameter_options import FrozenParamOpts
from snngine_v4.utils.settings.xml_converter.xml_settings_source import (
    default_xml_model_config_dict, XMLConfigSettingsSource,
    XMLSettingsConfigDict,
)


class XMLSettingsModel(BaseSettings, ConfigModelMixin):

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        expanded=True,
        c_auto_collapse=True,
        c_collapsed_children=True,
    )

    model_config: ClassVar[XMLSettingsConfigDict] = (
        default_xml_model_config_dict(xml_file=None))

    def model_dump(self, mode: str | ModelDumpTypes = 'python',
                   include=None, round_trip=False,
                   **kwargs):
        return self._model_dump(
            mode=mode, include=include, round_trip=round_trip,
            **kwargs)

    @classmethod
    def settings_customise_sources(
            cls, settings_cls: type[BaseSettings],
            init_settings, env_settings,
            dotenv_settings, file_secret_settings):
        xml_files = cls._xml_file_paths()
        return (
            init_settings,
            XMLConfigSettingsSource(settings_cls, xml_files=xml_files),
        )

    # noinspection PyNestedDecorators
    # @classmethod
    # def _validate_model_after(cls, data: Any) -> Any:
    def model_post_init(self, __context):
        super().model_post_init(__context)
        self.post_init_process_extra_classes()

    @classmethod
    def validate_model_item(cls, data, key, field_info=None) -> Any:
        if not super().validate_model_iterable_item(
                data, key, field_info=field_info):
            super().validate_model_item(
                data=data, key=key, field_info=field_info)


class XMLSettingsContainerModel(XMLSettingsModel):

    model_config: ClassVar[XMLSettingsConfigDict] = (
        default_xml_model_config_dict(extra='allow'))

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        expanded=True,
        c_auto_collapse=True,
        c_collapsed_children=True,
    )

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)
