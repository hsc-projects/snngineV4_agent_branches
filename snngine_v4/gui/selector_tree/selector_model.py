from enum import IntEnum, auto

from snngine_v4.utils.settings.config_model import ConfigModel


class SelectorType(IntEnum):
    NEURON = 0
    L_GROUP = auto()


class SelectorModel(ConfigModel):
    selector_type: SelectorType = SelectorType.NEURON

