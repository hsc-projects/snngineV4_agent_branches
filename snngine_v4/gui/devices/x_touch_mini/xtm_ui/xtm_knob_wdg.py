import sys
from functools import cached_property
from typing import ClassVar

import pyqtgraph as pg
from qtpy import QtCore, QtGui, QtWidgets

from snngine_v4.gui.common.python_guis_qt_widgets.power_bar import PowerBar
from snngine_v4.gui.devices.x_touch_mini.x_touch_mini_device import \
    XTouchMiniDevice
from snngine_v4.gui.devices.x_touch_mini.xtm_state import XTMKnobModel
from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_button_wdgs import \
    XTMNoteButton
from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_ui_config import (
    UIConfig,
    XTMRangeMapWidget
)
from snngine_v4.gui.parameter_trees.linker_tree.range_map_widget import (
    RangeMap
)


class XTMKnobWidget(PowerBar):

    # sigValueChanged = QtCore.Signal(object)

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
            channel=11, b_range_map: bool = True,
            steps=None, *args, **kwargs):

        if steps is None:
            steps = self.gradient_colors

        super().__init__(steps=steps, *args, **kwargs)

        self.cc = control_num
        self.xtm_device: XTouchMiniDevice = xtm_device
        self.channel = channel

        self._range_map: RangeMap | None = None

        self.button = XTMNoteButton(
            button_idx=control_num-1, xtm_device=self.xtm_device)
        self.spinbox = pg.SpinBox(value=0, int=True)
        self.spinbox.setMinimumWidth(50)

        self.label = QtWidgets.QLabel(str(self.cc))
        if sys.platform != 'win32':
            # self.label.setContentsMargins(-5, 10, -5, 0)
            # self.label.setMinimumWidth(14)
            self.label.setContentsMargins(-5, 5, -5, 0)
            self.label.setMaximumWidth(10)
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
        self.max_count = 0
        self.min_count = 0
        self.b_max_prev = False
        self.b_min_prev = False

        self.connect_to_device_led()
        self.connect_to_spinbox()
        self.spinbox.valueChanged.connect(self.update_from_spinbox)

        self.setContentsMargins(-2, -2, -2, -2)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setFixedWidth(UIConfig.TEXT_BUTTON_WIDTH - 10)
        self.setMinimumHeight(UIConfig.MIN_KNOB_HEIGHT)

        # self.contextMenu: QtWidgets.QMenu | None = None
        if b_range_map:
            self.range_map_widget.setVisible(False)

    @cached_property
    def knob_config(self) -> XTMKnobModel:
        return self.xtm_device.device_config.encoder_values.knobs[self.cc]

    def connect_to_device_led(self):
        self.valueChanged.connect(self.update_led)

    def connect_to_spinbox(self):
        self.valueChanged.connect(self.update_spinbox)

    @cached_property
    def auto_increment_range_map_action(self):
        action = QtGui.QAction("Auto Range Increment")
        action.setCheckable(True)
        action.triggered.connect(self.set_auto_increment_range_map)
        action.setChecked(self.get_auto_value_reset())
        return action

    @cached_property
    def auto_value_reset_action(self):
        action = QtGui.QAction("Auto Value Reset")
        action.setCheckable(True)
        action.triggered.connect(self.set_auto_value_reset)
        action.setChecked(self.get_auto_value_reset())
        return action

    @cached_property
    def show_range_map_action(self):
        action = QtGui.QAction("Range Map")
        action.setCheckable(True)
        action.triggered.connect(self.show_range_map_widget)
        return action

    # noinspection PyPep8Naming
    @cached_property
    def contextMenu(self):
        menu = QtWidgets.QMenu()
        menu.addAction(self.auto_value_reset_action)
        menu.addAction(self.auto_increment_range_map_action)
        menu.addAction(self.show_range_map_action)
        return menu

    def contextMenuEvent(self, ev):
        self.contextMenu.exec(ev.globalPos())

    def disconnect_from_device_led(self):
        self.valueChanged.disconnect(self.update_led)

    def disconnect_from_spinbox(self):
        self.valueChanged.disconnect(self.update_spinbox)

    @cached_property
    def range_map_widget(self):
        wdg = XTMRangeMapWidget.from_spinbox(
            spinbox=self.spinbox,)
        wdg.setWindowTitle(f"Knob Nr. {self.cc}")
        self._range_map = wdg.range_map
        wdg.setVisible(False)
        wdg.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        return wdg

    def set_auto_increment_range_map(self, value):
        self.xtm_device.device_config.set_knob_auto_increment_range_map(
            self.cc - 1, value=value)

    def get_auto_increment_range_map(self):
        return self.xtm_device.device_config.get_knob_auto_increment_range_map(
            self.cc - 1)

    def set_auto_value_reset(self, value):
        self.xtm_device.device_config.set_knob_auto_value_reset(
            self.cc - 1, value=value)

    def get_auto_value_reset(self):
        return self.xtm_device.device_config.get_knob_auto_value_reset(
            self.cc - 1)

    def setMaximum(self, value: int):
        super().setMaximum(value)
        self.spinbox.setMaximum(value)

    def setMinimum(self, value: int):
        super().setMinimum(value)
        self.spinbox.setMinimum(value)

    def show_range_map_widget(self, value):
        self.range_map_widget.setVisible(value)

    def update_from_device(self):
        self.disconnect_from_device_led()

        b_update_span = False
        threshold = 3

        value = self.xtm_device.device_config.get_knob_value(self.cc - 1)

        b_reset_allowed = self.get_auto_value_reset()
        b_increment_allowed = self.get_auto_increment_range_map()
        b_check_span = b_reset_allowed or b_increment_allowed
        if not b_check_span:
            self.setValue(value)
            self.connect_to_device_led()
            return

        if value == self._dial.maximum():

            if not self.b_max_prev:
                self.b_max_prev = True
            elif b_check_span:
                self.max_count += 1
                # print(self.max_count)
                b_update_span = self.max_count > threshold
        else:
            self.b_max_prev = False
            self.max_count = 0

            if value == self._dial.minimum():
                if not self.b_min_prev:
                    self.b_min_prev = True
                elif b_check_span:
                    self.min_count += 1
                    # print(self.min_count)
                    b_update_span = self.min_count > threshold
            else:
                self.min_count = 0
                self.b_min_prev = False

        if not b_update_span:
            self.setValue(value)
            self.connect_to_device_led()
        else:
            self.connect_to_device_led()
            hard_max_reached = False
            hard_min_reached = False
            offset = 0
            if b_increment_allowed:
                (offset,
                 hard_min_reached,
                 hard_max_reached) = self._range_map.increment_range1(
                    dir_sign=1 if (self.max_count > threshold) else -1)

                self.range_map_widget.update_widgets()

            if hard_min_reached or hard_max_reached:
                print(offset)
                if hard_min_reached:
                    self.setValue(self._dial.minimum() - offset)
                elif hard_max_reached:
                    self.setValue(self._dial.maximum() - offset + 1)

            else:
                if self.max_count > threshold:
                    self.setValue(self._dial.minimum())
                else:
                    self.setValue(self._dial.maximum())
            self.min_count = 0
            self.max_count = 0

    def update_from_spinbox(self):
        self.disconnect_from_spinbox()
        if not self._range_map:
            self.setValue(self.spinbox.value())
        else:
            source_value = self._range_map.convert_to_source(
                self.spinbox.value())
            self.setValue(source_value)
        self.connect_to_spinbox()

    def update_led(self):
        self.xtm_device.set_knob_value(
            channel=self.channel, control=self.cc, value=self.value())

    def update_spinbox(self):
        v = self._dial.value()
        self.spinbox.valueChanged.disconnect(self.update_from_spinbox)
        if not self._range_map:
            self.spinbox.setValue(v)
        else:
            target_value = self._range_map.convert_to_target(v)
            self.spinbox.setValue(target_value)
        self.spinbox.valueChanged.connect(self.update_from_spinbox)



