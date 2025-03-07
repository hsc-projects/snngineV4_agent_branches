from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from pyqtgraph.parametertree import Parameter, ParameterTree
from pyqtgraph.parametertree.parameterTypes import (
    SimpleParameter,
    WidgetParameterItem,
)
from qtpy import QtWidgets

from snngine_v4.gui.parameter_tree.parameters.common \
    .parameter_item_mixin import WidgetParameterItemMixin
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts

if TYPE_CHECKING:
    from snngine_v4.gui.parameter_tree.engine_parameter_tree import \
        EngineParameterTree


class ReferenceLineEdit(QtWidgets.QLineEdit):

    def __init__(self, value=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet('border: 0px')
        self.sigChanged = self.editingFinished
        self._value = value
        self.setValue = self.setText
        self.sigChanging = self.textChanged

    def value(self):
        return self._value

    def setText(self, value):
        self._value = value
        if isinstance(value, Parameter):
            value = value.name() + f" ({value.__class__.__name__})"
        else:
            value = f"<{value.__class__.__name__} at {hex(id(value))}>"
        super().setText(value)


class ReferenceParameterItem(WidgetParameterItem, WidgetParameterItemMixin):
    """Registered parameter type which displays a QLineEdit"""

    treeWidget: Callable[[], ParameterTree | EngineParameterTree]
    widget: ReferenceLineEdit

    def __init__(self, param, depth):
        self.makeWidget = ReferenceLineEdit
        super().__init__(param, depth)
        self._remove_spacer_item()
        self._replace_display_label()

    def updateDisplayLabel(self, value=None):
        value = self.widget.text()
        super().updateDisplayLabel(value)

    def get_ref_item(
            self, value: Parameter, tree=None) -> QtWidgets.QTreeWidgetItem:
        if tree is None:
            tree = self.treeWidget()
        for item in value.items:
            if item.treeWidget() == tree:
                return item

    def selected(self, sel):
        super().selected(self)
        if sel:
            tree = self.treeWidget()
            if tree:
                self.setSelected(False)
                value = self.param.value()
                item = self.get_ref_item(value, tree)
                if item:
                    # if self.parent():
                    #     self.parent().setExpanded(False)
                    tree.setCurrentItem(item)
                    item.setExpanded(True)
                else:
                    pass
        return


class ReferenceParameter(SimpleParameter):

    def __init__(self, name, ref: Parameter, movable=False, readonly=True,
                 removable=True, **opts):
        opts[ParamOpts.KW.NAME] = name
        opts[ParamOpts.KW.DEFAULT] = None
        opts[ParamOpts.KW.MOVABLE] = movable
        opts[ParamOpts.KW.VALUE] = ref
        opts[ParamOpts.KW.TYPE] = 'object'
        # opts[ParamOpts.KW.VALUE] =
        opts[ParamOpts.KW.READONLY] = readonly
        opts[ParamOpts.KW.REMOVABLE] = removable
        super().__init__(**opts)

    def _interpretValue(self, v):
        return v

    @property
    def itemClass(self):
        return ReferenceParameterItem

    def value(self):
        return super().value()

    # noinspection PyPep8Naming
    def setValue(self, value, blockSignal=None):
        return super().setValue(value, blockSignal=None)
