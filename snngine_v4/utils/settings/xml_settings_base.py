from __future__ import annotations

import os
from pathlib import Path
from types import NoneType
from typing import Any, ClassVar, get_origin, Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import (
    ConfigFileSourceMixin, InitSettingsSource,
    PathType,
)

from snngine_v4.utils.core_utils import get_intenum_member
from snngine_v4.utils.field_utils import (
    b_annotation_includes_type,
    b_is_enum_annotation, b_is_intenum_annotation,
    extract_basemodel_from_annotation,
    b_annotation_includes_basemodel, b_field_has_default,
)
from snngine_v4.utils.settings.settings_keywords import (
    BaseSettingsSlots,
)


class XMLSettingsConfigDict(SettingsConfigDict, total=False):
    xml_file: PathType | None


def default_xml_model_config_dict(
    xml_file: str | None = None,
    extra: Literal['allow', 'ignore', 'forbid'] | None = 'forbid',
    use_enum_values=False,
):
    return XMLSettingsConfigDict(
        # protected_namespaces=('model_', ParamOpts.UI_OPTIONS_KEYWORD),
        strict=True,
        use_enum_values=use_enum_values,
        validate_default=True,
        validate_assignment=True,
        extra=extra,
        arbitrary_types_allowed=False,
        xml_file=xml_file)


class XMLConfigSettingsSource(InitSettingsSource, ConfigFileSourceMixin):
    """
    A source class that loads variables from a JSON file
    """

    # noinspection PyTypedDict
    def __init__(
        self,
        settings_cls: type[XMLSettingsModelBase],
        xml_files: PathType | str | None = '',
    ):
        default_path: PathType = Path('')
        if xml_files == '':
            xml_files = default_path

        self.xml_file_paths = (
            xml_files
            if xml_files != default_path
            else settings_cls.model_config.get(BaseSettingsSlots.XML_FILE)
        )

        self.settings_cls = settings_cls
        xml_data = self._read_files(self.xml_file_paths)
        self.xml_data = xml_data
        super().__init__(settings_cls, self.xml_data)

    def _read_files(self, files: PathType | None) -> dict[str, Any]:
        if files is None:
            return {}
        if isinstance(files, (str, os.PathLike)):
            files = [files]
        vars: dict[str, Any] = {}
        for file in files:
            file_path = Path(file).expanduser()
            if file_path.is_file():
                new_vals = self._read_file(file_path)
                for k in new_vals:
                    if k in vars:
                        raise KeyError(k)
                vars.update(new_vals)
        return vars

    def _read_file(self, file_path: Path) -> dict[str, Any]:
        from snngine_v4.utils.settings.xml_converter import XMLConverter
        # noinspection PyTypeChecker
        xml_model = self.settings_cls.xml_model
        if xml_model is None:
            from snngine_v4.utils.settings.xml_converter_options import \
                XMLConverterOptions
            xml_model = XMLConverterOptions()
            self.settings_cls.xml_model = xml_model

        conv = XMLConverter(xml_model)

        res = conv.dict_from_xml(str(file_path))
        return res


class XMLSettingsModelBase(BaseSettings):

    xml_model: ClassVar[XMLSettingsModelBase] = None

    model_config: ClassVar[XMLSettingsConfigDict] = (
        default_xml_model_config_dict(xml_file=None))

    parameter_ui_opts: ClassVar[dict | None] = None

    def load(self):
        raise NotImplementedError

    def _export_submodels(self, conv, fn, sub_setting_pattern):
        for k in self.model_fields:
            sub_model = getattr(self, k)
            conv.to_xml_file(
                data={k: sub_model.model_dump(mode='json')},
                fn=fn.replace(sub_setting_pattern, k))

    def export(self, fn: str = None, mode='xml'):

        if mode != 'xml':
            raise NotImplementedError

        from snngine_v4.utils.settings.xml_converter import XMLConverter

        xml_model = self.xml_model
        if xml_model is None:
            from snngine_v4.utils.settings.xml_converter_options import \
                XMLConverterOptions
            xml_model = XMLConverterOptions()

        if (fn is None) or isinstance(fn, bool):
            # noinspection PyTypedDict
            fn = self.model_config[BaseSettingsSlots.XML_FILE]

        conv = XMLConverter(xml_model)

        sub_setting_pat = BaseSettingsSlots.SUB_SETTINGS_FILE_NAME_PATTERN
        if sub_setting_pat in fn:
            self._export_submodels(conv, fn, sub_setting_pat)
        else:
            conv.to_xml_file(data=self, fn=fn)

    @classmethod
    def settings_customise_sources(
            cls, settings_cls: type[XMLSettingsModelBase],
            init_settings, env_settings,
            dotenv_settings, file_secret_settings):
        xml_files = cls._xml_file_paths()
        return (
            init_settings,
            XMLConfigSettingsSource(settings_cls, xml_files=xml_files),
        )

    # noinspection PyNestedDecorators
    @model_validator(mode='before')
    @classmethod
    def validate_model_before(cls, data: Any) -> Any:
        return cls._validate_model_before(data)

    @classmethod
    def _validate_model_before(cls, data: Any) -> Any:
        if isinstance(data, dict):

            for k in cls.model_computed_fields:
                data.pop(k, None)

            for k, field_info in cls.model_fields.items():

                if k == 'method':
                    pass

                ann = field_info.annotation
                if k not in data:
                    if not b_field_has_default(field_info):
                        if b_annotation_includes_type(ann, type_=NoneType):
                            data[k] = None
                        elif b_annotation_includes_basemodel(ann):
                            if b_annotation_includes_type(ann=ann, type_=dict):
                                data[k] = {}
                            else:
                                data[k] = extract_basemodel_from_annotation(ann)()

                elif (isinstance(data[k], list) and
                      b_annotation_includes_type(ann, type_=tuple)):
                    data[k] = tuple(data[k])
                elif (isinstance(data[k], (int, str))
                      and (b_is_intenum_annotation(ann, True))):
                    data[k] = get_intenum_member(data[k], ann)
                elif (isinstance(data[k], str)
                      and (b_is_enum_annotation(ann, True))):
                    data[k] = get_intenum_member(data[k], ann)

        return data

    @classmethod
    def _xml_file_paths(cls):
        # noinspection PyTypedDict
        fn = cls.model_config[BaseSettingsSlots.XML_FILE]

        sub_setting_pat = BaseSettingsSlots.SUB_SETTINGS_FILE_NAME_PATTERN
        if (fn is not None) and (sub_setting_pat in fn):
            xml_files = []
            for k in cls.model_fields:
                xml_files.append(fn.replace(sub_setting_pat, k))
        else:
            xml_files = fn
        return xml_files
