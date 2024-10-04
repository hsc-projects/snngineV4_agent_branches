from typing import Callable

import numpy as np

from pydantic import BaseModel
from vispy.scene import TurntableCamera, XYZAxis
from vispy.visuals import BaseVisual

from snngine_v4.data.validation.array_annotation import ArrayInterfaces
from snngine_v4.geometry.spatial_pars import Ax3D
from snngine_v4.gui.parameter_tree.connectors.basemodel_signal_register import (
    ModelParameterLinks, ModelSignalRegister, ObjectParameterLink,
)

from snngine_v4.gui.parameter_tree.connectors.parameter_connector import \
    ParameterConnector
from snngine_v4.visualization.buffer_utils import adapt_dim

from snngine_v4.visualization.config_models.vispy_camera_configs import \
    TurnTableCameraParameters
from snngine_v4.visualization.config_models.vispy_visual_parameters import \
    RGBAColor
from snngine_v4.visualization.config_models.visual_configs import \
    XYZAxisVisualConfig

from snngine_v4.visualization.scenes.event_camera import (
    EventCameraMixin,
)
from snngine_v4.visualization.scenes.setattribute_event import (
    Set3DAttributeEvent, SetAttributeEvent,
)


class VispyConnector(ParameterConnector):

    SET_DATA_KWS = {
        XYZAxis: ['color', 'pos', 'connect', 'width']
    }

    @classmethod
    def connect_object(cls, model, obj,
                       signal_register: ModelSignalRegister):

        model_signals: ModelParameterLinks = signal_register[model]
        links: list[ObjectParameterLink] = model_signals.refs

        def update_object(link_, key, value):
            cls.update_object(obj, key, value, update_model)

        def update_model(event: SetAttributeEvent):
            cls.update_model(event=event, model_signals=model_signals,
                             block=update_object)

        if isinstance(obj, (EventCameraMixin, TurntableCamera)):
            assert isinstance(model, TurnTableCameraParameters)

            center_signals: ModelParameterLinks = signal_register[
                model.center]

            center_parameters = {
                x.name: center_signals.str_emitter_map[x.name].parameter
                for x in Ax3D
            }

            def update_camera_object(link_: ObjectParameterLink, key, value):
                if link_.obj == model.center:
                    key = 'center'
                    value = (
                        center_parameters[Ax3D.X.name].value(),
                        center_parameters[Ax3D.Y.name].value(),
                        center_parameters[Ax3D.Z.name].value(),
                    )
                block = update_camera_model
                if key == EventCameraMixin.Slots.CENTER:
                    obj.events.center_changed.disconnect(block)
                else:
                    obj.events.attr_changed.disconnect(block)
                try:
                    setattr(obj, key, value)
                except TypeError:
                    if value is None:
                        setattr(obj, key, np.nan)
                    else:
                        raise
                if key == EventCameraMixin.Slots.CENTER:
                    obj.events.center_changed.connect(block)
                else:
                    obj.events.attr_changed.connect(block)

            def update_camera_model(
                    event: SetAttributeEvent,
                    block: Callable | None = update_camera_object):
                if event.key == EventCameraMixin.Slots.CENTER:
                    signals_ = center_signals
                else:
                    signals_ = model_signals
                cls.update_model(
                    event=event, model_signals=signals_,
                    block=block)

            obj.events.attr_changed.connect(update_camera_model)
            obj.events.center_changed.connect(update_camera_model)

            for link in links:

                ev = SetAttributeEvent(
                    key=link.key, value=getattr(obj, link.key))
                update_camera_model(ev, None)

                link.sigAttributeValueChanged.connect(update_camera_object)

            center_links: list[ObjectParameterLink] = center_signals.refs

            for link in center_links:
                link.sigAttributeValueChanged.connect(update_camera_object)

        elif isinstance(obj, XYZAxis):

            assert isinstance(model, XYZAxisVisualConfig)
            obj.events.add(
                auto_connect=False,
                attr_changed=SetAttributeEvent)

            attr_changed_keys = [
                x for x in XYZAxisVisualConfig.model_fields.keys()
                if x not in cls.SET_DATA_KWS[XYZAxis]]

            def set_attr(self_, key, value):
                setattr(self_, key, value)
                if key in attr_changed_keys:
                    obj.events.attr_changed(key=key, value=value)

            # TODO:
            obj.__setattr__ = set_attr
            obj.events.attr_changed.connect(update_model)

            for link in links:
                link.sigAttributeValueChanged.connect(update_object)

            obj.antialias = True
            # obj.antialias = False
            # obj.antialias = True

        return

    @classmethod
    def adapt_condition(cls, arr0, arr1):
        if ((not ArrayInterfaces().D2.b_is_valid_np(arr0))
                or (not ArrayInterfaces().D2.b_is_valid_np(arr1))):
            return False
        return arr0.shape[0] != arr1.shape[0]

    @classmethod
    def handle_set_data_kwargs(cls, obj, key, value):
        kwargs = {key: value}
        if isinstance(obj, XYZAxis):
            if ((key == 'width')
                    or ((key == 'connect') and isinstance(value, str))):
                return kwargs
            if key == 'color':
                if isinstance(kwargs[key], (tuple, dict)):
                    kwargs[key] = RGBAColor.to_vispy(kwargs[key])
                other_key = 'pos'
            else:
                other_key = 'color'
            if cls.adapt_condition(
                    kwargs[key], other := getattr(obj, other_key)):
                kwargs[other_key] = adapt_dim(other, ref=kwargs[key])
                # cls.update_model()
        return kwargs

    @classmethod
    def update_object(cls,  obj: XYZAxis, key, value, block):
        obj.events.update.disconnect(block)
        new_kwargs = {}
        if ((type(obj) in cls.SET_DATA_KWS)
                and (key in cls.SET_DATA_KWS[type(obj)])):
            new_kwargs = cls.handle_set_data_kwargs(obj, key, value)
            obj.set_data(**new_kwargs)
        else:
            setattr(obj, key, value)
        obj.events.update.connect(block)
        if len(new_kwargs) > 1:
            for k, v in new_kwargs.items():
                if k != key:
                    obj.events.attr_changed(key=k, value=v)

    @classmethod
    def update_model_attribute(
            cls, link: ObjectParameterLink, key, value, block):
        if block:
            link.sigAttributeValueChanged.disconnect(block)
        link.set_parameter_value(
            link, key, value, b_block=False)
        if block:
            link.sigAttributeValueChanged.connect(block)

    @classmethod
    def update_model(cls, event: SetAttributeEvent,
                     model_signals: ModelParameterLinks, block):
        if isinstance(event, Set3DAttributeEvent):
            for ax in Ax3D:
                try:
                    link = model_signals.str_emitter_map[ax.name]
                    cls.update_model_attribute(
                        link, ax.name, event.value[ax.value], block)
                except KeyError:
                    raise

        elif isinstance(event, SetAttributeEvent):
            try:
                link = model_signals.str_emitter_map[event.key]
            except KeyError:
                raise
            cls.update_model_attribute(link, event.key, event.value, block)
        # elif event.type == 'update':
        #
        #     source: BaseVisual = event.source
        #     if isinstance(source, TurntableCamera):
        #         model: BaseModel = model_signals.model
        #         for link, p in model_signals.pairs():
        #             value = getattr(source, link.key)
        #             if not isinstance(value, np.ndarray):
        #                 if getattr(model, link.key) != value:
        #                     cls.update_model_attribute(
        #                         link, link.key, value, block)
