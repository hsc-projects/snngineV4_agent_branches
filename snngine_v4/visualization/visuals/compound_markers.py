from vispy.scene import Markers
from vispy.visuals import CompoundVisual, MarkersVisual


class CompoundMarkersVisual(CompoundVisual):

    def __init__(self,  subvisuals=None, **kwargs):

        self.unfreeze()
        self._markers_visual: MarkersVisual = Markers(parent=None, **kwargs)

        # noinspection PyTypeChecker
        self._markers_visual.set_gl_state(
            'translucent', blend=True, depth_test=True)

        if subvisuals is None:
            subvisuals = []

        subvisuals = [self._markers_visual] + subvisuals

        CompoundVisual.__init__(self, subvisuals=subvisuals)

    @property
    def alpha(self):
        return self._markers_visual._alpha

    @alpha.setter
    def alpha(self, value):
        self._markers_visual.alpha = value

    def set_data(self, *args, **kwargs):
        self._markers_visual.set_data(*args, **kwargs)
        # self.update()
