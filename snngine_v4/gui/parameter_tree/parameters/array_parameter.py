from typing import Type

import numpy as np
from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import WidgetParameterItem

from snngine_v4.gui.parameter_tree.parameter_builder.options_builder import \
    OptionsBuilder
from snngine_v4.gui.parameter_tree.parameters.engine_group_parameter import \
    EngineGroupParameter
from snngine_v4.utils.data_utils.dataframe_config import (
    DataFrameIndex,
    TypedDataFrameBase, TypedDataFrameBase3D,
)
# from qtpy import QtCore

from snngine_v4.utils.data_utils.validation.array_annotation \
    import ArrayInterfaces

from snngine_v4.gui.parameter_tree.parameters.widgets.table.df_table_widget \
    import QDataFrameTableWidget
from snngine_v4.gui.parameter_tree.parameters.widgets.table \
    .q_dataframe import (
        DataChangeType, QDataFrame,
    )
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
        val = self.widget.value()
        if val is None:
            return
        raise RuntimeError


# noinspection PyPep8Naming
class ArrayParameter(Parameter):

    itemClass = ArrayParameterItem

    # sigDataChanged = QtCore.Signal(object)

    def __init__(self, model: TypedDataFrameBase | None = None, **opts):

        if ((model is not None)
                and isinstance(model, TypedDataFrameBase)):
            c_data_types = OptionsBuilder.get_parameter_type(model, 'data')
            fi = model.model_fields['data']
            name = opts[ParamOpts.KW.NAME]
            opts = OptionsBuilder.from_field(
                fi=fi, c_data_types=c_data_types,
                c_model_field_name=name,
                value=model.data, **opts)
            column_names = opts.get(ParamOpts.KW.C_COLUMN_NAME_S, None)
            if opts[ParamOpts.KW.NAME] != name:
                raise AssertionError
            if column_names is not None:
                raise AssertionError
            column_names = model.columns
            if isinstance(column_names, DataFrameIndex):
                column_names = column_names.to_list()
            index_names = model.index
            if isinstance(index_names, DataFrameIndex):
                index_names = index_names.to_list()
            opts[ParamOpts.KW.C_INDEX_NAME_S] = index_names
            opts[ParamOpts.KW.C_COLUMN_NAME_S] = column_names

        array_type = opts[ParamOpts.KW.C_DATA_TYPES]
        self.qdf = QDataFrame(
            name=opts[ParamOpts.KW.NAME],
            validator=ArrayInterfaces()[array_type],
            column_names=opts.get(ParamOpts.KW.C_COLUMN_NAME_S, None),
            index_names=opts.get(ParamOpts.KW.C_INDEX_NAME_S, None),
            value=opts[ParamOpts.KW.VALUE],
            readonly=opts.get(ParamOpts.KW.READONLY, False)
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

    def onDataChanged(self, qdf, change_type: DataChangeType, changes):
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


class ArrayDictParameter(EngineGroupParameter):

    PARAMETER_CLASS: Type[ArrayParameter] = ArrayParameter

    def __init__(self, value: TypedDataFrameBase3D | None = None,
                 model: TypedDataFrameBase3D | None = None,
                 signal_register=None, **opts):

        opts.setdefault('name', 'arrays')

        if model is not None:
            if value is not None:
                raise RuntimeError
            value = model

        super().__init__(**opts)
        self.init_build = None
        if value is not None:
            self.init_build = self.build(value, signal_register)

    def build(self, value, signal_register, **opts):

        res = {}

        if isinstance(value, TypedDataFrameBase):
            model = value
            column_names = opts.get(ParamOpts.KW.C_COLUMN_NAME_S, None)
            if column_names is not None:
                raise AssertionError
            column_names = model.columns
            if isinstance(column_names, DataFrameIndex):
                column_names = column_names.to_list()
            opts[ParamOpts.KW.C_COLUMN_NAME_S] = column_names
            if isinstance(model, TypedDataFrameBase3D):
                dt = model.item_validation_interface()
                # opts[ParamOpts.KW.C_INDEX_NAME_S] = column_names
                items = list(model.items())
                for k, v in items:
                    opts_ = OptionsBuilder.from_annotation(
                        ann=dt, name=k, value=v, **opts)
                    if opts_[ParamOpts.KW.NAME] != k:
                        raise AssertionError
                    p = self.PARAMETER_CLASS(
                        signal_register=signal_register, **opts_)
                    self.addChild(p)
                    p.sigValueChanged.connect(self.valueChanged)
                    res[k] = p
            elif isinstance(value, TypedDataFrameBase):
                c_data_types = OptionsBuilder.get_parameter_type(
                    model, 'data')
                index_names = model.index
                if isinstance(index_names, DataFrameIndex):
                    index_names = index_names.to_list()
                opts[ParamOpts.KW.C_INDEX_NAME_S] = index_names

                name = TypedDataFrameBase.Slots.DATA
                opts_ = OptionsBuilder.from_annotation(
                    ann=c_data_types, name=name,
                    value=value.data, **opts)
                if opts_[ParamOpts.KW.NAME] != name:
                    raise AssertionError
                p = self.PARAMETER_CLASS(
                    signal_register=signal_register, **opts_)
                self.addChild(p)
                p.sigValueChanged.connect(self.valueChanged)
                res[name] = p
        else:
            raise NotImplementedError
