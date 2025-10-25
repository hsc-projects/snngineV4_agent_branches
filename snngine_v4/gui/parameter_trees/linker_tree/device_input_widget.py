from pyqtgraph.parametertree import Parameter
from qtpy import QtCore, QtWidgets

from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


class DeviceController(QtCore.QObject):
    sigDeviceInput = QtCore.Signal(object)
    sigHostInput = QtCore.Signal(object)

    def emit_device_input(self, device_input):
        self.sigDeviceInput.emit(device_input)


class DeviceInputSelectorWidget(QtWidgets.QWidget):

    sigValueSet = QtCore.Signal(object)

    @property
    def action_id_str(self):
        raise NotImplementedError

    def as_label_string(self):
        return str(self)

    def clear(self):
        raise NotImplementedError

    def make_device_controller(self) -> QtCore.Signal:
        raise NotImplementedError

    @classmethod
    def range_map_values(cls, parameter: Parameter):
        par_opts = parameter.opts
        if (span := par_opts.get(ParamOpts.KW.SPAN)) is not None:
            minimum = span[0]
            maximum = span[-1]
            minimum_allowed = minimum
            maximum_allowed = maximum
        else:
            minimum = maximum = minimum_allowed = maximum_allowed = None
        return minimum, maximum, minimum_allowed, maximum_allowed

    def update_target(self):
        raise NotImplementedError

    def value(self):
        raise NotImplementedError
