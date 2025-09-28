from __future__ import annotations

from pyqtgraph import ComboBox
from qtpy import QtWidgets

type ComboBoxType = CustomComboBox | QtWidgets.QComboBox


class CustomComboBox(ComboBox):

    def __init__(self: ComboBoxType, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self.apply_custom_settings(self, None)

    @classmethod
    def apply_custom_settings(cls, cb: ComboBoxType, max_height=20):
        cb.setStyleSheet("min-height: 1;")
        # noinspection PyTypeChecker
        q: QtWidgets.QListView = cb.view()
        q.setStyleSheet("min-height: 1; min-width: 120;")
        cb.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
        )
        if max_height is not None:
            cb.setMaximumHeight(max_height)
