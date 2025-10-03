import re
from copy import deepcopy
from enum import IntEnum
from typing import ClassVar

from pyqtgraph.parametertree.parameterTypes import ActionParameter

from snngine_v4.gui.parameters.common.engine_group_parameter import \
    EngineGroupParameter
from snngine_v4.gui.parameters.linker_paremeter import (
    AddLinkerActionParameter,
    LinkerParameter)
from snngine_v4.utils.containers.configurable_dict import ConfigurableDict


class PresetGroupParameter(EngineGroupParameter):

    PRESET_LIST_KW: ClassVar[str] = "preset_list"

    # noinspection PyPep8Naming
    def __init__(self,
                 name=None,
                 expanded=True,
                 preset_type=None,
                 autoIncrementName=True,
                 link_parameter_class: type[LinkerParameter] = LinkerParameter,
                 **kwargs):

        if name is None:
            name = preset_type.name.title()

        # self.preset_list_parameter = None
        self.preset_type: IntEnum = preset_type

        self.preset_states = ConfigurableDict.from_type(
            dict, b_duplicate_value_check_by_id=True)

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

        self.add_link_action_par = self.make_add_link_action_par()
        self.init_state = self.saveState()

    def make_add_link_action_par(self, name=" New links "):
        add_link_action_par = AddLinkerActionParameter(name=name)
        # add_link_action_par.sigActivated.connect(self.add_link_action)
        add_link_action_par.add_action(
            name=' ADD ', func=self.add_link_action,)
        self.addChild(add_link_action_par)
        return add_link_action_par

    # noinspection PyPep8Naming
    def add_link_action(self, **opts):
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
        else:
            self.preset_states[new_name].clear()
            self.preset_states[new_name].update(self.init_state)

        # Keep order (2/2)
        self.extend_list_action_limits(self.PRESET_LIST_KW, [new_name])

        self.list_map.list_parameters[self.PRESET_LIST_KW].setValue(new_name)

    def set_preset_state(self, par, value):
        dict_ = self.saveState()
        last_value = self.name()
        if last_value not in self.preset_states:
            self.preset_states[last_value] = dict_
        else:
            self.preset_states[last_value].clear()
            self.preset_states[last_value].update(dict_)

        if value in self.preset_states:
            new_dict_ = self.preset_states[value]
            self.restoreState(new_dict_)

        self.setName(value)
