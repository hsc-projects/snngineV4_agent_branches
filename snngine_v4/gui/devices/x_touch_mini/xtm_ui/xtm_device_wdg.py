from __future__ import annotations

import logging
from functools import cached_property

import mido
from pymeasure.display.log import LogHandler
from pymeasure.display.widgets.log_widget import HTMLFormatter
from qtpy import QtWidgets, QtCore

from snngine_v4.gui.devices.x_touch_mini.x_touch_mini_device import \
    XTouchMiniDevice
from snngine_v4.gui.devices.x_touch_mini.xtm_data_types import (
    XTMLayer,
    XTMMessageType
)
from snngine_v4.gui.devices.x_touch_mini.xtm_state import XTMMessageModel
from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_button_wdgs import (
    XTMButton,
    XTMConnectedButton,
    XTMLayerButton,
    XTMLedButton,
    XTMModeButton,
    XTMNoteButton
)
from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_cb_wdgs import \
    (XTMDeviceIdCb, XTMGlobalChannelCb)
from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_device_wdg_options import \
    XTMDeviceOptionsWindow
from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_fader_wdg import \
    XTMFaderWidget
from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_knob_wdg import \
    XTMKnobWidget
from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_ui_config import (
    UIConfig,
    XTMLabel
)


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class XTMDeviceWidget(QtWidgets.QWidget):

    fmt = '%(asctime)s : %(message)s (%(levelname)s)'
    datefmt = '%m/%d/%Y %I:%M:%S %p'

    def __init__(self, xtm_device=None, title=None, parent=None,
                 b_verbose: bool = True,
                 log_level=logging.DEBUG,
                 b_health_check: bool = True):

        self.b_verbose = b_verbose

        if xtm_device is None:
            xtm_device = XTouchMiniDevice(
                input_callback=self.input_message_callback)
        else:
            xtm_device.input_callback = self.input_message_callback

        self.xtm_device = xtm_device
        if title is None:
            title = self.xtm_device.NAME
        super().__init__(parent=parent)
        # noinspection PyUnresolvedReferences
        self.setWindowTitle(title)

        self.setLayout(QtWidgets.QHBoxLayout())

        self.knobs: dict[int, XTMKnobWidget] = {}
        self.buttons: dict[int, XTMLedButton | XTMNoteButton] = {}

        self.left_widget = QtWidgets.QWidget()

        self.left_widget_layout = QtWidgets.QGridLayout()
        self.left_widget.setLayout(self.left_widget_layout)
        self.layout().addWidget(self.left_widget)

        for i in range(8):
            knob_wdg = XTMKnobWidget(
                control_num=i+1, xtm_device=self.xtm_device)
            self.knobs[i + 1] = knob_wdg
            self.buttons[i] = knob_wdg.button
            self.left_widget_layout.addWidget(knob_wdg, 0, i)

        for i in range(8, 16):
            btn = XTMNoteButton(button_idx=i, xtm_device=self.xtm_device)
            self.buttons[btn.receive_data_note] = btn
            self.left_widget_layout.addWidget(btn, 1, i % 8)

        for i in range(16, 24):
            btn = XTMNoteButton(button_idx=i, xtm_device=self.xtm_device)
            self.buttons[btn.receive_data_note] = btn
            self.left_widget_layout.addWidget(btn, 2, i % 8)

        self.output_text_field = QtWidgets.QPlainTextEdit()

        self.output_text_field.setReadOnly(True)
        self.output_text_field.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum
        )
        self.output_text_field.setMaximumBlockCount(5)
        self.output_text_field.setMaximumHeight(110)
        self.log_level = log_level
        log.setLevel(self.log_level)
        log.info("ManagedWindow connected to logging")
        self.log_handler = LogHandler()
        self.log_handler.setFormatter(HTMLFormatter(
            fmt=self.fmt,
            datefmt=self.datefmt,
        ))
        self.log_handler.connect(self.output_text_field.appendHtml)
        logging.getLogger().addHandler(self.log_handler)
        self.output_text_field.setVisible(self.b_verbose)

        self.left_widget_layout.addWidget(self.output_text_field, 3, 0, 1, 8)

        self.fader_widget = XTMFaderWidget(xtm_device=self.xtm_device,
                                           b_verbose=b_verbose)
        self.layout().addWidget(self.fader_widget)

        right_widget = QtWidgets.QWidget()
        right_widget.setLayout(QtWidgets.QVBoxLayout())
        right_widget.layout().setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter)

        connected_label = XTMLabel('Connected: ', width_divider=1.4)
        self.connected_button = XTMConnectedButton(
            xtm_device=self.xtm_device, width_divider=4)
        connected_widget = QtWidgets.QWidget()
        connected_widget.setLayout(QtWidgets.QHBoxLayout())
        connected_widget.layout().addWidget(connected_label)
        connected_widget.layout().addWidget(self.connected_button)
        connected_widget.layout().setContentsMargins(0, 0, 0, 0)
        connected_widget.setContentsMargins(0, 0, 0, 0)

        self.read_info_button = XTMButton("Read Info")
        self.read_info_button.clicked.connect(
            self.xtm_device.send_read_device_info_command)

        self.options_btn = XTMButton("Options")
        self.options_btn.setCheckable(True)
        self.options_btn.clicked.connect(self.show_options)

        self.save_btn = XTMButton('Save', width_divider=2.08)
        self.save_btn.clicked.connect(self.save_device_config)

        self.load_btn = XTMButton('Load', width_divider=2.08)
        self.load_btn.clicked.connect(self.load_device_config)

        save_load_widget = QtWidgets.QWidget()
        save_load_widget.setLayout(QtWidgets.QHBoxLayout())
        save_load_widget.layout().addWidget(self.save_btn)
        save_load_widget.layout().addWidget(self.load_btn)
        save_load_widget.setContentsMargins(0, 0, 0, 0)
        save_load_widget.layout().setContentsMargins(0, 0, 0, 0)
        save_load_widget.setFixedWidth(UIConfig.TEXT_BUTTON_WIDTH)

        device_id_label = XTMLabel('Dev. ID: ', width_divider=2.1)
        device_id_label.setMargin(0)
        self.device_id_cb = XTMDeviceIdCb(xtm_device=self.xtm_device,
                                          width_divider=2.1)
        device_id_widget = QtWidgets.QWidget()
        device_id_widget.setLayout(QtWidgets.QHBoxLayout())
        device_id_widget.layout().addWidget(device_id_label)
        device_id_widget.layout().addWidget(self.device_id_cb)
        device_id_widget.layout().setContentsMargins(0, 0, 0, 0)
        device_id_widget.setContentsMargins(0, 0, 0, 0)

        self.global_channel_cb = (
            XTMGlobalChannelCb(xtm_device=self.xtm_device))

        self.mc_mode_button = XTMModeButton(xtm_device=self.xtm_device)
        self.channel_a_button = XTMLayerButton(
            xtm_layer=XTMLayer.A, xtm_device=self.xtm_device)
        self.channel_b_button = XTMLayerButton(
            xtm_layer=XTMLayer.B, xtm_device=self.xtm_device)

        right_widget.layout().addWidget(connected_widget)
        right_widget.layout().addWidget(save_load_widget)
        right_widget.layout().addWidget(self.read_info_button)
        right_widget.layout().addWidget(self.options_btn)
        right_widget.layout().addWidget(XTMLabel('Global Channel:'))
        right_widget.layout().addWidget(self.global_channel_cb)
        right_widget.layout().addWidget(device_id_widget)
        right_widget.layout().addWidget(self.mc_mode_button)
        right_widget.layout().addWidget(self.channel_a_button)
        right_widget.layout().addWidget(self.channel_b_button)

        self.layout().addWidget(right_widget)

        self.health_check()
        self.apply_device_config()
        self.health_check_timer = QtCore.QTimer(self)
        self.health_check_timer.timeout.connect(self.health_check)

        self.last_msg_time = 0

        if b_health_check:
            self.health_check_timer.start(2000)

    def apply_device_config(self):

        conf = self.xtm_device.device_config

        self.device_id_cb.update_from_device()
        self.global_channel_cb.update_from_device()
        self.mc_mode_button.update_from_device()
        self.channel_a_button.update_from_device()
        self.channel_b_button.update_from_device()

        for btn_conf in conf.encoder_values.buttons:
            btn: XTMNoteButton = self.buttons[btn_conf.note]
            btn.update_from_device()
        for knob_conf in conf.encoder_values.knobs:
            knob: XTMKnobWidget = self.knobs[knob_conf.cc]
            knob.update_from_device()
            knob.auto_value_reset_action.setChecked(
                conf.get_knob_auto_value_reset(knob_conf.cc - 1))
            knob.auto_increment_range_map_action.setChecked(
                conf.get_knob_auto_increment_range_map(knob_conf.cc - 1))

        self.fader_widget.update_from_device()

    def closeEvent(self, event):
        self.xtm_device.save_config()
        event.accept()

    def health_check(self):
        if self.xtm_device.connected is False:
            self.xtm_device.connect_to_device()
            self.apply_device_config()
        if self.xtm_device.connected != self.connected_button.b_ui_led_on:
            self.connected_button.update_from_device()

    def input_message_callback(
        self, msg: XTMMessageModel | mido.Message,
    ):
        if self.b_verbose:
            log.debug("[X-Touch-Mini] " + str(msg))

        self.xtm_device.device_config.update_from_message(msg)

        match msg.type:
            case XTMMessageType.control_change.name:
                if msg.control == 9:
                    wdg: XTMFaderWidget = self.fader_widget
                else:
                    wdg: XTMKnobWidget = self.knobs[msg.control]
                wdg.update_from_device()

            case XTMMessageType.note_on.name | XTMMessageType.note_off.name:
                btn = self.buttons[msg.note]
                btn.update_from_device()

            case XTMMessageType.sysex.name:
                self.apply_device_config()
            case _:
                pass
        return msg

    def load_device_config(self, a0):
        self.xtm_device.load_config()
        self.apply_device_config()

    @cached_property
    def options_window(self) -> XTMDeviceOptionsWindow:
        wdg = XTMDeviceOptionsWindow(
            window_title=self.windowTitle() + " - Options",
            device_widget=self)
        return wdg

    def save_device_config(self, a0):
        self.xtm_device.save_config()

    def show_options(self):
        value = self.options_btn.isChecked()
        self.options_window.setVisible(value)

        if value is True:
            point = self.rect().bottomRight()
            global_point = self.mapToGlobal(point / 2)
            self.options_window.move(
                global_point - QtCore.QPoint(
                    self.options_window.width() // 2,
                    self.options_window.height() // 2))


if __name__ == "__main__":
    import qdarktheme

    app_ = QtWidgets.QApplication([''])
    qdarktheme.setup_theme('dark')
    device_ = XTouchMiniDevice()
    # window_ = QtWidgets.QMainWindow()
    x_wdg_ = XTMDeviceWidget(
        b_verbose=True,
        xtm_device=device_)
    # window_.setCentralWidget(x_wdg_)
    x_wdg_.show()
    app_.exec()
