from typing import Type

import numpy as np
import torch
from qtpy import QtCore

from snngine_v4.gui.parameter_tree.parameters import ArrayParameter
from snngine_v4.gui.parameter_tree.parameters.array_parameter import \
    ArrayDictParameter
from snngine_v4.gui.parameter_tree.parameters.widgets.table.q_dataframe import \
    DataChangeType
from snngine_v4.utils.containers.configurable_dict import ConfigurableDict
from snngine_v4.utils.data_utils.dataframe_config import (
    TypedDataFrameBase,
    TypedDataFrameBase3D,
)
from snngine_v4.utils.data_utils.validation.array_annotation import \
    ArrayInterfaces
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts
from snngine_v4.visualization.cuda.gl_interop.gl_tensor_dict import GLTensorDict
from snngine_v4.utils.cuda_utils.tensor_dict import TensorDict


class TensorParameter(ArrayParameter):

    sigTensorChanged = QtCore.Signal(object)

    def __init__(self, tensor=None, **opts):
        self._tensor = None
        self._b_initialized = False
        super().__init__(**opts)
        if tensor is not None:
            self._tensor = tensor
        self._b_initialized = True

    @property
    def tensor(self):
        return self._tensor

    @tensor.setter
    def tensor(self, value):
        self._tensor = value
        dtype = ArrayInterfaces()[self.opts[ParamOpts.KW.C_DATA_TYPES]].dtype
        shape = self._tensor.shape
        if len(shape) == 2:
            new_type = ArrayInterfaces().array_2d_type(
                x=shape[0], y=shape[1], dtype=dtype)
        elif len(shape) == 3:
            new_type = ArrayInterfaces().array_3d_type(
                x=shape[0], y=shape[1], z=shape[2], dtype=dtype)
        else:
            raise NotImplementedError
        self.qdf.validator = ArrayInterfaces()[new_type]
        self.qdf.sigChanged.emit(self, self.qdf.BLOCK_SIGNAL_ROLE, None)

    def onDataChanged(self, qdf, change_type: DataChangeType, changes):

        if self._b_initialized is False:
            raise RuntimeError
        if change_type == DataChangeType.CELL_UPDATED:
            if self.tensor is not None:
                t_value = torch.from_numpy(np.array(
                    changes[2], dtype=changes[2].dtype))
                self.tensor[changes[0], changes[1]] = t_value
                self.sigTensorChanged.emit(self)
            else:
                pass
            super().onDataChanged(qdf, change_type, changes)

        elif change_type == DataChangeType.COLUMN_ADDED:
            raise NotImplementedError
            if isinstance(self.parent(), TensorDictParameter):
                pass
            super().onDataChanged(qdf, change_type, changes)

        elif change_type == DataChangeType.ROW_ADDED:
            raise NotImplementedError
            if isinstance(self.parent(), TensorDictParameter):
                pass
            super().onDataChanged(qdf, change_type, changes)
        elif change_type == self.qdf.BLOCK_SIGNAL_ROLE:
            super().onDataChanged(qdf, change_type, changes)
        else:
            raise NotImplementedError(f"{change_type}")


class TensorDictParameter(ArrayDictParameter):

    PARAMETER_CLASS: Type[TensorParameter] = TensorParameter

    def __init__(self, value: TensorDict | GLTensorDict = None,
                 model: TypedDataFrameBase3D | None = None,
                 signal_register=None, **opts):

        opts.setdefault('name', 'tensors')
        super().__init__(value=value, model=model,
                         signal_register=signal_register, **opts)

    def build(self, value, signal_register, **opts):
        if isinstance(value, TypedDataFrameBase):
            res: dict[str, TensorParameter] = (
                super().build(value, signal_register, **opts))
            # for i, (k, p) in enumerate(res.items()):
            return res
        elif isinstance(value, ConfigurableDict):
            res = {}
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
                    res[k] = p
                else:
                    raise NotImplementedError
            return res
        else:
            raise NotImplementedError

    def set_tensor(self, tensor):
        tensor_params = [x for x in self.children()
                         if isinstance(x, TensorParameter)]
        if len(tensor_params) == 1:
            tensor_params[0].tensor = tensor
        else:
            if len(tensor_params) != tensor.shape[0]:
                raise AssertionError
            for i, c in enumerate(tensor_params):
                c.tensor = tensor[i]
