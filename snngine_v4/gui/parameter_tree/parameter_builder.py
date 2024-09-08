from enum import IntEnum

import numpy as np
import pandas as pd
from pydantic import BaseModel
import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.parametertree import Parameter

from snngine_v4.config.base.base_settings_model import BaseSettingsConfigKW
from snngine_v4.config.base.ui_options import (
    ParameterUIOpts,
    PGParameterOptionKW,
)
from snngine_v4.gui.parameter_tree.parameters.spin_box_slider_parameter import \
    SpinBoxSliderParameter
from snngine_v4.gui.parameter_tree.signal_register import SignalMapRegister
from snngine_v4.utils.field_utils import (
    get_field_interval,
    get_field_json_schema_extra, get_field_multiple_of,
)
from snngine_v4.utils.interval_utils import linspace_from_interval


class ParameterBuilder:

    @classmethod
    def make_par(cls, model: BaseModel, key, value, **options):
        field_ = model.model_fields[key]
        json_schema_extra = get_field_json_schema_extra(field_)

        if PGParameterOptionKW.NAME not in options:
            options[PGParameterOptionKW.NAME] = key

        options[PGParameterOptionKW.VALUE] = value
        options.update(json_schema_extra)

        options[PGParameterOptionKW.TYPE] = field_.annotation.__name__

        parameter_ = None

        if field_.annotation in [float, int]:
            interval = get_field_interval(field_)
            multiple_of = get_field_multiple_of(field_)
            if (interval is not None) and (interval.length < np.inf):
                parameter_ = cls.make_slider_parameter(
                    interval=interval, value=value,
                    multiple_of=multiple_of,
                    **options)

        if parameter_ is None:
            # try:
            if issubclass(field_.annotation, IntEnum):
                if PGParameterOptionKW.LIMITS not in options:
                    # noinspection PyProtectedMember
                    options[PGParameterOptionKW.LIMITS] = (
                        field_.annotation._member_names_)
                    options[PGParameterOptionKW.TYPE] = 'list'
                parameter_ = Parameter.create(**options)
            # except Exception as e:
            #     pass
        if parameter_ is None:
            parameter_ = Parameter.create(**options)
        return parameter_

    @classmethod
    def make_slider_parameter(
            cls, interval: pd.Interval, name, value,
            multiple_of=None, span=None, **options):
        if span is None:
            if multiple_of is None:
                n_steps_if_closed = 101
            else:
                n_steps_if_closed = int(interval.length / multiple_of) + 1
            span = linspace_from_interval(interval=interval,
                                          n_steps_if_closed=n_steps_if_closed,
                                          b_change_n_steps_if_open=True)
        parameter_ = SpinBoxSliderParameter(
            name=name, value=value, span=span, **options)
        return parameter_

    @classmethod
    def make_group(cls, model: BaseModel, name=None,
                   model_dict: dict[str, BaseModel] = None):
        ui_opts = model_dict.get(ParameterUIOpts.UI_OPTIONS_KEYWORD, {})

        # noinspection PyTypedDict
        if model.model_config.get(BaseSettingsConfigKW.FROZEN, None):
            ui_opts[PGParameterOptionKW.READONLY] = True

        if name is None:
            name = ui_opts.pop(PGParameterOptionKW.NAME,
                               model.__class__.__name__)
            if name is None:
                name = model.__class__.__name__
        g = pTypes.GroupParameter(name=name, **ui_opts)
        return g

    @classmethod
    def make_pars(cls, model, model_dict,
                  signal_register: SignalMapRegister = None,
                  name=None):

        group = cls.make_group(
            model, name=name, model_dict=model_dict)

        inherited_options = {
            PGParameterOptionKW.READONLY: group.readonly(),
            PGParameterOptionKW.MOVABLE: group.opts.get(
                PGParameterOptionKW.MOVABLE, False)
        }

        for k, v in model_dict.items():
            if k not in [ParameterUIOpts.UI_OPTIONS_KEYWORD]:
                if isinstance(getattr(model, k), BaseModel):
                    par = cls.make_pars(
                        model=getattr(model, k), model_dict=v, name=k,
                        signal_register=signal_register)
                else:
                    par = cls.make_par(model=model, key=k, value=v,
                                       **inherited_options)
                    if ((signal_register is not None)
                            and (BaseSettingsConfigKW.b_is_frozen(model)
                                 is False)):
                        signal_register.connect_parameter(
                            model, key_=k, parameter=par)
                group.addChild(par)
        return group
