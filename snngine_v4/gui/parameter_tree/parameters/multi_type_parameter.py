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
from snngine_v4.utils.field_utils import (
    b_is_annotated, b_is_literal_annotation,
    extract_literal_values,
)
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

        b_is_og = False

        if type_ == NoneType:
            pass
        elif b_is_literal_annotation(type_):
            values = extract_literal_values(type_)
            b_is_og = value in values
            if b_is_og:
                value_ = value
            else:
                value_ = values[0]
        elif b_is_annotated(type_):
            if isinstance(value, type_.__origin__):
                value_ = value
                b_is_og = True

        elif (not isinstance(type_, GenericAlias)) and isinstance(
                value, type_):
            value_ = value
            b_is_og = True
        elif (isinstance(type_, GenericAlias)) and isinstance(
                value, get_origin(type_)):
            value_ = value
            b_is_og = True
        elif (not isinstance(type_, GenericAlias)) and issubclass(
                type_, BaseModel):
            value_ = type_()
            b_is_og = True

        if isinstance(value, BaseModel):
            pass

        return value_, b_is_og

    def build(self, signal_register):
        opts = copy(self.opts)

        opts.pop(ParamOpts.KW.C_DATA_TYPES)
        opts.pop(ParamOpts.KW.TYPE)
        name = opts.pop(ParamOpts.KW.NAME)
        opts.pop(ParamOpts.KW.TITLE)
        value = opts.pop(ParamOpts.KW.VALUE)

        built_pars = []

        b_default_set = False

        for t in self.data_types:
            from snngine_v4.gui.parameter_tree.parameter_builder \
                .parameter_builder import ParameterBuilder

            value_, b_is_default = self.make_value(value, t)

            if b_is_annotated(t):
                og_t = get_args(t)[0]
                if og_t not in [float, int]:
                    raise NotImplementedError()
                name = og_t.__name__
            else:
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
                if name != 'Color':
                    raise
                # raise
                p = None
            if p is not None:
                self.addChild(p, autoIncrementName=True)
                built_pars.append(p)
                self.children_map[t] = p

                self.type_parameter.opts[ParamOpts.KW.LIMITS] += [p.name()]
                # b_is_default = (((value_ is None) and (value is None))
                #                 or (value_ is value)
                #                 or ((not isinstance(value, np.ndarray))
                #                     and (value_ == value)))
                if b_is_default:
                    self.type_parameter.setDefault(p.name())
                    b_default_set = True

                p.hide()
        if len(self.data_types) > 0:
            for c in self.children_map.key_map[str].values():
                if isinstance(c, EngineGroupParameter):
                    c.connect_sigValueChanged()
                c.sigValueChanged.connect(self.valueChanged)
            # self.type_parameter.sigValueChanged.connect(self.valueChanged)
        if b_default_set is True:
            self.type_parameter.setToDefault()
            self.onTypeChange(self.type_parameter, self.type_parameter.value())
        else:
            pass

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
        if value == NoneType.__name__:
            self.valueChanged(p, p.value())

    def setValue(self, value, blockSignal=None):
        super().setValue(value, blockSignal=blockSignal)
        try:
            key = self.type_parameter.value()
        except AttributeError:
            key = ''
        if key != '':
            return self.children_map[key].setValue(
                value, blockSignal=self.valueChanged)

    def valueChanged(self, child=None, value=PydanticUndefined):
        value_ = self.value()
        return self.sigValueChanged.emit(self, value_)

    def value(self):
        key = self.type_parameter.value()
        if key is None:
            key = NoneType
        if key != '':
            return self.children_map[key].value()
