from __future__ import annotations

from copy import copy

from types import NoneType
from typing import get_args, get_origin

from pydantic import BaseModel
from pydantic_core import PydanticUndefined
from pyqtgraph.parametertree.parameterTypes import (
    ListParameter,
    WidgetParameterItem,
)
from qtpy import QtCore, QtWidgets

from types import GenericAlias
# noinspection PyUnresolvedReferences,PyProtectedMember
from typing import (
    _AnnotatedAlias, _LiteralGenericAlias, Annotated, Any,
    Literal, NewType, Type,
)
from snngine_v4.utils.data_utils.index_config import (
    InconsistentType,
)
from pyqtgraph.parametertree import Parameter
from typing_extensions import TypeAliasType

from snngine_v4.gui.parameter_tree.parameters import (
    NoneTypeParameter,
)
from snngine_v4.gui.parameter_tree.parameters.common \
    .parameter_item_mixin import WidgetParameterItemMixin
from snngine_v4.gui.parameter_tree.parameters.spin_box_slider_parameter import \
    SpinBoxSliderParameterItem
from snngine_v4.utils.containers.super_maps import (
    TypeSortedMap,
)

from snngine_v4.gui.parameter_tree.parameters.common.engine_group_parameter \
    import (
        EngineGroupParameter, EngineGroupParameterItem,
    )

from snngine_v4.gui.parameter_tree.parameters.widgets.custom_combobox import \
    CustomComboBox
from snngine_v4.utils.field_utils import (
    b_is_annotated, b_is_literal_annotation,
    extract_literal_values,
)
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


QTreeWidgetItemType = QtWidgets.QTreeWidgetItem | WidgetParameterItem


ParameterValueType = NewType('ParameterValue', Any)


class MultiTypeParameterMap(TypeSortedMap):

    sub_maps: tuple = ((str, Parameter),
                       (type | GenericAlias | TypeAliasType
                        | _LiteralGenericAlias | _AnnotatedAlias
                        # | Type[Annotated]
                        ,
                        Parameter))

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        super().__setitem__(value.name(), value)


# noinspection PyPep8Naming
class MultiTypeParameterItem(EngineGroupParameterItem, ):

    def __init__(self, param, depth):
        self.param: MultiTypeParameter | None = None

        self.current_item = None
        self.current_widget = None
        self.target_item = None
        self.combobox = None
        super().__init__(param, depth)
        self.param.sigTypeChanged.connect(self.onTypeChange)

    def addChild(self, child: SpinBoxSliderParameterItem):

        super().addChild(child)
        if child.param == self.param.type_parameter:
            # child.setHidden(True)
            child.hideWidget = False
            wdg: QtWidgets.QComboBox = child.widget
            CustomComboBox.apply_custom_settings(wdg)
            self.layoutWidget.layout().insertWidget(0, wdg)
            self.combobox = wdg

        if self.param.b_flat:
            child.b_select_other = True

            if self.childCount() == len(self.param.children()):

                self.defaultBtn.setVisible(False)
                self.combobox.setMaximumWidth(120)

                if self.param.b_flat_merge_to_parent:

                    self.layoutWidget.setMinimumWidth(120)
                    self.layoutWidget.setMaximumWidth(120)

                    self.target_item = self.parent()
                    WidgetParameterItemMixin.cls_merge_layouts(
                        self, self.target_item)
                else:
                    self.target_item = self

                # noinspection PyTypeChecker,PydanticTypeChecker
                WidgetParameterItemMixin.cls_remove_spacer_item(
                    item=self, b_tentative=False, idx=1)
                for i in range(self.childCount()):
                    c0 = self.child(i)
                    if isinstance(c0, SpinBoxSliderParameterItem):
                        c0.select_other_target = self.target_item

                self.onTypeChange(
                    None,
                    self.param.children_map[self.param.type_parameter.value()])

    def selected(self, sel):
        super().selected(sel)
        if self.param.b_flat:
            if self.current_item is not None:
                if isinstance(self.current_item,
                              SpinBoxSliderParameterItem):
                    self.current_item.selected(sel)

    def onParentSelect(self, parent, value):
        if parent == self.parent():
            if self.param.b_flat_merge_to_parent is True:
                self.selected(value)

    def onTypeChange(self, p, c):

        if self.param.b_flat:
            tree = self.treeWidget()
            for i in range(self.childCount()):
                c0 = self.child(i)
                if c0.param == c:
                    if self.current_item is not None:
                        if isinstance(self.current_item.param,
                                      NoneTypeParameter):
                            # noinspection PyTypeChecker,PydanticTypeChecker
                            WidgetParameterItemMixin.cls_remove_spacer_item(
                                item=self, b_tentative=False, idx=1)
                            if self.param.b_flat_merge_to_parent:
                                self.layoutWidget.setMaximumWidth(120)
                        else:
                            tree.setItemWidget(self.current_item,
                                               1, self.current_widget)
                    if isinstance(c0, SpinBoxSliderParameterItem):
                        self.current_item = c0
                        self.current_widget = c0.layoutWidget
                        self.target_item.layoutWidget.layout().insertWidget(
                            1, self.current_widget)
                    else:
                        if isinstance(c0.param, NoneTypeParameter):
                            self.layoutWidget.layout().insertStretch(1, 0)
                            if self.param.b_flat_merge_to_parent:
                                self.layoutWidget.setMaximumWidth(5000)
                            self.current_item = c0
                        else:
                            self.current_item = None
                        self.current_widget = None


# noinspection PyPep8Naming
class MultiTypeParameter(EngineGroupParameter):
    itemClass = MultiTypeParameterItem

    sigTypeChanged = QtCore.Signal(object, object)

    def __init__(self, **opts):
        super().__init__(**opts)
        self.children_map = MultiTypeParameterMap()
        self.type_parameter = ListParameter(name='Type', visible=False)
        self.addChild(self.type_parameter, autoIncrementName=True)
        self.type_parameter.sigValueChanged.connect(self.onTypeChange)
        self.b_flat = False
        self.b_flat_merge_to_parent = False

    @classmethod
    def make_value(cls, value, type_, default_value):
        value_ = None

        b_is_og = False

        if type_ in [NoneType, InconsistentType]:
            return None, value is None, None
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

        if (type_ == str) and (b_is_og is False):
            value_ = ''

        return value_, b_is_og, value_

    def add_type_child(self, value, t, default_value, signal_register, **opts):
        from snngine_v4.gui.parameter_tree.parameter_builder \
            .parameter_builder import ParameterBuilder
        b_default_set = None
        value_, b_is_default, default_ = self.make_value(
            value, t, default_value)

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
                ann=t, name=name, value=value_, default=default_,
                # type=name,
                **opts)
        except KeyError as e:
            if name != 'Color':
                raise
            # raise
            p = None
        if p is not None:
            self.addChild(p, autoIncrementName=True)

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
        return p, b_default_set

    def build(self, signal_register):
        opts = copy(self.opts)

        opts.pop(ParamOpts.KW.C_DATA_TYPES)
        opts.pop(ParamOpts.KW.TYPE)
        name = opts.pop(ParamOpts.KW.NAME)
        opts.pop(ParamOpts.KW.TITLE)
        value = opts.pop(ParamOpts.KW.VALUE)

        built_pars = []
        b_default_set = False
        default_value = opts.pop(ParamOpts.KW.DEFAULT, None)

        for t in self.data_types:
            p, b_default_set_ = self.add_type_child(
                value, t, default_value, signal_register, **opts)
            if p is not None:
                built_pars.append(p)
            if b_default_set_ is not None:
                b_default_set = b_default_set_

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
                    c.show(s=not self.b_flat)
                    self.sigTypeChanged.emit(self, c)

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
        if not self.type_parameter._modifiedSinceReset:
            _modifiedSinceReset = child._modifiedSinceReset
        else:
            _modifiedSinceReset = True
        self._modifiedSinceReset = _modifiedSinceReset
        return self.sigValueChanged.emit(self, value_)

    def value(self):
        key = self.type_parameter.value()
        if key is None:
            key = NoneType
        if key != '':
            return self.children_map[key].value()
