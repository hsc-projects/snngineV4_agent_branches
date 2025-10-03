from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from pyqtgraph.parametertree import Parameter
from qtpy import QtCore, QtWidgets
from qtpy.QtWidgets import QSizePolicy

from snngine_v4.gui.parameter_trees.linker_tree.linker_widget import \
    (LinkerWidget, ShortCutWidget)


if TYPE_CHECKING:
    from snngine_v4.gui.parameter_trees.linker_tree.linker_tree \
        import LinkerTree


class LinkerWindowHeader(QtWidgets.QWidget):

    layout: Callable[..., QtWidgets.QFormLayout]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.setLayout(QtWidgets.QFormLayout())
        self.param_label = QtWidgets.QLabel()
        self.layout().addRow('Parameter: ', self.param_label)
        self.setSizePolicy(QSizePolicy.Policy.Fixed,
                           QSizePolicy.Policy.Fixed,)


class LinkerWindow(QtWidgets.QScrollArea):

    layout: Callable[..., QtWidgets.QVBoxLayout]

    def __init__(self, linker_tree, window_title, **kwargs):
        super().__init__(**kwargs)

        self.linker_tree: LinkerTree = linker_tree

        self.setWindowTitle(window_title)
        wdg = QtWidgets.QWidget()
        # self.setLayout(QtWidgets.QVBoxLayout())
        wdg.setLayout(QtWidgets.QVBoxLayout())
        self.setWidget(wdg)

        # noinspection PyTypeChecker
        layout: QtWidgets.QVBoxLayout = self.widget().layout()

        alignment = QtCore.Qt.AlignmentFlag.AlignTop
        layout.setAlignment(alignment)

        self._parameter = None
        self.header = LinkerWindowHeader()
        layout.addWidget(self.header)

        self.header_qline = QtWidgets.QFrame()
        self.header_qline.setFrameShape(QtWidgets.QFrame.Shape.HLine)

        layout.addWidget(self.header_qline)

        self.widgets: list[LinkerWidget] = []

        self.add_btn = QtWidgets.QPushButton('ADD')
        layout.addWidget(self.add_btn)
        self.add_btn.clicked.connect(self.add_widget)
        self.setWidgetResizable(True)
        # self.setFixedHeight(200)
        self.add_widget()

    def make_widget(self):
        return LinkerWidget(parameter=self._parameter,
                            linker_tree=self.linker_tree)

    def add_widget(self):
        wdg = self.make_widget()
        # noinspection PyTypeChecker
        layout: QtWidgets.QVBoxLayout = self.widget().layout()

        idx = layout.indexOf(self.add_btn)
        layout.insertWidget(idx, wdg)
        self.widgets.append(wdg)
        qline = QtWidgets.QFrame()
        qline.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        layout.insertWidget(idx+1, qline)

        def remove_widget():
            wdg.disconnect_parameter()
            layout.removeWidget(wdg)
            layout.removeWidget(qline)
            wdg.setParent(None)
            qline.setParent(None)
            self.widgets.remove(wdg)

        wdg.delete_button.clicked.connect(remove_widget)

        return wdg

    @property
    def parameter(self):
        return self._parameter

    @parameter.setter
    def parameter(self, value):
        self._parameter = value
        text = LinkerWidget.parameter_label_text(self._parameter)
        self.header.param_label.setText(text)

        controllers = []
        if value in self.linker_tree.controls_map:
            controllers = list(self.linker_tree.controls_map[value].values())

        controller_count = len(controllers)

        wdg_count = len(self.widgets)

        for i in range(max(controller_count, wdg_count)):
            if i < wdg_count:
                widget = self.widgets[i]
            else:
                widget = self.add_widget()

            widget.parameter = value
            if i < controller_count:
                widget.load_controller(controllers[i])

        # for widget in self.widgets:
        #     widget.parameter = value


class ShortCutWindow(LinkerWindow):

    def __init__(self, linker_tree: LinkerTree, **kwargs):
        super().__init__(
            linker_tree=linker_tree,
            window_title='Set short-cut', **kwargs)

    def make_widget(self,) -> ShortCutWidget:
        return ShortCutWidget(parameter=self._parameter,
                              linker_tree=self.linker_tree)

    # def add_widget(self) -> ShortCutWidget:
        # wdg: ShortCutWidget = super().add_widget()
        # return wdg
