from qtpy import QtCore, QtWidgets


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

    def value(self):
        raise NotImplementedError

    def make_device_controller(self) -> DeviceController:
        raise NotImplementedError
