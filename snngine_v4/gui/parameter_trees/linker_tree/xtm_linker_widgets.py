from __future__ import annotations

from enum import IntEnum, auto
from typing import Callable

from pyqtgraph import ComboBox
from pyqtgraph.parametertree import Parameter
from qtpy import QtCore, QtGui, QtWidgets

from snngine_v4.gui.devices.x_touch_mini.xtm_data_types import XTMLayer
from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_button_wdgs import \
    XTMNoteButton
from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_device_wdg import \
    (XTMDeviceWidget, XTMFaderWidget)
from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_knob_wdg import \
    XTMKnobWidget
from snngine_v4.gui.parameter_trees.linker_tree.controls_map import \
    ControllerAction
from snngine_v4.gui.parameter_trees.linker_tree.linker_tree import LinkerTree
from snngine_v4.gui.parameter_trees.linker_tree.linker_widget import \
    LinkerWidget
from snngine_v4.gui.parameter_trees.linker_tree.linker_window import \
    LinkerWindow


class XTMElementType(IntEnum):
    NONE = 0
    BUTTON = auto()
    KNOB = auto()
    FADER = auto()


class XTMLinkerInputWidget(QtWidgets.QWidget):

    sigValueSet = QtCore.Signal(object)

    layout: Callable[..., QtWidgets.QHBoxLayout]

    def __init__(self, xtm_device_wdg: XTMDeviceWidget,
                 parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        self.xtm_device_wdg = xtm_device_wdg

        self.type_combobox = ComboBox(
            items={x.name.title(): x for x in XTMElementType})

        self.choices = {
            XTMElementType.BUTTON: {
                str(k): v for (k, v) in self.xtm_device_wdg.buttons.items()},
            XTMElementType.KNOB: {
                str(k): v for (k, v) in self.xtm_device_wdg.knobs.items()},
            # XTMElementType.FADER: {
            #     'FADER': self.xtm_device_wdg.fader_widget},
        }

        self.element_combobox = ComboBox()
        self.layer_combobox = ComboBox(items={'A': XTMLayer.A,
                                              'B': XTMLayer.B})

        self.confirm_btn = QtWidgets.QPushButton("Confirm")
        self._confirmed = False

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setSpacing(1)
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.layout().addWidget(self.type_combobox)
        self.layout().addWidget(self.element_combobox)
        self.layout().addWidget(self.layer_combobox)
        self.layout().addWidget(self.confirm_btn)

        self.connect_comboboxes()
        self.confirm_btn.clicked.connect(self.on_confirm)

    def connect_comboboxes(self):
        self.type_combobox.currentTextChanged.connect(self.update_choices)
        self.element_combobox.currentTextChanged.connect(self.on_change)
        self.layer_combobox.currentTextChanged.connect(self.on_change)

    def disconnect_comboboxes(self):
        self.type_combobox.currentTextChanged.disconnect(self.update_choices)
        self.element_combobox.currentTextChanged.disconnect(self.on_change)
        self.layer_combobox.currentTextChanged.disconnect(self.on_change)

    def on_confirm(self):
        self._confirmed = True
        self.sigValueSet.emit(self)
        self.confirm_btn.setEnabled(False)
        self.sigValueSet.emit(self.element_combobox.value())

    def on_change(self):
        self._confirmed = False
        self.confirm_btn.setEnabled(True)

    def clear(self):
        self.type_combobox.setValue(XTMElementType.NONE)

    def b_is_empty(self):
        return self.type_combobox.value() == XTMElementType.NONE

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

    def to_label_string(self):
        return (
            f"{self.type_combobox.currentText()}"
            f"{self.element_combobox.currentText()}"
            f" (Layer{self.layer_combobox.currentText()})"
        )

    def update_choices(self):
        elt_type: XTMElementType = self.type_combobox.value()
        match elt_type:
            case XTMElementType.NONE \
                 | XTMElementType.FADER:
                self.element_combobox.setItems({})
                self.element_combobox.setVisible(False)
            case _:
                values = self.choices[elt_type]
                self.element_combobox.setItems(values)
                self.element_combobox.setVisible(True)

    def value(self):
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

    @property
    def b_has_input(self):
        return self.input_widget.b_is_empty()

    def clear_input_widget(self):
        self.input_widget.clear()

    @property
    def input_object(self):
        return self.input_widget.element_combobox.value()

    @property
    def input_object_string(self):
        return self.input_object.to_label_string()

    def make_input_widget(self):
        return XTMLinkerInputWidget(xtm_device_wdg=self.xtm_device_wdg,)

    @property
    def sig_input_changed(self):
        return self.input_widget.sigValueSet

    def _update_input_widget(self, controller: ControllerAction):
        self.input_widget.load_element(controller.input_obj)


class XTMLinkerWindow(LinkerWindow):

    def __init__(self,
                 linker_tree: LinkerTree,
                 window_title='X Touch Mini Controls',
                 **kwargs):

        self.xtm_device_widget = XTMDeviceWidget(
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

