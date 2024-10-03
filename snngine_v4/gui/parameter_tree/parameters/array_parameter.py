from pyqtgraph import functions
from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import WidgetParameterItem
from qtpy import QtCore, QtWidgets

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

        self.addRowWidget = QtWidgets.QPushButton('Add Row')
        self.addRowWidget.clicked.connect(self.addRowClicked)
        self.layoutWidget.layout().insertWidget(
            self.layoutWidget.layout().count() - 2, self.addRowWidget)
        self.addRowWidget.setEnabled(False)

        self.addColWidget = QtWidgets.QPushButton('Add Col')
        self.addColWidget.clicked.connect(self.addColClicked)
        self.layoutWidget.layout().insertWidget(
            self.layoutWidget.layout().count() - 2, self.addColWidget)
        self.param.sigValueChanged.connect(self.updateTableWidgets)
        if self.param.qdf.df is not None:
            self.updateTableWidgets()

    def addColClicked(self,):

        self.param.qdf.addColumn()
        self.updateTableWidgets()

    def addRowClicked(self,):
        self.param.qdf.addRow()
        self.updateTableWidgets()

    def makeWidget(self):
        self.asSubItem = True
        self.hideWidget = False

        table = QDataFrameTableWidget(data=self.param.qdf)
        table.setMaximumHeight(200)
        table.editable = not self.param.opts[ParamOpts.KW.READONLY]
        return table

    def valueChanged(self, param, val, force=False):
        super().valueChanged(param, val, force)

    def widgetValueChanged(self, ):
        super().widgetValueChanged()

    def updateTableWidgets(self):
        shape = self.param.qdf.as_array().shape

        add_row_enabled = (
            (len(self.param.qdf.df.columns) > 0)
            and (len(shape) > 1)
            and self.param.validator.validate_shape((shape[0]+1, shape[1]))
        )
        self.addRowWidget.setEnabled(add_row_enabled)

        add_col_enabled = (len(self.param.qdf.df.columns) > 0)
        if len(shape) == 1:
            next_shape = shape[0] + 1,
        else:
            next_shape = shape[0], shape[1] + 1
        add_col_enabled &= self.param.validator.validate_shape(next_shape)

        self.addColWidget.setEnabled(add_col_enabled)


# noinspection PyPep8Naming
class ArrayParameter(Parameter):

    itemClass = ArrayParameterItem

    sigDataChanged = QtCore.Signal(object)

    def __init__(self, **opts):
        array_type = opts[ParamOpts.KW.C_DATA_TYPES]
        interface = ArrayInterfaces()[array_type]
        self.qdf = QDataFrame(validator=interface,
                              value=opts[ParamOpts.KW.VALUE])
        opts[ParamOpts.KW.VALUE] = self.qdf.value()
        opts[ParamOpts.KW.EXPANDED] = False
        super().__init__(**opts)
        self.qdf.sigChanged.connect(self.onDataChanged)

    def onDataChanged(self):
        data = self.qdf.value()
        if functions.eq(self.opts.get(ParamOpts.KW.VALUE, None), data):
            self.sigValueChanged.emit(self, data)
        else:
            super().setValue(value=data)

    def setValue(self, value, blockSignal=None):
        value = self.qdf.setValue(value, b_block_signal=True)
        return super().setValue(value=value, blockSignal=blockSignal)

    @property
    def validator(self):
        return self.qdf.validator

    def value(self):
        return self.opts[ParamOpts.KW.VALUE]
