from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import WidgetParameterItem
from qtpy import QtCore, QtWidgets

from snngine_v4.gui.parameter_tree.parameters \
    .multi_type_parameter_widget import MultiTypeParameterWidget


# noinspection PyPep8Naming
class MultiTypeParameterItem(WidgetParameterItem):

    def __init__(self, *args, **kwargs):

        self.widget: MultiTypeParameterWidget | None = None

        super().__init__(*args, **kwargs)

    def makeWidget(self):
        wdg = MultiTypeParameterWidget(**self.param.opts)
        wdg.sigWidgetCreated.connect(self.onWidgetTypeCreated)
        return wdg

    def onTypeChange(self, ev=None):
        if self.widget.editor_widget:
            pass

    def onWidgetTypeCreated(self, widget, key, type_):
        if isinstance(widget, QtWidgets.QLineEdit):
            self.widget.editor_widget.sizeHint = self.displayLabel.sizeHint


class MultiTypeParameter(Parameter):
    itemClass = MultiTypeParameterItem
