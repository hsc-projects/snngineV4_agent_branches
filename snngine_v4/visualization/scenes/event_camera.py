from __future__ import annotations

from typing import ClassVar

from vispy.scene import BaseCamera, TurntableCamera
from vispy.util.event import Event


class SetAttributeEvent(Event):
    def __init__(self, *arg, **kwargs):
        key = kwargs.pop('key', None)
        value = kwargs.pop('value', None)
        super().__init__(*arg, **kwargs)
        self.key = key
        self.value = value


class EventCameraMixin:

    class Slots:
        AZIMUTH: ClassVar[str] = 'azimuth'
        DISTANCE: ClassVar[str] = 'distance'
        ELEVATION: ClassVar[str] = 'elevation'
        FOV: ClassVar[str] = 'fov'
        ROLL: ClassVar[str] = 'roll'
        TRANSLATE_SPEED: ClassVar[str] = 'translate_speed'

    EVENT_KEYS: ClassVar[list[str]] = [
        Slots.AZIMUTH,
        Slots.DISTANCE,
        Slots.ELEVATION,
        Slots.FOV,
        Slots.ROLL,
        Slots.TRANSLATE_SPEED,
    ]

    def __init__(self: EventCameraMixin | BaseCamera):

        # TODO: dedicated events for each property
        self.events.add(auto_connect=False, cam_view_changed=SetAttributeEvent)

    def __setattr__(self, key, value):
        if (hasattr(self, 'events') and
                hasattr(getattr(self, 'events'), 'cam_view_changed')
                and key in self.EVENT_KEYS):
            self.events.cam_view_changed(key=key, value=value)
        super().__setattr__(key, value)


class EventTurntableCamera(EventCameraMixin, TurntableCamera):

    def __init__(
        self,
        azimuth=30.0,
        distance=None,
        elevation=30.0,
        fov=45.0,
        roll=0.0,
        translate_speed=1.0,
        name=None,
        **kwargs
    ):
        TurntableCamera.__init__(self, fov=fov,
                                 elevation=elevation,
                                 azimuth=azimuth,
                                 roll=roll,
                                 distance=distance,
                                 translate_speed=translate_speed,
                                 name=name, **kwargs)
        super().__init__()

    def connect_camera(self, func: callable):
        self.events.cam_view_changed.connect(func)
