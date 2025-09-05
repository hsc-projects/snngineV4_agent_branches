from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING

from snngine_v4.nn.construction.config_models.engine_element_config import \
    EngineElementConfig
from snngine_v4.nn.construction.engine_element import EngineElement
from snngine_v4.nn.sim.gpu_plots import (
    CudaBackendPlotConfig,
    CudaBackendPlotTensors,
)

from snngine_v4.nn.spnn_reservoir import NetworkReservoir
from snngine_v4.utils.containers.mappings import (
    Object2ObjectMap,
)


if TYPE_CHECKING:
    from snngine_v4.nn.spnn import GetNetworkElementType


class SimulatorOptions(EngineElementConfig):
    """

    """

    T: int = 1000
    plots: CudaBackendPlotConfig


class Simulator(EngineElement):
    """

    """

    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        CudaBackendPlotConfig: CudaBackendPlotTensors,
    }

    config_model: SimulatorOptions

    plots: CudaBackendPlotTensors

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.backends = Object2ObjectMap()

    def _make_simulator_backend(self, element: NetworkReservoir):
        if self.b_cuda_backend_available is False:
            return None

        # noinspection PyUnresolvedReferences
        from snngine_v4.nn.cuda_backend import snn_simulation_gpu

        spnn = self.parent_element()
        N = element.config_model.N
        G = element.config_model.G
        S = element.config_model.S
        D = element.config_model.D

        volt_plot = self.plots.voltage_plot
        volt_plot = self.plots[self.plots.config_model.voltage_plot]

        volt_plot.pos_vbo()
        return
        sim = snn_simulation_gpu.SnnSimulation(
            N=N, G=G, S=S, D=D,
            T=spnn.config_model.simulator.T,
            n_voltage_plots=volt_plot.config_model.n_plots,
            voltage_plot_length=volt_plot.config_model.size_x,
            voltage_plot_data=volt_plot.pos_vbo().te.data_ptr(),
            voltage_plot_map=self._voltage_multiplot.map.data_ptr(),
            n_scatter_plots=plotting_config.firing_scatter_plot.n_plots,
            scatter_plot_length=plotting_config.firings_x_length,
            scatter_plot_data=self._firing_scatter_plot.vbo_array.data_ptr(),
            scatter_plot_map=self._firing_scatter_plot.map.data_ptr(),
            curand_states_p=self.neurons.curand_states,
            N_pos=self.neurons.N_visual.gpu_array.data_ptr(),
            # N_G=self.N_G.data_ptr(),
            G_group_delay_counts=self.neurons.G_group_delay_counts.data_ptr(),
            G_flags=self.neurons.G_flags.data_ptr(),
            G_props=self.neurons.G_props.data_ptr(),
            N_rep=self.synapse_arrays.N_rep.data_ptr(),
            N_rep_buffer=self.synapse_arrays.N_rep_buffer.data_ptr(),
            N_rep_pre_synaptic=self.synapse_arrays.N_rep_pre_synaptic
            .data_ptr(),
            N_rep_pre_synaptic_idcs=self.synapse_arrays.N_rep_pre_synaptic_idcs
            .data_ptr(),
            N_rep_pre_synaptic_counts=self.synapse_arrays
            .N_rep_pre_synaptic_counts.data_ptr(),
            N_delays=self.synapse_arrays.N_delays.data_ptr(),
            N_flags=self.neurons.N_flags.data_ptr(),
            N_states=self.neurons.N_states.data_ptr(),
            N_weights=self.synapse_arrays.N_weights.data_ptr(),
            fired=self.Fired.data_ptr(),
            last_fired=self.last_Fired.data_ptr(),
            firing_times=self.Firing_times.data_ptr(),
            firing_idcs=self.Firing_idcs.data_ptr(),
            firing_counts=self.Firing_counts.data_ptr(),
            G_firing_count_hist=self.G_firing_count_hist.data_ptr(),
            G_stdp_config0=self.neurons.G2G_info.G_stdp_configs[0].data_ptr(),
            G_stdp_config1=self.neurons.G2G_info.G_stdp_configs[1].data_ptr(),
            G_avg_weight_inh=self.neurons.G2G_info.G_avg_weight_inh.data_ptr(),
            G_avg_weight_exc=self.neurons.G2G_info.G_avg_weight_exc.data_ptr(),
            G_syn_count_inh=self.neurons.G2G_info.G_syn_count_inh.data_ptr(),
            G_syn_count_exc=self.neurons.G2G_info.G_syn_count_exc.data_ptr(),
            L_winner_take_all_map=self.synapse_arrays.L_winner_take_all_map
            .data_ptr(),
            max_n_winner_take_all_layers=self._config.layering
            .max_n_winner_take_all_layers,
            max_winner_take_all_layer_size=self._config.layering
            .max_winner_take_all_layer_size,
            C_old=self.chemical_concentrations.c0.state.c_current.data_ptr(),
            C_new=self.chemical_concentrations.c0.state.c_next.data_ptr(),
            C_source=self.chemical_concentrations.c0.state.c_source.data_ptr(),
            # debug_neuron_id=-1,
            chem_grid_w=self.chemical_concentrations.c0.width,
            chem_grid_h=self.chemical_concentrations.c0.height,
            chem_grid_d=self.chemical_concentrations.c0.depth,
            chem_k_val=self.chemical_concentrations.c0.k_val,
            chem_depreciation=self.chemical_concentrations.c0.depreciation
        )
        return sim

    def init_simulator_backend(self, element: GetNetworkElementType):
        element = self.root_element.get_network_element(element)
        self.backends[element] = self._make_simulator_backend(element=element)

    def run_sim(self, element):
        element = self.root_element.get_network_element(element)

