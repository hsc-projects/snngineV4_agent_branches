import os
from functools import cached_property


from snngine_v4.construction.nn_builder import NetworkBuilder
from snngine_v4.geometry.volume import VolumeShapeHDW
from snngine_v4.gui.parameter_tree.engine_parameter_tree import \
    EngineParameterTree
from snngine_v4.gui.parameter_tree.tensor_connector import TensorConnector
from snngine_v4.gui.parameter_tree.vispy_connector import VispyConnector
from snngine_v4.gui.selector_tree.engine_selector_tree import EngineSelectorTree
from snngine_v4.nn.spnn import SpatialNetwork
from snngine_v4.snngine_config import EngineConfig

try:
    from snngine_v4.visualization.cuda.gl_interop.gl_buffer import GLBufferMap
except ModuleNotFoundError:
    GLBufferMap = None

from snngine_v4.visualization.scenes.scene_manager import SceneManager


class SNNgine:

    def __init__(self, settings: EngineConfig | str = None, app=None):

        if settings is None:
            # noinspection PyArgumentList
            settings = EngineConfig()
        self.conf = settings

        self.init_core()

        self.scene_manager: SceneManager = SceneManager(
            self.conf.scenes, app=app)

        self.network_manager = NetworkBuilder(
            container_model=self.conf.built)

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

    def build(self, scene_tree: EngineParameterTree,
              network_tree: EngineParameterTree,
              selector_tree: EngineSelectorTree):

        self.main_scene.set_current()
        self.conf.built = self.build_network()
        network_tree.clear()
        network_tree.set_parameters_from_model(
            model=self.constructed_model,
            readonly=True,
            showTop=False)
        self.build_visuals()
        self.connect_visuals(scene_tree, network_tree)
        if self.b_pycuda_available:
            self.network.cuda_opengl_map = (
                self.build_cuda_gl_tensors(network_tree))
        self.connect_tensors(network_tree, )

        self.main_scene.set_current()

        self.network.configure_simulator(element=0)

        if selector_tree is not None:
            selector_tree.connect_engine(self)

    def build_network(self):
        device = self.conf.template.network.device
        if isinstance(device, int):
            import torch
            if torch.cuda.is_available():
                if (device + 1) > torch.cuda.device_count():
                    self.conf.template.network.device = 0
            else:
                self.conf.template.network.device = 'cpu'

        self.network_manager.build(self.conf.template)
        return self.network_manager.container_model

    def build_cuda_gl_tensors(self, network_tree):
        from snngine_v4.gui.parameter_tree.cuda_connector import (
            CudaVispyConnector)
        model2buffers = CudaVispyConnector.cls_connect_tree(
            tree=network_tree, scene_manager=self.scene_manager,
            device=self.constructed_model.network.device)
        return model2buffers

    def build_visuals(self):

        elt_config0 = self.conf.built.network.elements[0]
        new_visuals = []

        neurons_visual = self.scene_manager.build_visuals(
            visuals=[elt_config0],
            scene=self.conf.scenes.main)
        new_visuals.append(neurons_visual)

        grid_visual = self.scene_manager.build_visuals(
            visuals=[elt_config0.grid],
            scene=self.conf.scenes.main,
            grid=self.network.grid)
        new_visuals.append(grid_visual)

        plot_visual0 = self.scene_manager.build_visuals(
            visuals=[self.conf.built.network.simulator.plots
                     .voltage_plot],
            scene=self.conf.scenes.multiplot_voltage)
        new_visuals.append(plot_visual0)

        plot_visual1 = self.scene_manager.build_visuals(
            visuals=[self.conf.built.network.simulator.plots
                     .firings_scatter_plot],
            scene=self.conf.scenes.multiplot_firings)
        new_visuals.append(plot_visual1)

        c0_config = elt_config0.chemicals.C0
        chem_data = self.network[c0_config].init_data_cpu
        ref_shape = VolumeShapeHDW.hdw_to_wdh(c0_config.shape.data)
        elt_shape = elt_config0.grid.shape
        initial_scale = (elt_shape[0] / (ref_shape[0]),
                         elt_shape[1] / (ref_shape[1]),
                         elt_shape[2] / (ref_shape[2]))

        chem_visual0 = self.scene_manager.build_visuals(
            visuals=[elt_config0.chemicals.C0],
            scene=self.conf.scenes.main,
            vol=chem_data,
            initial_scale=initial_scale,
        )
        new_visuals.append(chem_visual0)
        return new_visuals

    def connect_tensors(self, network_tree):
        model2tensors = TensorConnector.cls_connect_tree(
            tree=network_tree,
            network_manager=self.network_manager,)
        return model2tensors

    def connect_visuals(self, scene_tree: EngineParameterTree,
                        network_tree: EngineParameterTree):
        VispyConnector.cls_connect_tree(
            tree=scene_tree, scene_manager=self.scene_manager)

        VispyConnector.cls_connect_tree(
            tree=network_tree, scene_manager=self.scene_manager)

    @property
    def constructed_model(self):
        if self.conf.built is not self.network_manager.container_model:
            raise RuntimeError()
        return self.conf.built

    @cached_property
    def main_scene(self):
        return self.scene_manager[self.conf.scenes.main]

    @property
    def network(self) -> SpatialNetwork:
        return self.network_manager[
            self.conf.built.network]

    def run_sim(self, n_steps):
        simulator = self.network.simulator

        if n_steps is None:
            n_steps = simulator.config.T
        else:
            n_steps = min(n_steps, simulator.config.T)
        from snngine_v4.nn.spnn_reservoir import NetworkReservoir
        element: NetworkReservoir = (
            self.network.get_network_element(0))

        sim = simulator.simulations[element].backend

        voltage_plot_scene = self.scene_manager[
            self.conf.scenes.multiplot_voltage]
        firing_plot_scene = self.scene_manager[
            self.conf.scenes.multiplot_firings]

        for i in range(n_steps):
            print(element.neuron_states.N_props.gpu_values[2, :10])
            print(simulator.voltage_plot.pos_vbo[1:20:2])
            sim.update(False, True)
            voltage_plot_scene.update()
            firing_plot_scene.update()

    def close(self):
        if GLBufferMap:
            GLBufferMap().unregister_all()

    # def post_connect_network_init(self):

