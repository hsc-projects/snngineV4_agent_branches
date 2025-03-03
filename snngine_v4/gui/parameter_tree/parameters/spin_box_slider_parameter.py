from dataclasses import dataclass

import numpy as np
import pandas as pd
from pyqtgraph import SpinBox
from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import (
    NumericParameterItem,
)
from qtpy import QtCore, QtWidgets

from snngine_v4.gui.icons import getEngineGraphIcon
from snngine_v4.gui.parameter_tree.parameters.widgets.custom_spin_box import \
    CustomSpinBox
from snngine_v4.gui.parameter_tree.parameters.widgets.spin_box_slider import (
    CustomSlider, SpinBoxSlider,
)

from snngine_v4.gui.parameter_tree.parameters.parameter_item_mixin import (
    WidgetParameterItemMixin
)

from snngine_v4.utils.data_utils.interval_utils import (
    coerce_value_into_interval,
)
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


# noinspection PyPep8Naming
class SpinBoxSliderParameterItem(NumericParameterItem,
                                 WidgetParameterItemMixin):

    def __init__(self, param, depth):

        self.widget: SpinBox | QtWidgets.QWidget | None = None

        self.setNoneCheckbox = None
        self._nullable = param.opts.get(ParamOpts.KW.C_NULLABLE_VALUE, True)

        param.opts.setdefault(ParamOpts.KW.DELAY, .1)

        # if param.opts[ParamOpts.KW.C_MODEL_FIELD_NAME] == 'width':
        #     pass

        super().__init__(param, depth)

        self.slider = SpinBoxSlider(spinbox=self.widget, **self.param.opts)
        self.slider_layout_widget = self.slider.layout_widget()
        self.slider.sliderPressed.connect(self.valueWidgetClicked)

        self._remove_spacer_item(idx=2)
        self._replace_display_label()
        self._set_size_policies()

        self.widget.setOpts(compactHeight=False)
        # self.optsChanged(self.param, {ParamOpts.KW.SPAN: self.span})
        self.optsChanged(self.param, self.param.opts)

        self.param._modifiedSinceReset = False
        # self.updateDefaultBtn()

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
            self.param.setValue(self.slider.span[not_none_value])

        self.displayNoneValue(b_set_to_none, b_update_checkbox=False)
        self.valueWidgetClicked()

    def hideEditor(self):
        if self.setNoneCheckbox.isChecked():
            self.widget.hide()
            self.displayLabel.show()
        else:
            self.widget.hide()
            self.displayLabel.show()
        self.slider.clearFocus()

    def makeWidget(self):
        w = CustomSpinBox.from_opts(**self.param.opts)
        w.sigChanged = w.sigValueChanged
        w.sigChanging = w.sigValueChanging
        return w

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

    def optsChanged(self, param, opts):
        super().optsChanged(param, opts)

        if hasattr(self, 'slider') and (ParamOpts.KW.SPAN in opts):
            self.slider.set_span(opts[ParamOpts.KW.SPAN])

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

    def showEditor(self):
        if self.setNoneCheckbox.isChecked():
            self.widget.show()
            self.displayLabel.hide()
        else:
            self.widget.hide()
            self.displayLabel.show()

        self.widget.setFocus(QtCore.Qt.FocusReason.OtherFocusReason)
        self.widget.selectNumber()

    def treeWidgetChanged(self):
        super().treeWidgetChanged()
        self._set_sizes()
        if self.is_from_numeric_group() is False:
            lay_wdg = self.layoutWidget
            slider_idx = lay_wdg.layout().count() - 1
            lay_wdg.layout().insertWidget(slider_idx,
                                          self.slider_layout_widget)
            lay_wdg.setMinimumWidth(
                lay_wdg.minimumWidth()
                + self.slider_layout_widget.minimumWidth())

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


# noinspection PyPep8Naming
class SpinBoxSliderParameter(Parameter):

    itemClass = SpinBoxSliderParameterItem

    def __init__(self, **options):

        if options.get(ParamOpts.KW.SPAN, None) is None:

            if options[ParamOpts.KW.C_VALUE_INTERVAL] is None:
                pass

            span = CustomSlider.make_span(
                interval=options[ParamOpts.KW.C_VALUE_INTERVAL],
                value=options[ParamOpts.KW.VALUE],
                step_size=options[ParamOpts.KW.STEP]
            )
            options[ParamOpts.KW.SPAN] = span
        
        super().__init__(**options)

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

    def makeTreeItem(self, depth) -> SpinBoxSliderParameterItem:
        return super().makeTreeItem(depth=depth)

    def setValue(self, value, blockSignal=None):
        return super().setValue(value, blockSignal)


@dataclass
class PseudoCheckBox:

    checked: bool = True

    def isChecked(self):
        return self.checked
