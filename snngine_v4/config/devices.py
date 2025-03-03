from typing import ClassVar

from snngine_v4.utils.settings.config_model import ConfigModel
from snngine_v4.utils.settings.ui_parameter_options import FrozenParamOpts


class OpenGLSettings(ConfigModel):
    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts()

    gloo_target: str = "gl+"


class CudaSettings(ConfigModel):
    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts()

    b_require_pycuda: bool = True


class DeviceSettings(ConfigModel):

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        movable=False)
    b_use_cuda: bool = True
    opengl: OpenGLSettings = OpenGLSettings()
    cuda: CudaSettings
