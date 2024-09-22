from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from pyqtgraph import SpinBox
from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import (
    NumericParameterItem,
)
from qtpy import QtCore, QtWidgets

from snngine_v4.gui.icons import getEngineGraphIcon

from snngine_v4.gui.parameter_tree.parameters.engine_group_parameter import \
    EngineGroupParameterItem
from snngine_v4.utils.core_utils import IntervalClosedType
from snngine_v4.utils.field_utils import (
    b_is_int_annotation, extract_field_interval,
    get_field_multiple_of,
)
from snngine_v4.utils.interval_utils import (
    coerce_value_into_interval,
    limits_from_interval, linspace_from_interval,
)
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


if TYPE_CHECKING:
    from snngine_v4.gui.parameter_tree.engine_parameter_tree import \
        EngineParameterTree


class ClickableLabel(QtWidgets.QLabel):
    sigClicked = QtCore.Signal()
    
    def __init__(self, *args, conversion=None, **kwargs):
        if conversion is None:
            conversion = {}
        self.conversion = conversion
        super().__init__(*args, **kwargs)
    
    def mousePressEvent(self, e):
        self.sigClicked.emit()
        
    def setText(self, txt):
        if txt in self.conversion:
            txt = self.conversion[txt]
        super().setText(txt)


class CustomSlider(QtWidgets.QSlider):

    def wheelEvent(self, e) -> None:
        if self.hasFocus():
            super().wheelEvent(e)


# noinspection PyPep8Naming
@dataclass
class PseudoCheckBox:

    checked: bool = True

    def isChecked(self):
        return self.checked


# noinspection PyPep8Naming
class SpinBoxSliderParameterItem(NumericParameterItem):

    TEXT_CONVERSIONS = {
        'nan': {'nan': 'None'},
        ParamOpts.KW.C_NONE_MEANS_UNKNOWN: {'nan': 'Unkown'},
    }

    def __init__(self, param, depth):

        self.widget: SpinBox | QtWidgets.QWidget | None = None
        self.span = None
        self.charSpan = None

        self.setNoneCheckbox = None
        self._nullable = param.opts.get(ParamOpts.KW.C_NULLABLE_VALUE, True)

        param.opts.setdefault(ParamOpts.KW.DELAY, .1)

        # if param.opts[ParamOpts.KW.C_MODEL_FIELD_NAME] == 'width':
        #     pass

        super().__init__(param, depth)

        self._reset_slider_divider = 20

        self.slider = self.makeSliderWidget()
        self.widget.sigValueChanging.connect(self.setValueFromSpinBox)

        self.slider_layout_widget = QtWidgets.QWidget()
        self.slider_layout_widget.setLayout(QtWidgets.QHBoxLayout())
        self.slider_layout_widget.layout().addWidget(self.slider)
        self.slider_layout_widget.layout().setContentsMargins(13, 0, 13, 0)

        w = self.layoutWidget.layout().takeAt(2)
        if not isinstance(w, QtWidgets.QSpacerItem):
            raise ValueError(f"{w}")
        self.layoutWidget.layout().removeItem(w)

        self._replace_display_label()

        self.slider.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

        self.widget.setOpts(compactHeight=True)
        self.optsChanged(self.param, {ParamOpts.KW.SPAN: self.span})

        self.param._modifiedSinceReset = False
        self.updateDefaultBtn()

        self.not_none_idx = None

        self.setNoneCheckbox: QtWidgets.QCheckBox | PseudoCheckBox = (
            self.makeSetToNoneCheckbox())
        if isinstance(self.setNoneCheckbox, QtWidgets.QCheckBox):
            self.setNoneCheckbox.clicked.connect(self.checkBoxClicked)
            self.updateCheckBoxUI(self.param.value())

    def checkBoxClicked(self, value):
        b_set_to_none = not bool(value)

        if b_set_to_none is True:
            self.not_none_idx = self.slider.value()
            self.param.setValue(np.nan)
        elif b_set_to_none is False:
            not_none_value = self.not_none_idx
            self.param.setValue(self.span[not_none_value])

        self.displayNoneValue(b_set_to_none, b_update_checkbox=False)
        self.valueWidgetClicked()

    def _replace_display_label(self):
        display_label_item = self.layoutWidget.layout().takeAt(1)
        if display_label_item.wid != self.displayLabel:
            raise ValueError(f"{display_label_item.wid}")
        del self.displayLabel
        self.layoutWidget.layout().removeItem(display_label_item)
        if (self.param.opts.get(ParamOpts.KW.C_NONE_MEANS_UNKNOWN, False)
                is True):
            conversion = self.TEXT_CONVERSIONS[
                ParamOpts.KW.C_NONE_MEANS_UNKNOWN]
        else:
            conversion = self.TEXT_CONVERSIONS['nan']
        self.displayLabel = ClickableLabel(conversion=conversion)
        self.displayLabel.sigClicked.connect(self.valueWidgetClicked)
        self.layoutWidget.layout().insertWidget(0, self.displayLabel)

    def hideEditor(self):
        if self.setNoneCheckbox.isChecked():
            self.widget.hide()
            self.displayLabel.show()
        else:
            self.widget.hide()
            self.displayLabel.show()
        self.slider.clearFocus()

    def makeDefaultButton(self):
        defaultBtn = QtWidgets.QPushButton()
        defaultBtn.setAutoDefault(False)
        defaultBtn.setFixedWidth(20)
        defaultBtn.setFixedHeight(20)
        defaultBtn.setIcon(getEngineGraphIcon('kamiyamane/default'))
        defaultBtn.clicked.connect(self.defaultClicked)
        return defaultBtn

    def makeSetToNoneCheckbox(self):
        if (self.param.opts.get(
                ParamOpts.KW.C_NULLABLE_VALUE, False)):
            self.not_none_idx = self.slider.value()
            cb = QtWidgets.QCheckBox()
            cb.setChecked(True)

            self.layoutWidget.layout().insertWidget(0, cb)
            return cb
        else:
            return PseudoCheckBox()

    def makeSliderWidget(self):
        opts = self.param.opts

        opts.setdefault(
            ParamOpts.KW.LIMITS,
            [0, 0] if ParamOpts.KW.LIMITS not in opts
            else opts[ParamOpts.KW.LIMITS])

        slider = CustomSlider()

        orientation = opts.get('widget_orientation', 'Horizontal')

        slider.setOrientation(QtCore.Qt.Orientation[orientation])

        slider.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Maximum,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

        slider_value = self.spanToSliderValue(self.param.value())
        if ParamOpts.KW.SPAN in opts:
            len_span = len(opts[ParamOpts.KW.SPAN])
            if len_span != 100:
                slider.setMaximum(len_span - 1)
        else:
            slider.setMinimum(opts[ParamOpts.KW.LIMITS][0])
            slider.setMaximum(opts[ParamOpts.KW.LIMITS][-1])

        slider.setValue(slider_value)
        # slider.focus_in_parent = self

        slider.valueChanged.connect(self.setValueFromSlider)
        slider.sliderReleased.connect(self.onSliderRelease)
        slider.sliderPressed.connect(self.valueWidgetClicked)
        return slider

    def optsChanged(self, param, opts):
        super().optsChanged(param, opts)

        span = opts.get(ParamOpts.KW.SPAN, None)
        if span is None:
            step = opts.get(ParamOpts.KW.STEP, 1)
            start, stop = opts.get(ParamOpts.KW.LIMITS,
                                   param.opts[ParamOpts.KW.LIMITS])
            # Add a bit to 'stop' since python slicing excludes the last value
            span = np.arange(start, stop + step, step)
        defs = {ParamOpts.KW.STEP: span[1] - span[0],
                ParamOpts.KW.DECIMALS: 3,
                # 'min': span[0],
                # 'max': span[-1]
                }

        self.widget.setOpts(**defs)

        precision = opts.get('precision', 2)
        if precision is not None:
            span = span.round(precision)
        self.span = span
        self.charSpan = np.char.array(span)
        if hasattr(self, 'slider'):
            w = self.slider
            w.setMinimum(0)
            w.setMaximum(len(span) - 1)

    def onSliderRelease(self):
        if self._reset_span_condition():
            idx = self.slider.value()
            d = self._reset_slider_divider
            if ((idx < len(self.span) // d)
                    or (idx > (d - 1) * len(self.span) // d)):
                new_idx = self._reset_span(self.span[idx])
                # new_idx = self.spanToSliderValue(self.span[idx])
                self.setValueFromSpinBox(None, self.span[new_idx])

    def _reset_span(self, value):
        lims = self.param.opts[ParamOpts.KW.LIMITS]
        step = self.param.opts.get(ParamOpts.KW.STEP, 1)
        span = np.arange(
            max(lims[0], value - step * 500),
            min(lims[1], value + step * 500), step)
        self.span = span
        if hasattr(self, 'slider'):
            w = self.slider
            w.setMinimum(0)
            w.setMaximum(len(span) - 1)
        new_value = self.spanToSliderValue(value)
        return new_value

    def _reset_span_condition(self):
        lims = self.param.opts[ParamOpts.KW.LIMITS]
        has_inf = np.isinf(lims)
        return bool(np.any(has_inf))

    def displayNoneValue(self, value: bool, b_update_checkbox):
        if isinstance(value, int):
            value = bool(value)

        if b_update_checkbox:
            self.setNoneCheckbox.clicked.disconnect(self.checkBoxClicked)
            self.setNoneCheckbox.setChecked(not value)
            self.setNoneCheckbox.clicked.connect(self.checkBoxClicked)

        self.widget.setDisabled(value)
        self.slider.setDisabled(value)
        if value is True:
            if self.widget.isVisible():
                self.widget.setVisible(False)
            if not self.displayLabel.isVisible():
                self.displayLabel.setVisible(True)
        elif value is False:
            if not self.widget.isVisible():
                self.widget.setVisible(True)
            if self.displayLabel.isVisible():
                self.displayLabel.setVisible(False)

    def setValueFromSpinBox(self, box, value):
        self.slider.valueChanged.disconnect(self.setValueFromSlider)
        new_value = self.spanToSliderValue(value)
        if self._reset_span_condition():
            d = self._reset_slider_divider
            if ((value < self.span[len(self.span) // d])
                    or (value > self.span[(d - 1) * len(self.span) // d])):
                self._reset_span(value)
        self.slider.setValue(new_value)
        self.slider.valueChanged.connect(self.setValueFromSlider)

    def setValueFromSlider(self, idx):
        self.widget.sigValueChanging.disconnect(self.setValueFromSpinBox)
        self.widget.setValue(self.span[idx])
        self.widget.sigValueChanging.connect(self.setValueFromSpinBox)

    def showEditor(self):
        if self.setNoneCheckbox.isChecked():
            self.widget.show()
            self.displayLabel.hide()
        else:
            self.widget.hide()
            self.displayLabel.show()

        self.widget.setFocus(QtCore.Qt.FocusReason.OtherFocusReason)
        self.widget.selectNumber()
        # self.slider.setFocus(QtCore.Qt.FocusReason.OtherFocusReason)

    def spanToSliderValue(self, v):
        return int(np.argmin(np.abs(self.span - v)))

    def treeWidgetChanged(self):
        super().treeWidgetChanged()
        # tree = self.treeWidget()

        parent = self.parent()

        b_add_slider_to_column = True

        if isinstance(parent, EngineGroupParameterItem):
            b_add_slider_to_column = not parent.param.opts.get(
                ParamOpts.KW.C_NUMERIC_GROUP, False)
            # parent.add_engine_slider_parameter_widgets(self)
        # b_add_slider_to_column = False
        if b_add_slider_to_column is True:
            # col_count = tree.columnCount()
            # if col_count <= 2:
            #     header = tree.headerItem()
            #     labels = []
            #     for col in range(col_count):
            #         labels.append(header.text(col))
            #     tree.setColumnCount(col_count + 1)
            #     tree.setHeaderLabels(labels + ["Slider"])
            # noinspection PyTypeChecker
            width = self.widget.opts.get(ParamOpts.KW.DECIMALS, 3) * 20 + 15

            slider_idx = self.layoutWidget.layout().count() - 1
            if not isinstance(self.setNoneCheckbox, PseudoCheckBox):
                self.widget.setFixedWidth(width)
                self.displayLabel.setFixedWidth(width)
            else:
                self.widget.setMaximumWidth(width)
                self.displayLabel.setMaximumWidth(width)
            self.displayLabel.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Expanding,
            )
            self.widget.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Expanding,
            )
            self.layoutWidget.layout().insertWidget(
                slider_idx,
                self.slider_layout_widget)

    def updateCheckBoxUI(self, val):
        b_checked = self.setNoneCheckbox.isChecked()
        if b_none := (pd.isna(val) and b_checked):
            self.displayNoneValue(b_none, b_update_checkbox=True)
        elif b_not_none := (pd.notna(val) and (not b_checked)):
            self.displayNoneValue(not b_not_none, b_update_checkbox=True)

    def valueChanged(self, param, val, force=False):
        if self._nullable and self.setNoneCheckbox:
            self.updateCheckBoxUI(val=val)
        super().valueChanged(param, val, force)

    def valueWidgetClicked(self):
        tree: EngineParameterTree = self.treeWidget()
        self.setSelected(False)
        tree.setCurrentItem(self)


# noinspection PyPep8Naming
class SpinBoxSliderParameter(Parameter):

    itemClass = SpinBoxSliderParameterItem

    @classmethod
    def from_field(cls, field, **options):
        # if options[ParamOpts.KW.C_MODEL_FIELD_NAME] == 'distance':
        #     pass
        interval = extract_field_interval(field)
        multiple_of = get_field_multiple_of(field)

        if multiple_of is not None:
            step_size = multiple_of
        else:
            is_int = b_is_int_annotation(field.annotation, True)
            if is_int:
                step_size = options.get(ParamOpts.KW.STEP, 1)
            else:
                step_size = options.get(ParamOpts.KW.STEP, .01)
                options[ParamOpts.KW.DECIMALS] = 6

        options[ParamOpts.KW.STEP] = step_size

        return cls.from_interval(
                interval=interval, **options)

    @classmethod
    def from_interval(cls, interval: pd.Interval, **options):
        if (options[ParamOpts.KW.C_NULLABLE_VALUE] and
                options.get(ParamOpts.KW.DEFAULT) is None):
            options[ParamOpts.KW.DEFAULT] = np.nan

        limits = limits_from_interval(
            interval, step_size=options[ParamOpts.KW.STEP])
        options[ParamOpts.KW.LIMITS] = limits
        options[ParamOpts.KW.BOUNDS] = limits

        # if options[ParamOpts.KW.C_MODEL_FIELD_NAME] == 'width':
        #     pass

        options[ParamOpts.KW.C_VALUE_INTERVAL] = interval

        value = options[ParamOpts.KW.VALUE]
        step_size = options[ParamOpts.KW.STEP]
        span = options.get(ParamOpts.KW.SPAN, None)

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

        if span is None:
            if interval.length == np.inf:
                if step_size is None:
                    step_size = 1
                offset = 1000 * step_size

                if abs(value) * 9 < offset:
                    ref_value = 0
                else:
                    ref_value = value
                if interval.left == -np.inf:

                    if interval.right == np.inf:
                        interval = pd.Interval(ref_value - offset,
                                               ref_value + offset,
                                               closed='neither')
                    else:
                        if interval.closed in ['left', 'neither']:
                            closed: IntervalClosedType = 'left'
                        else:
                            closed = 'both'
                        interval = pd.Interval(ref_value - offset,
                                               interval.right,
                                               closed=closed)
                elif interval.right == np.inf:
                    if interval.closed in ['right', 'neither']:
                        closed: IntervalClosedType = 'right'
                    else:
                        closed = 'both'
                    interval = pd.Interval(interval.left, ref_value + offset,
                                           closed=closed)
            if step_size is None:
                n_steps_if_closed = 2001
            else:
                # noinspection PyTypeChecker
                n_steps_if_closed = int(interval.length / step_size) + 1

            span = linspace_from_interval(interval=interval,
                                          n_steps_if_closed=n_steps_if_closed,
                                          b_change_n_steps_if_open=True)
        return cls(span=span, **options)

    def makeTreeItem(self, depth) -> SpinBoxSliderParameterItem:
        return super().makeTreeItem(depth=depth)
    
    def hasDefault(self):
        if self.opts.get(ParamOpts.KW.C_NULLABLE_VALUE, False):
            s = super().hasDefault()
            return True
        return super().hasDefault()

    def _interpretValue(self, v):
        # if self.name() == 'width':
        #     pass
        if v is None:
            v = np.nan
        elif pd.notna(v) and self.opts.get(
                ParamOpts.KW.C_COERCE_TO_LIMITS, False):
            intv = self.opts[ParamOpts.KW.C_VALUE_INTERVAL]
            if v not in intv:
                s = self.opts[ParamOpts.KW.STEP]
                init_v = v
                v = coerce_value_into_interval(v, intv=intv, step_size=s)
                print(f"coerced {init_v} into {intv} -> {v}")
        return v

    def setValue(self, value, blockSignal=None):
        return super().setValue(value, blockSignal)
