from __future__ import annotations

from typing import ClassVar

import numpy as np
from vispy.scene import BaseCamera, TurntableCamera

from snngine_v4.visualization.scenes.setattribute_event import (
    Set3DAttributeEvent, SetAttributeEvent,
)


class EventCameraMixin:

    class Slots:
        AZIMUTH: ClassVar[str] = 'azimuth'
        DISTANCE: ClassVar[str] = 'distance'
        ELEVATION: ClassVar[str] = 'elevation'
        FOV: ClassVar[str] = 'fov'
        NAME: ClassVar[str] = 'name'
        ROLL: ClassVar[str] = 'roll'
        TRANSLATE_SPEED: ClassVar[str] = 'translate_speed'
        SCALE_FACTOR: ClassVar[str] = 'scale_factor'

        CENTER: ClassVar[str] = 'center'

    EVENT_KEYS: ClassVar[list[str]] = [
        Slots.AZIMUTH,

        Slots.CENTER,

        Slots.DISTANCE,
        Slots.ELEVATION,
        Slots.FOV,
        Slots.NAME,
        Slots.ROLL,
        Slots.TRANSLATE_SPEED,
        Slots.SCALE_FACTOR,
    ]

    def __init__(self: EventCameraMixin | BaseCamera):

        # TODO: dedicated events for each property
        self.events.add(
            auto_connect=False,
            attr_changed=SetAttributeEvent,
            # center_changed=SetAttributeEvent
        )

    def __setattr__(self, key, value):
        super().__setattr__(key, value)

        if key == '_scale_factor':
            key = 'scale_factor'

        if (hasattr(self, 'events')
                # and hasattr(getattr(self, 'events'), 'center_changed')
                and hasattr(getattr(self, 'events'), 'attr_changed')
                and key in self.EVENT_KEYS):
            value = getattr(self, key)
            if key == EventCameraMixin.Slots.CENTER:
                value = np.array(value, dtype=np.float32)
            #     self.events.center_changed(key=key, value=value)
            # else:
            self.events.attr_changed(key=key, value=value)


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
