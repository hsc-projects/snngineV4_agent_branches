from enum import IntEnum, auto
from functools import cached_property
from typing import ClassVar

from PySide6.QtGui import QKeySequence
from pydantic import BaseModel
from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import ActionParameter

from snngine_v4.gui.parameter_trees.linker_tree.controls_map import \
    ControllerAction
from snngine_v4.gui.parameter_trees.linker_tree.linker_tree import LinkerTree
from snngine_v4.gui.parameter_trees.linker_tree.range_map_widget import RangeMap
from snngine_v4.gui.parameter_trees.linker_tree.xtm_linker_widgets import (
    XTMLinkerInputWidget, XTMLinkerWindow)
from snngine_v4.gui.parameters.preset_parameter import PresetGroupParameter


class DeviceTypes(IntEnum):
    KEYBOARD = 0
    X_TOUCH_MINI = auto()


class KeyBoardLinks(PresetGroupParameter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class XTouchMiniLinks(PresetGroupParameter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class EngineLinkerTree(LinkerTree):

    X_TOUCH_MINI_KW: ClassVar[str] = 'xtm'

    def __init__(self, name: str = 'Selections',
                 model: BaseModel = None,
                 # engine: SNNgine = None,
                 parameter_type_dict=None,
                 default_context=None,
                 trees=None,
                 export_file_path: str = "./controls_export.xml",
                 **kwargs):
        if parameter_type_dict is None:
            parameter_type_dict = {
                DeviceTypes.KEYBOARD: KeyBoardLinks,
                DeviceTypes.X_TOUCH_MINI: XTouchMiniLinks,
            }
        self.parameter_type_dict = parameter_type_dict

        if default_context is None:
            default_context = {
                self.SHORTCUT_KW: 'Edit Shortcut(s)',
                self.X_TOUCH_MINI_KW: 'Edit X-Touch Mini Controller(s)'}

        super().__init__(name=name, model=model,
                         default_context=default_context,
                         preset_types=DeviceTypes,
                         presets_name='Devices',
                         parameter_type_dict=parameter_type_dict,
                         export_file_path=export_file_path,
                         trees=trees,
                         **kwargs)

        self.update_action_p = ActionParameter(name="  Update  ")

        def reset_tree_controls():
            self.reset_tree_controls()

        self.update_action_p.sigActivated.connect(reset_tree_controls)
        self.addParameters(self.update_action_p)

        self.save_action_p = ActionParameter(name="  Save  ")
        self.save_action_p.sigActivated.connect(self.save_controls)
        self.addParameters(self.save_action_p)

        self.load_action_p = ActionParameter(name="  Load  ")
        self.load_action_p.sigActivated.connect(self.load_controls)
        self.addParameters(self.load_action_p)

    def add_controller(self, dct, key, value: ControllerAction):
        if isinstance(value.input_obj, QKeySequence):
            p_presets = self.get_preset_group(
                preset_type=DeviceTypes.KEYBOARD)
        elif isinstance(value.input_obj, XTMLinkerInputWidget):
            p_presets = self.get_preset_group(
                preset_type=DeviceTypes.X_TOUCH_MINI)
        else:
            raise NotImplementedError(f"{type(value.input_obj)}")
        new_p = p_presets.add_link_action(value=value)
        # new_p.setValue(value)
        self.controls_map.tree_parameters[value] = new_p
        self.resize_sections()

    def get_linker_window(self, ctrl: ControllerAction):
        if isinstance(ctrl.input_obj, XTMLinkerInputWidget):
            return self.x_touch_mini_window
        else:
            return super().get_linker_window(ctrl=ctrl)

    def make_ctrl_input_obj(self, ctrl: ControllerAction):

        if isinstance(ctrl.input_obj, str):
            input_object_str = ctrl.input_obj.split(';', 1)
            input_object_type = input_object_str[0]
            input_object_content_str = input_object_str[1]
            if input_object_type == XTMLinkerInputWidget.__name__:
                input_obj = XTMLinkerInputWidget(
                    xtm_device_wdg=self.x_touch_mini_window.xtm_device_widget)
                input_obj.interpret_label_string(
                    label_str=input_object_content_str)
                return input_obj
            else:
                return super().make_ctrl_input_obj(ctrl=ctrl)
        else:
            return super().make_ctrl_input_obj(ctrl=ctrl)

    @classmethod
    def make_range_map(cls, parameter: Parameter):
        (minimum, maximum,
         minimum_allowed,
         maximum_allowed) = XTMLinkerInputWidget.range_map_values(
            parameter)
        return RangeMap(
            min0=0, max0=127, min1=minimum, max1=maximum, _step0=1,
            hard_min1=minimum_allowed,
            hard_max1=maximum_allowed,)

    def on_sig_context_menu_changed(self, param, data):
        match data:
            case self.X_TOUCH_MINI_KW:
                self.x_touch_mini_window.parameter = param
                self.x_touch_mini_window.show()
            case _:
                super().on_sig_context_menu_changed(param, data)
    
    @cached_property
    def x_touch_mini_window(self):
        return XTMLinkerWindow(linker_tree=self)
    

if __name__ == '__main__':

    from qtpy import QtCore, QtWidgets
    from snngine_v4.config.template import SpatialNetworkConfig
    from snngine_v4.gui.parameter_trees.engine_parameter_tree import \
        EngineParameterTree

    app = QtWidgets.QApplication([])

    wdg = QtWidgets.QWidget()
    wdg.setLayout(QtWidgets.QVBoxLayout())
    splitter = QtWidgets.QSplitter()
    wdg.layout().addWidget(splitter)

    model0_ = SpatialNetworkConfig()

    tree2_ = EngineParameterTree(model=model0_)
    tree_ = EngineLinkerTree(trees=[tree2_])
    # tree_.win()
    splitter.addWidget(tree_)
    splitter.addWidget(tree2_)

    wdg.show()
    app.exec()
