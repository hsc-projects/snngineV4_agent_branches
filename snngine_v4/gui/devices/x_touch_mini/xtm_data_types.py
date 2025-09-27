from __future__ import annotations

from enum import auto, IntEnum
from typing import ClassVar

from pydantic import BaseModel


class XTMMode(IntEnum):
    STANDARD = 0
    MC = 1
    UNKNOWN = 2

    @classmethod
    def from_byte(cls, value, b_allow_unknown: bool = False):
        if value == 0x00:
            mode = cls.STANDARD
        elif value == 0x01:
            mode = cls.MC
        else:
            if b_allow_unknown:
                mode = cls.UNKNOWN
            else:
                raise ValueError(f"Unknown XTM-mode value '{value}'")
        return mode


class XTMLayer(IntEnum):
    A = 0
    B = 1
    UNKNOWN = 3

    @classmethod
    def from_byte(cls, value, b_allow_unknown: bool = False):
        if value == 0x00:
            layer = cls.A
        elif value == 0x01:
            layer = cls.B
        else:
            if b_allow_unknown:
                layer = cls.UNKNOWN
            else:
                raise ValueError(f"Unknown XTM-layer value '{value}'")
        return layer


# class LEDButtonState(IntEnum):
#     OFF = 0
#     ON = 1
#     BLINK = 2


class LedRingMode(IntEnum):
    SINGLE = 0
    PAN = auto()
    FAN = auto()
    SPREAD = auto()
    TRIM = auto()


class XTMMessageType(IntEnum):
    control_change = 0
    note_on = auto()
    note_off = auto()
    sysex = auto()
    program_change = auto()


# @dataclass(repr=False)
class XTMGlobalChannel(BaseModel):

    OFF_VALUE: ClassVar[int] = 0x12

    value: int

    @classmethod
    def from_byte(cls, value):
        return cls(value=value)

    def __repr__(self):
        if self.value == XTMGlobalChannel.OFF_VALUE:
            str_value = "Off"
        else:
            str_value = self.value + 1
        return f"{self.__class__.__name__}(value={str_value})"
