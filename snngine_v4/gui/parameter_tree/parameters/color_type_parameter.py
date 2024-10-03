from typing import get_args

from snngine_v4.data.validation.array_annotation import ArrayInterfaces
from snngine_v4.gui.parameter_tree.parameters.multi_type_parameter import \
    MultiTypeParameter
from snngine_v4.utils.settings.ui_parameter_options import ParamOpts
from snngine_v4.visualization.config_models.vispy_visual_parameters import (
    ColorVBO, RGBAColor,
)


class ColorTypeParameter(MultiTypeParameter):

    def __init__(self, **opts):
        super().__init__(**opts)

    def build(self, signal_register):
        built_pars = super().build(signal_register)
        if self.children_map[ColorVBO] not in built_pars:
            raise AssertionError
        if ArrayInterfaces()[ColorVBO].b_is_valid(
                self.opts.get(ParamOpts.KW.VALUE)):
            name = self.children_map[ColorVBO].name()
            self.type_parameter.setValue(name)

    @property
    def data_types(self):
        return get_args(self.opts[ParamOpts.KW.C_DATA_TYPES].__value__)

    @classmethod
    def make_value(cls, value, type_):
        if type_ == RGBAColor:
            if ArrayInterfaces()[ColorVBO].b_is_valid(value):
                value_ = RGBAColor()
            else:
                value_ = value
            if value_ is None:
                raise ValueError
        else:
            if ArrayInterfaces()[ColorVBO].b_is_valid(value):
                if type_ == ColorVBO:
                    value_ = value
                else:
                    value_ = RGBAColor().as_type(type_)
            elif isinstance(value, RGBAColor):
                value_ = value.as_type(type_)
            else:
                raise TypeError(type(value))
        return value_
