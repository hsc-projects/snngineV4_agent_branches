from __future__ import annotations

import os
import time
from typing import Callable, ClassVar, Union

import mido

from snngine_v4.gui.devices.x_touch_mini.xtm_data_types import (
    XTMGlobalChannel,
    XTMLayer, XTMMessageType, XTMMode)
from snngine_v4.gui.devices.x_touch_mini.xtm_state import (XTMConfig,
                                                           XTMMessageModel)


class XTouchMiniDevice:

    NAME: ClassVar[str] = "X-TOUCH MINI"

    def __init__(
        self, io_device_config: XTMConfig = None,
        input_callback: Union[Callable, None] = None,
        # config_file_path='./xtm_conf.xml',
        fader_state_file_path='./fader_sate.xml',
        b_verbose: bool = False,
    ):

        self.b_verbose = b_verbose
        if io_device_config is None:
            io_device_config = XTMConfig()

        self.device_config = io_device_config

        config_file_path = XTMConfig._xml_file_paths()
        self.config_file_path = config_file_path
        self.fader_state_file_path = fader_state_file_path

        if input_callback is None:
            input_callback = self._device_config.update_from_message

        self._input_callback = input_callback

        self._device_config: XTMConfig = XTMConfig()
        self.input_port = None
        self.output_port = None
        self._connected = False

        self.connect_to_device()

        # if os.path.exists(self.config_file_path):
        #     self.load_config()

    def apply_config(self):

        self.set_global_channel(self._device_config.info.global_channel)
        self.set_mode(self._device_config.info.mode)
        self.set_device_id(self._device_config.info.device_id)
        self.set_layer(self._device_config.info.layer)

        for knob in self._device_config.encoder_values.knobs:
            self.set_knob_value(
                control=knob.cc,
                channel=self._device_config.knob_channel(knob.cc - 1),
                value=self._device_config.get_knob_value(knob.cc - 1),
            )
        for btn in self._device_config.encoder_values.buttons:
            self.set_button_led(
                note=btn.note,
                channel=self._device_config.button_channel(btn.note),
                b_pressed=self._device_config.b_is_button_pressed(btn.note)
            )

    def connect_to_device(self):
        try:
            # noinspection PyUnresolvedReferences
            self.input_port = mido.open_input(
                name=self.device_config.midi_input_device.name,
                callback=self._input_callback)

            # noinspection PyUnresolvedReferences
            self.output_port = mido.open_output(
                name=self.device_config.midi_output_device.name)
            self._connected = True
            self.initialize_ports()
            self.send_read_device_info_command()
            # self.input_port._rt.ignore_types(timing=False)
        except OSError as e:
            print('Error:', e)

    @property
    def connected(self):
        return self._connected

    @property
    def device_config(self) -> XTMConfig:
        return self._device_config

    @device_config.setter
    def device_config(self, value: XTMConfig):
        self._device_config = value

    def initialize_ports(self, ):
        # noinspection PyProtectedMember
        rtmidi_in = self.input_port._rt
        rtmidi_in.cancel_callback()
        # noinspection PyProtectedMember
        rtmidi_out = self.output_port._rt
        device_info = 'f0 40 41 42 51 00 00 00 00 00 00 00 00 f7'
        sending_data = bytearray.fromhex(device_info)
        rtmidi_out.send_message(sending_data)
        timeout = 2
        timeout_start = time.time()
        while True:
            receiving_data = rtmidi_in.get_message()
            timeout_actual = time.time()
            if (timeout_actual - timeout_start) > timeout:
                print(
                    'No answering from device')
                break
            if receiving_data is not None and isinstance(receiving_data, tuple):
                break
        self.input_port.callback = self._input_callback
        return receiving_data

    @property
    def input_callback(self):
        return self._input_callback

    @input_callback.setter
    def input_callback(self, value):
        self._input_callback = value
        self.input_port.callback = value

    def load_config(self, fn=None):
        if fn is None:
            fn = self.config_file_path

        # conf_xml = ElementTree(file=fn)
        # conf = XTMConfig.from_xml(conf_xml)

        conf = XTMConfig.from_xml_file_s(files=fn)
        self.device_config = conf
        self.apply_config()

    def save_config(self, fn=None, **kwargs):
        if fn is None:
            fn = self.config_file_path
        self._device_config.export(fn)
        # nodel_dict = self._device_config.model_dump(mode='json')
        # with open(fn, 'w') as file:
        #     content = XMLConverter.to_xml_str(nodel_dict, **kwargs)
        #     file.write(content)

    def save_fader_state(self, fn=None, **kwargs):
        if fn is None:
            fn = self.fader_state_file_path
        self._device_config.encoder_values.fader.value.export(fn)
        # nodel_dict = self._device_config.encoder_values.fader.value.model_dump(
        #     mode='json')
        # with open(fn, 'w') as file:
        #     content = XMLConverter.to_xml_str(nodel_dict, **kwargs)
        #     file.write(content)

    def send_read_device_info_command(self):
        msg = mido.Message(type=XTMMessageType.sysex.name,
                           data=[0x40, 0x41, 0x42, 0x51])
        self.write(msg)

    def set_button_led(self, note, channel, b_pressed: bool):
        value = int(b_pressed)
        self.device_config.set_button_value(button_idx=note, value=value)
        msg = mido.Message(
            XTMMessageType.note_on.name,
            channel=channel-1,
            note=note, velocity=value)
        self.write(msg)

    def set_device_id(self, device_id: int):
        self._device_config.info.device_id = device_id
        msg = mido.Message(type=XTMMessageType.sysex.name,
                           data=[0x40, 0x41, 0x42, 0x60, device_id])
        self.write(msg)

    def set_global_channel(self, global_channel: int | XTMGlobalChannel):

        if isinstance(global_channel, XTMGlobalChannel):
            global_channel = global_channel.value

        self._device_config.info.global_channel.value = global_channel
        msg = mido.Message(type=XTMMessageType.sysex.name,
                           data=[0x40, 0x41, 0x42, 0x61, global_channel])
        self.write(msg)

    def set_knob_value(self, control, value, channel):
        self.device_config.set_knob_value(knob_idx=control-1, value=value)
        msg = mido.Message(
            XTMMessageType.control_change.name,
            channel=channel-1,
            control=control,
            value=value)
        self.write(msg)

    def set_layer(self, xtm_layer: XTMLayer):
        if (self._device_config.info.global_channel.value
                != XTMGlobalChannel.OFF_VALUE):
            self._device_config.info.layer = xtm_layer
            msg = mido.Message(
                XTMMessageType.program_change.name,
                channel=self._device_config.info.global_channel.value,
                program=xtm_layer.value)
            self.write(msg)

    def set_mode(self, mode: XTMMode | int):
        if isinstance(mode, int):
            mode = XTMMode(mode)
        self._device_config.info.mode = mode
        mode_v = mode.value
        msg = mido.Message(type=XTMMessageType.sysex.name,
                           data=[0x40, 0x41, 0x42, 0x59, mode_v])
        self.write(msg)

    def write(self, msg: mido.Message | XTMMessageModel):
        if self._connected is False:
            self.connect_to_device()
        if self._connected is True:
            if self.b_verbose:
                print('output:', msg)
            self.output_port.send(msg)

