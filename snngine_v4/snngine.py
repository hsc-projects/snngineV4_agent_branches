from snngine_v4.config.engine_config_model import EngineConfig


class SNNgine:
    def __init__(self, settings: EngineConfig | str = None):

        # noinspection PyUnresolvedReferences
        from pycuda import autoinit
        from vispy import gloo

        if settings is None:
            settings = EngineConfig()

        self.conf = settings
        gloo.gl.use_gl(self.conf.open_gl.gloo_target)

    def close(self):
        from snngine_v4.visualization.cuda.gl_interop.gl_buffer import GLBuffer
        GLBuffer.GLOBAL_MAP.unregister_all()
