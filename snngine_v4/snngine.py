from snngine_v4.nn.nn_builder import NetworkBuilder
from snngine_v4.snngine_config import EngineConfig
from snngine_v4.visualization.scenes.scene_manager import SceneManager


class SNNgine:
    def __init__(self, settings: EngineConfig | str = None):

        # noinspection PyUnresolvedReferences
        from pycuda import autoinit
        from vispy import gloo

        if settings is None:
            settings = EngineConfig()

        self.conf = settings
        gloo.gl.use_gl(self.conf.open_gl.gloo_target)

        self.scene_manager = SceneManager(self.conf.scenes)

        self.network_manager = NetworkBuilder()

        self.build()

    def build(self):
        self.network_manager.update(self.conf.construction.network)


    def close(self):
        from snngine_v4.visualization.cuda.gl_interop.gl_buffer import GLBuffer
        GLBuffer.GLOBAL_MAP.unregister_all()
