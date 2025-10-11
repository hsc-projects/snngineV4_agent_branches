from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Callable

import numpy as np
from pyqtgraph import SpinBox
from qtpy import QtCore, QtWidgets

from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


@dataclass(kw_only=True)
class RangeMap:
    min0: int | float = 0
    max0: int | float = 1
    min1: int | float = 0
    max1: int | float = 1
    _step0: int | float = 1
    _step1: int | float = field(init=False, default=None)

    def convert_to_source(self, value):
        n_steps1 = (value - self.min1) / self._step1
        source_value = self.min0 + self._step0 * n_steps1
        return source_value

    def convert_to_target(self, value):
        n_steps0 = (value - self.min0) / self._step0
        target_value = self.min1 + self._step1 * n_steps0
        return target_value

    @property
    def step0(self):
        return self._step0

    @step0.setter
    def step0(self, value):
        if isinstance(value, Decimal):
            value = float(value)
        self._step0 = value
        self.reset_step1()

    def reset_step1(self):
        if self._step0 != 0:
            n_steps0 = (self.max0 - self.min0) / self._step0
            if n_steps0 != 0:
                self._step1 = (self.max1 - self.min1) / n_steps0
            else:
                self._step1 = np.nan
        else:
            self._step1 = np.nan


class RangeMapWidget(QtWidgets.QGroupBox):

    sigRangeMapUpdated = QtCore.Signal(object)

    layout: Callable[..., QtWidgets.QHBoxLayout]

    def __init__(self,
                 label0: str,
                 label1: str,
                 title="Range Map",
                 range_map=None,
                 **kwargs):
        super().__init__(title=title, **kwargs)
        self.setLayout(QtWidgets.QHBoxLayout())

        self.label0 = QtWidgets.QLabel(label0)
        self.max0 = SpinBox()
        self.min0 = SpinBox()

        self.label1 = QtWidgets.QLabel(label1)
        self.max1 = SpinBox()
        self.min1 = SpinBox()

        v_layout0 = QtWidgets.QVBoxLayout()
        v_layout0.addWidget(self.label0)
        v_layout0.addWidget(self.max0)
        v_layout0.addWidget(self.min0)

        v_layout1 = QtWidgets.QVBoxLayout()
        v_layout1.addWidget(self.label1)
        v_layout1.addWidget(self.max1)
        v_layout1.addWidget(self.min1)

        self.layout().addLayout(v_layout0)
        self.layout().addLayout(v_layout1)

        if range_map is None:
            range_map = RangeMap()
            self.range_map = range_map
        else:
            self.range_map = range_map
            self.update_widgets()

        self.connect_range_map()

    def connect_range_map(self):
        self.min0.sigValueChanged.connect(self.update_range_map)
        self.max0.sigValueChanged.connect(self.update_range_map)
        self.min1.sigValueChanged.connect(self.update_range_map)
        self.max1.sigValueChanged.connect(self.update_range_map)

    def disconnect_range_map(self):
        self.min0.sigValueChanged.connect(self.update_range_map)
        self.max0.sigValueChanged.connect(self.update_range_map)
        self.min1.sigValueChanged.connect(self.update_range_map)
        self.max1.sigValueChanged.connect(self.update_range_map)

    @classmethod
    def from_spinbox(cls, spinbox: SpinBox, **kwargs):
        new = cls(**kwargs)
        new.disconnect_range_map()

        min_value = spinbox.opts['bounds'][0]
        max_value = spinbox.opts['bounds'][1]
        new.set_range0(min_value, max_value,
                       min_value, max_value,
                       step=1, int=True)
        new.set_range1(min_value, max_value,
                       step=1, int=True)
        new.update_range_map()
        new.connect_range_map()

        def set_max(spinbox_):
            spinbox.setMaximum(spinbox_.value())

        def set_min(spinbox_):
            spinbox.setMinimum(spinbox_.value())

        new.min1.sigValueChanged.connect(set_min)
        new.max1.sigValueChanged.connect(set_max)
        return new

    def update_range_map(self):
        self.range_map.min0 = self.min0.value()
        self.range_map.max0 = self.max0.value()
        self.range_map.min1 = self.min1.value()
        self.range_map.max1 = self.max1.value()
        self.range_map.step0 = self.min0.opts[ParamOpts.KW.STEP]
        self.sigRangeMapUpdated.emit(self.range_map)

    def update_widgets(self):
        self.min0.setValue(self.range_map.min0)
        self.max0.setValue(self.range_map.max0)
        self.min1.setValue(self.range_map.min1)
        self.max1.setValue(self.range_map.max1)

    def _set_range(self,
                   min_spinbox: SpinBox,
                   max_spinbox: SpinBox,
                   minimum, maximum,
                   minimum_allowed=None,
                   maximum_allowed=None,
                   **opts):
        if maximum is not None:
            max_spinbox.setValue(maximum)
        if minimum is not None:
            min_spinbox.setValue(minimum)
        if minimum_allowed is not None:
            max_spinbox.setMinimum(minimum_allowed)
            min_spinbox.setMinimum(minimum_allowed)
        if maximum_allowed is not None:
            min_spinbox.setMaximum(maximum_allowed)
            max_spinbox.setMaximum(maximum_allowed)
        if len(opts) > 0:
            max_spinbox.setOpts(**opts)
            min_spinbox.setOpts(**opts)

    def set_range0(self, minimum, maximum,
                   minimum_allowed=None, maximum_allowed=None,
                   **opts):
        self._set_range(
            min_spinbox=self.min0, max_spinbox=self.max0,
            minimum_allowed=minimum_allowed,
            maximum_allowed=maximum_allowed,
            minimum=minimum, maximum=maximum, **opts)

    def set_range1(self, minimum, maximum,
                   minimum_allowed=None,
                   maximum_allowed=None,
                   **opts):
        self._set_range(
            min_spinbox=self.min1, max_spinbox=self.max1,
            minimum_allowed=minimum_allowed,
            maximum_allowed=maximum_allowed,
            minimum=minimum, maximum=maximum, **opts)
