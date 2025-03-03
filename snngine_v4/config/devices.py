from typing import ClassVar

from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
from snngine_v4.utils.settings.ui_parameter_options import FrozenParamOpts


class OpenGLSettings(XMLSettingsModel):
    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts()

    gloo_target: str = "gl+"


class CudaSettings(XMLSettingsModel):
    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts()

    b_require_pycuda: bool = True


class DeviceSettings(XMLSettingsModel):

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        movable=False)
    b_use_cuda: bool = True
    opengl: OpenGLSettings = OpenGLSettings()
    cuda: CudaSettings
