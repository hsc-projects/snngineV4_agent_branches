from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import WidgetParameterItem
from qtpy import QtCore, QtWidgets

from snngine_v4.gui.parameter_tree.parameters \
    .multi_type_parameter_widget import MultiTypeParameterWidget
from snngine_v4.gui.parameter_tree.parameters.parameter_item_mixin import \
    WidgetParameterItemMixin
from snngine_v4.gui.parameter_tree.parameters.rgba_widget import \
    MultiSpinBoxWidget


# noinspection PyPep8Naming
class MultiTypeParameterItem(WidgetParameterItem, WidgetParameterItemMixin):

    def __init__(self, *args, **kwargs):
        self.widget: MultiTypeParameterWidget | None = None
        super().__init__(*args, **kwargs)
        self._remove_spacer_item()
        self.layoutWidget.layout().insertWidget(0, self.displayLabel)

        self.typeSubItem = QtWidgets.QTreeWidgetItem()
        self.typeSubItem.setText(0, 'Type')
        self.addChild(self.typeSubItem)

        self.widget_children_items: list[QtWidgets.QTreeWidgetItem] = []
        # self.n_visible_children = 0

        self._set_size_policies()

    def makeWidget(self):
        wdg = MultiTypeParameterWidget(**self.param.opts)
        wdg.sigWidgetTypeChanged.connect(self.onTypeChange)
        return wdg

    def is_from_numeric_group(self):
        return True

    def onTypeChange(self, widget, key, type_):
        if isinstance(widget, MultiSpinBoxWidget):
            tree: QtWidgets.QTreeWidget = self.treeWidget()
            if tree is not None:
                n_visible_children = 0
                n_sliders = len(widget.slider_map.items())
                for i,  (k, slider) in enumerate(widget.slider_map.items()):
                    if i >= len(self.widget_children_items):
                        item = QtWidgets.QTreeWidgetItem()
                        self.widget_children_items.append(item)
                        self.addChild(item)
                    else:
                        item = self.widget_children_items[i]
                        item.setHidden(False)
                    n_visible_children += 1
                    item.setText(0, k)
                    tree.setItemWidget(item, 1, slider)
                if n_sliders < n_visible_children:
                    for i in range(n_sliders, n_visible_children):
                        self.widget_children_items[i].setHidden(True)
        else:
            for item in self.widget_children_items:
                item.setHidden(True)
        self.valueWidgetClicked()

    def treeWidgetChanged(self):
        super().treeWidgetChanged()
        tree: QtWidgets.QTreeWidget = self.treeWidget()
        if tree is not None:
            tree.setItemWidget(self.typeSubItem, 1, self.widget.type_combo)
            self.selected(False)


class MultiTypeParameter(Parameter):
    itemClass = MultiTypeParameterItem

    def __init__(self, **opts):
        # opts[ParamOpts.KW.C_NUMERIC_GROUP] = True
        super().__init__(**opts)
