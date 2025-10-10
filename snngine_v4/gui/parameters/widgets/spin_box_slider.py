from decimal import Decimal
from functools import cached_property

import numpy as np
import pandas as pd
from pyqtgraph import SpinBox
from qtpy import QtCore, QtWidgets

from snngine_v4.gui.parameters.widgets.clickable_label import (
    ClickableLabel,
)
from snngine_v4.gui.parameters.widgets.custom_spin_box import \
    CustomSpinBox
from snngine_v4.utils.core_utils import IntervalClosedType
from snngine_v4.utils.data_utils.interval_utils import (
    linspace_from_interval,
    restricted_linspace_interval,
)
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


class CustomSlider(QtWidgets.QSlider):

    @classmethod
    def make_span(cls, interval, step_size, value,
                  n_offset_steps=1000):

        b_value_is_none = pd.isna(value)
        if b_value_is_none:
            if interval.length == np.inf:
                if step_size is None:
                    step_size = 1
                if interval.left == -np.inf:
                    if interval.right == np.inf:
                        value = 0
                    else:
                        value = interval.right
                        if interval.closed in ['right', 'neither']:
                            value -= step_size
                else:
                    value = interval.left
                    if interval.closed in ['lift', 'neither']:
                        value += step_size

        if interval.length == np.inf:
            if step_size is None:
                step_size = 1
            offset = n_offset_steps * step_size

            if abs(value) * 9 < offset:
                ref_value = 0
            else:
                ref_value = value
            if interval.left == -np.inf:

                if interval.right == np.inf:
                    interval = pd.Interval(
                        ref_value - offset,
                        ref_value + offset,
                        closed='neither')
                else:
                    if interval.closed in ['left', 'neither']:
                        closed: IntervalClosedType = 'left'
                    else:
                        closed = 'both'
                    interval = pd.Interval(
                        ref_value - offset,
                        interval.right,
                        closed=closed)
            elif interval.right == np.inf:
                if interval.closed in ['right', 'neither']:
                    closed: IntervalClosedType = 'right'
                else:
                    closed = 'both'
                interval = pd.Interval(
                    interval.left, ref_value + offset,
                    closed=closed)

        max_n_steps = 2 * n_offset_steps + 1
        if step_size is None:
            n_steps_if_closed = max_n_steps
        else:
            # noinspection PyTypeChecker,PydanticTypeChecker
            n_steps_if_closed = int(interval.length / step_size + .5) + 1

        if n_steps_if_closed > 1e6:
            interval, n_steps_if_closed = restricted_linspace_interval(
                interval=interval,
                step_size=step_size,
                value=value, max_n_steps=max_n_steps
            )

        span = linspace_from_interval(
            interval=interval,
            n_steps_if_closed=n_steps_if_closed,
            b_change_n_steps_if_open=True)

        return span

    def wheelEvent(self, e) -> None:
        if self.hasFocus():
            super().wheelEvent(e)


# noinspection PyPep8Naming
class SpinBoxSlider(CustomSlider):

    sigSliderSpanChanged = QtCore.Signal(object)

    def __init__(self,
                 spinbox: SpinBox = None,
                 orientation=QtCore.Qt.Orientation.Horizontal,
                 parent=None, **opts):

        if opts.get(ParamOpts.KW.SPAN, None) is None:
            span = CustomSlider.make_span(
                interval=opts[ParamOpts.KW.C_VALUE_INTERVAL],
                value=opts[ParamOpts.KW.VALUE],
                step_size=opts[ParamOpts.KW.STEP]
            )
            opts[ParamOpts.KW.SPAN] = span

        if spinbox is None:
            spinbox = CustomSpinBox.from_opts(**opts)

        super().__init__(orientation=orientation, parent=parent)

        self._display_widget = None
        self._conversion = None

        self.spinbox = spinbox
        self.span = None
        self.charSpan = None
        self.set_span(opts[ParamOpts.KW.SPAN])
        self._reset_slider_divider = 20

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
        )

        orientation = opts.get('widget_orientation', 'Horizontal')
        self.setOrientation(QtCore.Qt.Orientation[orientation])

        self.spinbox.sigValueChanging.connect(self.setValueFromSpinBox)
        self.spinbox.sigValueChanged.connect(self.updateDisplayWidget)
        self.sliderReleased.connect(self.onSliderRelease)

        slider_value = self.spanToSliderValue(opts[ParamOpts.KW.VALUE])
        self.setValue(slider_value)

        self.valueChanged.connect(self.setValueFromSlider)

        self._layout_widget = None

    @cached_property
    def display_widget(self):
        return ClickableLabel(conversion=self._conversion)

    def updateDisplayWidget(self, ev=None):
        if self._display_widget is not None:
            txt = self.spinbox.lineEdit().text()
            self._display_widget.setText(txt)

    def layout_widget(self,):
        if self._layout_widget is None:
            widget = QtWidgets.QWidget()
            widget.setLayout(QtWidgets.QHBoxLayout())
            widget.layout().addWidget(self)
            widget.layout().setContentsMargins(13, 0, 13, 0)
            widget.setMinimumWidth(50)
            self._layout_widget = widget
        return self._layout_widget

    @property
    def bounds(self):
        return np.float64(np.array(self.opts[ParamOpts.KW.BOUNDS]))

    @property
    def opts(self) -> dict:
        return self.spinbox.opts

    def setFocusOnSpinBox(self):
        self.spinbox.setFocus(QtCore.Qt.FocusReason.OtherFocusReason)
        self.spinbox.selectNumber()

    def onSliderRelease(self):
        if self._reset_span_condition():
            idx = self.value()
            d = self._reset_slider_divider
            if ((idx < len(self.span) // d)
                    or (idx > (d - 1) * len(self.span) // d)):
                new_idx = self._reset_span(self.span[idx])
                # new_idx = self.spanToSliderValue(self.span[idx])
                self.setValueFromSpinBox(None, self.span[new_idx])

    def set_span(self, span):
        self.span = span
        self.charSpan = np.char.array(span)
        self.setMinimum(0)
        self.setMaximum(len(span) - 1)
        self.sigSliderSpanChanged.emit(self.span)

    def _reset_span(self, value):
        lims = self.bounds
        step = float(self.opts.get(ParamOpts.KW.STEP, 1))

        span = np.arange(
            max(lims[0], value - step * 100),
            min(lims[1], value + step * 100), step)
        self.set_span(span)
        new_value = self.spanToSliderValue(value)
        return new_value

    def _reset_span_condition(self):
        lims = self.bounds
        has_inf = np.isinf(lims)
        return bool(np.any(has_inf))

    def setValueFromSlider(self, idx):
        self.spinbox.sigValueChanging.disconnect(self.setValueFromSpinBox)
        value = self.span[idx]
        if self.opts[ParamOpts.KW.STEP] == Decimal('0.01'):
            value = round(Decimal(self.span[idx]), 2)
        self.spinbox.setValue(value)
        self.spinbox.sigValueChanging.connect(self.setValueFromSpinBox)

    def setValueFromSpinBox(self, box, value):
        self.valueChanged.disconnect(self.setValueFromSlider)
        new_value = self.spanToSliderValue(value)
        if self._reset_span_condition():
            d = self._reset_slider_divider
            if ((value < self.span[len(self.span) // d])
                    or (value > self.span[(d - 1) * len(self.span) // d])):
                self._reset_span(value)
        self.setValue(new_value)
        self.valueChanged.connect(self.setValueFromSlider)

    def spanToSliderValue(self, v):
        return int(np.argmin(np.abs(self.span - v)))
