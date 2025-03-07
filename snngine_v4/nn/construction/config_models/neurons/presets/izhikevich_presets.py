import numpy as np
import pandas as pd
from pydantic import computed_field, Field


from snngine_v4.utils.data_utils.validation.array_annotation import \
    ArrayInterfaces
from snngine_v4.utils.settings.config_model import ConfigModel


IzPreset = ArrayInterfaces().make_type(4, dtype=np.float32)


def make_iz_preset(a, b, c, d):
    return np.array([a, b, c, d],
                    dtype=ArrayInterfaces()[IzPreset].dtype)


class IzhikevichPresets(ConfigModel, arbitrary_types_allowed=True):

    RS: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.02, b=0.2, c=-65., d=8.))
    IB: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.02, b=0.2, c=-55., d=4.))
    CH: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.02, b=0.2, c=-50., d=2.))
    FS: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.1, b=0.2, c=-65., d=2.))
    FS25: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.09, b=0.24, c=-65., d=2.))
    TC: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.02, b=0.25, c=-65., d=0.05))
    RZ: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.1, b=0.26, c=-65., d=2.))
    LTS: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.02, b=0.25, c=-65., d=2.))
    tonic_spiking: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.02, b=0.2, c=-65., d=6.))
    phasic_spiking: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.02, b=0.25, c=-65., d=6.))
    tonic_bursting: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.02, b=0.2, c=-50., d=2.))
    phasic_bursting: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.02, b=0.25, c=-55., d=0.05))
    mixed_mode: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.02, b=0.2, c=-55., d=4))
    spike_frequency_adaptation: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.01, b=0.2, c=-65., d=8))
    class_1_exc: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.02, b=-0.1, c=-65., d=6))
    class_2_exc: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.2, b=0.26, c=-65., d=0))
    spike_latency: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.02, b=0.2, c=-65., d=6.))
    subthreshold_oscillations: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.05, b=0.26, c=-60., d=0.))
    resonator: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.1, b=0.26, c=-60., d=-1.))
    integrator: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.02, b=-0.1, c=-55., d=6))
    rebound_spike: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.03, b=0.25, c=-60., d=4))
    rebound_burst: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.03, b=0.25, c=-52., d=0))
    threshold_variability: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.03, b=0.25, c=-60., d=4))
    bistability: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=1, b=1.5, c=-60., d=0))
    depolarizing_after_potential: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=1, b=.2, c=-60., d=-21))
    accommodation: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=0.02, b=1, c=-55., d=4))
    inh_induced_spiking: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=-0.02, b=-1, c=-60., d=8))
    inh_induced_bursting: IzPreset = Field(
        default_factory=lambda: make_iz_preset(a=-0.026, b=-1, c=-45., d=0))

    @computed_field
    def dataframe(self) -> pd.DataFrame:
        vals = self.filtered_model_dict(
            type_filter=IzPreset, b_include_computed=False)
        df = pd.DataFrame(data=vals, index=['a', 'b', 'c', 'd'])
        return df

    def default_init(self, df_props: pd.DataFrame,
                     mask_inh, mask_exc, r):
        # n_neurons = len(df_props)
        # r = torch.rand(n_neurons, dtype=torch.float32, device=device)
        df_props['v'] = -65.
        df_props['a'] = .02 + .08 * r * mask_inh
        df_props['b'] = .2 + .05 * (1. - r) * mask_inh
        df_props['c'] = -65 + 15 * (r ** 2) * mask_exc
        df_props['d'] = 2 * mask_inh + (8 - 6 * (r ** 2)) * mask_exc
        df_props['u'] = df_props['b'] * df_props['v']
        df_props['v_prev'] = df_props['v']
