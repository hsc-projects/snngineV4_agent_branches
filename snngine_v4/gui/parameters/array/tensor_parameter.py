from typing import Type

import numpy as np
import torch
from qtpy import QtCore

from snngine_v4.gui.parameters import ArrayParameter
from snngine_v4.gui.parameters.array.array_parameter import \
    ArrayDictParameter
from snngine_v4.gui.parameters.widgets.table.q_dataframe import \
    DataChangeType
from snngine_v4.utils.containers.configurable_dict import ConfigurableDict
from snngine_v4.utils.containers.mappings import Object2ObjectMap
from snngine_v4.utils.data_utils.dataframe_config import (
    SeriesModel,
    TypedDataFrameBase3D,
)
from snngine_v4.utils.data_utils.validation.array_annotation import \
    ArrayInterfaces
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts

from snngine_v4.visualization.cuda.gl_interop import GLTensorDict

from snngine_v4.utils.cuda_utils.tensor_dict import TensorDict


class TensorParameter(ArrayParameter):

    sigTensorSet = QtCore.Signal(object, object)
    # sigTensorChanged = QtCore.Signal(object, int, object)

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
        old_value = self._tensor
        self._tensor = value
        dtype = ArrayInterfaces()[self.opts[ParamOpts.KW.C_DATA_TYPES]].dtype
        shape = self._tensor.shape
        if len(shape) in [1, 2, 3]:
            new_type = ArrayInterfaces().make_type(
                *shape, dtype=dtype)
        else:
            raise NotImplementedError
        self.qdf.validator = ArrayInterfaces()[new_type]
        self.sigTensorSet.emit(self, value)
        # self.qdf.sigChanged.emit(self, self.qdf.BLOCK_SIGNAL_ROLE, None)

    def onDataChanged(self, qdf, change_type: DataChangeType, changes):

        if self._b_initialized is False:
            raise RuntimeError

        match change_type:
            case DataChangeType.CELL_UPDATED:
                if self.tensor is not None:
                    t_value = torch.from_numpy(np.array(
                        changes[2], dtype=changes[2].dtype))
                    self.tensor[changes[0], changes[1]] = t_value
                    # self.sigTensorChanged.emit(self, change_type, changes)
                else:
                    pass

            case DataChangeType.COLUMN_VALUE_UPDATED:
                if self.tensor is not None:
                    self.tensor[:, changes[0]] = changes[1]

            case DataChangeType.INDEX_VALUE_UPDATED:
                if self.tensor is not None:
                    self.tensor[changes[0], :] = changes[1]

            case (DataChangeType.COLUMN_ADDED
                  | DataChangeType.ROW_ADDED
                  | DataChangeType.SET_VALUE
                  | DataChangeType.UNDEFINED):
                if self.tensor is not None:
                    raise NotImplementedError
        super().onDataChanged(qdf, change_type, changes)


type TensorDictType = TensorDict | GLTensorDict | None


class TensorDictParameter(ArrayDictParameter):
    """
    Only interacts with the dict (not the model)
    """
    PARAMETER_CLASS: Type[TensorParameter] = TensorParameter

    def __init__(
            self,
            value: TensorDictType = None,
            model: TypedDataFrameBase3D | None = None,
            signal_register=None,
            **opts):

        opts.setdefault('name', 'tensors')
        super().__init__(value=value, model=model,
                         signal_register=signal_register, **opts)

    def build(self, value, signal_register, **opts):
        if isinstance(value, SeriesModel):
            res: dict[str, TensorParameter] = (
                super().build(value, signal_register, **opts))
            # for i, (k, p) in enumerate(res.items()):
            return res
        elif isinstance(value, ConfigurableDict):
            res = {}
            items = list(value.items())
            for k, v in items:

                if isinstance(value, Object2ObjectMap):
                    k = value.inv[v]

                if len(v.shape) in [2, 3]:
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
                    raise NotImplementedError(f"len(v.shape) == {len(v.shape)}")
            return res
        else:
            raise NotImplementedError(f"type(value) == {type(value)}")

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
