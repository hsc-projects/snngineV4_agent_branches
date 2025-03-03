from typing import ClassVar

from pydantic import Field

from snngine_v4.geometry.spatial_pars import EnginePos3D, SpatialParUIOpts
from snngine_v4.utils.settings.config_model import ConfigModel
from snngine_v4.utils.settings.ui_parameter_options import (
    FrozenParamOpts,
    ParamOpts,
)


class CameraCenter(EnginePos3D):
    parameter_ui_opts: ClassVar = SpatialParUIOpts(
        expanded=False,
        # c_auto_collapse=True
    )


class TurnTableCameraParameters(ConfigModel):

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        renamable=False,
        expanded=True,
        c_coerce_to_limits=True,
        # expanded=False,
    )

    center: CameraCenter

    # name: str | None = None
    fov: float = Field(default=45, ge=0, le=180)
    elevation: float = Field(default=30, ge=-90, le=90)
    azimuth: float = Field(default=30, ge=-180, le=180)
    roll: float = Field(default=0, ge=-180, le=180)
    distance: float | None = Field(default=None, ge=0)
    translate_speed: float = Field(default=1, ge=0, le=10)
    scale_factor: float | None = Field(
        default=None, gt=0, title='Zoom', json_schema_extra={
            ParamOpts.KW.C_NONE_MEANS_UNKNOWN: True
        })
