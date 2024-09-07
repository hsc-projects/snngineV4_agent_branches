from __future__ import annotations

from vispy.scene import VisualNode
from vispy.visuals import CompoundVisual

from snngine_v4.visualization.opengl.engine_visual_mixin import EngineVisualMixin
from snngine_v4.visualization.opengl.visual_config import (
    VispyObjectLocation, VisualEngineObjectConfig,
)


class EngineCompoundVisual(CompoundVisual, EngineVisualMixin):

    def __init__(self, subvisuals, visual_config: VisualEngineObjectConfig,
                 vispy_location: VispyObjectLocation = None, **kwargs):

        self.unfreeze()
        EngineVisualMixin.__init__(
            self, visual_config=visual_config,
            vispy_location=vispy_location,)
        self.unfreeze()
        CompoundVisual.__init__(self, subvisuals)


class EngineCompoundVisualNode(VisualNode, EngineCompoundVisual):

    def __init__(self, parent=None,
                 subvisuals: list = None,
                 visual_config: VisualEngineObjectConfig = None,
                 vispy_location: VispyObjectLocation = None,
                 **kwargs):
        self.unfreeze()
        if not hasattr(self, 'name'):
            self.name = visual_config.name
            # to allow __str__ before Node.__init__
        self._visual_superclass = EngineCompoundVisual
        EngineCompoundVisual.__init__(
            self, visual_config=visual_config, vispy_location=vispy_location,
            subvisuals=subvisuals, **kwargs)
        VisualNode.__init__(self, parent=parent, name=self.name)
        if self.interactive is True:
            self.interactive = visual_config.interactive
