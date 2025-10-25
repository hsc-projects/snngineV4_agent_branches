import re
from copy import deepcopy
from enum import IntEnum
from typing import ClassVar

from qtpy import QtCore

from snngine_v4.gui.parameter_trees.linker_tree.controls_map import \
    ControllerAction
from snngine_v4.gui.parameters.common.engine_group_parameter import \
    EngineGroupParameter
from snngine_v4.gui.parameters.linker_parameter import (
    AddLinkerActionParameter,
    LinkerParameter)
from snngine_v4.utils.containers.configurable_dict import ConfigurableDict


class PresetGroupParameter(EngineGroupParameter):

    PRESET_LIST_KW: ClassVar[str] = "preset_list"

    sigPresetLoaded = QtCore.Signal(object)

    # noinspection PyPep8Naming
    def __init__(self,
                 name=None,
                 expanded=True,
                 preset_type=None,
                 autoIncrementName=True,
                 link_parameter_class: type[LinkerParameter] = LinkerParameter,
                 b_add_single_visible: bool = False,
                 **kwargs):

        if name is None:
            name = preset_type.name.title()

        # self.preset_list_parameter = None
        self.preset_type: IntEnum = preset_type

        self.preset_states = ConfigurableDict.from_type(
            dict, b_duplicate_value_check_by_id=True)

        self.preset_controls = ConfigurableDict.from_type(
            list, b_duplicate_value_check_by_id=True)
        self.previous_name = None

        self.link_parameter_class = link_parameter_class

        super().__init__(name=name,
                         # removable=removable,
                         expanded=expanded,
                         autoIncrementName=autoIncrementName,
                         **kwargs)

        self.add_list_action(name=self.PRESET_LIST_KW, limits=[self.name()],
                             func=self.set_preset_state)

        self.add_action(
            f'add_{self.preset_type.name.lower()}',
            self.add_preset_variant,
            # f"+ {self.preset_type.name.upper()}")
            '  +  ')

        self.add_link_action_par = self.make_add_link_action_par(
            visible=b_add_single_visible)
        self.init_state = self.saveState()

    def make_add_link_action_par(self, name=" New links ",
                                 visible=True):
        add_link_action_par = AddLinkerActionParameter(
            name=name, visible=visible)
        # add_link_action_par.sigActivated.connect(self.add_link_action)
        add_link_action_par.add_action(
            name=' ADD ', func=self.add_link_action,)
        self.addChild(add_link_action_par)
        return add_link_action_par

    def add_link_action(self, **opts) -> LinkerParameter:
        link_parameter_class: type[LinkerParameter] = self.link_parameter_class
        new_p = link_parameter_class(**opts)
        # new_idx = max(0, len(self.children()) - 1)
        self.insertChild(self.add_link_action_par, new_p)
        return new_p

    def increment_name(self, name, names=None):
        if names is None:
            names = self.names
        base, num = re.match(r'(\D*)(\d*)', name).groups()
        num_len = len(num)
        if num_len == 0:
            num = 2
            num_len = 1
        else:
            num = int(num)
        while True:
            new_name = base + ("%%0%dd" % num_len) % num
            if new_name not in names:
                return new_name
            num += 1

    def add_preset_variant(self, ):
        current_list = self.get_list_action_limits(self.PRESET_LIST_KW)
        last_name = current_list[-1]
        new_name = self.increment_name(last_name, names=current_list)

        # Keep order (1/2)
        if new_name not in self.preset_states:
            self.preset_states[new_name] = deepcopy(self.init_state)
            self.preset_controls[new_name] = []
        else:
            self.preset_states[new_name].clear()
            self.preset_states[new_name].update(self.init_state)
            self.preset_controls[new_name].clear()

        # Keep order (2/2)
        self.extend_list_action_limits(self.PRESET_LIST_KW, [new_name])

        self.list_map.list_parameters[self.PRESET_LIST_KW].setValue(new_name)

    @property
    def controls_list(self):
        return [x.value() for x in self.children()
                if (isinstance(x, LinkerParameter)
                    and isinstance(x.value(), ControllerAction))]

    @property
    def previous_controls(self):
        return self.preset_controls[self.previous_name]

    def save_preset_state(self, name=None):
        if name is None:
            name = self.name()

        prev_state = self.saveState()
        previous_controls = self.controls_list

        if name not in self.preset_states:
            self.preset_states[name] = prev_state
            self.preset_controls[name] = previous_controls
        else:
            self.preset_states[name].clear()
            self.preset_states[name].update(prev_state)
            self.preset_controls[name].clear()
            self.preset_controls[name].extend(previous_controls)

    def set_preset_state(self, par, value):

        self.previous_name = self.name()
        self.save_preset_state(name=self.previous_name)

        if value in self.preset_states:
            new_dict_ = self.preset_states[value]
            self.restoreState(new_dict_)
        self.setName(value)
        self.sigPresetLoaded.emit(self)
