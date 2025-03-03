from __future__ import annotations

import os
from pathlib import Path
from typing import Any, ClassVar, Literal

from pydantic import ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import (
    ConfigFileSourceMixin, InitSettingsSource, PathType,
)


from snngine_v4.utils.data_utils.validation.array_io import ArrayDictRW
from snngine_v4.utils.settings.settings_keywords import BaseSettingsSlots
from snngine_v4.utils.settings.xml_converter.xml_converter_options \
    import XMLConverterOptions


class XMLSettingsConfigDict(SettingsConfigDict, total=False):
    xml_file: PathType | None
    env_file: None


def default_xml_model_config_dict(
    xml_file: str | None = None,
    extra: Literal['allow', 'ignore', 'forbid'] | None = 'forbid',
    use_enum_values=False,
):
    return XMLSettingsConfigDict(
        strict=True,
        env_file=None,
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
        settings_cls: type[BaseSettings],
        xml_files: PathType | str | None = '',
        b_verbose: bool = False,
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

        if b_verbose:
            print("\nFILE(S):")
            print(self.xml_file_paths)
            print("\nDATA:")
            print(xml_data)

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
                    ArrayDictRW.extract_arrays(
                        array_file_path, dests=[new_vals])
                    pass
                vars_.update(new_vals)

        return vars_

    def _read_file(self, file_path: Path) -> dict[str, Any]:
        from snngine_v4.utils.settings.xml_converter import XMLConverter
        # noinspection PyTypeChecker
        xml_model = self.settings_cls.xml_model
        if xml_model is None:
            from snngine_v4.utils.settings.xml_converter \
                .xml_converter_options import XMLConverterOptions
            xml_model = XMLConverterOptions()
            self.settings_cls.xml_model = xml_model

        conv = XMLConverter(xml_model)

        res = conv.dict_from_xml(str(file_path))
        return res


if __name__ == '__main__':

    from snngine_v4.utils.settings.config_model_base import (
        ConfigModelMixin, default_config_dict,
    )

    class XMLConverterTester(BaseSettings, ConfigModelMixin):
        model_config: ClassVar[ConfigDict] = (
            default_config_dict(
                xml_file='./xml_converter_settings.xml'))

        xml_model: ClassVar[XMLConverterOptions] = XMLConverterOptions()

        opts: XMLConverterOptions = XMLConverterOptions()

        @classmethod
        def settings_customise_sources(
                cls, settings_cls: type[BaseSettings],
                init_settings, env_settings,
                dotenv_settings, file_secret_settings):
            return (
                init_settings,
                XMLConfigSettingsSource(settings_cls, b_verbose=True),
            )


    opts_ = XMLConverterTester()
    opts_.export()
