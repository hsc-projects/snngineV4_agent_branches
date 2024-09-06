from snngine_v4.utils.parameter_model.settings_model import BaseSettingsModel


class VisualObjectConfigModel(BaseSettingsModel):
    # shape: tuple | None = None
    b_is_cuda: bool = True
    cuda_attributes_initialized: bool = False
