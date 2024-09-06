from __future__ import annotations

from typing import NamedTuple

from pyqtgraph import ViewBox
from qtpy.QtWidgets import QMainWindow
from vispy.scene import Node, SceneCanvas, VisualNode
from vispy.util import Frozen
from vispy.visuals import CompoundVisual

from snngine_v4.opengl.vispy_gl_mixin import VispyGLMixin
from snngine_v4.opengl.visual_object_config_model import VisualObjectConfigModel
from snngine_v4.utils.class_helpers import PostInitCaller


class VispyObjectLocation(NamedTuple):

    view: ViewBox | None
    scene: SceneCanvas | None
    window: QMainWindow | None

    def set_current(self):
        self.scene.set_current()

    def add(self, obj):
        self.view.add(obj)
        # noinspection PyProtectedMember
        self.scene._draw_scene()


class VisualEngineObjectMixin(VispyGLMixin, metaclass=PostInitCaller):

    ENGINE_LOCATION_KEY = 'vispy_location'

    def __new__(cls, *arg, **kwargs):
        print(f'Creating a new {cls.__name__} object...')
        vispy_location: VispyObjectLocation = kwargs[
            cls.ENGINE_LOCATION_KEY]
        vispy_location.set_current()
        obj = object.__new__(cls)
        return obj

    def __init__(self,
                 visual_config: VisualObjectConfigModel,
                 vispy_location: VispyObjectLocation = None):
        self.vispy_location = vispy_location
        super().__init__(visual_config=visual_config)

    def __post_init__(self: VisualEngineObjectMixin | Frozen | Node):
        b_replace = False
        p = None
        if self.parent is not None:
            b_replace = True
            p = self.parent
        self.vispy_location.add(self)
        if b_replace is True:
            self.parent = p
        self.freeze()


class EngineCompoundVisual(CompoundVisual, VisualEngineObjectMixin):

    def __init__(self, subvisuals, visual_config: VisualObjectConfigModel,
                 vispy_location: VispyObjectLocation = None, **kwargs):

        self.unfreeze()
        VisualEngineObjectMixin.__init__(
            self, visual_config=visual_config,
            vispy_location=vispy_location,)
        self.unfreeze()
        CompoundVisual.__init__(self, subvisuals)


class EngineCompoundVisualNode(VisualNode, EngineCompoundVisual):

    MODIFIER_ARROWS_KEY = 'modifier_arrows'

    def __init__(self, parent=None, name=None, interactive=None,
                 subvisuals: list = None,
                 visual_config: VisualObjectConfigModel = None,
                 vispy_location: VispyObjectLocation = None,
                 **kwargs):
        self.unfreeze()
        if not hasattr(self, 'name'):
            self.name = name  # to allow __str__ before Node.__init__
        self._visual_superclass = EngineCompoundVisual
        EngineCompoundVisual.__init__(
            self, visual_config=visual_config, vispy_location=vispy_location,
            subvisuals=subvisuals, **kwargs)
        VisualNode.__init__(self, parent=parent, name=self.name)
        if self.interactive is True:
            self.interactive = interactive
