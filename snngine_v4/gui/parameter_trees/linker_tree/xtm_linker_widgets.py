from __future__ import annotations

from copy import copy
from enum import IntEnum, auto
from functools import cached_property
from typing import Callable, TYPE_CHECKING

import numpy as np
from pyqtgraph import ComboBox
from pyqtgraph.parametertree import Parameter
from qtpy import QtCore, QtWidgets

from snngine_v4.gui.devices.x_touch_mini.xtm_data_types import XTMLayer
from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_button_wdgs import \
    XTMNoteButton
from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_device_wdg import (
    XTMDeviceWidget
)
from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_fader_wdg import \
    XTMFaderWidget
from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_knob_wdg import \
    XTMKnobWidget
from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_ui_config import \
    XTMRangeMapWidget
from snngine_v4.gui.parameter_trees.linker_tree.device_input_widget import (
    DeviceInputSelectorWidget)
from snngine_v4.gui.parameter_trees.linker_tree.linker_widget import \
    LinkerWidget
from snngine_v4.gui.parameter_trees.linker_tree.linker_window import \
    LinkerWindow
from snngine_v4.gui.parameter_trees.linker_tree.range_map_widget import (
    RangeMap,
    RangeMapWidget
)
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


if TYPE_CHECKING:
    from snngine_v4.gui.parameter_trees.linker_tree.controls_map import (
        ControllerAction)
    from snngine_v4.gui.parameter_trees.linker_tree.linker_tree import (
        LinkerTree)


class XTMElementType(IntEnum):
    NONE = 0
    BUTTON = auto()
    KNOB = auto()
    FADER = auto()


class XTMLinkerInputWidget(DeviceInputSelectorWidget):

    layout: Callable[..., QtWidgets.QHBoxLayout]

    def __init__(self, xtm_device_wdg: XTMDeviceWidget,
                 parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        self.xtm_device_wdg = xtm_device_wdg

        self.number_prefix = "Nr. "
        self.layer_a_str = " Layer: A "
        self.layer_b_str = " Layer: B "

        self.type_combobox = ComboBox(
            items={x.name.title(): x for x in XTMElementType})
        self.type_combobox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.choices = {
            XTMElementType.BUTTON: {
                self.number_prefix + str(k): v for (k, v)
                in self.xtm_device_wdg.buttons.items()},
            XTMElementType.KNOB: {
                self.number_prefix + str(k): v for (k, v) in
                self.xtm_device_wdg.knobs.items()},
        }

        self.element_combobox = ComboBox()
        self.layer_combobox = ComboBox(items={
            self.layer_a_str: XTMLayer.A,
            self.layer_b_str: XTMLayer.B
        })
        self.layer_combobox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.stretch_item = None

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setSpacing(1)
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.layout().addWidget(self.type_combobox)
        self.layout().addStretch()
        self.layout().addWidget(self.element_combobox)
        self.layout().addWidget(self.layer_combobox)

        self._has_stretch = True

        self.update_choices()
        self.connect_comboboxes()

        self.range_map: RangeMap | None = None

    @property
    def action_id_str(self):
        return self.as_label_string()

    def as_label_string(self):
        second_text = self.element_combobox.currentText()
        if second_text != '':
            second_text = f"({second_text.replace(self.number_prefix, '')})"
        return (
            f"{self.type_combobox.currentText()};"
            f"{second_text};"
            f"({self.layer_combobox.currentText()})"
        )

    def update_target(self):
        element = self.value()
        if isinstance(element, (XTMKnobWidget, XTMFaderWidget)):
            element.range_map_widget.set_range1(
                self.range_map.min1, self.range_map.max1,
                self.range_map.hard_min1, self.range_map.hard_max1,
            )
        else:
            pass

    def interpret_label_string(self, label_str: str):

        self.disconnect_comboboxes()

        parts = label_str.split(';')
        type_str = parts[0]
        element_str = parts[1].strip('()') if len(parts) > 1 else ''
        layer_str = parts[2].strip('()') if len(parts) > 2 else ''

        self.type_combobox.setValue(XTMElementType[type_str.upper()])

        self.update_choices()

        if element_str != '':
            self.element_combobox.setCurrentText(
                self.number_prefix + element_str)

        match layer_str:
            case self.layer_a_str:
                self.layer_combobox.setValue(XTMLayer.A)
            case self.layer_b_str:
                self.layer_combobox.setValue(XTMLayer.B)
            case _:
                raise ValueError(f"Unknown layer string: {layer_str}")

        self.connect_comboboxes()

    def b_is_empty(self):
        return self.type_combobox.value() == XTMElementType.NONE

    def clear(self):
        self.type_combobox.setValue(XTMElementType.NONE)

    def connect_comboboxes(self):
        self.type_combobox.currentTextChanged.connect(self.update_choices)
        self.element_combobox.currentTextChanged.connect(self.on_change)
        self.layer_combobox.currentTextChanged.connect(self.on_change)

    def disconnect_comboboxes(self):
        self.type_combobox.currentTextChanged.disconnect(self.update_choices)
        self.element_combobox.currentTextChanged.disconnect(self.on_change)
        self.layer_combobox.currentTextChanged.disconnect(self.on_change)

    def load_element(self, element):

        self.disconnect_comboboxes()

        if isinstance(element, XTMKnobWidget):
            self.type_combobox.setValue(XTMElementType.KNOB)
            self.update_choices()
            self.element_combobox.setCurrentText(str(element.cc))
        elif isinstance(element, XTMNoteButton):
            self.type_combobox.setValue(XTMElementType.KNOB)
            self.update_choices()
            self.element_combobox.setCurrentText(str(element.button_index))
        elif isinstance(element, XTMFaderWidget):
            self.type_combobox.setValue(XTMElementType.FADER)
            self.update_choices()
        elif element is None:
            self.type_combobox.setValue(XTMElementType.NONE)
            self.update_choices()
        else:
            raise TypeError(
                f"Unknown element type: {element} ({type(element)})")

        self.connect_comboboxes()

    def make_device_controller(self) -> QtCore.Signal:
        element = self.value()
        # controller = DeviceController(self)
        if isinstance(element, XTMKnobWidget):
            signal = element.spinbox.valueChanged
        elif isinstance(element, XTMNoteButton):
            signal = element.sigDeviceInput
        elif isinstance(element, XTMFaderWidget):
            signal = element.fader_item.widget.valueChanged
        else:
            raise TypeError(
                f"Unknown element type: {element} ({type(element)})")
        return signal

    def on_change(self):
        self.sigValueSet.emit(self)

    @classmethod
    def range_map_values(cls, parameter: Parameter):
        par_opts = parameter.opts
        if (((span := par_opts.get(ParamOpts.KW.SPAN)) is not None)
                and len(span) > 128):
            value_idx = np.argmin(np.abs(
                span - par_opts.get(ParamOpts.KW.VALUE, span[0])))
            idx_factor = value_idx // 128
            minimum = span[idx_factor * 128]
            maximum = span[min(len(span), (idx_factor + 1) * 128)]
            minimum_allowed = span[0]
            maximum_allowed = span[-1]
            return minimum, maximum, minimum_allowed, maximum_allowed
        else:
            return super().range_map_values(parameter)

    def update_choices(self):
        elt_type: XTMElementType = self.type_combobox.value()
        match elt_type:
            case XTMElementType.NONE \
                 | XTMElementType.FADER:
                self.element_combobox.setItems({})
                self.element_combobox.setVisible(False)
                is_fader = elt_type == XTMElementType.FADER
                self.layer_combobox.setVisible(is_fader)

                if self.stretch_item is not None:
                    self.layout().insertItem(1, self.stretch_item)
                    self.stretch_item = None
            case _:
                values = self.choices[elt_type]
                self.element_combobox.setItems(values)
                self.element_combobox.setVisible(True)
                self.layer_combobox.setVisible(True)
                if self.stretch_item is None:
                    self.stretch_item = self.layout().itemAt(1)
                    self.layout().takeAt(1)
        self.on_change()

    def value(self) -> XTMKnobWidget | XTMNoteButton | XTMFaderWidget:
        elt_type: XTMElementType = self.type_combobox.value()
        match elt_type:
            case XTMElementType.NONE:
                raise ValueError(" No element selected ")
            case XTMElementType.FADER:
                return self.xtm_device_wdg.fader_widget
            case _:
                return self.element_combobox.value()


class XTMLinkerWidget(LinkerWidget):

    input_widget: XTMLinkerInputWidget

    def __init__(self,
                 parameter: Parameter,
                 linker_tree: LinkerTree,
                 xtm_device_wdg: XTMDeviceWidget,
                 input_label='Shortcut: ',
                 exists_text_prefix=' already set to ',
                 **kwargs):

        self.xtm_device_wdg = xtm_device_wdg
        super().__init__(exists_text_prefix=exists_text_prefix,
                         linker_tree=linker_tree,
                         parameter=parameter,
                         input_label=input_label, **kwargs)

        self.range_map_wdg.set_range0(
            0, 127, 0, 127,
            step=1, int=True)

    @property
    def b_has_input(self):
        return not self.input_widget.b_is_empty()

    def clear_input_widget(self):
        self.input_widget.clear()

    def connect_inputs(self):
        super().connect_inputs()
        self.input_widget.type_combobox.currentTextChanged.connect(
            self.reset_type_combobox)
        self.input_widget.type_combobox.currentTextChanged.connect(
            self.on_input_change)

    def disconnect_inputs(self):
        super().disconnect_inputs()
        self.input_widget.type_combobox.currentTextChanged.disconnect(
            self.reset_type_combobox)
        self.input_widget.type_combobox.currentTextChanged.disconnect(
            self.on_input_change)

    @property
    def input_object(self):
        # return self.input_widget.element_combobox.value()
        return self.input_widget

    @property
    def input_object_string(self):
        return self.input_object.action_id_str

    def make_input_widget(self):
        return XTMLinkerInputWidget(xtm_device_wdg=self.xtm_device_wdg,)

    @cached_property
    def range_map_wdg(self) -> XTMRangeMapWidget:
        self.has_range_map_wdg = True
        range_map_wdg = XTMRangeMapWidget(label1="Parameter",)
        range_map_wdg.setVisible(False)
        self.layout().insertRow(2, range_map_wdg)
        return range_map_wdg

    @classmethod
    def range_map_values(cls, parameter: Parameter):
        return XTMLinkerInputWidget.range_map_values(parameter)

    def reset_type_combobox(self):
        if self.input_widget.type_combobox.value() in [
                XTMElementType.BUTTON, XTMElementType.NONE]:
            super().reset_type_combobox()
        else:
            items = self.parameter_type_combo_value_items
            self.type_combo.setItems(items)

    def save_controller(self, b_block_signal: bool):
        self.input_object.range_map = copy(self.range_map_wdg.range_map)
        super().save_controller(b_block_signal=b_block_signal)

    @property
    def sig_input_changed(self):
        return self.input_widget.sigValueSet

    def _update_input_widget(self, controller: ControllerAction):
        self.input_widget.load_element(controller.input_obj.value())


class XTMLinkerWindow(LinkerWindow):

    def __init__(self,
                 linker_tree: LinkerTree,
                 window_title='X Touch Mini Controls',
                 **kwargs):

        self.xtm_device_widget = XTMDeviceWidget(
            b_verbose=False,
            b_health_check=False
        )
        self.xtm_device_widget.setVisible(False)

        super().__init__(linker_tree=linker_tree,
                         window_title=window_title, **kwargs)

        self.show_widget_btn = QtWidgets.QPushButton("Show device")
        self.header.layout().addWidget(self.show_widget_btn)

        def show_xtm():
            self.xtm_device_widget.setVisible(
                not self.xtm_device_widget.isVisible()
            )
        self.show_widget_btn.clicked.connect(show_xtm)

    def make_widget(self,) -> XTMLinkerWidget:
        return XTMLinkerWidget(parameter=self._parameter,
                               linker_tree=self.linker_tree,
                               xtm_device_wdg=self.xtm_device_widget)

