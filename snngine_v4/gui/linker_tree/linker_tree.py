import re
from dataclasses import dataclass
from enum import IntEnum, auto

from click.types import BoolParamType
from pydantic import BaseModel
from pyqtgraph.parametertree.parameterTypes import (ListParameter,
                                                    SimpleParameter)

from snngine_v4.gui.parameter_tree.connectors.model_signals_register import \
    ExtendedModelSignalsRegister
from snngine_v4.gui.parameter_tree.engine_parameter_tree import \
    EngineParameterTree
from snngine_v4.gui.parameter_tree.parameters.common \
    .engine_group_parameter import EngineGroupParameter
from snngine_v4.snngine import SNNgine
from snngine_v4.utils.containers.configurable_dict import ConfigurableDict


class DeviceTypes(IntEnum):
    KEYBOARD = 0
    X_TOUCH_MINI = auto()


class DeviceGroupParameter(EngineGroupParameter):

    COUNT: int = 0

    def __init__(self,
                 # signal_register: ExtendedModelSignalsRegister,
                 name=None,
                 # removable=True,
                 expanded=False,
                 autoIncrementName=True,
                 device_type=None,
                 **kwargs):

        if name is None:
            name = device_type.name.title()

        name += str(self.__class__.COUNT)
        self.__class__.COUNT += 1

        self.preset_list_parameter = None
        self.device_type: DeviceTypes = device_type

        self.presets = ConfigurableDict.from_type(
            dict, b_duplicate_check_by_id=True)

        super().__init__(name=name,
                         # removable=removable,
                         expanded=expanded,
                         autoIncrementName=autoIncrementName,
                         **kwargs)

        self.addChild(SimpleParameter(name='K0', type='bool'))

    def increment_name(self, name, names=None):

        if names is None:
            names = self.names

        base, num = re.match(r'([^\d]*)(\d*)', name).groups()
        numLen = len(num)
        if numLen == 0:
            num = 2
            numLen = 1
        else:
            num = int(num)
        while True:
            newName = base + ("%%0%dd"%numLen) % num
            if newName not in names:
                return newName
            num += 1

    def add_device_variant(self,):
        if self.preset_list_parameter is None:
            self.preset_list_parameter = ListParameter(
                name='Preset List')
            self.parent().insertChild(0, self.preset_list_parameter)
            self.preset_list_parameter.setLimits([self.name()])

            self.preset_list_parameter.sigValueChanged.connect(
                self.set_preset
            )

        last_name = self.preset_list_parameter.opts['limits'][-1]
        new_name = self.increment_name(
            last_name, names=self.preset_list_parameter.opts['limits'])
        self.preset_list_parameter.setLimits(
            self.preset_list_parameter.opts['limits'] + [new_name]
        )
        return
        # self.parent().addChild(
        #     self.__class__(device_type=self.device_type)
        # )

    def set_preset(self, par, value):
        dict_ = self.saveState()
        last_value = self.name()

        # dict_['children'].pop(self.preset_list_parameter.name())

        if last_value not in self.presets:
            self.presets[last_value] = dict_
        else:
            self.presets[last_value].update(dict_)
        self._last_preset = value

        if value in self.presets:
            new_dict_ = self.presets[value]
            self.restoreState(new_dict_)

        self.setName(value)


class LinkerTree(EngineParameterTree):

    def __init__(self, name: str = 'Selections',
                 model: BaseModel = None,
                 engine: SNNgine = None,
                 **kwargs):
        super().__init__(name=name, model=model, **kwargs)

        self.p_devices = EngineGroupParameter(name="Devices")

        self.parameter_type_dict: dict[DeviceTypes, DeviceGroupParameter] = (
            ConfigurableDict.from_type(
                DeviceGroupParameter,
                allowed_key_types=DeviceTypes))

        for device_t in DeviceTypes:
            self.append_add_device_action(device_t)

        self.addParameters(self.p_devices)

    def add_device(self, device_type: DeviceTypes):

        if device_type not in self.parameter_type_dict:

            p_device = DeviceGroupParameter(
                device_type=device_type,
            )
            self.p_devices.addChild(p_device)
            self.parameter_type_dict[device_type] = p_device
        else:
            self.parameter_type_dict[device_type].add_device_variant()

    def append_add_device_action(self, device_type: DeviceTypes):

        def add_device():
            self.add_device(device_type=device_type)

        self.p_devices.add_action(
            f'add_{device_type.name.lower()}',
            add_device, f"+ {device_type.name.upper()}")


if __name__ == '__main__':

    from qtpy import QtWidgets

    app = QtWidgets.QApplication([])

    tree_ = LinkerTree()
    tree_.show()
    app.exec()
