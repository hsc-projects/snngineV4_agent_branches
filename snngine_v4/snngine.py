from snngine_v4.nn.nn_builder import NetworkBuilder
from snngine_v4.snngine_config import EngineConfig

from snngine_v4.visualization.scenes.main_network_scene import \
    EngineSceneCanvas
from snngine_v4.visualization.scenes.scene_manager import SceneManager
from snngine_v4.visualization.visual_builder import VispyVisualManager


class SNNgine:
    def __init__(self, settings: EngineConfig | str = None):

        # noinspection PyUnresolvedReferences
        from pycuda import autoinit
        from vispy import gloo

        if settings is None:
            settings = EngineConfig()

        self.conf = settings
        gloo.gl.use_gl(self.conf.open_gl.gloo_target)

        # noinspection PyTypeHints
        self.scene_manager: dict[str, EngineSceneCanvas] | SceneManager = (
            SceneManager(self.conf.scenes))

        self.network_manager = NetworkBuilder()

        self.build()

    def build(self):
        self.network_manager.update(self.conf.construction.network)

        scene: EngineSceneCanvas = self.scene_manager[self.conf.scenes.main]
        parent = scene.new_visual_node_parent()

        box = VispyVisualManager.cls_build(
            self.conf.construction.network.grid, parent=parent).built

        return

    def close(self):
        from snngine_v4.visualization.cuda.gl_interop.gl_buffer import GLBuffer
        GLBuffer.GLOBAL_MAP.unregister_all()
