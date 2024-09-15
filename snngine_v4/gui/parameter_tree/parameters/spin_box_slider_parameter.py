import numpy as np
from pyqtgraph import SpinBox
from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import (
    NumericParameterItem,
)
from qtpy import QtCore, QtWidgets

from snngine_v4.gui.icons import getEngineGraphIcon
from snngine_v4.gui.parameter_tree.parameters.engine_group_parameter import \
    EngineGroupParameterItem
from snngine_v4.utils.settings.settings_keywords import (
    PGParOption,
)


class ClickableLabel(QtWidgets.QLabel):
    sigClicked = QtCore.Signal()

    def mousePressEvent(self, e):
        self.sigClicked.emit()


class CustomSlider(QtWidgets.QSlider):

    def wheelEvent(self, e) -> None:
        if self.hasFocus():
            super().wheelEvent(e)


# noinspection PyPep8Naming
class SpinBoxSliderParameterItem(NumericParameterItem):

    def __init__(self, param, depth):

        self.widget: SpinBox
        self.span = None
        self.charSpan = None

        super().__init__(param, depth)

        self._reset_slider_divider = 20
        self.slider = self.make_slider_widget()
        self.widget.sigValueChanging.connect(self.setValueFromSpinBox)

        self.slider_layout_widget = QtWidgets.QWidget()
        self.slider_layout_widget.setLayout(QtWidgets.QHBoxLayout())
        self.slider_layout_widget.layout().addWidget(self.slider)
        self.slider_layout_widget.layout().setContentsMargins(13, 0, 13, 0)

        w = self.layoutWidget.layout().takeAt(2)
        if not isinstance(w, QtWidgets.QSpacerItem):
            raise ValueError(f"{w}")
        self.layoutWidget.layout().removeItem(w)

        display_label_item = self.layoutWidget.layout().takeAt(1)
        if display_label_item.wid != self.displayLabel:
            raise ValueError(f"{display_label_item.wid}")
        del self.displayLabel
        self.layoutWidget.layout().removeItem(display_label_item)
        self.displayLabel = ClickableLabel()
        self.displayLabel.sigClicked.connect(self.subWidgetClicked)

        # self.displayLabel = QtWidgets.QPushButton()
        # self.displayLabel.setFlat(True)
        self.layoutWidget.layout().insertWidget(0, self.displayLabel)

        self.slider.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.widget.setOpts(compactHeight=True)
        self.optsChanged(self.param, {PGParOption.SPAN: self.span})

        self.param._modifiedSinceReset = False
        self.updateDefaultBtn()

    def subWidgetClicked(self):
        self.treeWidget().setCurrentItem(self)

    def hideEditor(self):
        super().hideEditor()
        self.slider.clearFocus()

    def makeDefaultButton(self):
        defaultBtn = QtWidgets.QPushButton()
        defaultBtn.setAutoDefault(False)
        defaultBtn.setFixedWidth(20)
        defaultBtn.setFixedHeight(20)
        defaultBtn.setIcon(getEngineGraphIcon('kamiyamane/default'))
        defaultBtn.clicked.connect(self.defaultClicked)
        return defaultBtn

    def make_slider_widget(self):
        param = self.param
        opts = param.opts

        opts.setdefault(
            PGParOption.LIMITS,
            [0, 0] if PGParOption.LIMITS not in opts
            else opts[PGParOption.LIMITS])

        slider = CustomSlider()

        orientation = opts.get('widget_orientation', 'Horizontal')

        slider.setOrientation(QtCore.Qt.Orientation[orientation])

        slider.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Maximum,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

        slider_value = self.spanToSliderValue(param.value())
        if PGParOption.SPAN in param.opts:
            len_span = len(param.opts[PGParOption.SPAN])
            if len_span != 100:
                slider.setMaximum(len_span - 1)
        else:
            slider.setMinimum(param.opts[PGParOption.LIMITS][0])
            slider.setMaximum(param.opts[PGParOption.LIMITS][-1])

        slider.setValue(slider_value)
        # slider.focus_in_parent = self

        slider.valueChanged.connect(self.setValueFromSlider)
        slider.sliderReleased.connect(self.onSliderRelease)
        slider.sliderPressed.connect(self.subWidgetClicked)
        return slider

    def optsChanged(self, param, opts):
        super().optsChanged(param, opts)

        span = opts.get(PGParOption.SPAN, None)
        if span is None:
            step = opts.get(PGParOption.STEP, 1)
            start, stop = opts.get(PGParOption.LIMITS,
                                   param.opts[PGParOption.LIMITS])
            # Add a bit to 'stop' since python slicing excludes the last value
            span = np.arange(start, stop + step, step)
        defs = {PGParOption.STEP: span[1] - span[0],
                PGParOption.DECIMALS: 3,
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
        lims = self.param.opts[PGParOption.LIMITS]
        step = self.param.opts.get(PGParOption.STEP, 1)
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
        lims = self.param.opts[PGParOption.LIMITS]
        has_inf = np.isinf(lims)
        return bool(np.any(has_inf))

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

    def spanToSliderValue(self, v):
        return int(np.argmin(np.abs(self.span - v)))

    def showEditor(self):
        super().showEditor()
        self.slider.setFocus(QtCore.Qt.FocusReason.OtherFocusReason)

    def treeWidgetChanged(self):
        super().treeWidgetChanged()
        tree = self.treeWidget()

        parent = self.parent()

        b_add_slider_to_column = True

        if isinstance(parent, EngineGroupParameterItem):
            b_add_slider_to_column = not parent.param.opts.get(
                PGParOption.CUSTOM_NUMERIC_GROUP, False)
            # parent.add_engine_slider_parameter_widgets(self)
        b_add_slider_to_column = False
        if b_add_slider_to_column is True:
            col_count = tree.columnCount()
            if col_count <= 2:
                header = tree.headerItem()
                labels = []
                for col in range(col_count):
                    labels.append(header.text(col))
                tree.setColumnCount(col_count + 1)
                tree.setHeaderLabels(labels + ["Slider"])
            # noinspection PyTypeChecker

            tree.setItemWidget(self, 2, self.slider_layout_widget)


class SpinBoxSliderParameter(Parameter):
    itemClass = SpinBoxSliderParameterItem

    def makeTreeItem(self, depth) -> SpinBoxSliderParameterItem:
        return super().makeTreeItem(depth=depth)
