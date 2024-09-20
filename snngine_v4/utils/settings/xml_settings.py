from __future__ import annotations

from typing import Any, ClassVar, Type

from pydantic import BaseModel, computed_field, model_validator

from snngine_v4.utils.settings.xml_settings_base import (
    default_xml_model_config_dict, XMLSettingsConfigDict,
    XMLSettingsModelBase,
)

from snngine_v4.utils.settings.xml_converter_options import XMLConverterOptions


class XMLSettingsModel(XMLSettingsModelBase):

    CLASS_NAME_XML_TAG: ClassVar[str] = 'class'
    CLASS_NAME_KW: ClassVar[str] = 'model__class__name'
    EXTRA_CLASSES: ClassVar[list[Type[BaseModel]] | None] = None

    xml_model: ClassVar[XMLConverterOptions] = XMLConverterOptions(
        dict_key_to_tag_attributes={CLASS_NAME_KW: CLASS_NAME_XML_TAG},
    )

    @computed_field
    @property
    def model__class__name(self) -> str:
        return self.__class__.__name__

    @classmethod
    def model_extra_class_dict(cls) -> dict[str, Type[BaseModel]]:
        if cls.EXTRA_CLASSES is not None:
            return {c.__name__: c for c in cls.EXTRA_CLASSES}

    @classmethod
    def model_interpret_dict(cls, dct: dict) -> dict | BaseModel:
        if cls.EXTRA_CLASSES is not None:
            if (model_type := cls.model_interpret_dict_type(dct)) is not None:
                return model_type(**dct)
        return dct

    @classmethod
    def model_interpret_dict_type(cls, dct: dict) -> Type[BaseModel]:
        if cls.EXTRA_CLASSES is not None:
            class_name = dct[cls.CLASS_NAME_KW]
            if class_name in (classes_dict := cls.model_extra_class_dict()):
                return classes_dict[class_name]

    @classmethod
    def pop_model__class__name_keyword(
            cls, dct: dict, b_recursive: bool = True):
        key_list = list(dct.keys())
        for k in key_list:
            if k == cls.CLASS_NAME_KW:
                dct.pop(cls.CLASS_NAME_KW)
            elif b_recursive and isinstance(dct[k], dict):
                dct[k] = cls.pop_model__class__name_keyword(
                    dct[k], b_recursive=True)
        return dct

    # noinspection PyNestedDecorators
    @model_validator(mode='after')
    @classmethod
    def validate_model_after(cls, data: Any) -> Any:

        if isinstance(data, BaseModel):
            if data.model_extra is not None:
                if cls.EXTRA_CLASSES is not None:
                    for k in data.model_extra:
                        if isinstance(data.model_extra[k], dict):
                            new = cls.model_interpret_dict(data.model_extra[k])
                            if new is not None:
                                setattr(data, k, new)
        return data


class XMLSettingsContainerModel(XMLSettingsModel):

    model_config: ClassVar[XMLSettingsConfigDict] = (
        default_xml_model_config_dict(extra='allow'))
