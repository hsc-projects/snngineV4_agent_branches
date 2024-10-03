from __future__ import annotations

from copy import copy
from types import GenericAlias, NoneType
from typing import get_args, get_origin

from pydantic import BaseModel
from pydantic_core import PydanticUndefined
from pyqtgraph.parametertree.parameterTypes import (
    ListParameter,
    WidgetParameterItem,
)
from qtpy import QtWidgets

# from numba import NoneType

from snngine_v4.gui.parameter_tree.parameters.engine_group_parameter import (
    EngineGroupParameter, EngineGroupParameterItem,
)
from snngine_v4.gui.parameter_tree.parameters.type_parameter_map import \
    MultiTypeParameterMap
from snngine_v4.gui.parameter_tree.parameters.widgets.custom_combobox import \
    CustomComboBox
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


QTreeWidgetItemType = QtWidgets.QTreeWidgetItem | WidgetParameterItem


# noinspection PyPep8Naming
class MultiTypeParameterItem(EngineGroupParameterItem):

    def __init__(self, param, depth):
        self.param: MultiTypeParameter | None = None
        super().__init__(param, depth)

    def addChild(self, child):
        super().addChild(child)
        if child.param == self.param.type_parameter:
            # child.setHidden(True)
            child.hideWidget = False
            wdg: QtWidgets.QComboBox = child.widget
            CustomComboBox.apply_custom_settings(wdg)
            self.layoutWidget.layout().insertWidget(0, wdg)


# noinspection PyPep8Naming
class MultiTypeParameter(EngineGroupParameter):
    itemClass = MultiTypeParameterItem

    def __init__(self, **opts):

        super().__init__(**opts)
        self.children_map = MultiTypeParameterMap()
        self.type_parameter = ListParameter(name='Type', visible=False)
        self.addChild(self.type_parameter, autoIncrementName=True)
        self.type_parameter.sigValueChanged.connect(self.onTypeChange)

    @classmethod
    def make_value(cls, value, type_):
        value_ = None
        if type_ == NoneType:
            pass
        elif (not isinstance(type_, GenericAlias)) and isinstance(
                value, type_):
            value_ = value
        elif (isinstance(type_, GenericAlias)) and isinstance(
                value, get_origin(type_)):
            value_ = value
        elif (not isinstance(type_, GenericAlias)) and issubclass(
                type_, BaseModel):
            value_ = type_()

        if isinstance(value, BaseModel):
            pass
        return value_

    def build(self, signal_register):
        opts = copy(self.opts)
        opts.pop(ParamOpts.KW.C_DATA_TYPES)
        opts.pop(ParamOpts.KW.TYPE)
        opts.pop(ParamOpts.KW.NAME)
        opts.pop(ParamOpts.KW.TITLE)
        value = opts.pop(ParamOpts.KW.VALUE)

        built_pars = []

        for t in self.data_types:
            from snngine_v4.gui.parameter_tree.parameter_builder \
                .parameter_builder import ParameterBuilder

            value_ = self.make_value(value, t)

            name = t.__name__
            # title = self.opts[ParamOpts.KW.NAME] + f" ({name})"
            try:
                p = ParameterBuilder.make_par_from_annotation(
                    signal_register=signal_register,
                    # title=title,
                    ann=t, name=name, value=value_,
                    # type=name,
                    **opts)
            except KeyError as e:
                # raise
                p = None
            if p is not None:
                self.addChild(p, autoIncrementName=True)
                built_pars.append(p)
                self.children_map[t] = p

                self.type_parameter.opts[ParamOpts.KW.LIMITS] += [p.name()]
                p.hide()
        if len(self.data_types) > 0:
            for c in self.children_map.key_map[str].values():
                if isinstance(c, EngineGroupParameter):
                    c.connect_sigValueChanged()
                c.sigValueChanged.connect(self.valueChanged)
            # self.type_parameter.sigValueChanged.connect(self.valueChanged)
        return built_pars

    @property
    def data_types(self):
        return get_args(self.opts[ParamOpts.KW.C_DATA_TYPES])

    def onTypeChange(self, p, value):
        for c in self.childs:
            if c != p:
                if c.name() != value:
                    c.hide()
                else:
                    c.show()
        # self.valueChanged(p, p.value())

    def setValue(self, value, blockSignal=None):
        super().setValue(value, blockSignal=blockSignal)

    def valueChanged(self, child=None, value=PydanticUndefined):
        value_ = self.value()
        return self.sigValueChanged.emit(self, value_)

    def value(self):
        key = self.type_parameter.value()
        if key != '':
            return self.children_map[key].value()
