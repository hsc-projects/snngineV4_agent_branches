from typing import Type

from pydantic import BaseModel
from qtpy import QtCore, QtWidgets

from snngine_v4.gui.common.widget_dict import QWidgetDict
from snngine_v4.gui.parameter_tree.parameters.custom_widgets import \
    CustomSpinBox
from snngine_v4.gui.parameter_tree.parameters.spin_box_slider import \
    SpinBoxSlider

from snngine_v4.utils.settings.ui_parameter_options import ParamOpts
from snngine_v4.visualization.config_models.vispy_visual_parameters import \
    RGBAColor


# noinspection PyPep8Naming
class MultiSpinBoxWidget(QtWidgets.QWidget):

    sigValueChanged = QtCore.Signal(object)
    # sigChanging = QtCore.Signal(object, object)

    def __init__(self, model: Type[BaseModel], **kwargs):
        super().__init__(**kwargs)

        self.slider_map: dict[str, QtWidgets] | QWidgetDict = QWidgetDict()
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.setMaximumHeight(20)
        self.model = model()
        self.model_opts = ParamOpts.from_model(self.model)
        self.heritable_options = ParamOpts.heritable_options(**self.model_opts)
        self.edits = {}

        self.add_widgets()

    def add_widget(self, key):

        from snngine_v4.gui.parameter_tree.parameter_builder import \
            ParameterBuilder
        opts = ParamOpts.from_field(
            key=key, value=0,
            parent_model=self.model,
            c_data_types=ParameterBuilder.get_parameter_type(self.model, key),
            **self.heritable_options
        )
        slider = SpinBoxSlider(**opts)
        self.layout().addWidget(slider.spinbox)
        slider.spinbox.valueChanged.connect(self.onValueChanged)
        self.slider_map[key] = slider

    def add_widgets(self):
        for k in self.model.model_fields:
            self.add_widget(k)

    def onValueChanged(self, ev=None):
        self.sigValueChanged.emit(self)

    def value(self):
        return tuple([x.spinbox.value() for x in self.slider_map.values()])


class RGBAWidget(MultiSpinBoxWidget):
    def __init__(self, **kwargs):
        super().__init__(model=RGBAColor, **kwargs)

    def value(self):
        return tuple([x.spinbox.value() for x in self.slider_map.values()])
