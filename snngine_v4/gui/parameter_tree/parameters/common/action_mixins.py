from __future__ import annotations

from functools import cached_property
from typing import Type

from pyqtgraph.parametertree import Parameter, ParameterItem
from pyqtgraph.parametertree.parameterTypes import WidgetParameterItem
from qtpy import QtWidgets

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

    def add_action(self, name, func, title=None):
        self[name] = func
        if title is not None:
            self.titles[name] = title


class ActionItemMixin:

    @cached_property
    def widget_dict(self):
        return QWidgetDict()

    def add_actions(self: ActionItemMixin | ParameterItem):
        for name in self.param.action_map.refs:
            self.add_action_button(name)

    def add_action_button(self: ActionItemMixin | WidgetParameterItem, name):
        button_name = self.param.action_map.titles.get(name, name)
        action_button = QtWidgets.QPushButton(button_name)

        def call_action():
            self.param.action_map[name]()

        action_button.clicked.connect(call_action)
        self.widget_dict[name] = action_button
        self.layoutWidget.layout().addWidget(action_button)


class ActionParameterMixin(ActionItemMixin):

    @cached_property
    def action_map(self) -> ActionMap:
        return ActionMap()

    def add_action(self, name, func, title=None):
        self.action_map.add_action(name, func, title)

    @cached_property
    def main_window(self: ActionParameterMixin | Parameter):
        for item in self.items.keys():
            if (item is not None) and isinstance(item, ParameterItem):
                # noinspection PyUnresolvedReferences
                window = (item.widget_dict[list(item.widget_dict.keys())[0]]
                          .window())
                if isinstance(window, MainEngineWindowBase):
                    return window
