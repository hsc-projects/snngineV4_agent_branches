from __future__ import annotations

import os
from enum import auto, IntEnum
from pathlib import Path
from typing import Any, ClassVar, Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import (
    ConfigFileSourceMixin, InitSettingsSource,
    PathType,
)

from snngine_v4.utils.core_utils import get_intenum_member
from snngine_v4.utils.data.validation.array_io import ArrayDictRW
from snngine_v4.utils.data.deepdish_pack import deepdish
from snngine_v4.utils.field_utils import (
    b_annotation_includes_type,
    b_is_intenum_annotation,
    b_is_optional, extract_basemodel_from_annotation,
    b_annotation_includes_basemodel, b_field_has_default, model_keys,
)
from snngine_v4.utils.settings.settings_keywords import (
    BaseModelSlots, BaseSettingsSlots,
)


class ModelDumpTypes(IntEnum):
    python = 0
    json = auto()
    only_arrays = auto()


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
        vars_: dict[str, Any] = {}
        for file in files:
            file_path = Path(file).expanduser()
            if file_path.is_file():
                new_vals = self._read_file(file_path)
                for k in new_vals:
                    if k in vars_:
                        raise KeyError(k)
                array_path = file.replace(
                    BaseSettingsSlots.XML_FILE_ENDING,
                    BaseSettingsSlots.H5_FILE_ENDING)
                array_file_path = Path(array_path).expanduser()
                if array_file_path.is_file():
                    ArrayDictRW.extract_arrays(array_file_path, dests=[new_vals])
                    pass
                vars_.update(new_vals)

        return vars_

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

    def _export_submodels(self, conv, fn, sub_setting_pattern, **kwargs):
        for k in model_keys(self, exclude=BaseModelSlots.CLASS__NAME):
            sub_model = getattr(self, k)
            fn_ = fn.replace(sub_setting_pattern, k)
            data = {k: sub_model.model_dump(mode='json', **kwargs)}
            conv.to_xml_file(data=data, fn=fn_)

            data = BaseModelSlots.pop_class__name_kw(data)
            array_dct, array_list = ArrayDictRW.extract_arrays(
                data, b_recursive=True, dests=({}, []))
            array_path = fn_.replace(
                BaseSettingsSlots.XML_FILE_ENDING,
                BaseSettingsSlots.H5_FILE_ENDING)
            if len(array_list) > 0:
                deepdish.io.save(array_path, array_dct)
                # a = deepdish.io.load(array_path)
                pass

    def export(self, fn: str = None, mode='xml', round_trip=True, **kwargs):

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
            self._export_submodels(conv, fn, sub_setting_pat,
                                   round_trip=round_trip, **kwargs)
        else:
            conv.to_xml_file(data=self, fn=fn, round_trip=round_trip, **kwargs)

    def model_dump(self, mode: str | ModelDumpTypes = 'python',
                   include=None, round_trip=False,
                   **kwargs):
        if isinstance(mode, (int, ModelDumpTypes)):
            mode = get_intenum_member(mode, ModelDumpTypes).name
        match mode:
            case ModelDumpTypes.only_arrays.name:
                res = {}
                ArrayDictRW.extract_arrays(self, b_recursive=True, dests=[res])
            case _:
                # if round_trip is True:
                #     if include is None:
                #         include = model_keys(self)
                #     include += [{BaseModelSlots.CLASS_NAME_KW: '__all__'}]
                res = super().model_dump(
                    mode=mode,
                    include=include, round_trip=round_trip, **kwargs)
                # if round_trip:
                #     res[self.CLASS_NAME_KW] =
                #     getattr(self, BaseModelSlots.CLASS_NAME_KW)
        return res

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
                cls._validate_model_item(
                    data=data, key=k, field_info=field_info)
        return data

    @classmethod
    def _validate_model_item(cls, data, key, field_info=None, ):
        if key == 'elements':
            pass

        if field_info is None:
            field_info = cls.model_fields[key]

        ann = field_info.annotation
        if key not in data:
            if not b_field_has_default(field_info):
                if b_is_optional(ann, b_strict=False):
                    data[key] = None
                elif b_annotation_includes_basemodel(
                        ann, b_strict=False):
                    if b_annotation_includes_type(ann=ann, type_=dict):
                        data[key] = {}
                    else:
                        data[key] = extract_basemodel_from_annotation(
                            ann, b_strict=False)()
        elif isinstance(data[key], list):
            if b_annotation_includes_type(ann, type_=tuple):
                data[key] = tuple(data[key])
        elif (isinstance(data[key], (int, str))
              and (b_is_intenum_annotation(ann, True))):
            data[key] = get_intenum_member(data[key], ann)

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
