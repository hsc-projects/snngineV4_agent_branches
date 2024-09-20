from __future__ import annotations

from enum import IntEnum
from typing import ClassVar

from pydantic import Field, NonNegativeInt, PositiveFloat

from snngine_v4.utils.settings.settings_keywords import ParamOpts
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


class Ax3D(IntEnum):
    X = 0
    Y = 1
    Z = 2


class AxDir3D(IntEnum):
    XP = 0
    XM = 1
    YP = 2
    YM = 3
    ZP = 4
    ZM = 5


class XYZPars(XMLSettingsModel):

    parameter_ui_opts: ClassVar[ParamOpts] = ParamOpts(
        renamable=False,
        expanded=True,
        c_numeric=True,
        prefix='X,Y,Z')

    X: float
    Y: float
    Z: float


class FloatShape3D(XYZPars):

    X: PositiveFloat = Field(default=1, gt=0)
    Y: PositiveFloat = Field(default=1, gt=0)
    Z: PositiveFloat = Field(default=1, gt=0)


class Segmentation3D(XYZPars):

    X: NonNegativeInt = 10
    Y: NonNegativeInt = 10
    Z: NonNegativeInt = 10


class EnginePos3D(XYZPars):

    X: float = Field(default=0., ge=-10, le=10)
    Y: float = Field(default=0., ge=-10, le=10)
    Z: float = Field(default=0., ge=-10, le=10)


class Directions3DBoolPars(XMLSettingsModel):

    parameter_ui_opts: ClassVar[ParamOpts] = ParamOpts(
        expanded=False,
        c_numeric=True,
    )

    XP: bool
    XM: bool
    YP: bool
    YM: bool
    ZP: bool
    ZM: bool
