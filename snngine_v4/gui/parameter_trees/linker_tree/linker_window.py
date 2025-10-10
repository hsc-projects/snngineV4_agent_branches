from __future__ import annotations

from typing import Callable, TYPE_CHECKING, Union

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtWidgets import QSizePolicy

from snngine_v4.gui.parameter_trees.linker_tree.controls_map import \
    ControllerAction
from snngine_v4.gui.parameter_trees.linker_tree.linker_widget import \
    (LinkerWidget, ShortCutWidget)
from snngine_v4.utils.containers.mappings import Object2ObjectMap


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


type CtrlWidgetMap = Union[Object2ObjectMap,
                           dict[ControllerAction, LinkerWidget]]


class LinkerWindow(QtWidgets.QScrollArea):

    layout: Callable[..., QtWidgets.QVBoxLayout]

    def __init__(self, linker_tree, window_title, **kwargs):
        super().__init__(**kwargs)
        
        self.setWindowTitle(window_title)
        self.setWindowModality(
            QtCore.Qt.WindowModality.ApplicationModal)

        self.base_title = window_title
        self.linker_tree: LinkerTree = linker_tree

        self.widget_line_map = Object2ObjectMap.from_types(
            QtWidgets.QWidget, QtWidgets.QWidget, b_pop_allowed=True)
        self.ctrl_widget_map: CtrlWidgetMap = (
            Object2ObjectMap.from_types(
                type0=ControllerAction, type1=QtWidgets.QWidget,
                b_pop_allowed=True, b_clear_allowed=True))
        self.widgets: list[LinkerWidget] = []
        self._parameter = None

        self.header = LinkerWindowHeader()
        self.header_qline = QtWidgets.QFrame()
        self.header_qline.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.add_btn = QtWidgets.QPushButton("  ADD  ")
        self.add_btn.clicked.connect(self.add_widget)
        self.add_btn.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )

        self.setWidget(QtWidgets.QWidget())
        self.setWidgetResizable(True)
        self.widget().setLayout(QtWidgets.QVBoxLayout())

        # noinspection PyTypeChecker
        layout: QtWidgets.QVBoxLayout = self.widget().layout()
        layout.addWidget(self.header)
        layout.addWidget(self.header_qline)
        layout.addWidget(self.add_btn)
        layout.setAlignment(QtGui.Qt.AlignmentFlag.AlignTop)
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

        self.widget_line_map[wdg] = qline

        wdg.sigWidgetDelete.connect(self.remove_linker_widget)

        def on_link_saved():
            self.ctrl_widget_map[wdg.controller] = wdg

        wdg.sigLinkSaved.connect(on_link_saved)

        def on_link_deleted():
            self.ctrl_widget_map.pop(self.ctrl_widget_map.inv[wdg])

        wdg.sigLinkDeleted.connect(on_link_deleted)

        return wdg

    def remove_linker_widget(
            self, widget: LinkerWidget, b_disconnect: bool = True):
        # noinspection PyTypeChecker
        layout: QtWidgets.QVBoxLayout = self.widget().layout()
        if b_disconnect:
            widget.disconnect_parameter(b_block_signal=True)
        if widget in self.ctrl_widget_map.inv:
            self.ctrl_widget_map.pop(self.ctrl_widget_map.inv[widget])
        layout.removeWidget(widget)
        qline = self.widget_line_map.pop(widget)
        layout.removeWidget(qline)
        widget.setParent(None)
        qline.setParent(None)
        self.widgets.remove(widget)

    @property
    def parameter(self):
        return self._parameter

    @parameter.setter
    def parameter(self, parameter):
        self._parameter = parameter
        text = LinkerWidget.parameter_label_text(self._parameter)
        self.header.param_label.setText(text)

        self.ctrl_widget_map.clear()

        controllers = []
        if parameter in self.linker_tree.controls_map:
            controllers = list(
                self.linker_tree.controls_map[parameter].values())

        controller_count = len(controllers)

        wdg_count = len(self.widgets)

        for i in range(max(controller_count, wdg_count)):
            if i < wdg_count:
                widget = self.widgets[i]
            else:
                widget = self.add_widget()

            widget.parameter = parameter
            if i < controller_count:
                self.ctrl_widget_map[controllers[i]] = widget
                widget.load_controller(controllers[i])
            else:
                widget.reset(parameter=parameter)
        # for widget in self.widgets:
        #     widget.parameter = value

    def set_window_title(self, suffix, base_title: str | None = None):
        if base_title is None:
            base_title = self.base_title
        self.setWindowTitle(base_title + suffix)


class ShortCutWindow(LinkerWindow):

    def __init__(self,
                 linker_tree: LinkerTree,
                 window_title='Shortcut',
                 **kwargs):

        super().__init__(linker_tree=linker_tree,
                         window_title=window_title, **kwargs)

    def make_widget(self,) -> ShortCutWidget:
        return ShortCutWidget(parameter=self._parameter,
                              linker_tree=self.linker_tree)
