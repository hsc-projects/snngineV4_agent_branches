from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from snngine_v4.geometry.spatial_pars import (
    EnginePos3D, FloatShape3D,
    Object3DConfig, Segmentation3D,
)
from snngine_v4.utils.settings.config_model import ConfigModel
from snngine_v4.utils.settings.ui_parameter_options import FrozenParamOpts


class TechnicalValues(ConfigModel):

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        expanded=False)

    max_z: int = 100


class FiniteGridConfig(Object3DConfig):

    pos_origin: EnginePos3D = Field(
        default_factory=lambda: EnginePos3D.from_tuple((0, 0, 0)))

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        expanded=True,
        c_auto_collapse=True,
        c_collapsed_children=True,
    )

    technical: TechnicalValues
    shape: FloatShape3D
    seg: Segmentation3D
