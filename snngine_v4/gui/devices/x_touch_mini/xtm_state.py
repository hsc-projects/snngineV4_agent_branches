from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import auto, IntEnum
from typing import ClassVar

from pydantic import BaseModel, Field, model_validator

from snngine_v4.gui.devices.x_touch_mini.xtm_data_types import (
    XTMGlobalChannel,
    XTMLayer, XTMMessageType, XTMMode)
from snngine_v4.utils.settings.xml_converter.xml_settings_source import \
    (XMLSettingsConfigDict, default_xml_model_config_dict)
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


class MoveEncoderType(IntEnum):
    CC = 0
    PITCH_BEND = auto()
    PROGRAM_CHANGE = auto()


class PushEncoderType(IntEnum):
    CC = MoveEncoderType.CC.value
    PITCH_BEND = MoveEncoderType.PITCH_BEND.value
    PROGRAM_CHANGE = MoveEncoderType.PROGRAM_CHANGE.value
    NOTE = auto()
    MMC = auto()


class XTMButtonBehavior(IntEnum):
    TOGGLE = 0
    MOMENTARY = auto()


class XTMIntValue(XMLSettingsModel):
    A: int = Field(default=0, ge=-1, le=127)
    B: int = Field(default=0, ge=-1, le=127)
    MC: int = Field(default=0, ge=-1, le=127)

    @classmethod
    def from_value(cls, value: int):
        return cls(A=value, B=value, MC=value)

    def get_value(self, mode: XTMMode, layer: XTMLayer | None = None):
        match mode:
            case XTMMode.MC:
                return self.MC
            case XTMMode.STANDARD | XTMMode.UNKNOWN:
                match layer:
                    case XTMLayer.A | XTMLayer.UNKNOWN:
                        return self.A
                    case XTMLayer.B:
                        return self.B
                    # case _:
                    #     raise ValueError(f"Unknown layer '{layer.name}'")
            # case _:
            #     raise ValueError(f"Unknown mode '{mode.name}'")

    def set_all_values(self, value: int):
        self.A = value
        self.B = value
        self.MC = value

    def set_value(self, value: int, mode: XTMMode,
                  layer: XTMLayer | None = None,
                  b_verbose: bool = False):
        if b_verbose:
            print(f"value: {value}, "
                  f"mode: {mode.name}, "
                  f"layer: {layer.name}")
        match mode:
            case XTMMode.MC:
                self.MC = value
            case XTMMode.STANDARD:
                match layer:
                    case XTMLayer.A:
                        self.A = value
                    case XTMLayer.B:
                        self.B = value
                    case _:
                        raise ValueError(f"Unknown layer '{layer.name}'")
            case _:
                raise ValueError(f"Unknown mode '{mode.name}'")


class XTMChannelValue(XTMIntValue):
    A: int = Field(default=11, ge=-1, le=16)
    B: int = Field(default=11, ge=-1, le=16)
    MC: int = Field(default=11, ge=-1, le=16)


class XTMBooleanValue(XTMIntValue):
    A: bool = False
    B: bool = False
    MC: bool = False


class XTMValueType(IntEnum):
    CURRENT = 0
    MIN = auto()
    MAX = auto()


class XTMElementModel(BaseModel):

    name_id: str
    channel: XTMChannelValue = XTMChannelValue.from_value(11)
    # cc: XTMIntValue = XTMIntValue.from_value(-1)
    cc: int = -1
    element_type: MoveEncoderType | PushEncoderType
    min_value: XTMIntValue = XTMIntValue()
    max_value: XTMIntValue = XTMIntValue(A=127, B=127, MC=127)
    value: XTMIntValue = XTMIntValue()

    # noinspection PyMethodParameters
    @model_validator(mode='before')
    def validate_int_values(cls, data: dict):
        for k, v in data.items():
            if k in ['min_value', 'max_value', 'value']:
                if isinstance(v, int):
                    data[k] = XTMIntValue.from_value(int(v))
            elif k == 'channel':
                if isinstance(v, int):
                    data[k] = XTMChannelValue.from_value(int(v))
        return data

    def get_value(
        self,
        mode: XTMMode,
        layer: XTMLayer | None = None,
        value_type: XTMValueType = XTMValueType.CURRENT,
    ):
        match value_type:
            case XTMValueType.CURRENT:
                xtm_value = self.value
            case XTMValueType.MIN:
                xtm_value = self.min_value
            case XTMValueType.MAX:
                xtm_value = self.max_value
            case _:
                raise ValueError(f"Unknown value type '{value_type}'")
        return xtm_value.get_value(mode=mode, layer=layer)

    def set_value(self,
                  value: int, mode: XTMMode,
                  layer: XTMLayer | None = None,
                  value_type: XTMValueType = XTMValueType.CURRENT,
                  b_verbose: bool = False):
        match value_type:
            case XTMValueType.CURRENT:
                self.value.set_value(
                    value=value, mode=mode, layer=layer, b_verbose=b_verbose)
            case XTMValueType.MIN:
                self.min_value.set_value(
                    value=value, mode=mode, layer=layer, b_verbose=b_verbose)
            case XTMValueType.MAX:
                self.max_value.set_value(
                    value=value, mode=mode, layer=layer, b_verbose=b_verbose)


class XTMFaderModel(XTMElementModel):
    element_type: MoveEncoderType = MoveEncoderType.CC


class XTMKnobModel(XTMElementModel):
    element_type: MoveEncoderType = MoveEncoderType.CC


class XTMButtonModel(XTMElementModel):
    b_pressed: XTMBooleanValue = XTMBooleanValue.from_value(False)
    note: int
    behavior: XTMButtonBehavior = XTMButtonBehavior.TOGGLE
    element_type: PushEncoderType = PushEncoderType.NOTE

    def set_value(self, value: int, mode: XTMMode,
                  layer: XTMLayer | None = None,
                  value_type: XTMValueType = XTMValueType.CURRENT,
                  b_verbose: bool = False):
        # print(f"set_value: {value}, ")
        super().set_value(value=value, mode=mode, value_type=value_type,
                          layer=layer, b_verbose=b_verbose)
        min_value = self.get_value(
            value_type=XTMValueType.MIN, mode=mode, layer=layer)
        # print(f"min_value: {min_value}, ")
        self.b_pressed.set_value(
            value=value != min_value, mode=mode, layer=layer,
            b_verbose=b_verbose)


class XTMValues(BaseModel):
    knobs: list[XTMKnobModel] = [
        XTMKnobModel(name_id='knob_1', cc=1),
        XTMKnobModel(name_id='knob_2', cc=2),
        XTMKnobModel(name_id='knob_3', cc=3),
        XTMKnobModel(name_id='knob_4', cc=4),
        XTMKnobModel(name_id='knob_5', cc=5),
        XTMKnobModel(name_id='knob_6', cc=6),
        XTMKnobModel(name_id='knob_7', cc=7),
        XTMKnobModel(name_id='knob_8', cc=8),
    ]

    buttons: list[XTMButtonModel] = [
        XTMButtonModel(name_id='knob_button_1', note=0),
        XTMButtonModel(name_id='knob_button_2', note=1),
        XTMButtonModel(name_id='knob_button_3', note=2),
        XTMButtonModel(name_id='knob_button_4', note=3),
        XTMButtonModel(name_id='knob_button_5', note=4),
        XTMButtonModel(name_id='knob_button_6', note=5),
        XTMButtonModel(name_id='knob_button_7', note=6),
        XTMButtonModel(name_id='knob_button_8', note=7),

        XTMButtonModel(name_id='button_1', note=8),
        XTMButtonModel(name_id='button_2', note=9),
        XTMButtonModel(name_id='button_3', note=10),
        XTMButtonModel(name_id='button_4', note=11),
        XTMButtonModel(name_id='button_5', note=12),
        XTMButtonModel(name_id='button_6', note=13),
        XTMButtonModel(name_id='button_7', note=14),
        XTMButtonModel(name_id='button_8', note=15),
        XTMButtonModel(name_id='button_9', note=16),
        XTMButtonModel(name_id='button_10', note=17),
        XTMButtonModel(name_id='button_11', note=18),
        XTMButtonModel(name_id='button_12', note=19),
        XTMButtonModel(name_id='button_13', note=20),
        XTMButtonModel(name_id='button_14', note=21),
        XTMButtonModel(name_id='button_15', note=22),
        XTMButtonModel(name_id='button_16', note=23),
    ]
    fader: XTMFaderModel = XTMFaderModel(
        name_id='fader', channel=XTMChannelValue.from_value(11), cc=9)


class MidiPort(BaseModel):
    win: str
    lin: str

    @property
    def name(self):
        if sys.platform == 'win32':
            return self.win
        return self.lin


class XTMDeviceInfo(BaseModel):
    device_id: int = - 1
    global_channel: XTMGlobalChannel = XTMGlobalChannel(
        value=XTMGlobalChannel.OFF_VALUE)
    mode: XTMMode = XTMMode.UNKNOWN
    layer: XTMLayer = XTMLayer.UNKNOWN

    @classmethod
    def from_sysex_data(cls, data: tuple):
        return cls().update_sysex_data(data=data)

    def update_sysex_data(self, data: tuple):
        self.device_id = data[4]
        self.global_channel = XTMGlobalChannel.from_byte(value=data[5])
        self.mode = XTMMode.from_byte(data[6], b_allow_unknown=False)
        self.layer = XTMLayer.from_byte(data[10], b_allow_unknown=False)


class XTMConfig(XMLSettingsModel):

    model_config: ClassVar[XMLSettingsConfigDict] = (
        default_xml_model_config_dict(
            xml_file=f".snngine/x_touch_mini.xml"))

    midi_input_device: MidiPort = MidiPort(
        win='X-TOUCH MINI 0', lin='X-TOUCH MINI:X-TOUCH MINI MIDI 1'
    )
    midi_output_device: MidiPort = MidiPort(
        win='X-TOUCH MINI 1', lin='X-TOUCH MINI:X-TOUCH MINI MIDI 1'
    )

    info: XTMDeviceInfo = XTMDeviceInfo()

    encoder_values: XTMValues = XTMValues()

    def b_is_button_pressed(self, button_idx: int):
        return self.encoder_values.buttons[button_idx].b_pressed.get_value(
            mode=self.info.mode, layer=self.info.layer)

    def button_channel(self, button_idx: int):
        return self.encoder_values.buttons[button_idx].channel.get_value(
            mode=self.info.mode, layer=self.info.layer)

    def get_fader_value(self):
        return self.encoder_values.fader.get_value(
            mode=self.info.mode, layer=self.info.layer)

    def get_knob_value(self, knob_idx: int):
        knob = self.encoder_values.knobs[knob_idx]
        return knob.get_value(mode=self.info.mode, layer=self.info.layer)

    def knob_channel(self, knob_idx: int):
        return self.encoder_values.knobs[knob_idx].channel.get_value(
            mode=self.info.mode, layer=self.info.layer)

    def set_button_value(self, button_idx: int, value: int):
        btn = self.encoder_values.buttons[button_idx]
        btn.set_value(value=value, mode=self.info.mode, layer=self.info.layer)

    def set_fader_value(self, value: int):
        self.encoder_values.fader.value.set_all_values(value=value)

    def set_knob_value(self, knob_idx: int, value: int):
        # print(f"set_knob_value: {knob_idx} {value}")
        knob = self.encoder_values.knobs[knob_idx]
        knob.set_value(value=value, mode=self.info.mode, layer=self.info.layer)

    def update_from_message(self, msg: XTMMessageModel):
        match msg.type:
            case XTMMessageType.sysex.name:
                self.info.update_sysex_data(msg.data)
            case XTMMessageType.note_on.name | XTMMessageType.note_off.name:
                self.set_button_value(button_idx=msg.note, value=msg.velocity)
            case XTMMessageType.control_change.name:
                v = msg.value
                if msg.control == 9:
                    self.set_fader_value(value=v)
                else:
                    self.set_knob_value(knob_idx=msg.control - 1, value=v)
        return self

    # noinspection PyMethodParameters
    @model_validator(mode='before')
    def validate_int_values(cls, data: dict):
        for k, v in data.items():
            if k in ['mode', 'layer']:
                if isinstance(v, str):
                    match k:
                        case 'mode':
                            data[k] = XTMMode[data[k]]
                        case 'layer':
                            data[k] = XTMLayer[data[k]]
                elif isinstance(v, int):
                    match k:
                        case 'mode':
                            data[k] = XTMMode(v)
                        case 'layer':
                            data[k] = XTMLayer(v)
                        # case
        return data


@dataclass
class XTMMessageModel:
    type: str
    channel: int = None
    control: int = None
    value: int = None
    note: int = None
    time: int = None
    data: tuple = None
    program: int = None
    velocity: int = None
