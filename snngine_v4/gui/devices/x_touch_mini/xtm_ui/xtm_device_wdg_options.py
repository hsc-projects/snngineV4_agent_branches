from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from qtpy import QtCore, QtGui, QtWidgets


if TYPE_CHECKING:
    from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_device_wdg import (
        XTMDeviceWidget)


class XTMDeviceOptionsWindow(QtWidgets.QWidget):

    layout: Callable[..., QtWidgets.QFormLayout]

    def __init__(self,
                 window_title,
                 *args,
                 device_widget: XTMDeviceWidget, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle(window_title)
        self.setWindowModality(
            QtCore.Qt.WindowModality.ApplicationModal)

        self.device_widget: XTMDeviceWidget = device_widget

        self.display_group = QtWidgets.QGroupBox("Display")
        self.show_button_numbers_checkbox = QtWidgets.QCheckBox(
            "Button numbers")
        self.show_output_field = QtWidgets.QCheckBox("Show Messages")
        self.show_output_field.setChecked(self.device_widget.b_verbose)

        self.show_button_numbers_checkbox.clicked.connect(
            self.show_button_numbers)
        self.show_output_field.clicked.connect(
            self.show_log_output)

        self.setLayout(QtWidgets.QFormLayout())
        display_group_layout = QtWidgets.QVBoxLayout()
        self.display_group.setLayout(display_group_layout)
        display_group_layout.addWidget(self.show_button_numbers_checkbox)
        display_group_layout.addWidget(self.show_output_field)
        self.layout().addRow(self.display_group)

        # knob_options_layout0 = QtWidgets.QHBoxLayout()
        # knob_options_layout1 = QtWidgets.QHBoxLayout()

    def closeEvent(self, event: QtGui.QCloseEvent):
        self.device_widget.options_btn.setChecked(False)
        super().closeEvent(event)

    def show_button_numbers(self, value):
        for btn in self.device_widget.buttons.values():
            if value is True:
                btn.setText(str(btn.button_index))
            else:
                btn.setText("")

    def show_log_output(self, value):
        self.device_widget.b_verbose = value
        self.device_widget.output_text_field.setVisible(value)
