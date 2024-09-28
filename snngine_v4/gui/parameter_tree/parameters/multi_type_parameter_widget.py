from typing import get_args

from pyqtgraph import ComboBox
from qtpy import QtCore, QtWidgets

from snngine_v4.gui.common.widget_dict import QWidgetDict
from snngine_v4.gui.parameter_tree.parameters.rgba_widget import (
    MultiSpinBoxWidget, RGBAWidget,
)
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts
from snngine_v4.visualization.config_models.vispy_visual_parameters import \
    RGBAColor


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

        self._previous_type = None
        self._next_previous_type = self.current_type
        self.type_combo.currentIndexChanged.connect(self.onTypeChange)

        self.widget_map: dict[str, QtWidgets] | QWidgetDict = QWidgetDict()

        # self.editor_widget = QtWidgets.QLineEdit()

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setSpacing(0)
        # self.setContentsMargins(0, 0, 0, 0)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.type_combo.setStyleSheet("min-height: 1;")
        self.type_combo.setMaximumHeight(20)
        # noinspection PyTypeChecker
        q: QtWidgets.QListView = self.type_combo.view()
        q.setStyleSheet("min-height: 1; min-width: 120;")
        self.type_combo.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
        )

        self.layout().addWidget(self.type_combo)

        self._build_widget(self.current_type)
        self.setValue(self._value)

    def _build_widget(self, key):

        if self.types[key] == str:
            wdg = QtWidgets.QLineEdit()
            wdg.setMaximumHeight(20)
            wdg.setContentsMargins(0, 0, 0, 0)
            wdg.textChanged.connect(self.onValueChanged)
        elif self.types[key] == RGBAColor:
            wdg = RGBAWidget()
            wdg.sigValueChanged.connect(self.onValueChanged)
        else:
            return
            # raise NotImplementedError(f"{key}")

        # wdg.setStyleSheet("min-height: 1;")
        wdg.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
        )
        self.widget_map[key] = wdg
        self.layout().addWidget(wdg)
        self.sigWidgetCreated.emit(wdg, key, self.types[key])
        return wdg

    @property
    def current_type(self):
        return self.type_combo.value()

    @property
    def value_text(self):
        return str(self.value())

    @property
    def editor_widget(self):
        key = self.current_type
        if key not in self.widget_map:
            self._build_widget(key=key)
        wdg = self.widget_map[key]
        for k, v in self.widget_map.items():
            if k != key:
                v.hide()
            else:
                v.show()
        return wdg

    def hide(self):
        self.editor_widget.hide()

    def onValueChanged(self):
        self.sigChanged.emit(self)

    def onTypeChange(self, ev=None):
        key = self.current_type
        self._previous_type = self._next_previous_type
        self._next_previous_type = key
        # if self._previous_type:
        self.widget_map[self._previous_type].hide()
        self.layout().removeWidget(self.widget_map[self._previous_type])
        wdg = self.editor_widget  # build the wdg if necessary
        self.sigWidgetTypeChanged.emit(wdg, key, self.types[key])

    def setValue(self, value):

        if isinstance(value, tuple):
            if self.types[self.current_type] != RGBAColor:
                self._value = value
                self.type_combo.setText('RGBAColor')
                return
        elif not isinstance(value, self.types[self.current_type]):
            for k, type_ in self.types.items():
                if isinstance(value, type_):
                    self._value = value
                    self.type_combo.setText(k)
                    return

        if isinstance(self.editor_widget, QtWidgets.QLineEdit):
            self.editor_widget.setText(str(value))
        elif isinstance(self.editor_widget, MultiSpinBoxWidget):
            self.editor_widget.setValue(value)

    def show(self):
        self.editor_widget.show()

    def value(self):
        if isinstance(self.editor_widget, QtWidgets.QLineEdit):
            return self.editor_widget.text()
        return self.editor_widget.value()
