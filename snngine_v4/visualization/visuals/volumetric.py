from vispy.scene.visuals import create_visual_node
from vispy.visuals import CompoundVisual, VolumeVisual


class R32fVolumeVisual(VolumeVisual):
    def __init__(self, vol, **kwargs):
        VolumeVisual.__init__(
            self, vol=vol, texture_format='r32f', **kwargs)


R32fVolume = create_visual_node(R32fVolumeVisual)


class CompoundR32fVolumeVisual(CompoundVisual):
    """
    A visual that represents a volume of a chemical concentration.
    """

    _subvisuals: list[R32fVolumeVisual]

    def __init__(self, **kwargs):
        if len(kwargs) > 0:
            subvisuals = [R32fVolumeVisual(**kwargs)]
        else:
            subvisuals = []
        super().__init__(subvisuals=subvisuals)

    def set_data(self, data, subvisual_index=0, **kwargs):
        self._subvisuals[subvisual_index].set_data(data, **kwargs)


CompoundR32fVolume = create_visual_node(CompoundR32fVolumeVisual)
