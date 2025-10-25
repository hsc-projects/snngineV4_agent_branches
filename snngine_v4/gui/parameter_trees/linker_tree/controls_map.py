from dataclasses import dataclass, field
from enum import IntEnum, auto
from typing import Any, Callable, ClassVar

from qtpy import QtCore
from qtpy.QtGui import QKeySequence, QShortcut
from qtpy.QtWidgets import QWidget
from pyqtgraph.parametertree import Parameter

from snngine_v4.gui.common.qobject_dicts import QObjectDictSignals
from snngine_v4.gui.parameter_trees.linker_tree.device_input_widget import (
    DeviceInputSelectorWidget
)
from snngine_v4.utils.containers.configurable_dict import (ConfigurableDict,
                                                           DictContainerConfig)
from snngine_v4.utils.containers.mappings import (Object2ObjectMap,
                                                  ObjectMapConfig)
from snngine_v4.utils.core_utils import type_assertion
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


class ControllerActionType(IntEnum):
    TOGGLE = 0
    VALUE = auto()
    INCREASE = auto()
    DECREASE = auto()
    # EDIT = auto()
    # FOCUS = auto()


@dataclass(kw_only=True)
class ControllerAction:

    action_type: ControllerActionType
    input_obj: QKeySequence | DeviceInputSelectorWidget
    parameter: Parameter
    window: QWidget
    controller_obj: QShortcut | QtCore.Signal = field(
        init=False, default=None)
    func: Callable | None = field(init=False, default=None)

    @property
    def action_id(self):
        return self.cls_action_id(self.input_obj)

    def connect_parameter(self):

        if self.controller_obj is None:
            if isinstance(self.input_obj, QKeySequence):
                self.controller_obj = QShortcut(self.input_obj, self.window)
            elif isinstance(self.input_obj, DeviceInputSelectorWidget):
                self.input_obj.update_target()
                self.controller_obj = self.input_obj.make_device_controller()

        match self.action_type:
            case ControllerActionType.TOGGLE:
                self.func = self.toggle_parameter
            case ControllerActionType.VALUE:
                self.func = self.set_parameter_value
            case _:
                def print_():
                    print(f"Not implemented: {self.action_type.name}")
                self.func = print_
                # raise NotImplementedError(f"{self.action_type.name}")

        if isinstance(self.controller_obj, QShortcut):
            self.controller_obj.activated.connect(self.func)
        elif isinstance(self.controller_obj, QtCore.Signal):
            self.controller_obj.connect(self.func)

    @staticmethod
    def cls_action_id(input_obj):
        if isinstance(input_obj, QKeySequence):
            return input_obj.toString()
        elif isinstance(input_obj, DeviceInputSelectorWidget):
            return input_obj.action_id_str
        elif isinstance(input_obj, ControllerAction):
            return input_obj.action_id
        else:
            # noinspection PyInconsistentReturns
            type_assertion(input_obj, (QKeySequence,
                                       DeviceInputSelectorWidget,
                                       ControllerAction))

    def compare_fields(self, other):

        for k, fi in self.__dataclass_fields__.items():
            if fi.init is True:
                v0 = getattr(self, k)
                v1 = getattr(other, k)
                if not isinstance(v0, type(v1)):
                    return False
                if isinstance(v0, QKeySequence):
                    res = v0.toString() == getattr(other, k).toString()
                else:
                    res = v0 == v1
                if res is False:
                    return False
        return True

    def disconnect_parameter(self):

        if isinstance(self.controller_obj, QShortcut):
            self.controller_obj.activated.disconnect(self.func)
        elif isinstance(self.controller_obj, QtCore.Signal):
            self.controller_obj.disconnect(self.func)

        self.func = None

    @property
    def input_object_string(self) -> str:
        if isinstance(self.input_obj, QKeySequence):
            return self.input_obj.toString()
        elif isinstance(self.input_obj, DeviceInputSelectorWidget):
            return self.input_obj.as_label_string()
        else:
            raise NotImplementedError(
                f"type({type(self.input_obj)})")

    @staticmethod
    def make_parameter_label_text(par: Parameter | None):
        if par is None:
            return 'None'
        text = par.name()
        parent = par.parent()
        while parent:
            text = parent.name() + '.' + text
            parent = parent.parent()
        return text

    def export_version(self) -> dict[str, str]:
        return {
            'action_type': self.action_type.name,
            'input_object': self.input_object_string,
            'input_object_type': self.input_obj.__class__.__name__,
            'parameter': self.parameter_label,
        }

    @classmethod
    def from_export_version(cls, data: dict[str, Any], window):
        action_type = ControllerActionType[data['action_type']]
        input_object_type = data['input_object_type']
        if input_object_type == QKeySequence.__name__:
            input_obj = QKeySequence(data['input_object'])
        else:
            input_obj = input_object_type + ';' + data['input_object']
            # raise NotImplementedError(
            #     f"Input object type {input_object_type} not supported")
        parameter = data['parameter']
        return cls(
            action_type=action_type,
            input_obj=input_obj,
            parameter=parameter,
            window=window  # To be set after creation
        )

    @property
    def parameter_label(self):
        return self.make_parameter_label_text(self.parameter)

    def toggle_parameter(self):
        value = not self.parameter.value()
        self.parameter.setValue(value)

    def set_parameter_value(self, value):
        if self.parameter.opts[ParamOpts.KW.TYPE] == 'int':
            value = int(value)
        self.parameter.setValue(value)


class ParameterControls(ConfigurableDict):
    class ContainerConfigClass(DictContainerConfig, frozen=True):
        allowed_types: type[ControllerAction] = ControllerAction
        b_clear_allowed: bool = True


class ControlsMap(Object2ObjectMap):

    class ContainerConfigClass(ObjectMapConfig, frozen=True):
        b_pop_allowed: bool = True
        b_clear_allowed: bool = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.all_actions: ParameterControls | dict[str, ControllerAction] = (
            ParameterControls())

        self.map_signals = QObjectDictSignals(None)
        self.tree_parameters = Object2ObjectMap.from_types(
            ControllerAction, Parameter,
            b_clear_allowed=True,
            b_pop_allowed=True)

    @classmethod
    def to_controller(
            cls, ctrl_or_parameter: Parameter | ControllerAction,
            input_obj=None, action_type=None, window=None) -> ControllerAction:
        if isinstance(ctrl_or_parameter, ControllerAction):
            action = ctrl_or_parameter
            if ((input_obj is not None) or (action_type is not None)
                    or (window is not None)):
                raise ValueError(
                    "If action_or_parameter is ControllerAction, obj, "
                    "action_type and window must be None")
        else:
            action = ControllerAction(
                input_obj=input_obj, action_type=action_type,
                parameter=ctrl_or_parameter, window=window)
        return action

    def add_controller(
            self, ctrl_or_parameter: Parameter | ControllerAction,
            obj=None, action_type=None, window=None,
            set_connect: bool | None = True,
            b_block_signal: bool = False) -> ControllerAction:

        action = self.to_controller(
            ctrl_or_parameter=ctrl_or_parameter, input_obj=obj,
            action_type=action_type, window=window)
        parameter = action.parameter

        try:
            controllers = self[parameter]
        except KeyError:
            controllers = ParameterControls()
            self[parameter] = controllers

        controllers[action.action_id] = action

        self.all_actions[action.action_id] = action

        if set_connect is True:
            action.connect_parameter()
        elif set_connect is False:
            action.disconnect_parameter()

        if b_block_signal is False:
            self.map_signals.sigAdded.emit(self, action.action_id, action)

        return action

    def b_action_exists(self, obj):
        return ControllerAction.cls_action_id(obj) in self.all_actions

    def clear(self, b_force: bool = False, b_clear_inv: bool = True):

        for ctrl in self.all_actions.values():
            self.remove_controller(ctrl, b_block_signal=False)

        self.all_actions.clear(b_force=b_force, )
        self.tree_parameters.clear(b_force=b_force, )

        super().clear(b_force=b_force, b_clear_inv=b_clear_inv)

    def compare_controller(self, ctrl_or_parameter0,
                           ctrl_or_parameter1,
                           obj1=None, action_type1=None, window1=None):

        other = self.to_controller(
            ctrl_or_parameter=ctrl_or_parameter1,
            action_type=action_type1, input_obj=obj1, window=window1)

        obj = other.input_obj

        if isinstance(ctrl_or_parameter0, ControllerAction):
            action = ctrl_or_parameter0
        else:
            type_assertion(ctrl_or_parameter0, Parameter)
            try:
                action = self.get_controller(
                    parameter=ctrl_or_parameter0, obj=obj)
            except KeyError:
                return False

        res = action.compare_fields(other)
        return res

    def get_controller(self, parameter, obj) -> ControllerAction:
        action_id = ControllerAction.cls_action_id(obj)
        if parameter is None:
            ctrl = self.all_actions[action_id]
        else:
            ctrl = self[parameter][action_id]
        return ctrl

    # def __setitem__(self, key, value):
    #     super().__setitem__(key, value)

    def remove_controller(
            self, ctrl: ControllerAction, b_block_signal: bool):
        controls: ParameterControls = self[ctrl.parameter]
        found_ctrl: ControllerAction = controls.pop(ctrl.action_id)
        self.all_actions.pop(ctrl.action_id)

        if found_ctrl is not ctrl:
            raise AssertionError
        ctrl.disconnect_parameter()
        if not b_block_signal:
            self.map_signals.sigRemoved.emit(self, ctrl.action_id, ctrl)
        else:
            self.tree_parameters.pop(ctrl)

    # def pop(self, item, default=Undefined):
    #     super().pop(item, default=default)
    #     self.map_signals.sigRemoved.emit(self, item)
