import sys
from typing import ClassVar

import pyqtgraph as pg
from qtpy import QtCore, QtWidgets

from snngine_v4.gui.common.python_guis_qt_widgets.power_bar import PowerBar
from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_button_wdgs import \
    XTMNoteButton
from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_ui_config import UIConfig


class XTMKnobWidget(PowerBar):

    gradient_colors: ClassVar[list[str]] = [
        '#FAAE7B',
        '#FAAE7B',
        '#E9A17A',
        '#E9A17A',

        '#D99579',
        '#D99579',
        '#C88878',
        '#C88878',

        '#B77B77',
        '#B77B77',
        '#A76F76',
        '#A76F76',

        '#966276',
        '#966276',
        '#865675',
        '#865675',

        '#754974',
        '#754974',
        '#643C73',
        '#643C73',

        '#543072',
        '#543072',
        '#432371',
        '#432371',
    ]

    def __init__(
            self, control_num, xtm_device,
            channel=11,
            steps=None, *args, **kwargs):

        if steps is None:
            steps = self.gradient_colors

        super().__init__(steps=steps, *args, **kwargs)

        self.cc = control_num
        self.xtm_device = xtm_device
        self.channel = channel

        self.button = XTMNoteButton(
            button_idx=control_num-1, xtm_device=self.xtm_device)
        self.spinbox = pg.SpinBox(value=0, int=True)
        self.spinbox.setMinimumWidth(50)

        self.label = QtWidgets.QLabel(str(self.cc))
        if sys.platform != 'win32':
            self.label.setContentsMargins(-5, 10, -5, 0)
            self.label.setMinimumWidth(14)
        else:
            self.label.setContentsMargins(-2, 10, -2, 0)
            self.label.setMaximumWidth(10)

        bottom_wdg = QtWidgets.QWidget()
        bottom_wdg.setLayout(QtWidgets.QHBoxLayout())
        bottom_wdg.setContentsMargins(0, 0, 0, 0)
        bottom_wdg.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().insertWidget(0, self.button)
        self.button.setFixedWidth(UIConfig.TEXT_BUTTON_WIDTH - 10)
        bottom_wdg.layout().addWidget(self.label)
        bottom_wdg.layout().addWidget(self.spinbox)

        self.layout().addWidget(bottom_wdg)
        self.setMinimum(0)
        self.setMaximum(127)

        self.connect_to_device_led()
        self.connect_to_spinbox()
        self.spinbox.valueChanged.connect(self.update_from_spinbox)

        self.setContentsMargins(-2, -2, -2, -2)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setFixedWidth(UIConfig.TEXT_BUTTON_WIDTH - 10)
        self.setMinimumHeight(UIConfig.MIN_KNOB_HEIGHT)

    def connect_to_device_led(self):
        self.valueChanged.connect(self.update_led)

    def disconnect_from_device_led(self):
        self.valueChanged.disconnect(self.update_led)

    def connect_to_spinbox(self):
        self.valueChanged.connect(self.update_spinbox)

    def disconnect_from_spinbox(self):
        self.valueChanged.disconnect(self.update_spinbox)

    def update_led(self):
        self.xtm_device.set_knob_value(
            channel=self.channel, control=self.cc, value=self.value())

    def update_spinbox(self):
        v = self._dial.value()
        self.spinbox.valueChanged.disconnect(self.update_from_spinbox)
        self.spinbox.setValue(v)
        self.spinbox.valueChanged.connect(self.update_from_spinbox)

    def update_from_spinbox(self):
        self.disconnect_from_spinbox()
        self.setValue(self.spinbox.value())
        self.connect_to_spinbox()

    def setMaximum(self, value: int):
        super().setMaximum(value)
        self.spinbox.setMaximum(value)

    def setMinimum(self, value: int):
        super().setMinimum(value)
        self.spinbox.setMinimum(value)

    def update_from_device(self):
        self.disconnect_from_device_led()
        value = self.xtm_device.device_config.get_knob_value(self.cc - 1)
        self.setValue(value)
        self.connect_to_device_led()
