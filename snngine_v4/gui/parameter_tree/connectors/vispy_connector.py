from vispy.scene import TurntableCamera

from snngine_v4.gui.parameter_tree.connectors.basemodel_signal_register import (
    ModelParameterLinks, ModelSignalRegister, ObjectParameterLink,
)
from snngine_v4.gui.parameter_tree.connectors.parameter_connector import \
    ParameterConnector
from snngine_v4.visualization.config_models.vispy_camera_configs import \
    TurnTableCameraParameters
from snngine_v4.visualization.scenes.event_camera import (
    EventCameraMixin,
)


class VispyConnector(ParameterConnector):

    @classmethod
    def connect_object(cls, model, obj,
                       signal_register: ModelSignalRegister):

        signals: ModelParameterLinks = signal_register[model]

        def update_object(link_, key, value):
            obj.events.cam_view_changed.disconnect(update_model)
            setattr(obj, key, value)
            obj.events.cam_view_changed.connect(update_model)

        def update_model(event):
            link.sigAttributeValueChanged.disconnect(update_object)
            model.__setattr__(model, event.key, event.value)
            link.sigAttributeValueChanged.connect(update_object)

        if isinstance(obj, (EventCameraMixin, TurntableCamera)):
            assert isinstance(model, TurnTableCameraParameters)
            obj.events.cam_view_changed.connect(update_model)

            for link in signals.refs:
                link: ObjectParameterLink
                link.sigAttributeValueChanged.connect(update_object)

        return
