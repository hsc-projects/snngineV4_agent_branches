from __future__ import annotations

from typing import ClassVar

from snngine_v4.geometry.spatial_pars import FloatShape3D, Segmentation3D
from snngine_v4.utils.settings.settings_keywords import ParamOpts
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


class TechnicalValues(XMLSettingsModel):

    parameter_ui_opts: ClassVar[ParamOpts] = ParamOpts(
        expanded=False)

    max_z: int = 100


class FiniteGridConfig(XMLSettingsModel):

    technical: TechnicalValues
    shape: FloatShape3D
    seg: Segmentation3D
