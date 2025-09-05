import os
from functools import cached_property

from pydantic import BaseModel

from snngine_v4.nn.construction.nn_builder import NetworkBuilder
from snngine_v4.nn.spnn import SpatialNetwork
from snngine_v4.snngine_config import EngineConfig
from snngine_v4.visualization.config_models.plotting.multi_line_plot import \
    MultiPlotConfig

try:
    from snngine_v4.visualization.cuda.gl_interop.gl_buffer import GLBufferMap
except ModuleNotFoundError:
    GLBufferMap = None

from snngine_v4.visualization.scenes.main_network_scene import \
    EngineSceneCanvas
from snngine_v4.visualization.scenes.scene_manager import SceneManager


class SNNgine:

    def __init__(self, settings: EngineConfig | str = None, app=None):

        if settings is None:
            settings = EngineConfig()
        self.conf = settings

        self.init_core()

        # self.scene_manager: dict[str | BaseModel, EngineSceneCanvas]
        # | SceneManager = SceneManager(self.conf.scenes)
        self.scene_manager: SceneManager = SceneManager(
            self.conf.scenes, app=app)

        self.network_manager = NetworkBuilder(
            container_model=self.conf.current)


    @cached_property
    def b_pycuda_available(self):
        try:
            import pycuda
            return True
        except ModuleNotFoundError:
            return False

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
            if torch.cuda.is_available():
                if (device + 1) > torch.cuda.device_count():
                    self.conf.construction.network.device = 0
            else:
                self.conf.construction.network.device = 'cpu'

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

        # reservoir1: NetworkReservoir = network[
        #     self.conf.current.network.elements[1]]
        network_elt_config = self.conf.current.network.elements[0]

        visual_models = [
            # self.conf.current.network.elements[1].grid,
            network_elt_config
        ]

        new_visuals = self.scene_manager.build_visuals(
            visuals=visual_models,
            scene=self.conf.scenes.main,
        )
        new_visuals = self.scene_manager.build_visuals(
            visuals=[network_elt_config.grid],
            scene=self.conf.scenes.main,
            grid=self.network[network_elt_config.grid]
        )

        plot_visual0 = self.scene_manager.build_visuals(
            visuals=[self.conf.current.network.simulator.plots
                     .voltage_plot],
            scene=self.conf.scenes.multiplot_voltage,
        )

        plot_visual1 = self.scene_manager.build_visuals(
            visuals=[self.conf.current.network.simulator.plots
                     .current_plot],
            scene=self.conf.scenes.multiplot_current,
        )
        return new_visuals

    def post_connect_network_init(self):
        self.network.configure_simulator(element=0)

    @property
    def network(self) -> SpatialNetwork:
        return self.network_manager[
            self.conf.current.network]

    def close(self):
        if GLBufferMap:
            GLBufferMap().unregister_all()
