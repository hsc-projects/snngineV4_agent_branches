import numpy as np
import torch
from qtpy import QtCore

from snngine_v4.gui.parameter_tree.parameters import ArrayParameter
from snngine_v4.gui.parameter_tree.parameters.engine_group_parameter import \
    EngineGroupParameter
from snngine_v4.gui.parameter_tree.parameters.widgets.q_dataframe import \
    DataChangeType
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts
from snngine_v4.visualization.cuda.gl_interop.gl_tensor_dict import GLTensorDict


class TensorParameter(ArrayParameter):

    sigTensorChanged = QtCore.Signal(object)

    def __init__(self, tensor, **opts):
        self.tensor = tensor
        super().__init__(**opts)

    def onDataChanged(self, qdf, change_type: DataChangeType, changes):

        if change_type == DataChangeType.CELL_UPDATED:
            t_value = torch.from_numpy(np.array(
                changes[2], dtype=changes[2].dtype))
            self.tensor[changes[0], changes[1]] = t_value
            self.sigTensorChanged.emit(self)
            super().onDataChanged(qdf, change_type, changes)
        else:
            raise NotImplementedError


class TensorDictParameter(EngineGroupParameter):

    def __init__(self, value: GLTensorDict, signal_register=None, **opts):
        opts.setdefault('name', 'tensor')
        super().__init__(**opts)
        if signal_register is not None:
            self.build(value, signal_register)

    def build(self, value, signal_register, **opts):
        items = list(value.items())
        for k, v in items:
            if len(v.shape) == 2:
                if isinstance(value, GLTensorDict):
                    dt = value.str2gl[k].validation_interface

                else:
                    # dt = ArrayInterfaces().array_2d_type(
                    #     x='* x', y=v.shape, dtype=np.float32)
                    raise NotImplementedError

                opts.update({
                    ParamOpts.KW.C_DATA_TYPES: dt,
                    # ParamOpts.KW.C_COLUMN_NAME_S: dt,
                })

                p = TensorParameter(
                    signal_register=signal_register,
                    tensor=v,
                    name=k, value=v.cpu().numpy(), **opts)
                self.addChild(p)
                p.sigValueChanged.connect(self.valueChanged)
            else:
                raise NotImplementedError
