from __future__ import annotations

from functools import cached_property

import numpy as np
import pandas as pd
from qtpy import QtCore, QtGui, QtWidgets

from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_ui_config import (UIConfig,
                                                                      XTMRangeMapWidget)
from snngine_v4.gui.parameter_trees.linker_tree.range_map_widget import \
    (RangeMap, RangeMapWidget)


class XTMFaderWidget(QtWidgets.QWidget):

    def __init__(self, xtm_device, b_range_map: bool = True,
                 b_verbose: bool = True,
                 **kwargs):
        super().__init__(**kwargs)
        self._xtm_device = xtm_device

        self.b_verbose = b_verbose
        from snngine_v4.gui.parameters.spin_box_slider_parameter import (
            SpinBoxSliderParameter)

        self._range_map: RangeMap | None = None
        self.fader_par = SpinBoxSliderParameter(
            default=0,
            name='Fader',
            c_value_interval=pd.Interval(0, 128),
            # limits=(0, 127),
            step=1, value=0,
            bounds=(0, 127),
            widget_orientation='Vertical')

        self.fader_item = self.fader_par.makeTreeItem(depth=0)
        self.fader_item.widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.Minimum,
        )

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.fader_item.slider)
        self.layout().addWidget(self.fader_item.widget)

        self.setFixedWidth(UIConfig.TEXT_BUTTON_WIDTH)

        self.contextMenu: QtWidgets.QMenu | None = None
        if b_range_map:
            self.range_map_widget.setVisible(False)

    def contextMenuEvent(self, ev):
        self.contextMenu = QtWidgets.QMenu()
        show_range_map_action = QtGui.QAction("Range Map")
        show_range_map_action.setCheckable(True)
        show_range_map_action.triggered.connect(self.show_range_map_widget)
        self.contextMenu.addAction(show_range_map_action)
        self.contextMenu.exec(ev.globalPos())

    @cached_property
    def range_map_widget(self):
        wdg = XTMRangeMapWidget.from_spinbox(spinbox=self.fader_item.widget)
        wdg.setWindowTitle(f"Fader")
        self._range_map = wdg.range_map
        wdg.setVisible(False)
        wdg.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)

        def set_max(spinbox_):
            span = np.linspace(wdg.min1.value(),
                               spinbox_.value(), 128)
            self.fader_item.slider.set_span(span)
            self.fader_item.slider.setValueFromSlider(
                self.fader_item.slider.value()
                # self.fader_item.slider.spanToSliderValue(
                #     self.fader_item.widget.value())
            )

        def set_min(spinbox_):
            span = np.linspace(spinbox_.value(),
                               wdg.max1.value(), 128)
            self.fader_item.slider.set_span(span)
            self.fader_item.slider.setValueFromSlider(
                self.fader_item.slider.value()
                # self.fader_item.slider.spanToSliderValue(
                #     self.fader_item.widget.value())
            )

        wdg.min1.sigValueChanged.connect(set_min)
        wdg.max1.sigValueChanged.connect(set_max)
        return wdg

    def update_from_device(self):
        value = self._xtm_device.device_config.get_fader_value()

        # if self._range_map is not None:
        #     new_value = self._range_map.convert_to_target(value)
        #     if self.b_verbose:
        #         print('fader value (widget):', value, f"({new_value})")
        #     self.fader_item.slider.setValue(new_value)
        # else:
        # if self.b_verbose:
        #     self.
        self.fader_item.slider.setValue(value)

    def show_range_map_widget(self, value):
        self.clearFocus()
        self.range_map_widget.setVisible(value)
