from __future__ import annotations

from typing import Any, ClassVar, Type

from pydantic import BaseModel, field_validator, model_validator

from snngine_v4.utils.field_utils import (
    b_annotation_includes_type, extract_basemodel_from_iterable_annotation,
)
from snngine_v4.utils.settings.settings_keywords import (
    BaseModelSlots,
    BaseSettingsSlots,
)
from snngine_v4.utils.settings.ui_parameter_options import FrozenParamOpts
from snngine_v4.utils.settings.xml_settings_base import (
    default_xml_model_config_dict, XMLSettingsConfigDict,
    XMLSettingsModelBase,
)

from snngine_v4.utils.settings.xml_converter_options import XMLConverterOptions


class XMLSettingsModel(XMLSettingsModelBase):

    # NOTE: BaseModelSlots.CLASS_NAME
    class__name: str = ''
    # NOTE: BaseModelSlots.EXTRA_CLASSES
    EXTRA_CLASSES: ClassVar[list[Type[BaseModel]] | None] = None

    xml_model: ClassVar[XMLConverterOptions] = XMLConverterOptions(
        dict_key_to_tag_attributes={
            BaseModelSlots.CLASS__NAME: BaseSettingsSlots.CLASS_NAME_XML_TAG},
    )

    # noinspection PyNestedDecorators
    @field_validator(BaseModelSlots.CLASS__NAME, mode='before')
    @classmethod
    def set_class__name(cls, v: str) -> str:
        if v == '':
            v = cls.__name__
        elif v != cls.__name__:
            raise AssertionError
        return v

    # @computed_field()
    # @property
    # def model__class__name(self) -> str:
    #     self.class__name = self.__class__.__name__
    #     return self.__class__.__name__

    @classmethod
    def model_interpret_basemodel_iterable(
            cls, values, ann=None, allowed_types=None):
        if allowed_types is None:
            allowed_types = extract_basemodel_from_iterable_annotation(
                ann, b_raise=True)
        class_dict = {c.__name__: c for c in allowed_types}
        for i, x in enumerate(values):
            if isinstance(x, dict):
                new = cls.model_interpret_dict(
                    dct=x, b_raise=True, class_dict=class_dict)
                values[i] = new

    @classmethod
    def model_interpret_dict(
        cls, dct: dict, b_raise: bool = False, class_dict=None
    ) -> dict | BaseModel:
        if (class_dict is None) and (cls.EXTRA_CLASSES is not None):
            class_dict = {c.__name__: c for c in cls.EXTRA_CLASSES}
        if class_dict is not None:
            if ((model_type := cls.model_interpret_dict_type(
                    dct, b_raise=b_raise, class_dict=class_dict)) is not None):
                return model_type(**dct)
        return dct

    @classmethod
    def model_interpret_dict_type(
        cls, dct: dict, b_raise: bool = False, class_dict=None,
    ) -> Type[BaseModel]:
        if class_dict is not None:
            class_name = dct[BaseModelSlots.CLASS__NAME]
            if class_name in class_dict:
                return class_dict[class_name]
        if b_raise:
            raise TypeError(
                f"Unknown model type: {dct[BaseModelSlots.CLASS__NAME]} "
                f"not in {class_dict.keys()}")

    @classmethod
    def model_interpret_extra_dict(
        cls, dct: dict, b_raise: bool = False, class_dict=None
    ) -> dict | BaseModel:
        return cls.model_interpret_dict(
            dct=dct, b_raise=b_raise, class_dict=class_dict)

    @classmethod
    def model_interpret_extra_dict_type(
        cls, dct: dict, b_raise: bool = False, class_dict=None
    ) -> Type[BaseModel]:
        if (class_dict is None) and (cls.EXTRA_CLASSES is not None):
            class_dict = {c.__name__: c for c in cls.EXTRA_CLASSES}
        return cls.model_interpret_dict_type(
            dct=dct, b_raise=b_raise, class_dict=class_dict)

    @model_validator(mode='after')
    @classmethod
    def validate_model_after(cls, data: Any) -> Any:
        return cls._validate_model_after(data=data)

    # noinspection PyNestedDecorators
    @classmethod
    def _validate_model_after(cls, data: Any) -> Any:
        if isinstance(data, BaseModel):
            if data.model_extra is not None:
                if cls.EXTRA_CLASSES is not None:
                    for k in data.model_extra:
                        if isinstance(data.model_extra[k], dict):
                            new = cls.model_interpret_dict(
                                data.model_extra[k], b_raise=True)
                            if new is not None:
                                setattr(data, k, new)
        return data

    @classmethod
    def _validate_model_item(cls, data, key, field_info=None) -> Any:
        if field_info is None:
            field_info = cls.model_fields[key]
        ann = field_info.annotation
        if ((key in data) and isinstance(data[key], (list, tuple))
                and any([isinstance(x, dict) for x in data[key]])
                and b_annotation_includes_type(ann, type_=list)):
            allowed_types = extract_basemodel_from_iterable_annotation(
                ann=ann, b_raise=False)
            if len(allowed_types) > 0:
                cls.model_interpret_basemodel_iterable(
                    values=data[key], allowed_types=allowed_types)
        super()._validate_model_item(data=data, key=key, field_info=field_info)


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
