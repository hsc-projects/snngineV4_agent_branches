import pandas as pd
from pyqtgraph.parametertree import Parameter

from snngine_v4.gui.parameters import (
    ArrayParameter, MultiTypeParameter, SpinBoxSliderParameter,
)
from snngine_v4.gui.parameters.common.engine_group_parameter import EngineGroupParameter
from snngine_v4.utils.core_utils import type_assertion

from snngine_v4.utils.data_utils.dataframe_config import (
    SeriesModel,
)
from snngine_v4.utils.data_utils.index_config import (
    Column, IndexConfig, Row,
    RowOrColumn,
)
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


class IndexParameter(EngineGroupParameter):

    def __init__(self, model: IndexConfig, parent_model: SeriesModel,
                 signal_register,
                 **opts):

        opts[ParamOpts.KW.C_B_GROUP_APPLY_BUTTON] = True
        opts[ParamOpts.KW.C_B_GROUP_DEFAULT_BUTTON] = True
        opts[ParamOpts.KW.C_GROUP_APPLY_BUTTON_NAME] = ' Apply Changed  '

        self.model = model
        self.parent_model = parent_model
        self.signal_register = signal_register

        super().__init__(**opts)

        self.sigApply.connect(self.apply_values)

        from snngine_v4.gui.parameter_trees.parameter_builder \
            .parameter_builder import ParameterBuilder

        ParameterBuilder.make_pars_from_model(
            group=self, parent_model=parent_model,
            exclude_keys={None: RowOrColumn.Slots.NAME},
            model=model, signal_register=signal_register)

        dtype = parent_model.data.dtype
        import numpy as np
        if np.issubdtype(dtype, np.floating):
            dt = 'float'
        elif np.issubdtype(dtype, np.integer):
            dt = 'int'
        else:
            raise NotImplementedError

        for index_or_col_p in self.children():
            index_or_col_p.setOpts(**{
                ParamOpts.KW.EXPANDED: False,
                # ParamOpts.KW.C_B_GROUP_APPLY_BUTTON: True
            })
            for value_p in index_or_col_p.children():

                row_col_name = value_p.name()

                if row_col_name == RowOrColumn.Slots.SCALAR_VALUE:
                    index_or_col_p.add_apply_action(self.apply_values)

                if isinstance(value_p, MultiTypeParameter):
                    if row_col_name == RowOrColumn.Slots.SCALAR_VALUE:
                        value_p.b_flat_merge_to_parent = True

                    value_p.b_flat = True
                    value_p.onTypeChange(
                        value_p.type_parameter,
                        value_p.type_parameter.value())
                elif isinstance(value_p, SpinBoxSliderParameter):
                    if row_col_name == RowOrColumn.Slots.SCALAR_VALUE:
                        value_p.b_merge_to_parent = True
                        value_p.show(s=False)

        self.connect_sigValueChanged(1)

        self.array_parameter: ArrayParameter = (
            signal_register.parameter_map[parent_model])

        self.add_action(
            name='show_array_editor', title='  show array  ',
            func=self.array_parameter.show_array_editor)

        self.add_action(
            name='read_scalars', title='  read scalars  ',
            func=self.read_scalars)

    def apply_values(self, param: Parameter):
        if param is self:
            pass
        else:
            model = self.signal_register.group_map.inv[param]
            value = param.child(RowOrColumn.Slots.SCALAR_VALUE).value()
            if pd.notna(value) or self.parent_model.b_nullable:
                if isinstance(model, Row):
                    self.array_parameter.qdf.setRowValue(
                         value=value, row=model.name)
                elif isinstance(model, Column):
                    self.array_parameter.qdf.setColumnValue(
                        value=value, column=model.name)
                else:
                    type_assertion(model, (Row, Column))
        return

    def read_scalars(self):
        pass

    def valueChanged(self, child=None, value=None):
        value_ = self.value()
        super().valueChanged(child, value)


