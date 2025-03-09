import os

from snngine_v4.nn.construction.nn_builder import NetworkBuilder
from snngine_v4.nn.spnn import SpatialNetwork
from snngine_v4.snngine_config import EngineConfig
from snngine_v4.visualization.cuda.gl_interop.gl_buffer import GLBufferMap

from snngine_v4.visualization.scenes.main_network_scene import \
    EngineSceneCanvas
from snngine_v4.visualization.scenes.scene_manager import SceneManager


class SNNgine:

    def __init__(self, settings: EngineConfig | str = None):

        if settings is None:
            settings = EngineConfig()
        self.conf = settings

        self.init_core()

        # noinspection PyTypeHints
        self.scene_manager: dict[str, EngineSceneCanvas] | SceneManager = (
            SceneManager(self.conf.scenes))

        self.network_manager = NetworkBuilder(
            container_model=self.conf.current)

    def init_core(self):

        if 'CUDA_DEVICE' in os.environ:
            import torch
            cuda_device = int(os.environ['CUDA_DEVICE'])
            if (cuda_device + 1) > torch.cuda.device_count():
                os.environ['CUDA_DEVICE'] = '0'

        if self.conf.devices.b_use_cuda:
            try:
                # noinspection PyUnresolvedReferences
                from pycuda import autoinit
            except (ModuleNotFoundError, RuntimeError) as error:
                if self.conf.devices.cuda.b_require_pycuda:
                    raise error
                pass

            # import cupy
            import torch
            from numba import cuda
            # from rmm.allocators.cupy import rmm_cupy_allocator
            # from rmm.allocators.torch import rmm_torch_allocator
            # from rmm.allocators.numba import RMMNumbaManager

            # cupy.cuda.set_allocator(rmm_cupy_allocator)
            # torch.cuda.change_current_allocator(rmm_torch_allocator)
            # cuda.set_memory_manager(RMMNumbaManager)

        from vispy import gloo
        gloo.gl.use_gl(self.conf.devices.opengl.gloo_target)

    def build_network(self):
        device = self.conf.construction.network.device
        if isinstance(device, int):
            import torch
            if (device + 1) > torch.cuda.device_count():
                self.conf.construction.network.device = 0

        self.network_manager.build(self.conf.construction)
        self.conf.current = self.network_manager.container_model

        # visual_models = {
        #     # 'grid': self.conf.current.network.grid,
        #     'grid': self.conf.current.network.elements[1].grid,
        # }
        #
        # # visual_models1 = {}
        # if self.conf.current.network.elements:
        #     for i, el in enumerate(self.conf.current.network.elements):
        #         if isinstance(el, NetworkReservoirConfig):
        #             visual_models[f"el{i}"] = el

        network: SpatialNetwork = self.network_manager[
            self.conf.current.network]

        # reservoir1: NetworkReservoir = network[
        #     self.conf.current.network.elements[1]]

        visual_models = [
            # self.conf.current.network.elements[1].grid,
            self.conf.current.network.elements[1],
        ]

        new_visuals = self.scene_manager.build_visuals(
            visuals=visual_models,
            scene=self.conf.scenes.main,
        )
        new_visuals = self.scene_manager.build_visuals(
            visuals=[self.conf.current.network.elements[1].grid],
            scene=self.conf.scenes.main,
            grid=network[self.conf.current.network.elements[1].grid]
        )

        plot_configs = list(
            self.conf.current.network.simulator.plots.plot_config_values())

        new_visuals0 = self.scene_manager.build_visuals(
            visuals=plot_configs,
            scene=self.conf.scenes.main,
        )

        lines = new_visuals0[plot_configs[0]].built
        self.scene_manager[self.conf.scenes.main]

        return new_visuals

    def close(self):
        GLBufferMap().unregister_all()
