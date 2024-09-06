from vispy import gloo

from snngine_v4.config.engine_config_model import EngineConfig
from snngine_v4.opengl.cuda.gl_interop.gl_buffer import GLBuffer


class SNNgine:
    def __init__(self, settings: EngineConfig | str = None):

        # noinspection PyUnresolvedReferences
        from pycuda import autoinit
        gloo.gl.use_gl('gl+')

        if settings is None:
            settings = EngineConfig()

        self.conf = settings

    def close(self):
        GLBuffer.GLOBAL_MAP.unregister_all()
