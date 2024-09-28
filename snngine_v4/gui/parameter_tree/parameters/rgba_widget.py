from typing import Type

import numpy as np
from pydantic import BaseModel
from qtpy import QtCore, QtWidgets

from snngine_v4.gui.common.widget_dict import QWidgetDict

from snngine_v4.gui.parameter_tree.parameters.spin_box_slider import \
    SpinBoxSlider

from snngine_v4.utils.settings.ui_parameter_options import ParamOpts
from snngine_v4.visualization.config_models.vispy_visual_parameters import (
    RGBAColor, RGBAEnum,
)


# noinspection PyPep8Naming
class MultiSpinBoxWidget(QtWidgets.QWidget):

    sigValueChanged = QtCore.Signal(object)
    # sigChanging = QtCore.Signal(object, object)

    def __init__(self, model: Type[BaseModel], **kwargs):
        super().__init__(**kwargs)

        self.slider_map: dict[str, SpinBoxSlider] | QWidgetDict = QWidgetDict()
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
            key=key,
            parent_model=self.model,
            c_data_types=ParameterBuilder.get_parameter_type(self.model, key),
            **self.heritable_options
        )
        slider = SpinBoxSlider(**opts)

        self.layout().addWidget(slider.spinbox)
        self.layout().addWidget(slider.display_widget())

        slider.spinbox.valueChanged.connect(self.onValueChanged)

        self.slider_map[key] = slider

    def add_widgets(self):
        for k in self.model.model_fields:
            self.add_widget(k)

    def onValueChanged(self, ev=None):
        v = self.value()
        self.sigValueChanged.emit(self)

    def value(self):
        return tuple([x.spinbox.value() for x in self.slider_map.values()])


# noinspection PyPep8Naming
class RGBAWidget(MultiSpinBoxWidget):
    def __init__(self, **kwargs):
        super().__init__(model=RGBAColor, **kwargs)

    def value(self):
        v = (
            self.slider_map[RGBAEnum.R].spinbox.value(),
            self.slider_map[RGBAEnum.G].spinbox.value(),
            self.slider_map[RGBAEnum.B].spinbox.value(),
            self.slider_map[RGBAEnum.A].spinbox.value(),
        )
        return v

    def setValue(self, value):

        if isinstance(value, RGBAColor):
            value = value.as_tuple()

        if isinstance(value, np.ndarray):
            value = tuple(value)

        if len(value) == 4:
            value3 = value[3]
        else:
            value3 = 1
        self.slider_map[RGBAEnum.R].spinbox.setValue(value[0])
        self.slider_map[RGBAEnum.G].spinbox.setValue(value[1])
        self.slider_map[RGBAEnum.B].spinbox.setValue(value[2])
        self.slider_map[RGBAEnum.A].spinbox.setValue(value3)


if __name__ == '__main__':
    from snngine_v4.utils.settings.xml_settings import XMLSettingsModel
    from snngine_v4.gui.app.debug_app import make_app
    from snngine_v4.visualization.config_models.vispy_visual_parameters import \
        ColorType3

    class LineVisualConfig(XMLSettingsModel):
        pos: None = None
        color: ColorType3

    make_app(LineVisualConfig)
