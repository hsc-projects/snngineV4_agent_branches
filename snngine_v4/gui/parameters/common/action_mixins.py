from __future__ import annotations

from functools import cached_property
from typing import Type

from pyqtgraph import ComboBox
from pyqtgraph.parametertree import Parameter, ParameterItem
from pyqtgraph.parametertree.parameterTypes import (ListParameter,
                                                    ListParameterItem,
                                                    WidgetParameterItem)
from qtpy import QtCore, QtWidgets

from snngine_v4.gui.common.qobject_dicts import QWidgetDict
from snngine_v4.gui.windows.main_window_base import MainEngineWindowBase
from snngine_v4.utils.containers.configurable_dict import ConfigurableDict
from snngine_v4.utils.containers.mappings import CallablesMap, ObjectMapConfig


class ActionMap(CallablesMap):

    class InvertedConfigClass(ObjectMapConfig):
        allowed_types: Type[str] = str

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.titles = ConfigurableDict.from_type(str)
        # self.limits = ConfigurableDict.from_type(list)
        self.list_parameters: dict[str, ListParameter] | ConfigurableDict = (
            ConfigurableDict.from_type(ListParameter))
        self.string_dict = {}

    def add_action(self, name, func, title=None):
        self[name] = func
        self.string_dict[name] = id(name)
        if title is not None:
            self.titles[name] = title

    def add_list(self, name, func, limits=None):
        self[name] = func
        self.string_dict[name] = id(name)
        if limits is None:
            limits = []
        list_parameter = ListParameter(
            name=name, limits=limits,
        )
        list_parameter.sigValueChanged.connect(func)
        self.list_parameters[name] = list_parameter

    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except KeyError:
            if isinstance(item, str):
                return super().__getitem__(self.string_dict[item])
            raise


class ActionItemMixin:

    param: ActionParameterMixin

    @cached_property
    def widget_dict(
            self) -> QWidgetDict | dict[str, ComboBox | QtWidgets.QPushButton]:
        return QWidgetDict()

    def add_actions(self: ActionItemMixin | ParameterItem):
        for name in self.param.action_map.refs:
            if name in self.param.action_map.list_parameters:
                self.add_list_combobox(name)
            else:
                self.add_action_button(name)

    def add_action_button(self: ActionItemMixin | WidgetParameterItem, name):
        button_name = self.param.action_map.titles.get(name, name)
        action_button = QtWidgets.QPushButton(button_name)

        # def call_action():
        #     self.param.action_map[name]()

        call_action = self.param.action_map[name]

        action_button.clicked.connect(call_action)
        self.widget_dict[name] = action_button
        self.layoutWidget.layout().addWidget(action_button)

    def add_list_combobox(
            self: ActionItemMixin | WidgetParameterItem, name):

        list_param = self.param.list_map.list_parameters[name]
        list_param_item = ListParameterItem(param=list_param, depth=0)
        combobox = list_param_item.widget
        self.widget_dict[name] = combobox
        self.layoutWidget.layout().addWidget(combobox)


class ActionParameterMixin:

    @cached_property
    def action_map(self) -> ActionMap:
        return ActionMap()

    def add_action(self, name, func, title=None):
        self.action_map.add_action(name, func=func, title=title)

    def add_list_action(self, name, func, limits=None):
        self.list_map.add_list(name, func=func, limits=limits)

    def get_list_action_limits(self, name):
        limits_ = self.list_map.list_parameters[name].opts['limits']
        return limits_

    def extend_list_action_limits(self, name, limits):
        limits_ = self.get_list_action_limits(name) + limits
        self.update_list_action_limits(name, limits=limits_)

    def update_list_action_limits(self, name, limits):
        self.list_map.list_parameters[name].setLimits(limits)

    @cached_property
    def list_map(self) -> ActionMap:
        return self.action_map

    # @cached_property
    # def list_map(self) -> ActionMap:
    #     return ActionMap()

    @cached_property
    def main_window(self: ActionParameterMixin | Parameter):
        for item in self.items.keys():
            if (item is not None) and isinstance(item, ParameterItem):
                # noinspection PyUnresolvedReferences
                window = (item.widget_dict[list(item.widget_dict.keys())[0]]
                          .window())
                if isinstance(window, MainEngineWindowBase):
                    return window
        return None
