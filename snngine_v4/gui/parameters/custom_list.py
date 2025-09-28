from pyqtgraph.parametertree.parameterTypes import ListParameter


class CustomListParameter(ListParameter):

    def setLimits(self, limits):
        super().setLimits(limits)

    def setValue(self, value, blockSignal=None):
        super().setValue(value, blockSignal)
