from typing import get_args

from pyqtgraph import ComboBox
from qtpy import QtCore, QtWidgets

from snngine_v4.gui.common.widget_dict import QWidgetDict
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts


# noinspection PyPep8Naming
class MultiTypeParameterWidget(QtWidgets.QWidget):

    sigChanged = QtCore.Signal(object)
    sigChanging = QtCore.Signal(object, object)

    sigWidgetCreated = QtCore.Signal(object, str, object)
    sigWidgetTypeChanged = QtCore.Signal(object, str, object)

    def __init__(self, parent=None, value=None, **kwargs):

        super().__init__(parent)

        self.opts = {}
        self.opts.update(kwargs)
        self._value = value

        self.types = {
            t.__name__:
                t for t in get_args(self.opts[ParamOpts.KW.C_DATA_TYPES])
        }
        self.type_combo = ComboBox(items=list(self.types.keys()))

        self.widget_map: dict[str, QtWidgets] | QWidgetDict = QWidgetDict()

        # self.editor_widget = QtWidgets.QLineEdit()

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setSpacing(0)
        self.setContentsMargins(0, 0, 0, 0)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.type_combo.setStyleSheet("min-height: 1;")
        # noinspection PyTypeChecker
        q: QtWidgets.QListView = self.type_combo.view()
        q.setStyleSheet("min-height: 1;")
        self.type_combo.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
        )

        self.layout().addWidget(self.type_combo)
        self.type_combo.currentIndexChanged.connect(self.onTypeChange)

    def _build_widget(self, key):

        if self.types[key] == str:
            wdg = QtWidgets.QLineEdit()
            self.widget_map[key] = wdg
            self.layout().addWidget(wdg)

        else:
            raise NotImplementedError(f"{key}")
        self.sigWidgetCreated.emit(wdg, key, self.types[key])
        return wdg

    @property
    def current_type(self):
        return self.type_combo.value()

    @property
    def editor_widget(self):
        key = self.current_type
        if key not in self.widget_map:
            self._build_widget(key=key)
        return self.widget_map[key]

    def onTypeChange(self, ev):
        return self.editor_widget

    def hide(self):
        self.editor_widget.hide()

    def setValue(self, value):
        if isinstance(self.editor_widget, QtWidgets.QLineEdit):
            self.editor_widget.setText(str(value))
        self._value = value

    def show(self):
        self.editor_widget.show()

    def value(self):
        return self._value
