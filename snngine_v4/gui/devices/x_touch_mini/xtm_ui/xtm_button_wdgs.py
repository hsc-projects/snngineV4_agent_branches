from qtpy.QtWidgets import QPushButton

from snngine_v4.gui.devices.x_touch_mini.x_touch_mini_device import \
    XTouchMiniDevice
from snngine_v4.gui.devices.x_touch_mini.xtm_data_types import XTMLayer, XTMMode
from snngine_v4.gui.devices.x_touch_mini.xtm_ui.xtm_ui_config import \
    XTMUIElementMixin


class XTMButton(XTMUIElementMixin, QPushButton):
    def __init__(self, *args, xtm_device=None,
                 width_divider=1,
                 **kwargs):
        QPushButton.__init__(self, *args, **kwargs)
        XTMUIElementMixin.__init__(
            self, xtm_device, width_divider=width_divider)


class XTMLedButton(XTMButton):

    def __init__(self, xtm_device: XTouchMiniDevice,
                 color_on_str="rgb(220,150,50)",
                 color_off_str="rgb(200,250,250)",
                 width_divider=1,
                 **kwargs):
        super().__init__(xtm_device=xtm_device, width_divider=width_divider,
                         **kwargs)
        self.clicked.connect(self.update_from_ui)

        self.color_on_str = color_on_str
        self.color_off_str = color_off_str
        self._b_ui_led_on = None
        self.set_color(False)
        self.counter = 0
        # self.setAutoFillBackground(False)
        # self.setCheckable(True)
        # self.setChecked(True)
        # self.setFlat(True)

    @property
    def b_ui_led_on(self):
        return self._b_ui_led_on

    def set_color(self, value_or_color):
        self._set_color(value_or_color)
        # self._set_color(value_or_color)

    # def mouseMoveEvent(self, event):
    #     pass

    def paintEvent(self, arg__1):
        super().paintEvent(arg__1)
        if self.counter == 0:
            self._set_color(self._b_ui_led_on, counter=True)

    def _set_color(self, value_or_color, counter=False):
        if counter is True:
            self.counter += 1
        else:
            self.counter = 0

        if isinstance(value_or_color, bool):
            if value_or_color:
                color = self.color_on_str
            else:
                color = self.color_off_str
        else:
            color = value_or_color
        self.setStyleSheet(f"background-color: {color}; color:black;")
        self._b_ui_led_on = color == self.color_on_str

        # self.setFlat(True)
        # self.setFlat(False)
        # self.setDown(False)
        # self.setChecked(False)
        # self.setDisabled(True)
        # self.setDisabled(False)
        # self.update()
        self.update()

    def update_from_ui(self):
        raise NotImplementedError

    def update_from_device(self):
        pass


# noinspection PyAbstractClass
class XTMNoteButton(XTMLedButton):
    def __init__(
        self, button_idx,
        xtm_device: XTouchMiniDevice,
        channel=11, **kwargs
    ):
        super().__init__(xtm_device, **kwargs)
        self._button_index = button_idx
        self.channel = channel
        self._receive_data_note = self._button_index
        self._led_control_note = self._button_index

    @property
    def receive_data_note(self):
        return self._receive_data_note

    def update_from_ui(self):
        if self._b_ui_led_on:
            # value = LEDButtonState.OFF
            value = False
        else:
            # value = LEDButtonState.ON
            value = True
        self._xtm_device.set_button_led(
            channel=self.channel,
            note=self._led_control_note,
            b_pressed=value)
        self.set_color(
            self._xtm_device.device_config.b_is_button_pressed(
                button_idx=self._button_index))

    def update_from_device(self):
        b_pressed = self._xtm_device.device_config.b_is_button_pressed(
            button_idx=self._button_index)
        self.set_color(b_pressed)


class XTMLayerButton(XTMLedButton):
    def __init__(
        self, xtm_layer: XTMLayer, xtm_device: XTouchMiniDevice, text=None,
        **kwargs
    ):
        super().__init__(xtm_device=xtm_device, **kwargs)
        self._xtm_layer = xtm_layer
        if text is None:
            text = f"LAYER {xtm_layer.name}"
        self.setText(text)

    def update_from_ui(self):
        self._xtm_device.set_layer(xtm_layer=self._xtm_layer)
        self._xtm_device.send_read_device_info_command()

    def update_from_device(self):
        device_info = self._xtm_device.device_config.info
        b_valid = ((device_info.mode != XTMMode.MC)
                   and (device_info.layer == self._xtm_layer))
        # print(self.__class__.__name__, self._xtm_layer, b_valid)
        self.set_color(value_or_color=b_valid)


class XTMModeButton(XTMLedButton):
    def __init__(
        self, xtm_device: XTouchMiniDevice,
        text=None, **kwargs
    ):
        super().__init__(xtm_device, text=text or f"MC MODE", **kwargs)

    def update_from_ui(self):
        if self._b_ui_led_on:
            self._xtm_device.set_mode(XTMMode.STANDARD)
        else:
            self._xtm_device.set_mode(XTMMode.MC)
        self._xtm_device.send_read_device_info_command()

    def update_from_device(self):
        device_info = self._xtm_device.device_config.info
        b_valid = (device_info.mode == XTMMode.MC)
        # print(self.__class__.__name__, b_valid)
        self.set_color(value_or_color=b_valid)


class XTMConnectedButton(XTMLedButton):

    def __init__(self, xtm_device: XTouchMiniDevice, **kwargs):
        super().__init__(
            xtm_device=xtm_device,
            color_on_str='rgb(50, 200, 50)',
            color_off_str='rgb(200, 50, 50)',
            **kwargs
        )

    def update_from_ui(self):
        if self._xtm_device.connected:
            pass
        else:
            self._xtm_device.connect_to_device()
        self.set_color(self._xtm_device.connected)

    def update_from_device(self):
        self.set_color(self._xtm_device.connected)
