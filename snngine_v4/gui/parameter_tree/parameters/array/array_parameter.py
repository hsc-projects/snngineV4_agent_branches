from typing import Any, Type

import numpy as np
from pydantic_core import PydanticUndefined


from pyqtgraph.parametertree import ParameterItem
from pyqtgraph.parametertree.parameterTypes import (
    ActionParameter,
)
from pyqtgraph.parametertree.parameterTypes.action import \
    ParameterControlledButton
from qtpy import QtWidgets

from snngine_v4.gui.parameter_tree.parameter_builder.options_builder import \
    OptionsBuilder
from snngine_v4.gui.parameter_tree.parameters.common.action_mixins import \
    (
    ActionItemMixin, ActionParameterMixin,
)
from snngine_v4.gui.parameter_tree.parameters.common \
    .engine_group_parameter import EngineGroupParameter
from snngine_v4.gui.parameter_tree.parameters.widgets.table \
    .array_editor import ArrayEditorArea
from snngine_v4.gui.parameter_tree.parameters.widgets.table \
    .df_table_widget import QDataFrameTableWidget
from snngine_v4.gui.parameter_tree.parameters.widgets.table \
    .df_table_widget_dock import (
        TableDock
    )
from snngine_v4.gui.windows.main_window_base import MainEngineWindowBase
from snngine_v4.utils.core_utils import type_assertion
from snngine_v4.utils.data_utils.dataframe_config import (
    SeriesModel,
    TypedDataFrameModel,
    TypedDataFrameBase3D,
)
from snngine_v4.utils.data_utils.index_config import IndexConfig
from snngine_v4.utils.data_utils.validation.array_annotation \
    import ArrayInterfaces


from snngine_v4.gui.parameter_tree.parameters.widgets.table \
    .q_dataframe import (
        DataChangeType, QDataFrame,
    )
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


class ArrayParameterItem(ParameterItem, ActionItemMixin):
    """ParameterItem displaying a clickable button."""
    def __init__(self, param, depth):
        self.param: ArrayParameter = param
        self.model: SeriesModel = param.opts.get(ParamOpts.KW.MODEL, None)
        # self.parent_model: SeriesBase = param.opts.get(
        #     ParamOpts.KW.PARENT_MODEL, None)

        super().__init__(param, depth)
        self.layoutWidget = QtWidgets.QWidget()
        self.layout = QtWidgets.QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layoutWidget.setLayout(self.layout)

        self.add_actions()

        self.layout.addStretch()
        self.titleChanged()

    def titleChanged(self):
        self.setSizeHint(
            1, self.widget_dict['show_array'].sizeHint())

    def treeWidgetChanged(self):
        super().treeWidgetChanged()
        tree = self.treeWidget()
        if tree is None:
            return
        tree.setItemWidget(self, 1, self.layoutWidget)

    def valueChanged(self, param, val, force=False):
        # print(id(self))
        if ((self.param.table_dock is not None)
                and (self.param.table_dock.parent() is not None)):
            if self.param.table_dock.isVisible():
                self.param.widget.onDataChange()
            # self.updateDefaultBtn()


class ArrayParameter(ActionParameter, ActionParameterMixin):

    itemClass = ArrayParameterItem

    def __init__(self, **opts):

        self.model: SeriesModel | TypedDataFrameModel | None = (
            opts.get(ParamOpts.KW.MODEL, None))
        # signal_register = opts.get(ParamOpts.KW.SIGNAL_REGISTER, None)

        if self.model is not None:
            type_assertion(self.model, SeriesModel)
            signal_register = opts[ParamOpts.KW.SIGNAL_REGISTER]
            c_data_types = OptionsBuilder.get_parameter_type(
                self.model, SeriesModel.Slots.DATA)
            fi = self.model.model_fields[SeriesModel.Slots.DATA]
            name = opts[ParamOpts.KW.NAME]
            opts = OptionsBuilder.from_field(
                fi=fi, c_data_types=c_data_types,
                c_model_field_name=name,
                value=self.model.data, **opts)

            if opts[ParamOpts.KW.NAME] != name:
                raise AssertionError

            opts = self.make_idx_opts(self.model, opts)
            opts = self.make_col_opts(self.model, opts)

        array_type = opts[ParamOpts.KW.C_DATA_TYPES]
        self.qdf = QDataFrame(
            name=opts[ParamOpts.KW.NAME],
            validator=ArrayInterfaces()[array_type],
            column_names=opts.get(ParamOpts.KW.C_COLUMN_NAME_S, None),
            index_names=opts.get(ParamOpts.KW.C_INDEX_NAME_S, None),
            value=opts[ParamOpts.KW.VALUE],
            readonly=opts.get(ParamOpts.KW.READONLY, False)
        )

        default = opts.get(ParamOpts.KW.DEFAULT, None)
        if ((default is not None)
                and (default is PydanticUndefined)):
            pass
        opts[ParamOpts.KW.DEFAULT] = self.qdf.value()
        opts[ParamOpts.KW.VALUE] = None
        opts[ParamOpts.KW.EXPANDED] = False

        super().__init__(**opts)
        self.table_dock: TableDock | None = None
        self.widget: QDataFrameTableWidget | None = None

        self._modifiedSinceReset = False

        self.qdf.sigChanged.connect(self.onDataChanged)

        self.add_action(
            name='show_array', title='  show  ',
            func=self.show_array_editor)

        if isinstance(self.model, TypedDataFrameModel):
            self.add_action(
                name='edit_index', title='  edit index  ',
                func=self.show_index_editor)

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

    @staticmethod
    def make_idx_opts(model, opts) -> dict:

        index_names = model.index
        if isinstance(index_names, IndexConfig):
            index_names = index_names.to_list()
        opts[ParamOpts.KW.C_INDEX_NAME_S] = index_names
        return opts

    @staticmethod
    def make_col_opts(model, opts) -> dict:
        column_names = opts.get(ParamOpts.KW.C_COLUMN_NAME_S, None)
        if column_names is not None:
            raise AssertionError
        if isinstance(model, TypedDataFrameModel):
            column_names = model.columns
            if isinstance(column_names, IndexConfig):
                column_names = column_names.to_list()
        opts[ParamOpts.KW.C_COLUMN_NAME_S] = column_names
        return opts

    def _actualize_value(self):
        data = self.qdf.value()
        self.opts[ParamOpts.KW.VALUE] = data
        self.sigValueChanged.emit(self, data)

    def onDataChanged(self, qdf, change_type: DataChangeType, changes):

        if change_type == self.qdf.BLOCK_SIGNAL_ROLE:
            raise RuntimeError(
                f"change_type = BLOCK_SIGNAL_ROLE ({change_type})")

        if self.model is not None:
            b_emit = True
            try:
                match change_type:
                    case DataChangeType.CELL_UPDATED:
                        self.model.data[changes[0], changes[1]] = changes[2]
                    case DataChangeType.COLUMN_VALUE_UPDATED:
                        self.model.data[:, changes[0]] = changes[1]
                    case DataChangeType.INDEX_VALUE_UPDATED:
                        self.model.data[changes[0], :] = changes[1]
                    case (DataChangeType.COLUMN_ADDED
                          | DataChangeType.ROW_ADDED):
                        raise NotImplementedError
                    case DataChangeType.SET_VALUE:
                        self._actualize_value()
                        b_emit = False
                    case DataChangeType.UNDEFINED:
                        pass
                    case _:
                        raise NotImplementedError(f"{change_type}")
            except IndexError:
                match change_type:
                    case DataChangeType.CELL_UPDATED:
                        if (changes[1] != 0) or (
                                len(self.model.data.shape) != 1):
                            raise AssertionError(
                                "(changes[1] != 0) "
                                "or (len(self.model.data.shape) != 1)")
                        self.model.data[changes[0]] = changes[2]
                    case DataChangeType.COLUMN_VALUE_UPDATED:
                        self.model.data[:] = changes[1]
                    case DataChangeType.INDEX_VALUE_UPDATED:
                        self.model.data[changes[0]] = changes[1]
                    case _:
                        raise NotImplementedError(f"{change_type}")
            if b_emit:
                self.sigValueChanged.emit(self, self.qdf.value())
        else:
            # if self.compare_value():
            #     self.opts[ParamOpts.KW.VALUE] = data
            #     self.sigValueChanged.emit(self, data)
            # else:
            #     # super().setValue(value=data)
            #     raise RuntimeError
            self._actualize_value()

    # def setToDefault(self):
    #     super().setToDefault()

    def setValue(self, value, blockSignal=None):
        self.qdf.setValue(value, b_block_signal=False)
        # self._actualize_value()
        # return super().setValue(value=value, blockSignal=blockSignal)
        return

    def show_index_editor(self):
        window = self.main_window
        if isinstance(window, MainEngineWindowBase):
            editor = window.extraParametersWindow
            signal_register = self.opts[ParamOpts.KW.SIGNAL_REGISTER]
            name = self.name()
            dock = editor.dock_map.get(self.model, None)
            if dock is None:
                editor.addDock(
                    name=name, dock=self.model,
                    exclude_keys=[SeriesModel.Slots.DATA],
                    signal_register=signal_register)
            elif not dock.isVisible():
                editor.addDock(dock)
                dock.label.show()
            if not editor.isVisible():
                editor.show()

    def show_array_editor(self):
        window = self.main_window
        if isinstance(window, MainEngineWindowBase):
            editor = window.arrayEditorDockWidget
            dock_area: ArrayEditorArea = editor.widget()

            # if self.param.qdf not in dock_area.qdf_map:
            if self.table_dock is None:
                self.table_dock = dock_area.addDock(self.qdf)
                self.widget = self.table_dock.widget().table
                if not editor.isVisible():
                    editor.show()
            else:
                # wdg, dock = dock_area[self.param.qdf]
                if self.table_dock.parent() is None:
                    self.table_dock.label.show()
                    dock_area.addDock(self.table_dock)
                    if not editor.isVisible():
                        editor.show()
                    self.widget.onDataChange()
                else:
                    self.table_dock.close()
            if dock_area.count() == 0:
                editor.close()
            return

    def value(self):
        if self.compare_value() is False:
            if self.opts[ParamOpts.KW.VALUE] is None:
                self.opts[ParamOpts.KW.VALUE] = self.qdf.value()
            else:
                self.compare_value()
                raise RuntimeError
        if self.model is not None:
            return {
                SeriesModel.Slots.INDEX: self.model.index,
                SeriesModel.Slots.DATA: self.opts[ParamOpts.KW.VALUE],
            }
        return self.opts[ParamOpts.KW.VALUE]


class ArrayDictParameter(EngineGroupParameter):

    """
    The models are exclusively used as templates for now.
    Do not update their (don't pass them to children parameters).
    """

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

        if isinstance(value, SeriesModel):
            model = value

            opts = ArrayParameter.make_col_opts(model, opts)

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
            else:
                c_data_types = OptionsBuilder.get_parameter_type(
                    model, SeriesModel.Slots.DATA)

                opts = ArrayParameter.make_idx_opts(model, opts)

                name = SeriesModel.Slots.DATA
                opts_ = OptionsBuilder.from_annotation(
                    ann=c_data_types, name=name,
                    value=model.data, **opts)
                if opts_[ParamOpts.KW.NAME] != name:
                    raise AssertionError
                p = self.PARAMETER_CLASS(
                    signal_register=signal_register, **opts_)
                self.addChild(p)
                p.sigValueChanged.connect(self.valueChanged)
                res[name] = p
        else:
            raise NotImplementedError(f"type(value)={type(value)}")

    def value(self):
        # data_dict = super().value()
        data_dict = {}
        return data_dict

