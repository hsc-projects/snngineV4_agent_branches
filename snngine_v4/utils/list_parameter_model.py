from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from snngine_v4.utils.field_utils import ListParameterType, NoneAcceptingString
from snngine_v4.utils.settings.config_model import ConfigModel


class ListParameterModel(ConfigModel):

    class Slots:
        limits: ClassVar[str] = "limits"
        value: ClassVar[str] = "value"

    limits: ListParameterType = Field(default_factory=list, repr=False)
    value: NoneAcceptingString = Field(default='')
