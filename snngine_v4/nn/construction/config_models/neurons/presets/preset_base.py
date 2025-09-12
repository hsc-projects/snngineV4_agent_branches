from typing import Callable, ClassVar

import pandas as pd
from pydantic import Field

from snngine_v4.nn.construction.config_models.neurons.presets \
    .izhikevich_presets import (
        IzhikevichPresets,
    )
from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict,
    SingletonDict,
)
from snngine_v4.utils.data_utils.dataframe_config import SeriesF32
from snngine_v4.utils.list_parameter_model import ListParameterModel
from snngine_v4.utils.settings.config_model import ConfigModel
from snngine_v4.utils.settings.ui_parameter_options import FrozenParamOpts


class PresetsContainer(SingletonDict):

    __getitem__: Callable[..., pd.DataFrame]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.preset_map: dict[str, IzhikevichPresets] | ConfigurableDict = (
            ConfigurableDict())
        self.add_presets(IzhikevichPresets())

    def add_presets(self, model: IzhikevichPresets, name=None):
        if name is None:
            name = model.__class__.__name__
        self[name] = model.dataframe
        self.preset_map[name] = model

    @property
    def preset_types(self):
        return list(self.keys())


class F32Preset(SeriesF32):
    index: list[str] = Field(default_factory=list)


class Preset(ConfigModel):
    f32: F32Preset


class PresetParameter(ConfigModel):
    """
    """
    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        expanded=True,
        c_auto_collapse=True,
        c_collapsed_children=True,
    )

    PRESET_CONTAINER: ClassVar[type[dict]] = PresetsContainer

    preset_type: ListParameterModel | str = Field(
        default_factory=ListParameterModel)
    preset_name: ListParameterModel | str = Field(
        default_factory=ListParameterModel)

    preset: Preset

    def default_init(self, **kwargs):
        self.preset_container.preset_map[self.preset_type.value].default_init(
            **kwargs)

    def model_post_init(self, __context):
        init_preset = None
        if isinstance(self.preset_type, str):
            init_preset = self.preset_type
            self.preset_type = ListParameterModel()
        if len(self.preset_type.limits) == 0:
            self.preset_type.limits = self.preset_container.preset_types
            if init_preset is not None:
                self.preset_type.value = init_preset
            else:
                self.preset_type.value = self.preset_type.limits[0]

        init_name = None
        if isinstance(self.preset_name, str):
            init_name = self.preset_name
            self.preset_name = ListParameterModel()
        if len(self.preset_name.limits) == 0:
            df = self.preset_type_values
            self.preset_name.limits = list(df.columns)
            if init_preset is not None:
                self.preset_name.value = init_name
            else:
                self.preset_name.value = self.preset_name.limits[0]
            self.preset = Preset(f32=df[self.preset_name.value])

    @property
    def preset_type_values(self) -> pd.DataFrame:
        return self.preset_container[self.preset_type.value]

    @property
    def preset_container(self) -> PresetsContainer:
        return self.PRESET_CONTAINER()


if __name__ == '__main__':
    a = PresetParameter()
