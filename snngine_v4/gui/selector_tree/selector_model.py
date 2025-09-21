from enum import IntEnum, auto
from typing import ClassVar

from pydantic import Field

from snngine_v4.utils.settings.config_model import ConfigModel
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


class SelectorType(IntEnum):
    """
    Represents different selector types in the neural network
    """
    NEURON = 0
    L_GROUP = auto()
    CHEMICAL = auto()


class SourceSinkType(IntEnum):
    """

    """
    SOURCE = 0
    SINK = auto()
    BOTH = auto()


class SelectorModel(ConfigModel):
    """Manages selector configuration settings"""

    class Slots:
        source_sink_type: ClassVar[str] = 'source_sink_type'
        selector_type: ClassVar[str] = 'selector_type'

    selector_type: SelectorType = Field(
        default=SelectorType.NEURON,
        json_schema_extra={
            ParamOpts.KW.TITLE: 'Type'})
    source_sink_type: SourceSinkType = Field(
        default=SourceSinkType.SOURCE,
        json_schema_extra={
            ParamOpts.KW.TITLE: 'Source/Sink/Both'})

