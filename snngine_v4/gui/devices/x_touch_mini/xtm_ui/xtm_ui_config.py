from typing import ClassVar

from qtpy import QtWidgets

from snngine_v4.gui.devices.x_touch_mini.x_touch_mini_device import \
    XTouchMiniDevice


class UIConfig:
    MIN_KNOB_HEIGHT: ClassVar[int] = 350
    TEXT_BUTTON_WIDTH: ClassVar[int] = 120
    TEXT_BUTTON_HEIGHT: ClassVar[int] = 28


class XTMUIElementMixin:
    def __init__(self: QtWidgets.QPushButton | QtWidgets.QWidget,
                 xtm_device: XTouchMiniDevice | None = None,
                 width_divider: int | float = 1):
        self.setFixedHeight(UIConfig.TEXT_BUTTON_HEIGHT)
        width = UIConfig.TEXT_BUTTON_WIDTH // width_divider
        self.setFixedWidth(width)
        self._xtm_device = xtm_device


class XTMLabel(XTMUIElementMixin, QtWidgets.QLabel, ):
    def __init__(self, *args, xtm_device=None, width_divider: int | float = 1,
                 **kwargs):
        QtWidgets.QLabel.__init__(self, *args, **kwargs)
        XTMUIElementMixin.__init__(self, width_divider=width_divider,
                                   xtm_device=xtm_device)
        self.setContentsMargins(0, 0, 0, 0)
