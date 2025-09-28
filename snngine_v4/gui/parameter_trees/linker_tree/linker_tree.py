from enum import IntEnum
from functools import cached_property
from typing import ClassVar

from pydantic import BaseModel
from pyqtgraph.parametertree import Parameter

from snngine_v4.gui.parameter_trees.engine_parameter_tree import \
    EngineParameterTree
from snngine_v4.gui.parameter_trees.linker_tree.linker_window import \
    ShortCutWindow
from snngine_v4.gui.parameters.common.engine_group_parameter import (
    EngineGroupParameter)
from snngine_v4.gui.parameters.preset_parameter import \
    PresetGroupParameter
from snngine_v4.utils.containers.configurable_dict import ConfigurableDict
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


class LinkerTree(EngineParameterTree):

    SHORTCUT_KW: ClassVar[str] = 'shortcut'

    def __init__(self,
                 preset_types: type[IntEnum],
                 presets_name: str,
                 name: str = 'Controls',
                 model: BaseModel = None,
                 parameter_type_dict=None,
                 default_context=None,
                 **kwargs):
        if parameter_type_dict is None:
            parameter_type_dict = {}
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

        self.all_params = None

    def add_preset_group(self, preset_type: IntEnum):

        if preset_type not in self.parameter_dict:
            name = preset_type.name.title() + str(self.counts[preset_type])
            par_class = self.parameter_type_dict.get(
                preset_type, PresetGroupParameter)
            p_presets = par_class(name=name, preset_type=preset_type, )
            self.p_presets.addChild(p_presets)
            self.parameter_dict[preset_type] = p_presets
        else:
            self.parameter_dict[preset_type].add_preset_variant()
        self.resize_header_sections_to_content()

    def append_add_preset_type_action(self, preset_type: IntEnum):

        def add_preset_group():
            self.add_preset_group(preset_type=preset_type)

        self.p_presets.add_action(
            f'add_{preset_type.name.lower()}',
            add_preset_group, f"+ {preset_type.name.upper()}")

    def update_parameter(self, param: Parameter):
        if param.opts.get(ParamOpts.KW.CONTEXT) is None:
            param.opts[ParamOpts.KW.CONTEXT] = self.default_context
        elif isinstance(param.opts[ParamOpts.KW.CONTEXT], dict):
            for k in self.default_context:
                param.opts[ParamOpts.KW.CONTEXT].setdefault(
                    k, self.default_context[k])
        else:
            raise NotImplementedError
        param.sigContextMenu.connect(self.on_sig_context_menu_changed)

    @cached_property
    def short_cut_window(self):
        return ShortCutWindow()

    def on_sig_context_menu_changed(self, param, data):
        match data:
            case self.SHORTCUT_KW:
                self.short_cut_window.parameter = param
                self.short_cut_window.show()

    def read_tree(self, tree: EngineParameterTree, item=None):

        # if item is None:
        #     item = tree.invisibleRootItem()
        #     items = []
        #     for i in range(item.childCount()):
        #         items.append(item.child(i))
        #
        #     params = [x.param for x in items if hasattr(x, 'param')]
        #     all_param_names = [x.name() for x in params]
        #     all_params = dict(zip(all_param_names, params))
        # else:
        #     param: Parameter = item.param
        #     all_params = param.names()

        all_params = tree.list_all_parameters()
        all_param_names = [x.name() for x in all_params]
        all_params_dict = dict(zip(all_param_names, all_params))
        self.all_params = all_params_dict

        for p in all_params:
            self.update_parameter(p)

        # my_param = self.list_all_parameters()
        #
        # for param in my_param:
        #     if isinstance(param, LinkerParameter):
        #         param.setLimits(all_params)

