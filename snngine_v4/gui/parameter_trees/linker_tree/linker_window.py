from enum import IntEnum, auto
from typing import Callable

from pyqtgraph import ComboBox
from qtpy import QtWidgets


class ControllerTypes(IntEnum):
    TOGGLE = 0
    INCREASE = auto()
    DECREASE = auto()
    EDIT = auto()
    FOCUS = auto()


class LinkerWidget(QtWidgets.QWidget):

    layout: Callable[..., QtWidgets.QFormLayout]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.setLayout(QtWidgets.QFormLayout())
        self.type_combo = ComboBox()
        self.all_types_items = {
            x.name.title(): x for x in ControllerTypes
        }
        self.layout().addRow('Type: ', self.type_combo)

        self.clear_btn = QtWidgets.QPushButton('Clear')
        self.save_button = QtWidgets.QPushButton('Save')
        self.layout().addRow(self.clear_btn, self.save_button)


class LinkerWidgetHeader(QtWidgets.QWidget):

    layout: Callable[..., QtWidgets.QFormLayout]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.setLayout(QtWidgets.QFormLayout())
        self.param_label = QtWidgets.QLabel()
        self.layout().addRow('Parameter: ', self.param_label)


class LinkerWindow(QtWidgets.QWidget):

    layout: Callable[..., QtWidgets.QVBoxLayout]

    def __init__(self, window_title, **kwargs):
        super().__init__(**kwargs)
        self.setWindowTitle(window_title)

        self.setLayout(QtWidgets.QVBoxLayout())

        self._parameter = None
        self.header = LinkerWidgetHeader()
        self.layout().addWidget(self.header)

        self.header_qline = QtWidgets.QFrame()
        self.header_qline.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.layout().addWidget(self.header_qline)

        self.widgets: list[LinkerWidget] = []

        self.add_btn = QtWidgets.QPushButton('ADD')
        self.layout().addWidget(self.add_btn)
        self.add_btn.clicked.connect(self.add_widget)

        self.add_widget()

    def add_widget(self):
        wdg = LinkerWidget()
        idx = self.layout().indexOf(self.add_btn)
        self.layout().insertWidget(idx, wdg)
        self.widgets.append(wdg)
        qline = QtWidgets.QFrame()
        qline.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.layout().insertWidget(idx+1, qline)
        return wdg


    @property
    def parameter(self):
        return self._parameter

    @parameter.setter
    def parameter(self, value):
        self._parameter = value

        label = self._parameter.name()
        parent = self.parameter.parent()
        while parent:
            label = parent.name() + '.' + label
            parent = parent.parent()

        self.header.param_label.setText(label)
        for wdg in self.widgets:
            wdg.type_combo.setItems(wdg.all_types_items)


class ShortCutWindow(LinkerWindow):

    def __init__(self, **kwargs):
        super().__init__(window_title='Set short-cut', **kwargs)

    def add_widget(self):
        wdg = super().add_widget()
        shortcut_edit = QtWidgets.QKeySequenceEdit()
        wdg.layout().insertRow(1, 'Short Cut: ', shortcut_edit)
        wdg.clear_btn.clicked.connect(shortcut_edit.clear)
