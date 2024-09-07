from enum import IntEnum

import numpy as np
import pandas as pd
from pydantic import BaseModel
import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.parametertree import Parameter


from snngine_v4.config.base.ui_options import JSESlots, ParameterUIOpts
from snngine_v4.gui.parameter_tree.parameters.spin_box_slider_parameter import \
    SpinBoxSliderParameter
from snngine_v4.utils.field_utils import (
    get_field_interval,
    get_field_json_schema_extra, get_field_multiple_of,
)
from snngine_v4.utils.interval_utils import linspace_from_interval


class ParameterBuilder:

    @classmethod
    def make(cls, model: BaseModel, key, value):
        field_ = model.model_fields[key]
        json_schema_extra = get_field_json_schema_extra(field_)

        name = key

        # field_type_str = field_.annotation.__name__
        if ((JSESlots.ENUM in json_schema_extra)
                or (JSESlots.LIST in json_schema_extra)):
            if JSESlots.ENUM in json_schema_extra:
                limits = json_schema_extra[JSESlots.ENUM]
            else:
                limits = json_schema_extra[JSESlots.LIST]
            parameter_ = pTypes.ListParameter(
                name=name, value=value, limits=limits, )
        elif field_.annotation in [float, int]:
            interval = get_field_interval(field_)
            suffix = json_schema_extra.pop(JSESlots.SUFFIX, '')
            multiple_of = get_field_multiple_of(field_)

            if (interval is not None) and (interval.length < np.inf):
                parameter_ = cls.make_slider_parameter(
                    interval=interval, name=name, value=value,
                    type_=field_.annotation.__name__,
                    suffix=suffix, multiple_of=multiple_of)
            else:
                parameter_ = Parameter.create(
                    name=name, value=value,
                    type=field_.annotation.__name__,)
        elif field_.annotation in [str]:
            parameter_ = Parameter.create(
                name=name, value=value,
                type=field_.annotation.__name__, )
        else:
            try:
                if issubclass(field_.annotation, IntEnum):
                    parameter_ = Parameter.create(
                        name=name, value=value,
                        type='list', )
                else:
                    raise NotImplementedError
            except:
                raise NotImplementedError

        return parameter_

    @classmethod
    def make_slider_parameter(
            cls,
            interval: pd.Interval, name, value,
            # n_steps_if_closed=101,
            suffix='', type_=None, multiple_of=None):
        if multiple_of is None:
            n_steps_if_closed = 101
        else:
            n_steps_if_closed = int(interval.length / multiple_of) + 1
        span = linspace_from_interval(interval=interval,
                                      n_steps_if_closed=n_steps_if_closed,
                                      b_change_n_steps_if_open=True)
        parameter_ = SpinBoxSliderParameter(
            name=name,
            value=value,
            span=span,
            suffix=suffix,
            type=type_,
            )
        return parameter_

    @classmethod
    def make_group(cls, model: BaseModel, name=None,
                   model_dict: dict[str, BaseModel] = None):
        ui_opts = model_dict.pop(ParameterUIOpts.UI_OPTIONS_KEYWORD, {})
        g = pTypes.GroupParameter(
            name=name or model.__class__.__name__, **ui_opts)
        return g
