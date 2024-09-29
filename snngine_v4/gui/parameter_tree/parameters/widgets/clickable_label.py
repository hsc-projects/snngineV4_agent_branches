from qtpy import QtCore, QtWidgets


class ClickableLabel(QtWidgets.QLabel):
    sigClicked = QtCore.Signal()

    def __init__(self, *args, conversion=None, **kwargs):
        if conversion is None:
            conversion = {}
        self.conversion = conversion
        super().__init__(*args, **kwargs)

    def mousePressEvent(self, e):
        self.sigClicked.emit()
    
    def setVisible(self, visible):
        super().setVisible(visible)
    
    def setText(self, txt):
        if txt in self.conversion:
            txt = self.conversion[txt]
        super().setText(txt)
