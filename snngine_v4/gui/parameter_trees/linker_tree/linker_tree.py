from copy import copy
from enum import Enum, IntEnum
from functools import cached_property
from typing import ClassVar

from qtpy.QtGui import QKeySequence
from pydantic import BaseModel
from pyqtgraph.parametertree import Parameter

from snngine_v4.gui.parameter_trees.engine_parameter_tree import \
    EngineParameterTree
from snngine_v4.gui.parameter_trees.linker_tree.device_input_widget import \
    DeviceInputSelectorWidget
from snngine_v4.gui.parameter_trees.linker_tree.linker_window import \
    ShortCutWindow
from snngine_v4.gui.parameter_trees.linker_tree.controls_map import \
    (ControllerAction, ControllerActionType, ControlsMap)
from snngine_v4.gui.parameter_trees.linker_tree.range_map_widget import RangeMap
from snngine_v4.gui.parameters import LinkerParameter
from snngine_v4.gui.parameters.common.engine_group_parameter import (
    EngineGroupParameter)
from snngine_v4.gui.parameters.preset_parameter import \
    PresetGroupParameter
from snngine_v4.utils.containers.configurable_dict import ConfigurableDict
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts
from snngine_v4.utils.settings.xml_converter import XMLConverter


class LinkerTree(EngineParameterTree):

    SHORTCUT_KW: ClassVar[str] = 'shortcut'

    def __init__(self,
                 preset_types: type[IntEnum],
                 presets_name: str,
                 name: str = 'Controls',
                 model: BaseModel = None,
                 parameter_type_dict=None,
                 default_context=None,
                 export_file_path: str = "./controls_export.xml",
                 trees=None,
                 **kwargs):
        if parameter_type_dict is None:
            parameter_type_dict = {}

        self.controls_map: ControlsMap = ControlsMap()
        self.saved_controls: dict[str, ControlsMap] = {}

        self.export_file_path = export_file_path

        self.controls_map.map_signals.sigAdded.connect(self.add_controller)
        self.controls_map.map_signals.sigRemoved.connect(self.remove_controller)

        self.parameter_type_dict = parameter_type_dict

        self.preset_types = preset_types

        if default_context is None:
            default_context = {self.SHORTCUT_KW: 'Edit Shortcut(s)'}
        self.default_context = default_context

        super().__init__(name=name, model=model, **kwargs)

        self.counts = {x: 0 for x in self.preset_types}

        self.p_presets = EngineGroupParameter(name=presets_name)

        self.parameter_dict: dict[IntEnum, PresetGroupParameter] = (
            ConfigurableDict.from_type(
                PresetGroupParameter,
                allowed_key_types=self.preset_types))

        for preset_t in preset_types:
            self.append_add_preset_type_action(preset_t)

        self.addParameters(self.p_presets)

        self.all_params: list = []
        self.trees = trees
        self.main_params: dict = {}

    def add_controller(self, dct, key, value):
        pass

    def add_preset_group(
            self, preset_type: IntEnum) -> PresetGroupParameter:

        if preset_type not in self.parameter_dict:
            preset_group = self._make_preset_group(preset_type=preset_type)
        else:
            self.parameter_dict[preset_type].add_preset_variant()
            self.resize_sections()
            preset_group = self.parameter_dict[preset_type]

        return preset_group

    def append_add_preset_type_action(self, preset_type: IntEnum):

        def add_preset_group():
            self.add_preset_group(preset_type=preset_type)

        self.p_presets.add_action(
            f'add_{preset_type.name.lower()}',
            add_preset_group, f"+ {preset_type.name.upper()}")

    def find_parameter(self, par_lineage_str):
        par_lineage = par_lineage_str.split('.')

        if self.main_params is not None:
            try:
                current_par = self.main_params[par_lineage[0]]
                if current_par is not None:
                    for name in par_lineage[1:]:
                        current_par = current_par.child(name)
                    return current_par
            except KeyError:
                pass
        return None

    def get_preset_group(self, preset_type: IntEnum) -> PresetGroupParameter:
        if preset_type not in self.parameter_dict:
            self._make_preset_group(preset_type=preset_type)
        return self.parameter_dict[preset_type]

    def get_linker_window(self, ctrl: ControllerAction):
        if isinstance(ctrl.input_obj, QKeySequence):
            return self.short_cut_window
        else:
            raise NotImplementedError

    def _make_preset_group(
            self, preset_type: IntEnum) -> PresetGroupParameter:
        name = preset_type.name.title() + str(self.counts[preset_type])
        par_class = self.parameter_type_dict.get(
            preset_type, PresetGroupParameter)
        p_presets = par_class(name=name, preset_type=preset_type, )
        self.p_presets.addChild(p_presets)
        self.parameter_dict[preset_type] = p_presets
        self.resize_sections()

        p_presets.sigPresetLoaded.connect(self.on_preset_loaded)
        return p_presets

    def load_controls(self):

        fn = self.export_file_path

        importer = XMLConverter()
        data = importer.dict_from_xml(fn)

        for preset_type_name, preset_dct in data.items():

            try:
                # noinspection PyTypeChecker
                preset_type: IntEnum = self.preset_types[preset_type_name]
            except Exception as error:
                print(f"Could not find preset type for {preset_type_name}: "
                      f"{error}")
                continue

            p_presets = self.get_preset_group(preset_type=preset_type)

            for preset_name, ctrl_list in preset_dct.items():
                # p_presets.set_preset_state(preset_name)

                for ctrl_dct in ctrl_list:
                    ctrl = ControllerAction.from_export_version(
                        ctrl_dct, window=self.window())
                    if isinstance(ctrl.parameter, str):
                        ctrl.parameter = self.find_parameter(ctrl.parameter)

                    if ctrl.parameter is not None:
                        if isinstance(ctrl.input_obj, str):
                            ctrl.input_obj = self.make_ctrl_input_obj(ctrl)

                        if ctrl.action_type == ControllerActionType.VALUE:
                            ctrl.input_obj.range_map = self.make_range_map(
                                ctrl.parameter)
                        self.controls_map.add_controller(
                            ctrl_or_parameter=ctrl)

        return

    def make_ctrl_input_obj(self, ctrl: ControllerAction):
        return ctrl.input_obj

    @classmethod
    def make_range_map(cls, parameter: Parameter):
        # (minimum, maximum,
        #  minimum_allowed,
        #  maximum_allowed) = DeviceInputSelectorWidget.range_map_values(
        #     parameter)
        # return RangeMap(
        #     min0=0, max0=127, min1=minimum, max1=maximum, _step0=1,)
        raise NotImplementedError

    def on_preset_loaded(self, preset_group: PresetGroupParameter):
        lost_controls = preset_group.previous_controls
        for ctrl in lost_controls:
            self.controls_map.remove_controller(ctrl, b_block_signal=True)

        for par in preset_group.children():
            if (isinstance(par, LinkerParameter)
                    and isinstance(ctrl := par.value(), ControllerAction)):
                self.controls_map.add_controller(ctrl, b_block_signal=True)
                self.controls_map.tree_parameters[ctrl] = par

        self.short_cut_window.parameter = self.short_cut_window.parameter
        self.short_cut_window.set_window_title(
            suffix=f" ({preset_group.name()})")

    def on_sig_context_menu_changed(self, param, data):
        match data:
            case self.SHORTCUT_KW:
                self.short_cut_window.parameter = param
                self.short_cut_window.show()

    def read_tree(self, tree: EngineParameterTree, item=None):

        all_params = tree.list_all_parameters()
        self.all_params.extend(all_params)

        main_params = [x for x in all_params if x.parent() is None]
        main_params_names = [x.name() for x in main_params]
        main_params_dict = dict(zip(main_params_names, main_params))
        self.main_params.update(main_params_dict)

        for p in all_params:
            self.update_parameter(p)

    def remove_controller(self, dct, key, value):
        par: Parameter = self.controls_map.tree_parameters[value]
        parent: PresetGroupParameter = par.parent()
        parent.removeChild(par)
        self.controls_map.tree_parameters.pop(value)
        del par

    def reset_tree_controls(self, trees=None):
        if trees is not None:
            self.trees = trees

        self.all_params = []
        self.main_params = {}
        self.controls_map.clear()
        for tree in self.trees:
            self.read_tree(tree)

    def save_controls(self, ):
        res = {}
        for preset_type, par in self.parameter_dict.items():
            preset_dct_res = {}

            par.save_preset_state()

            for k in par.preset_states.data:
                preset_dct_res[k] = []

            for k, preset_dct in par.preset_states.data.items():
                if (chs := preset_dct.get('children')) is not None:
                    for ch in chs.values():
                        ctrl = ch.get('value')
                        if isinstance(ctrl, ControllerAction):
                            preset_dct_res[k].append(
                                ctrl.export_version())

            res[preset_type.name] = preset_dct_res

        exporter = XMLConverter()
        exporter.to_xml_file(data=res, fn=self.export_file_path)
        return

    @cached_property
    def short_cut_window(self) -> ShortCutWindow:
        return ShortCutWindow(linker_tree=self)

    def update_parameter(self, param: Parameter):

        connected_kw = ParamOpts.KW.C_B_LINKER_TREE_CONTEXT_MENU_CONNECTED
        if param.opts.get(connected_kw) is True:
            return
        if (param.opts[ParamOpts.KW.TYPE]
                in ['bool', 'int', 'float', Enum.__name__]):
            if param.opts.get(ParamOpts.KW.CONTEXT) is None:
                param.opts[ParamOpts.KW.CONTEXT] = self.default_context
            elif isinstance(param.opts[ParamOpts.KW.CONTEXT], dict):
                for k in self.default_context:
                    param.opts[ParamOpts.KW.CONTEXT].setdefault(
                        k, self.default_context[k])
            else:
                raise NotImplementedError
            param.sigContextMenu.connect(self.on_sig_context_menu_changed)
        param.opts[connected_kw] = True
