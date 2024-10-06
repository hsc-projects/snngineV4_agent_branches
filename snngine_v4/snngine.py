from snngine_v4.nn.nn_builder import NetworkManager
from snngine_v4.snngine_config import EngineConfig

from snngine_v4.visualization.scenes.main_network_scene import \
    EngineSceneCanvas
from snngine_v4.visualization.scenes.scene_manager import SceneManager


class SNNgine:

    def __init__(self, settings: EngineConfig | str = None):
        try:
            # noinspection PyUnresolvedReferences
            from pycuda import autoinit
        except ModuleNotFoundError:
            pass
        from vispy import gloo

        if settings is None:
            settings = EngineConfig()

        self.conf = settings
        gloo.gl.use_gl(self.conf.open_gl.gloo_target)

        # noinspection PyTypeHints
        self.scene_manager: dict[str, EngineSceneCanvas] | SceneManager = (
            SceneManager(self.conf.scenes))

        self.network_manager = NetworkManager(
            container_model=self.conf.current)

        # self.build()

    def build(self):
        self.network_manager.build(self.conf.construction)
        self.conf.current = self.network_manager.container_model
        self.scene_manager.build_visuals(
            visuals={'grid': self.conf.current.network.grid},
            scene=self.conf.scenes.main,
        )

        return

    def close(self):
        from snngine_v4.visualization.cuda.gl_interop.gl_buffer import GLBuffer
        GLBuffer.GLOBAL_MAP.unregister_all()
