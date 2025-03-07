from __future__ import annotations

from typing import ClassVar

from snngine_v4.nn.construction.config_models.neurons \
    .neuron_state_elements import (
        NeuronFlags, NeuronProperties,
    )

from snngine_v4.nn.construction.config_models.neurons.presets \
    .preset_base import PresetParameter
from snngine_v4.nn.construction.config_models.engine_element_config import \
    EngineElementConfig

from snngine_v4.utils.settings.config_model import ConfigModel


class NeuronInitializerParameters(ConfigModel):
    presets: PresetParameter


class NeuronStateModel(EngineElementConfig):

    class Slots(EngineElementConfig.Slots):
        FLAGS: ClassVar[str] = 'flags'
        PROPS: ClassVar[str] = 'props'

    initializer: NeuronInitializerParameters
    flags: NeuronFlags
    props: NeuronProperties

    @classmethod
    def reset_model(cls, neuron_model: dict | NeuronStateModel, n_neurons):
        if isinstance(neuron_model, dict):
            neuron_model = NeuronStateModel(**neuron_model)
        cls.reset_array(neuron_model, NeuronFlags, cls.Slots.FLAGS,
                        n_cols=n_neurons)
        cls.reset_array(neuron_model, NeuronProperties, cls.Slots.PROPS,
                        n_cols=n_neurons)
        return neuron_model


if __name__ == '__main__':
    from pprint import pprint
    pprint(NeuronStateModel())
