from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from snngine_v4.geometry.spatial_pars import (
    Shape3Df32,
    Object3DConfig, Segmentation3D,
)
from snngine_v4.utils.settings.config_model import ConfigModel
from snngine_v4.utils.settings.ui_parameter_options import FrozenParamOpts


class TechnicalValues(ConfigModel):

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        expanded=False)

    max_z: int = 100


class LinkedFiniteGridConfig(ConfigModel):

    technical: TechnicalValues

    parent_config: Object3DConfig = Field(exclude=True)

    @property
    def pos_origin(self):
        return self.parent_config.pos_origin

    @property
    def shape(self):
        raise NotImplementedError

    @property
    def seg(self):
        raise NotImplementedError


class FiniteGridConfig(Object3DConfig):

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        expanded=True,
        c_auto_collapse=True,
        c_collapsed_children=True,
    )

    technical: TechnicalValues
    shape: Shape3Df32
    seg: Segmentation3D


if __name__ == '__main__':
    from pprint import pprint
    pprint(FiniteGridConfig().model_dump())
