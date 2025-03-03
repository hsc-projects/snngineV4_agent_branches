from typing import Type

import numpy as np
from pyqtgraph.parametertree import ParameterItem
from pyqtgraph.parametertree.parameterTypes import (
    ActionParameter
)
from pyqtgraph.parametertree.parameterTypes.action import \
    ParameterControlledButton
from qtpy import QtWidgets

from snngine_v4.gui.parameter_tree.parameter_builder.options_builder import \
    OptionsBuilder
from snngine_v4.gui.parameter_tree.parameters.engine_group_parameter import \
    EngineGroupParameter
from snngine_v4.gui.parameter_tree.parameters.widgets.table \
    .array_editor import ArrayEditorArea
from snngine_v4.gui.windows.main_window_base import MainEngineWindowBase
from snngine_v4.utils.data_utils.dataframe_config import (
    DataFrameIndex,
    TypedDataFrameBase, TypedDataFrameBase3D,
)
# from qtpy import QtCore

from snngine_v4.utils.data_utils.validation.array_annotation \
    import ArrayInterfaces


from snngine_v4.gui.parameter_tree.parameters.widgets.table \
    .q_dataframe import (
        DataChangeType, QDataFrame,
    )
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


class ActionWidgetParameterItem(ParameterItem):
    """ParameterItem displaying a clickable button."""
    def __init__(self, param, depth):
        self.param = param
        super().__init__(param, depth)
        self.layoutWidget = QtWidgets.QWidget()
        self.layout = QtWidgets.QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layoutWidget.setLayout(self.layout)
        self.button: QtWidgets.QPushButton | ParameterControlledButton = (
            ParameterControlledButton(param, self.layoutWidget))
        param.sigNameChanged.disconnect(self.button.onNameChange)
        param.sigOptionsChanged.disconnect(self.button.updateOpts)
        self.button.updateOpts(None, dict(title='show'))
        # self.layout.addSpacing(100)
        self.layout.addWidget(self.button)
        self.layout.addStretch()
        self.titleChanged()

        self.button.clicked.connect(self.activate)

    def activate(self):
        w = self.button.window()
        if isinstance(w, MainEngineWindowBase):
            editor = w.arrayEditorDockWidget
            dock_area: ArrayEditorArea = editor.widget()
            if self.param.qdf not in dock_area.qdf_map:
                dock_area.addDock(self.param.qdf)
                if not editor.isVisible():
                    editor.show()
            else:
                wdg, dock = dock_area[self.param.qdf]
                if dock.parent() is None:
                    dock.label.show()
                    dock_area.addDock(dock)
                    if not editor.isVisible():
                        editor.show()
                else:
                    dock.close()
            if dock_area.count() == 0:
                editor.close()

    def treeWidgetChanged(self):
        super().treeWidgetChanged()
        tree = self.treeWidget()
        if tree is None:
            return
        tree.setItemWidget(self, 1, self.layoutWidget)

    def titleChanged(self):
        self.setSizeHint(1, self.button.sizeHint())


# noinspection PyPep8Naming
# class ArrayParameter(Parameter):
class ArrayParameter(ActionParameter):

    itemClass = ActionWidgetParameterItem

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
