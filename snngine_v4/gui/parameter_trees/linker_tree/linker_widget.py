from __future__ import annotations

from enum import Enum
from typing import Callable, TYPE_CHECKING

from pyqtgraph import ComboBox
from pyqtgraph.parametertree import Parameter
from qtpy import QtCore, QtWidgets, QtGui
from qtpy.QtWidgets import QSizePolicy
from sympy.core.cache import cached_property

from snngine_v4.gui.parameter_trees.linker_tree.controls_map import (
    ControllerAction,
    ControllerActionType
)
from snngine_v4.gui.parameter_trees.linker_tree.device_input_widget import \
    DeviceInputSelectorWidget
from snngine_v4.gui.parameter_trees.linker_tree.range_map_widget import \
    RangeMapWidget
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


if TYPE_CHECKING:
    from snngine_v4.gui.parameter_trees.linker_tree.linker_tree \
        import LinkerTree


class BindingExistsLabel(QtWidgets.QGroupBox):

    layout: Callable[..., QtWidgets.QVBoxLayout]

    def __init__(self, text, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setStyleSheet("QGroupBox {"
                           "border: 1px solid rgb(200,25,25);"
                           "border-radius: 3px}")

        self.keystroke_label = QtWidgets.QPushButton()
        self.keystroke_label.setDisabled(True)
        self.base_text_label = QtWidgets.QLabel(text)
        self.base_text_label.setAlignment(QtGui.Qt.AlignmentFlag.AlignCenter)
        self.parameter_label = QtWidgets.QPushButton()
        self.parameter_label.setSizePolicy(QSizePolicy.Policy.Expanding,
                                           QSizePolicy.Policy.Expanding,)
        self.parameter_label.setDisabled(True)
        self.plus_label = QtWidgets.QLabel("  for  ")
        self.plus_label.setSizePolicy(QSizePolicy.Policy.Minimum,
                                      QSizePolicy.Policy.Minimum,)
        self.plus_label.setAlignment(QtGui.Qt.AlignmentFlag.AlignCenter)

        self.action_type_label = QtWidgets.QPushButton()
        self.action_type_label.setDisabled(True)

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setSpacing(1)
        self.layout().setContentsMargins(2, 2, 2, 2)

        row0 = QtWidgets.QHBoxLayout()
        row1 = QtWidgets.QHBoxLayout()
        row0.setContentsMargins(0, 0, 0, 0)
        row1.setContentsMargins(0, 0, 0, 0)

        self.layout().addLayout(row0)
        self.layout().addLayout(row1)
        row0.addWidget(self.keystroke_label)
        row0.addWidget(self.base_text_label)
        row0.addWidget(self.action_type_label)
        row1.addWidget(self.plus_label)
        row1.addWidget(self.parameter_label)

    def __getattr__(self, item):
        if hasattr(self.base_text_label, item):
            raise NotImplementedError(
                self.__class__.__name__ + '.' + item)
        else:
            return super().__getattribute__(item)

    def setText(self, text: str):
        if isinstance(text, str):
            self.keystroke_label.setText('')
            self.base_text_label.setText(text)
            self.parameter_label.setText('')
            self.action_type_label.setText('')
        else:
            self.keystroke_label.setText(text[0])
            self.base_text_label.setText(text[1])
            self.parameter_label.setText(text[2])
            self.action_type_label.setText(text[3])


class LinkerWidget(QtWidgets.QWidget):

    layout: Callable[..., QtWidgets.QFormLayout]

    sigLinkSaved = QtCore.Signal(object, object)
    sigLinkDeleted = QtCore.Signal(object, object)
    sigWidgetDelete = QtCore.Signal(object)

    def __init__(self,
                 parameter: Parameter,
                 linker_tree: LinkerTree,
                 exists_text_prefix='Controller already linked',
                 input_label='Shortcut: ',
                 b_verbose: bool = False,
                 all_input_types=None,
                 **kwargs):
        super().__init__(**kwargs)

        self.b_verbose = b_verbose
        self._controller: ControllerAction | None = None
        self.linker_tree: LinkerTree | None = linker_tree
        self._parameter: Parameter | None = parameter

        self.setLayout(QtWidgets.QFormLayout())
        self.type_combo = ComboBox()
        if all_input_types is None:
            all_input_types = ControllerActionType

        self.has_range_map_wdg = ControllerActionType.VALUE in all_input_types
        self.all_types_items = {
            x.name.title(): x for x in all_input_types
        }

        self.type_combo.setItems(self.all_types_items)

        self.binding_exists_label_text_base = exists_text_prefix
        self.binding_exists_label = self.make_binding_exists_label()
        self.binding_exists_label.setVisible(False)

        self.clear_btn = QtWidgets.QPushButton('Clear')
        self.save_btn = QtWidgets.QPushButton('Save')
        self.delete_btn = QtWidgets.QPushButton('X')
        self.delete_btn.setStyleSheet(
            f"background-color: rgb(200,25,25);")
        self.save_btn.setSizePolicy(QSizePolicy.Policy.Expanding,
                                    QSizePolicy.Policy.Expanding, )
        self.save_btn.setEnabled(False)

        self.input_widget = self.make_input_widget()

        h_layout = QtWidgets.QHBoxLayout()
        h_layout.addWidget(self.save_btn)
        h_layout.addWidget(self.delete_btn)

        self.layout().addRow('Type: ', self.type_combo)

        self.layout().addRow(input_label, self.input_widget)
        self.layout().addWidget(self.binding_exists_label)
        self.layout().addRow(self.clear_btn, h_layout)
        self.setMinimumWidth(400)
        self.setSizePolicy(QSizePolicy.Policy.Fixed,
                           QSizePolicy.Policy.Fixed,)

        self.connect_inputs()

        def disconnect_parameter():
            self.disconnect_parameter(b_block_signal=False)

        self.clear_btn.clicked.connect(disconnect_parameter)

        def save_controller():
            self.save_controller(b_block_signal=False)

        self.save_btn.clicked.connect(save_controller)

        def emit_delete_widget():
            self.disconnect_parameter(b_block_signal=False)
            self.sigWidgetDelete.emit(self)

        self.delete_btn.clicked.connect(emit_delete_widget)

    @property
    def action_id(self):
        return ControllerAction.cls_action_id(self.input_object)

    @property
    def b_has_input(self):
        raise NotImplementedError()

    def connect_inputs(self):
        self.type_combo.currentTextChanged.connect(self.on_input_change)
        self.sig_input_changed.connect(self.on_input_change)

    @property
    def controller(self):
        return self._controller

    def clear(self):
        self.clear_input_widget()
        self.input_widget.setEnabled(True)
        self.type_combo.setEnabled(True)

    def clear_input_widget(self):
        raise NotImplementedError()

    def disconnect_inputs(self):
        self.type_combo.currentTextChanged.disconnect(self.on_input_change)
        self.sig_input_changed.disconnect(self.on_input_change)

    def disconnect_parameter(self, b_block_signal: bool,
                             b_raise=True):
        prev_controller = None
        if self._controller is not None:
            prev_controller = self._controller
            self._controller = None
            try:
                self.linker_tree.controls_map.remove_controller(
                    prev_controller, b_block_signal=False)
            except KeyError:
                if b_raise:
                    raise
        # self._parameter = None

        self.clear()

        if (prev_controller is not None) and (not b_block_signal):
            self.sigLinkDeleted.emit(self, prev_controller)

    @property
    def input_object(self):
        raise NotImplementedError()

    @property
    def input_object_string(self) -> str:
        raise NotImplementedError()

    def load_controller(self, controller: ControllerAction):

        self.disconnect_inputs()

        self._controller = controller
        self._parameter = controller.parameter
        self.reset_range()
        self._update_input_widget(controller=controller)
        self.type_combo.setValue(controller.action_type)
        self.input_widget.setEnabled(False)
        self.type_combo.setEnabled(False)
        self.save_btn.setEnabled(False)

        self.connect_inputs()

    def make_binding_exists_label(self):
        return BindingExistsLabel(self.binding_exists_label_text_base)

    def make_controller(self) -> ControllerAction:
        action = ControllerAction(
            input_obj=self.input_object,
            action_type=self.type_combo.value(),
            parameter=self._parameter,
            window=self.linker_tree.window())
        return action

    def make_input_widget(self) -> QtWidgets.QWidget:
        raise NotImplementedError()

    def on_input_change(self):

        if self.has_range_map_wdg:
            input_type = self.type_combo.value()
            match input_type:
                case ControllerActionType.VALUE:
                    if not self.range_map_wdg.isVisible():
                        self.range_map_wdg.setVisible(True)
                    self.range_map_wdg.setEnabled(True)
                case _:
                    if self.range_map_wdg.isVisible():
                        self.range_map_wdg.setEnabled(False)
                    else:
                        self.range_map_wdg.setVisible(False)

        b_has_input = self.b_has_input

        b_action_exists = False
        b_action_is_self = False

        if b_has_input:
            b_action_exists = (
                (self.linker_tree is not None)
                and self.linker_tree.controls_map.b_action_exists(
                    self.input_object))
            if b_action_exists and (self._controller is not None):
                potential_action = self.make_controller()
                b_action_is_self = (
                    self.linker_tree.controls_map.compare_controller(
                        # ctrl_or_parameter0=self.parameter,
                        ctrl_or_parameter0=self._controller,
                        ctrl_or_parameter1=potential_action
                    ))

        b_bind_label_visible = b_action_exists & (not b_action_is_self)
        self.update_binding_exists_label(
            b_bind_label_visible=b_bind_label_visible
        )

        self.save_btn.setEnabled(b_has_input
                                 and (not b_action_exists)
                                 and (not b_action_is_self))

    @cached_property
    def parameter_type_combo_items(self):
        num_dict = {
            # ControllerActionType.VALUE.name.title():
            #     ControllerActionType.VALUE,
            ControllerActionType.INCREASE.name.title():
                ControllerActionType.INCREASE,
            ControllerActionType.DECREASE.name.title():
                ControllerActionType.DECREASE,
        }
        toggle_dict = {ControllerActionType.TOGGLE.name.title():
                       ControllerActionType.TOGGLE}
        return {
            'bool': toggle_dict,
            'int': num_dict,
            'float': num_dict,
            Enum.__name__: num_dict,
        }

    @cached_property
    def parameter_type_combo_value_items(self):
        return {ControllerActionType.VALUE.name.title():
                ControllerActionType.VALUE}

    @cached_property
    def range_map_wdg(self) -> RangeMapWidget:
        self.has_range_map_wdg = True
        range_map_wdg = RangeMapWidget(
            label0="Device", label1="Host",)
        range_map_wdg.setVisible(False)
        self.layout().addRow(range_map_wdg)
        return range_map_wdg

    def reset_type_combobox(self):
        if self._parameter is None:
            parameter_type = ''
        else:
            parameter_type = self._parameter.opts[ParamOpts.KW.TYPE]
        items = self.parameter_type_combo_items.get(
            parameter_type, self.all_types_items)
        self.type_combo.setItems(items)

    def reset(self, parameter=None):
        self.disconnect_inputs()
        self._controller = None
        self._parameter = parameter
        self.reset_type_combobox()
        self.reset_range()
        self.clear()
        self.save_btn.setEnabled(False)
        self.connect_inputs()

    @classmethod
    def range_map_values(cls, parameter: Parameter):
        return DeviceInputSelectorWidget.range_map_values(parameter)

    def reset_range(self):
        if (self._parameter is not None) and self.has_range_map_wdg:
            opts = {}
            (minimum, maximum,
             minimum_allowed,
             maximum_allowed) = self.range_map_values(
                self._parameter)

            self.range_map_wdg.set_range1(
                minimum=minimum, maximum=maximum,
                minimum_allowed=minimum_allowed,
                maximum_allowed=maximum_allowed,
                **opts
            )

    def save_controller(self, b_block_signal: bool):
        new_action = self.make_controller()
        self._controller = self.linker_tree.controls_map.add_controller(
            ctrl_or_parameter=new_action, )
        self.save_btn.setEnabled(False)
        self.input_widget.setEnabled(False)
        self.type_combo.setEnabled(False)
        if not b_block_signal:
            self.sigLinkSaved.emit(self, self._controller)

    @property
    def sig_input_changed(self):
        raise NotImplementedError()

    def update_binding_exists_label(self, b_bind_label_visible):
        self.binding_exists_label.setVisible(b_bind_label_visible)
        if b_bind_label_visible:
            ctrl = self.linker_tree.controls_map.get_controller(
                parameter=None,
                obj=self.input_object)
            binding_txt = (
                self.input_object_string,
                self.binding_exists_label_text_base,
                ctrl.parameter_label,
                f"{ctrl.action_type.name}",)
        else:
            binding_txt = ''
        self.binding_exists_label.setText(binding_txt)

    def _update_input_widget(self, controller):
        raise NotImplementedError()


class ShortCutWidget(LinkerWidget):

    input_widget: QtWidgets.QKeySequenceEdit

    def __init__(self,
                 parameter: Parameter,
                 linker_tree: LinkerTree,
                 input_label='Shortcut: ',
                 exists_text_prefix=' already set to ',
                 max_sequence_length=1,
                 **kwargs):
        self.max_sequence_length = max_sequence_length
        super().__init__(exists_text_prefix=exists_text_prefix,
                         linker_tree=linker_tree,
                         parameter=parameter,
                         all_input_types=[
                             ControllerActionType.TOGGLE,
                             ControllerActionType.INCREASE,
                             ControllerActionType.DECREASE,
                         ],
                         input_label=input_label, **kwargs)

    @property
    def b_has_input(self):
        return not self.input_object.isEmpty()

    def clear_input_widget(self):
        self.input_widget.clear()

    @property
    def input_object(self) -> QtGui.QKeySequence:
        return self.input_widget.keySequence()

    @property
    def input_object_string(self):
        return self.input_object.toString()

    def make_input_widget(self):
        shortcut_edit = QtWidgets.QKeySequenceEdit()
        shortcut_edit.setMaximumSequenceLength(self.max_sequence_length)
        return shortcut_edit

    @property
    def sig_input_changed(self):
        return self.input_widget.keySequenceChanged

    def _update_input_widget(self, controller):
        self.input_widget.setKeySequence(controller.input_obj)


