from typing import ClassVar

import pyqtgraph as pg

from snngine_v4.gui.devices.x_touch_mini.x_touch_mini_device import \
    XTouchMiniDevice
from snngine_v4.gui.devices.x_touch_mini.xtm_data_types import XTMGlobalChannel
from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_ui_config import \
    XTMUIElementMixin


class XTMComboBox(XTMUIElementMixin, pg.ComboBox, ):
    def __init__(self, *args, xtm_device,
                 width_divider=1,
                 **kwargs):
        pg.ComboBox.__init__(self, *args, **kwargs)
        XTMUIElementMixin.__init__(
            self, xtm_device, width_divider=width_divider)
        self.currentIndexChanged.connect(self.on_current_index_changed)

    def on_current_index_changed(self, idx):
        raise NotImplementedError

    def update_from_device(self):
        raise NotImplementedError


class XTMGlobalChannelCb(XTMComboBox):

    def __init__(self, xtm_device: XTouchMiniDevice):

        items = {'Off': XTMGlobalChannel.OFF_VALUE}
        for i in range(16):
            items[str(i+1)] = i

        super().__init__(items=items, xtm_device=xtm_device)

    def on_current_index_changed(self, idx):
        self._xtm_device.set_global_channel(self.value())
        self._xtm_device.send_read_device_info_command()

    def update_from_device(self):
        self.currentIndexChanged.disconnect(self.on_current_index_changed)
        value = self._xtm_device.device_config.info.global_channel.value
        self.setValue(value)
        self.currentIndexChanged.connect(self.on_current_index_changed)


class XTMDeviceIdCb(XTMComboBox):

    UNKNOWN_VALUE: ClassVar[str] = -1

    def __init__(self, xtm_device: XTouchMiniDevice,
                 width_divider: int | float = 1):
        items = {'UNKNOWN': self.UNKNOWN_VALUE}
        for i in range(16):
            items[str(i+1)] = i
        super().__init__(items=items,
                         width_divider=width_divider,
                         xtm_device=xtm_device)

    # noinspection PyUnusedLocal
    def on_current_index_changed(self, idx):
        value = self.value()
        if value != self.UNKNOWN_VALUE:
            self._xtm_device.set_device_id(self.value())
        self._xtm_device.send_read_device_info_command()

    def update_from_device(self):
        self.currentIndexChanged.disconnect(self.on_current_index_changed)
        value = self._xtm_device.device_config.info.device_id
        self.setValue(value)
        self.currentIndexChanged.connect(self.on_current_index_changed)

    class XTMAvailablePorts(XTMComboBox):
        def __init__(self, xtm_device: XTouchMiniDevice):
            super().__init__(xtm_device=xtm_device)