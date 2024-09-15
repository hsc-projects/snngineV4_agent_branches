from __future__ import annotations

from enum import Enum, IntEnum
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, Field

from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.geometry.spatial_pars import (
    Ax3D, AxDir3D, Directions3DBoolPars, FloatShape3D,
    Segmentation3D,
)
from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict,
    DefaultDictContainerConfig,
)
from snngine_v4.utils.core_utils import get_intenum_member
from snngine_v4.utils.settings.settings_keywords import ParamOpts
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


class ConvertingEnum(Enum):

    @classmethod
    def mapping(cls):
        raise NotImplementedError

    @classmethod
    def convert_dict(cls, dct, mapping=None):
        if mapping is None:
            mapping = cls.mapping()
        for i, k in enumerate(cls._member_names_):
            if k in dct:
                raise KeyError(f"Key {k} already exists in dictionary")
            elif k in mapping:
                dct[k] = dct.pop(mapping[k])
        return dct


class WDHKw(ConvertingEnum):
    width = 0
    depth = 1
    height = 2

    @classmethod
    def mapping(cls):
        return {WDHKw.width.name: Ax3D.X.name,
                WDHKw.depth.name: Ax3D.Y.name,
                WDHKw.height.name: Ax3D.Z.name}


class WDHSegKw(ConvertingEnum):
    width_segments = 0
    depth_segments = 1
    height_segments = 2

    @classmethod
    def mapping(cls):
        return {WDHSegKw.width_segments.name: Ax3D.X.name,
                WDHSegKw.depth_segments.name: Ax3D.Y.name,
                WDHSegKw.height_segments.name: Ax3D.Z.name}


class ColorType(XMLSettingsModel):

    parameter_ui_opts: ParamOpts = ParamOpts(
        renamable=False,
        expanded=False,
        c_numeric=True,
        prefix='R,G,B,A')

    R: float = Field(default=.5, ge=0., le=1.)
    G: float = Field(default=.5, ge=0., le=1.)
    B: float = Field(default=1., ge=0., le=1.)
    A: float = Field(default=1., ge=0., le=1.)


class BoxPlaneTypes(XMLSettingsModel):

    R: bool = Field(default=.5, ge=0., le=1.)
    G: float = Field(default=.5, ge=0., le=1.)
    B: float = Field(default=1., ge=0., le=1.)
    A: float = Field(default=1., ge=0., le=1.)


class VispyVisualConfig(XMLSettingsModel):

    VISPY_VISUAL_DUMP: ClassVar[str] = 'vispy'

    @classmethod
    def ax_dir_aliases(cls, member):
        member = get_intenum_member(member, AxDir3D)
        match member:
            case AxDir3D.XP:
                return '+x'
            case AxDir3D.XM:
                return '-x'
            case AxDir3D.YP:
                return '+y'
            case AxDir3D.YM:
                return '-y'
            case AxDir3D.ZP:
                return '+z'
            case AxDir3D.ZM:
                return '-z'

    @classmethod
    def convert_to_vispy(cls, dump_value, model: BaseModel):
        res = ConfigurableDict(
            container_conf=DefaultDictContainerConfig(
                b_duplicates_allowed=True
            )
        )

        dump_value.pop('technical')

        if isinstance(dump_value, dict):
            up_keys = {}
            for k, dump_value_ in dump_value.items():
                model_ = getattr(model, k)
                if isinstance(model_, FloatShape3D):
                    up_keys[k] = WDHKw.convert_dict(dump_value_)
                elif isinstance(model_, Segmentation3D):
                    up_keys[k] = WDHSegKw.convert_dict(dump_value_)
                elif isinstance(model_, ColorType):
                    dump_value[k] = tuple(dump_value_.values())
                elif isinstance(model_, Directions3DBoolPars):
                    vals = list(dump_value_.keys())
                    vals = [cls.ax_dir_aliases(x) for x in vals]
                    dump_value[k] = tuple(vals)

            for k in up_keys:
                dump_value.pop(k)
                res.update(up_keys[k])
            res.update(dump_value)

        return res.data


class BoxVisualConfig(FiniteGridConfig):

    planes: Directions3DBoolPars = Directions3DBoolPars(
        XP=True, XM=True,
        YP=True, YM=True,
        ZP=True, ZM=True
    )

    vertex_colors: None = None
    face_colors: None = None
    color: ColorType
    edge_color: ColorType
