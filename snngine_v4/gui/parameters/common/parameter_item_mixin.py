from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from pyqtgraph.parametertree import ParameterItem
from pyqtgraph.parametertree.parameterTypes import WidgetParameterItem
from qtpy import QtCore, QtWidgets

from snngine_v4.gui.parameters.widgets.clickable_label import (
    ClickableLabel,
)
from snngine_v4.gui.parameters.common.engine_group_parameter import \
    EngineGroupParameterItem
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts

if TYPE_CHECKING:
    from snngine_v4.gui.parameter_trees.engine_parameter_tree import \
        EngineParameterTree


type WidgetParameterItemType = (WidgetParameterItemMixin
                                | WidgetParameterItem
                                | QtWidgets.QTreeWidgetItem)


# noinspection PyPep8Naming
class WidgetParameterItemMixin:

    TEXT_CONVERSIONS = {
        'nan': {'nan': 'None'},
        ParamOpts.KW.C_NONE_MEANS_UNKNOWN: {'nan': 'Unknown'},
    }

    parent: Callable[[...], EngineGroupParameterItem]
    layoutWidget: QtWidgets.QWidget

    def __init__(self):
        self._size_policy = QtWidgets.QSizePolicy.Policy.MinimumExpanding

    def is_from_numeric_group(self: WidgetParameterItemType):
        parent = self.parent()
        res = False
        if isinstance(parent, EngineGroupParameterItem):
            res = parent.param.opts.get(ParamOpts.KW.C_NUMERIC_GROUP, False)
        return res

    def parent(self: ParameterItem) -> EngineGroupParameterItem:
        # noinspection PyUnresolvedReferences
        return super().parent()

    @classmethod
    def cls_merge_layouts(cls, source, target: EngineGroupParameterItem):
        source.setHidden(True)
        target.layoutWidget.layout().insertWidget(
            0, source.layoutWidget)
        # noinspection PyTypeChecker,PydanticTypeChecker
        cls.cls_remove_spacer_item(
            item=target, b_tentative=False, idx=1)
        target.param.sigSelected.connect(source.onParentSelect)

    def merge_to_parent(self):
        self.cls_merge_layouts(self, self.parent())

    def onParentSelect(self: WidgetParameterItemType, parent, value):
        if parent == self.parent():
            if self.param.b_merge_to_parent is True:
                self.selected(value)

    @classmethod
    def cls_remove_spacer_item(cls, item: WidgetParameterItemType, idx=2,
                               b_tentative: bool = False):
        if b_tentative is True:
            pass
        w = item.layoutWidget.layout().takeAt(idx)
        if not isinstance(w, QtWidgets.QSpacerItem):
            raise ValueError(f"{w}")
        item.layoutWidget.layout().removeItem(w)

    def _remove_spacer_item(self: WidgetParameterItemType, idx=2,
                            b_tentative: bool = False):
        self.cls_remove_spacer_item(self, idx, b_tentative=b_tentative)

    def _replace_display_label(self: WidgetParameterItemType):
        txt = self.displayLabel.text()
        self.layoutWidget.layout().removeWidget(self.displayLabel)
        b_unknown = self.param.opts.get(ParamOpts.KW.C_NONE_MEANS_UNKNOWN,
                                        False)
        if b_unknown is True:
            conversion = self.TEXT_CONVERSIONS[
                ParamOpts.KW.C_NONE_MEANS_UNKNOWN]
        else:
            conversion = self.TEXT_CONVERSIONS['nan']
        self.displayLabel = ClickableLabel(conversion=conversion, text=txt)
        self.displayLabel.sigClicked.connect(self.valueWidgetClicked)
        self.layoutWidget.layout().insertWidget(0, self.displayLabel)

    def _set_size_policies(self: WidgetParameterItemType):
        self.displayLabel.setSizePolicy(self._size_policy, self._size_policy)
        self.widget.setSizePolicy(self._size_policy, self._size_policy)

    def _set_sizes(self: WidgetParameterItemType):

        width = self.param.opts.get(ParamOpts.KW.DECIMALS, 3) * 13 + 15
        self.widget.setMinimumWidth(width)
        self.displayLabel.setMinimumWidth(width)
        if self.is_from_numeric_group():
            self.parent().set_sizes()
        else:

            self.widget.setMaximumWidth(width)
            self.displayLabel.setMaximumWidth(width)

        sw: QtCore.QSize = self.widget.sizeHint()
        sb: QtCore.QSize = self.defaultBtn.sizeHint()
        # shrink row heights a bit for more compact look
        sw.setHeight(int(sw.height() * 0.9))
        sb.setHeight(int(sb.height() * 0.9))
        if self.asSubItem:
            self.setSizeHint(1, sb)
            self.subItem.setSizeHint(0, sw)
        else:
            w = sw.width() + sb.width()
            h = max(sw.height(), sb.height())
            self.setSizeHint(1, QtCore.QSize(w, h))
            self.layoutWidget.setMinimumWidth(w)

    def valueWidgetClicked(self: WidgetParameterItemType):
        tree: EngineParameterTree = self.treeWidget()
        if tree:
            self.setSelected(False)
            tree.setCurrentItem(self)
