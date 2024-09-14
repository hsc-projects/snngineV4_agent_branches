import numpy as np
from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import (
    NumericParameterItem,
)
from qtpy import QtCore, QtWidgets

from snngine_v4.gui.icons import getEngineGraphIcon
from snngine_v4.gui.parameter_tree.parameters.engine_group_parameter import \
    EngineGroupParameterItem
from snngine_v4.utils.settings.settings_keywords import PGParOption


class CustomSlider(QtWidgets.QSlider):

    def wheelEvent(self, e) -> None:
        if self.hasFocus():
            super().wheelEvent(e)


class SpinBoxSliderParameterItem(NumericParameterItem):

    def __init__(self, param, depth):
        super().__init__(param, depth)

        # self.slider_layout = QtWidgets.QHBoxLayout()
        # self.slider_layout.setContentsMargins(0, 0, 0, 0)
        # self.slider_layout.setSpacing(2)
        #
        self.slider = self.make_slider_widget()
        # self.slider_layout.addStretch(0)
        # self.slider_layout.addWidget(self.slider)

        w = self.layoutWidget.layout().takeAt(2)
        self.layoutWidget.layout().removeItem(w)
        # self.layoutWidget.layout().insertWidget(2, self.slider)
        #
        # width = param.opts.get('precision', 2) * 20 + 15
        # min_wdg_width = min(width, 100)
        # self.widget.setMaximumWidth(width)
        # self.widget.setMinimumWidth(min_wdg_width)
        # self.displayLabel.setMinimumWidth(min_wdg_width)
        # self.layoutWidget.setMinimumWidth(200)
        # self.displayLabel.setMaximumWidth(width)
        self.slider.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        # self.widget.setOpts(compactHeight=False)
        # self.optsChanged(self.param, {'span': self.span})
        self.param._modifiedSinceReset = False
        self.updateDefaultBtn()

    def optsChanged(self, param, opts):
        super().optsChanged(param, opts)

        span = opts.get('span', None)
        if span is None:
            step = opts.get('step', 1)
            start, stop = opts.get('limits', param.opts['limits'])
            # Add a bit to 'stop' since python slicing excludes the last value
            span = np.arange(start, stop + step, step)
        defs = {'step': span[1] - span[0], 'decimals': 3,
                'min': span[0],
                'max': span[-1]}
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

    # noinspection PyPep8Naming
    def spanToSliderValue(self, v):
        return int(np.argmin(np.abs(self.span - v)))

    # noinspection PyPep8Naming
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

        # noinspection PyPep8Naming
        def setValueFromSpinBox(box, value):
            slider.valueChanged.disconnect(setValueFromSlider)
            slider.setValue(self.spanToSliderValue(value))
            slider.valueChanged.connect(setValueFromSlider)

        # noinspection PyPep8Naming
        def setValueFromSlider(value):
            self.widget.sigValueChanging.disconnect(setValueFromSpinBox)
            self.widget.setValue(self.span[value])
            self.widget.sigValueChanging.connect(setValueFromSpinBox)

        self.widget.sigValueChanging.connect(setValueFromSpinBox)
        slider.valueChanged.connect(setValueFromSlider)
        slider_value = self.spanToSliderValue(param.value())
        if 'span' in param.opts:
            len_span = len(param.opts['span'])
            if len_span != 100:
                slider.setMaximum(len_span - 1)
        else:
            slider.setMinimum(param.opts[PGParOption.LIMITS][0])
            slider.setMaximum(param.opts[PGParOption.LIMITS][-1])

        slider.setValue(slider_value)
        # slider.focus_in_parent = self
        return slider

    def hideEditor(self):
        super().hideEditor()
        self.slider.clearFocus()

    def showEditor(self):
        super().showEditor()
        self.slider.setFocus(QtCore.Qt.FocusReason.OtherFocusReason)

    def treeWidgetChanged(self):
        super().treeWidgetChanged()
        tree = self.treeWidget()

        parent = self.parent()

        if isinstance(parent, EngineGroupParameterItem):
            pass
            # parent.add_engine_slider_parameter_widgets(self)
        else:
            col_count = tree.columnCount()
            if col_count <= 2:
                header = tree.headerItem()
                labels = []
                for col in range(col_count):
                    labels.append(header.text(col))
                tree.setColumnCount(col_count + 1)
                tree.setHeaderLabels(labels + ["Slider"])
            # noinspection PyTypeChecker
            tree.setItemWidget(self, 2, self.slider)


class SpinBoxSliderParameter(Parameter):
    itemClass = SpinBoxSliderParameterItem

    def makeTreeItem(self, depth) -> SpinBoxSliderParameterItem:
        return super().makeTreeItem(depth=depth)
