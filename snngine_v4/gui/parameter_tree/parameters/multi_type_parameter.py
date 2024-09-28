from pyqtgraph.parametertree import Parameter, ParameterItem
from pyqtgraph.parametertree.parameterTypes import WidgetParameterItem
from qtpy import QtWidgets

from snngine_v4.gui.parameter_tree.parameters \
    .multi_type_parameter_widget import MultiTypeParameterWidget
from snngine_v4.gui.parameter_tree.parameters.parameter_item_mixin import \
    WidgetParameterItemMixin
from snngine_v4.gui.parameter_tree.parameters.rgba_widget import \
    MultiSpinBoxWidget
from snngine_v4.gui.parameter_tree.parameters.spin_box_slider import \
    SpinBoxSlider


class PseudoParameterItem(QtWidgets.QTreeWidgetItem, WidgetParameterItemMixin):

    def __init__(self, widget, param: Parameter,
                 parent_item, parent=None, ):
        super().__init__(parent)
        self.hideWidget = True
        self._widget = None
        self._connected_widgets = []
        self.widget = widget
        self.param = param
        self.parent_item = parent_item

    @property
    def __class__(self):
        return WidgetParameterItem

    def selected(self, sel):

        if self._widget is None:
            return
        if sel and self.param.writable():
            self.parent_item.showEditor()
            if isinstance(self._widget, SpinBoxSlider):
                self._widget.setFocusOnSpinBox()
        elif self.hideWidget:
            self.parent_item.hideEditor()

    @property
    def widget(self):
        return self._widget

    @widget.setter
    def widget(self, value):
        self._widget = value
        if value not in self._connected_widgets:
            self._connected_widgets.append(value)
            if isinstance(value, SpinBoxSlider):
                value.sliderPressed.connect(self.valueWidgetClicked)


# noinspection PyPep8Naming
class MultiTypeParameterItem(WidgetParameterItem, WidgetParameterItemMixin):

    def __init__(self, *args, **kwargs):
        self.widget: MultiTypeParameterWidget | None = None
        super().__init__(*args, **kwargs)
        self._remove_spacer_item()
        self._replace_display_label()
        self.layoutWidget.layout().insertWidget(0, self.displayLabel)

        self.typeSubItem = QtWidgets.QTreeWidgetItem()
        self.typeSubItem.setText(0, 'Type')
        self.addChild(self.typeSubItem)

        self.widget_children_items: list[PseudoParameterItem] = []
        # self.n_visible_children = 0

        self._set_size_policies()

    def makeWidget(self):
        wdg = MultiTypeParameterWidget(**self.param.opts)
        wdg.sigWidgetTypeChanged.connect(self.onTypeChange)
        wdg.sigWidgetCreated.connect(self.onTypeChange)

        for widget in wdg.widget_map.values():
            self.onTypeWidgetCreated(widget)

        return wdg

    def is_from_numeric_group(self):
        return True

    def update_children(self):
        widget = self.widget.editor_widget
        if isinstance(widget, MultiSpinBoxWidget):
            tree: QtWidgets.QTreeWidget = self.treeWidget()
            if tree is not None:
                n_visible_children = 0
                n_sliders = len(widget.slider_map.items())
                for i,  (k, slider) in enumerate(widget.slider_map.items()):
                    if i >= len(self.widget_children_items):
                        item = PseudoParameterItem(
                            widget=slider, param=self.param,
                            parent_item=self)
                        self.widget_children_items.append(item)
                        self.addChild(item)
                    else:
                        item = self.widget_children_items[i]
                        item.widget = slider
                        item.setHidden(False)
                    n_visible_children += 1
                    item.setText(0, k)
                    tree.setItemWidget(item, 1, slider.layout_widget())
                if n_sliders < n_visible_children:
                    for i in range(n_sliders, n_visible_children):
                        self.widget_children_items[i].setHidden(True)
        else:
            for item in self.widget_children_items:
                item.setHidden(True)
        self.hideEditor()

    def onTypeWidgetCreated(self, widget, key=None, type_=None):
        # if isinstance(widget, MultiSpinBoxWidget):
        #     for i, (k, slider) in enumerate(widget.slider_map.items()):
                # slider.sliderPressed.connect(self.valueWidgetClicked)
                # slider.sliderPressed.connect(slider.setFocusOnSpinBox)
                # slider.spinbox.connect(slider.setFocusOnSpinBox)
        pass

    def onTypeChange(self, widget, key=None, type_=None):
        self.update_children()
        # if isinstance(widget, MultiSpinBoxWidget):
        self.displayLabel.setText(self.widget.value_text)
        self.valueWidgetClicked()
    
    def showEditor(self):
        super().showEditor()

    def treeWidgetChanged(self):
        super().treeWidgetChanged()
        tree: QtWidgets.QTreeWidget = self.treeWidget()
        if tree is not None:
            tree.setItemWidget(self.typeSubItem, 1, self.widget.type_combo)
            self.selected(False)
            self.update_children()

    def updateDisplayLabel(self):
        txt = self.widget.value_text
        super().updateDisplayLabel(txt)

    def widgetValueChanged(self):
        ## called when the widget's value has been changed by the user
        val = self.widget.value()
        self.param.setValue(val)


class MultiTypeParameter(Parameter):
    itemClass = MultiTypeParameterItem

    def __init__(self, **opts):
        # opts[ParamOpts.KW.C_NUMERIC_GROUP] = True
        super().__init__(**opts)

    def setValue(self, value, blockSignal=None):
        super().setValue(value, blockSignal=blockSignal)
