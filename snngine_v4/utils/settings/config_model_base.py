from __future__ import annotations

from enum import auto, IntEnum
from typing import Any, ClassVar, Literal, Type

from pydantic import (
    BaseModel, ConfigDict, Field, field_validator,
    model_validator,
)
from pydantic.types import PathType

from snngine_v4.utils.core_utils import filter_dict_keys, get_intenum_member
from snngine_v4.utils.data_utils.deepdish_pack import deepdish
from snngine_v4.utils.data_utils.validation.array_io import ArrayDictRW
from snngine_v4.utils.field_utils import (
    b_annotation_includes_basemodel, b_annotation_includes_type,
    b_field_has_default, b_is_intenum_annotation, b_is_optional,
    extract_basemodel_from_annotation,
    extract_basemodel_from_iterable_annotation,
)
from snngine_v4.utils.settings.settings_keywords import (
    BaseModelSlots,
    BaseSettingsSlots,
)
from snngine_v4.utils.settings.xml_converter.xml_converter_options \
    import XMLConverterOptions


class ModelDumpTypes(IntEnum):
    python = 0
    json = auto()
    only_arrays = auto()


class ConfigModelMixin:

    # NOTE: BaseModelSlots.CLASS__NAME
    class__name: str = Field(default='', repr=False)
    # NOTE: BaseModelSlots.EXTRA_CLASSES
    EXTRA_CLASSES: ClassVar[list[Type[BaseModel]] | None] = None

    parameter_ui_opts: ClassVar[dict | None] = None

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
            v = cls.__name__
            # raise AssertionError
        return v

    @classmethod
    def cls_model_keys(cls, model=None, b_exclude_class_name=True, **kwargs):
        if model is None:
            model = cls
        return BaseModelSlots.model_keys(
            model=model, b_exclude_class_name=b_exclude_class_name,
            **kwargs)

    def export(self: BaseModel | ConfigModelMixin,
               fn: str = None, mode='xml', round_trip=True, **kwargs):

        if mode != 'xml':
            raise NotImplementedError

        from snngine_v4.utils.settings.xml_converter import XMLConverter

        xml_model = self.xml_model
        if xml_model is None:
            from snngine_v4.utils.settings.xml_converter \
                .xml_converter_options import XMLConverterOptions
            # noinspection PyArgumentList
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
            conv.to_xml_file(data=self, fn=fn,
                             # round_trip=round_trip,
                             **kwargs)

    def _export_submodels(
            self: BaseModel | ConfigModelMixin, conv, fn, sub_setting_pattern,
            **kwargs):
        for k in self.model_keys():
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
            # if len(array_list) > 0:
            #     deepdish.io.save(array_path, array_dct)
            #     # a = deepdish.io.load(array_path)
            #     pass

    @classmethod
    def cls_filter_dict_keys(cls, dct, b_pop=False, keys=None,
                             include=None, exclude=None) -> dict:
        if keys is None:
            keys = cls.cls_model_keys()
        if include is not None:
            keys += include
        return filter_dict_keys(
            dct=dct, b_pop=b_pop, include=keys, exclude=exclude)

    def filtered_model_dict(self, type_filter=None, **kwargs):
        keys = self.model_keys(type_filter=type_filter, **kwargs)
        res = {}
        for k in keys:
            res[k] = getattr(self, k)
        return res

    def filtered_model_dump(self: BaseModel, type_filter=None,
                            mode='python', **kwargs):
        keys = self.model_keys(type_filter=type_filter, **kwargs)
        res = self.model_dump(mode=mode, include=keys)
        return res

    def filtered_model_values(self, type_filter=None, **kwargs):
        dct = self.filtered_model_dict(type_filter=type_filter, **kwargs)
        return list(dct.values())

    def _model_dump(self: BaseModel, mode: str | ModelDumpTypes = 'python',
                    include=None, round_trip=False,
                    **kwargs):
        if isinstance(mode, (int, ModelDumpTypes)):
            mode = get_intenum_member(mode, ModelDumpTypes).name
        match mode:
            case ModelDumpTypes.only_arrays.name:
                res = {}
                ArrayDictRW.extract_arrays(self, b_recursive=True, dests=[res])
            case _:
                res = BaseModel.model_dump(
                    self, mode=mode,
                    include=include, round_trip=round_trip, **kwargs)
        return res

    def model_keys(self, **kwargs):
        return self.cls_model_keys(model=self, **kwargs)

    @classmethod
    def model_interpret_basemodel_iterable(
            cls, values, ann=None, allowed_types=None) -> bool:
        if allowed_types is None:
            allowed_types = extract_basemodel_from_iterable_annotation(
                ann, b_raise=True)
        class_dict = {c.__name__: c for c in allowed_types}
        res = []
        for i, x in enumerate(values):
            if isinstance(x, dict):
                new = cls.model_interpret_dict(
                    dct=x, b_raise=True, class_dict=class_dict)
                values[i] = new
                res.append(True)
            else:
                res.append(False)
        return bool(all(res))

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
            cls, dct: dict, b_raise: bool = False,
            class_dict: dict[str, Type[BaseModel]] | None = None,
    ) -> Type[BaseModel] | None:
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

    def post_init_process_extra_classes(self: BaseModel | ConfigModelMixin):
        # if isinstance(data, BaseModel):
        if self.model_extra is not None:
            if self.EXTRA_CLASSES is not None:
                for k in self.model_extra:
                    if isinstance(self.model_extra[k], dict):
                        new = self.model_interpret_dict(
                            self.model_extra[k], b_raise=True)
                        if new is not None:
                            setattr(self, k, new)

    @classmethod
    def validate_model_iterable_item(
            cls: Type[BaseModel] | ConfigModelMixin,
            data, key, field_info=None) -> bool:
        if field_info is None:
            field_info = cls.model_fields[key]
        ann = field_info.annotation
        if ((key in data) and isinstance(data[key], (list, tuple))
                and any([isinstance(x, dict) for x in data[key]])
                and b_annotation_includes_type(ann, type_=list)):
            allowed_types = extract_basemodel_from_iterable_annotation(
                ann=ann, b_raise=False)
            if len(allowed_types) > 0:
                return cls.model_interpret_basemodel_iterable(
                    values=data[key], allowed_types=allowed_types)
        return False

    @classmethod
    def validate_model_item(
            cls: Type[BaseModel],
            data, key, field_info=None,
    ):
        if key == 'elements':
            pass

        if field_info is None:
            field_info = cls.model_fields[key]

        if key not in data:
            ann = field_info.annotation
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
            if b_annotation_includes_type(field_info, type_=tuple):
                data[key] = tuple(data[key])
        elif (isinstance(data[key], (int, str))
              and (b_is_intenum_annotation(
                    ann := field_info.annotation, True))
              and (not isinstance(data[key], ann))):
            data[key] = get_intenum_member(data[key], ann)

    @model_validator(mode='before')
    @classmethod
    def validate_model_before(cls, data: Any) -> Any:
        return cls._validate_model_before(data)

    @classmethod
    def _validate_model_before(
            cls: Type[BaseModel] | ConfigModelMixin, data: Any) -> Any:
        if isinstance(data, dict):
            for k in cls.model_computed_fields:
                data.pop(k, None)
            for k, field_info in cls.model_fields.items():
                cls.validate_model_item(
                    data=data, key=k, field_info=field_info)
        return data

    @classmethod
    def _xml_file_paths(cls: Type[BaseModel] | ConfigModelMixin, ):
        #  noinspection PyTypedDict
        fn = cls.model_config[BaseSettingsSlots.XML_FILE]

        sub_setting_pat = BaseSettingsSlots.SUB_SETTINGS_FILE_NAME_PATTERN
        if (fn is not None) and (sub_setting_pat in fn):
            xml_files = []
            for k in cls.model_fields:
                xml_files.append(fn.replace(sub_setting_pat, k))
        else:
            xml_files = fn
        return xml_files


class ConfigModelDict(ConfigDict, total=False):
    xml_file: PathType | None


def default_config_dict(
    xml_file: str | None = None,
    extra: Literal['allow', 'ignore', 'forbid'] | None = 'forbid',
    use_enum_values=False,
):
    return ConfigModelDict(
        xml_file=xml_file,
        strict=True,
        use_enum_values=use_enum_values,
        validate_default=True,
        validate_assignment=True,
        extra=extra,
        arbitrary_types_allowed=False)
