import numpy as np
from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import WidgetParameterItem
from qtpy import QtCore

from snngine_v4.data.validation.array_annotation import ArrayInterfaces

from snngine_v4.gui.parameter_tree.parameters.widgets \
    .dataframe_table_widget import QDataFrameTableWidget
from snngine_v4.gui.parameter_tree.parameters.widgets.q_dataframe import \
    QDataFrame
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


# noinspection PyPep8Naming
class ArrayParameterItem(WidgetParameterItem):

    def __init__(self, param, depth):

        self.param: ArrayParameter | None = None
        self.widget: QDataFrameTableWidget | None = None

        super().__init__(param, depth)

        self.ui_widgets = self.widget.make_ui_widgets()
        idx = self.layoutWidget.layout().count() - 2
        self.layoutWidget.layout().insertWidget(
            idx, self.ui_widgets.widget())

    def makeWidget(self):
        self.asSubItem = True
        self.hideWidget = False

        table = QDataFrameTableWidget(qdf=self.param.qdf)
        # table.setMaximumHeight(200)
        return table

    def valueChanged(self, param, val, force=False):
        # super().valueChanged(param, val, force)
        self.widget.onDataChange()
        self.updateDefaultBtn()

    def widgetValueChanged(self, ):
        raise RuntimeError


# noinspection PyPep8Naming
class ArrayParameter(Parameter):

    itemClass = ArrayParameterItem

    sigDataChanged = QtCore.Signal(object)

    def __init__(self, **opts):
        array_type = opts[ParamOpts.KW.C_DATA_TYPES]
        self.qdf = QDataFrame(
            name=opts[ParamOpts.KW.NAME],
            validator=ArrayInterfaces()[array_type],
            column_names=opts[ParamOpts.KW.C_COLUMN_NAME_S],
            value=opts[ParamOpts.KW.VALUE],
            readonly=opts[ParamOpts.KW.READONLY]
        )
        opts[ParamOpts.KW.VALUE] = self.qdf.value()
        opts[ParamOpts.KW.EXPANDED] = False
        super().__init__(**opts)
        self.qdf.sigChanged.connect(self.onDataChanged)

    def compare_value(self):
        v_par = self.opts[ParamOpts.KW.VALUE]
        v_qdf = self.qdf.value()
        try:
            b_arr = v_par == v_qdf
            return bool(np.all(b_arr))
        except ValueError as error:
            for i, s in enumerate(v_par.shape):
                if v_qdf.shape[i] != s:
                    return False
            raise error

    def onDataChanged(self):
        data = self.qdf.value()
        if self.compare_value():
            self.sigValueChanged.emit(self, data)
        else:
            super().setValue(value=data)

    def setValue(self, value, blockSignal=None):
        value = self.qdf.setValue(value, b_block_signal=True)
        return super().setValue(value=value, blockSignal=blockSignal)

    def value(self):
        if self.compare_value() is False:
            raise RuntimeError
        return self.opts[ParamOpts.KW.VALUE]
