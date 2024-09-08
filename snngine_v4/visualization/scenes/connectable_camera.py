from vispy.scene import TurntableCamera
from vispy.util.event import Event


class ConnectableTurntableCamera(TurntableCamera):

    def __init__(
        self,
        fov=45.0,
        elevation=30.0,
        azimuth=30.0,
        roll=0.0,
        distance=None,
        translate_speed=1.0,
        name=None,
        **kwargs
    ):
        super().__init__(fov=fov,
                         elevation=elevation,
                         azimuth=azimuth,
                         roll=roll,
                         distance=distance,
                         translate_speed=translate_speed,
                         name=name, **kwargs)
        # TODO: dedicated events for each property
        self.events.add(auto_connect=False, cam_view_changed=Event)

    def view_changed(self):
        super().view_changed()
        try:
            self.events.cam_view_changed()
        except AttributeError:
            pass
