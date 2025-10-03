from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from pyqtgraph import ComboBox
from pyqtgraph.parametertree import Parameter
from qtpy import QtWidgets, QtGui
from qtpy.QtWidgets import QSizePolicy

from snngine_v4.gui.parameter_trees.linker_tree.controls_map import \
    (ControllerAction, ControllerActionType, ParameterControls)


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

    def __init__(self,
                 parameter: Parameter,
                 linker_tree: LinkerTree,
                 exists_text_prefix='Controller already linked',
                 input_label='Short Cut: ',
                 b_verbose: bool = False,
                 **kwargs):
        super().__init__(**kwargs)

        self.b_verbose = b_verbose
        self._controller = None
        self.linker_tree = linker_tree
        self._parameter = parameter

        self.setLayout(QtWidgets.QFormLayout())
        self.type_combo = ComboBox()
        self.all_types_items = {
            x.name.title(): x for x in ControllerActionType
        }
        self.type_combo.setItems(self.all_types_items)

        self.binding_exists_label_text_base = exists_text_prefix
        self.binding_exists_label = self.make_binding_exists_label()
        self.binding_exists_label.setVisible(False)

        self.clear_btn = QtWidgets.QPushButton('Clear')
        self.save_button = QtWidgets.QPushButton('Save')
        self.delete_button = QtWidgets.QPushButton('X')
        self.delete_button.setStyleSheet(
            f"background-color: rgb(200,25,25);")
        self.save_button.setSizePolicy(QSizePolicy.Policy.Expanding,
                                       QSizePolicy.Policy.Expanding,)
        self.save_button.setEnabled(False)

        self.input_widget = self.make_input_widget()

        h_layout = QtWidgets.QHBoxLayout()
        h_layout.addWidget(self.save_button)
        h_layout.addWidget(self.delete_button)

        self.layout().addRow('Type: ', self.type_combo)
        self.layout().addRow(input_label, self.input_widget)
        self.layout().addWidget(self.binding_exists_label)
        self.layout().addRow(self.clear_btn, h_layout)
        self.setMinimumWidth(400)
        self.setSizePolicy(QSizePolicy.Policy.Fixed,
                           QSizePolicy.Policy.Fixed,)

        self.connect_inputs()
        self.clear_btn.clicked.connect(self.disconnect_parameter)
        self.save_button.clicked.connect(self.save_controller)

    @property
    def action_id(self):
        return ControllerAction.cls_action_id(self.input_object)

    @property
    def b_has_input(self):
        raise NotImplementedError()

    def connect_inputs(self):
        self.type_combo.currentTextChanged.connect(self.on_input_change)
        self.sig_input_changed.connect(self.on_input_change)

    def disconnect_inputs(self):
        self.type_combo.currentTextChanged.disconnect(self.on_input_change)
        self.sig_input_changed.disconnect(self.on_input_change)

    def disconnect_parameter(self):
        if self._controller is not None:
            prev_controller = self._controller
            self._controller = None
            controls: ParameterControls = self.linker_tree.controls_map[
                self._parameter]
            ctrl: ControllerAction = controls.pop(self.action_id)
            self.linker_tree.controls_map.all_actions.pop(self.action_id)
            if ctrl is not prev_controller:
                raise AssertionError
            ctrl.disconnect_parameter()
        self._parameter = None

        self.clear()

    def clear(self):
        self.input_widget.clear()
        self.input_widget.setEnabled(True)
        self.type_combo.setEnabled(True)

    @property
    def input_object(self):
        raise NotImplementedError()

    def load_controller(self, controller: ControllerAction):
        # if self._controller is not None:
        self.disconnect_inputs()
        self.type_combo.setValue(controller.action_type)
        self.input_widget.setKeySequence(controller.input_obj)
        self.save_button.setEnabled(False)
        self.input_widget.setEnabled(False)
        self.type_combo.setEnabled(False)
        self._controller = controller
        self._parameter = self._controller.parameter
        self.connect_inputs()

    def make_binding_exists_label(self):
        return BindingExistsLabel(self.binding_exists_label_text_base)

    def make_input_widget(self):
        raise NotImplementedError()

    def make_controller(self) -> ControllerAction:
        action = ControllerAction(
            input_obj=self.input_object,
            action_type=self.type_combo.value(),
            parameter=self._parameter,
            window=self.linker_tree.window())
        return action

    def on_input_change(self):
        b_has_input = self.b_has_input

        b_action_exists = False
        b_action_is_self = False

        if b_has_input:
            b_action_exists = (
                self.linker_tree.controls_map.b_action_exists(
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

        self.save_button.setEnabled(b_has_input
                                    and (not b_action_exists)
                                    and (not b_action_is_self))

    @property
    def parameter(self):
        return self._parameter

    @parameter.setter
    def parameter(self, value):
        self._controller = None
        self._parameter = value
        self.clear()

    @property
    def sig_input_changed(self):
        raise NotImplementedError()

    @staticmethod
    def parameter_label_text(par: Parameter):
        text = par.name()
        parent = par.parent()
        while parent:
            text = parent.name() + '.' + text
            parent = parent.parent()
        return text

    def save_controller(self):
        new_action = self.make_controller()
        self._controller = self.linker_tree.controls_map.add_controller(
            ctrl_or_parameter=new_action, )
        self.save_button.setEnabled(False)
        self.input_widget.setEnabled(False)
        self.type_combo.setEnabled(False)

    def update_binding_exists_label(self, b_bind_label_visible):
        self.binding_exists_label.setVisible(b_bind_label_visible)
        if b_bind_label_visible:
            ctrl = self.linker_tree.controls_map.get_controller(
                parameter=None,
                obj=self.input_object)
            binding_txt = (
                self.input_object.toString(),
                self.binding_exists_label_text_base,
                self.parameter_label_text(ctrl.parameter),
                f"{ctrl.action_type.name}",)
        else:
            binding_txt = ''
        self.binding_exists_label.setText(binding_txt)


class ShortCutWidget(LinkerWidget):

    input_widget: QtWidgets.QKeySequenceEdit

    def __init__(self,
                 parameter: Parameter,
                 linker_tree: LinkerTree,
                 input_label='Short Cut: ',
                 exists_text_prefix=' already set to ',
                 max_sequence_length=1,
                 **kwargs):
        self.max_sequence_length = max_sequence_length
        super().__init__(exists_text_prefix=exists_text_prefix,
                         linker_tree=linker_tree,
                         parameter=parameter,
                         input_label=input_label, **kwargs)

    @property
    def b_has_input(self):
        return not self.input_object.isEmpty()

    @property
    def sig_input_changed(self):
        return self.input_widget.keySequenceChanged

    def make_input_widget(self):
        shortcut_edit = QtWidgets.QKeySequenceEdit()
        shortcut_edit.setMaximumSequenceLength(self.max_sequence_length)
        return shortcut_edit

    @property
    def input_object(self) -> QtGui.QKeySequence:
        return self.input_widget.keySequence()


