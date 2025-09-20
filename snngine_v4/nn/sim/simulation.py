from __future__ import annotations


from typing import Callable, TYPE_CHECKING

from snngine_v4.construction.engine_element_config import \
    EngineElementConfig
from snngine_v4.construction.engine_element import EngineElement
from snngine_v4.nn.sim.gpu_plots import PlotElement


if TYPE_CHECKING:
    from snngine_v4.nn.sim.simulator import Simulator
    from snngine_v4.nn.spnn import SpatialNetwork
    from snngine_v4.nn.spnn_reservoir import NetworkReservoir


class SimulationModel(EngineElementConfig):

    # Fired: SeriesF32
    # last_Fired: SeriesI32
    # Firing_times: DataFrameF32
    # Firing_idcs: DataFrameI32
    # Firing_counts: DataFrameI32
    #
    # @classmethod
    # def reset_model(cls, sim_model: dict | SimulationModel, n_neurons,
    #                 d):
    #     if isinstance(sim_model, dict):
    #         sim_model = SimulationModel(**sim_model)
    #
    #     sim_model.reset_array(sim_model.Fired, n_indices=n_neurons)
    #     sim_model.reset_array(sim_model.last_Fired, n_indices=n_neurons)
    #     sim_model.last_Fired.data -=

    pass


class Simulation(EngineElement):
    parent_element: Callable[..., Simulator]

    def __init__(self,
                 element: NetworkReservoir,
                 buffer_size_factor=15,
                 **kwargs) -> None:
        super().__init__(**kwargs)

        spnn: SpatialNetwork = element.parent_element()
        n_neurons = element.config.N
        n_groups = element.config.G
        n_delays = element.config.D
        t_sim_duration = spnn.config.simulator.T

        self.Fired = self.zeros_f32(n_neurons)
        self.last_Fired = self.zeros_i32(n_neurons) - n_delays
        self.Firing_times = self.zeros_f32((buffer_size_factor, n_neurons))
        self.Firing_idcs = self.zeros_i32((buffer_size_factor, n_neurons))
        self.Firing_counts = self.zeros_i32((1, t_sim_duration, n_neurons))

        simulator: Simulator = spnn.simulator
        group_firings_plot = simulator.plots[
            simulator.plots.config.group_firings_plot]

        self.G_firing_count_hist = self.zeros_i32((
            group_firings_plot.config.size_x,
            n_groups))

        self.backend = self._make_simulator_backend(
            element=element,
        )

    def _make_simulator_backend(self, element: NetworkReservoir):

        if self.b_cuda_backend_available is False:
            return None

        # noinspection PyUnresolvedReferences
        from snngine_v4.nn.cuda_backend import snn_simulation_gpu

        spnn: SpatialNetwork = element.parent_element()
        simulator: Simulator = spnn.simulator
        neuron_states = element.neuron_states
        synapses = element.synapses
        chemicals = element.chemicals

        N = element.config.N
        G = element.config.G
        S = element.config.S
        D = element.config.D
        T = spnn.config.simulator.T

        # volt_plot = self.plots.voltage_plot
        volt_plot: PlotElement = simulator.voltage_plot
        firings_scatter_plot: PlotElement = simulator.firings_scatter_plot

        # volt_plot.pos_vbo_gl.gl_buffer.map()
        # firings_scatter_plot.pos_vbo_gl.gl_buffer.map()

        # return
        sim = snn_simulation_gpu.SnnSimulation(
            N=N, G=G, S=S, D=D,
            T=T,
            n_voltage_plots=volt_plot.config.n_plots,
            voltage_plot_length=volt_plot.config.size_x,
            voltage_plot_data=volt_plot.pos_vbo.data_ptr(),
            voltage_plot_map=volt_plot.map.data_ptr(),
            n_scatter_plots=firings_scatter_plot.config.n_plots,
            scatter_plot_length=firings_scatter_plot.config.size_x,
            scatter_plot_data=firings_scatter_plot.pos_vbo.data_ptr(),
            scatter_plot_map=firings_scatter_plot.map.data_ptr(),

            curand_states_p=element.curand_states,
            N_pos=element.pos_vbo.data_ptr(),
            # N_G=self.N_G.data_ptr(),
            G_group_delay_counts=element.L_Group_delay_counts.data_ptr(),
            G_flags=element.L_Group_flags.data_ptr(),
            G_props=element.L_Group_properties.data_ptr(),

            N_rep=synapses.N_rep.data_ptr(),
            N_rep_buffer=synapses.N_rep_buffer.data_ptr(),
            N_rep_pre_synaptic=synapses.rep_pre_synaptic.data_ptr(),
            N_rep_pre_synaptic_idcs=synapses.rep_pre_synaptic_idcs
            .data_ptr(),
            N_rep_pre_synaptic_counts=synapses
            .rep_pre_synaptic_counts.data_ptr(),
            N_delays=synapses.N_delays.data_ptr(),

            N_flags=neuron_states.N_flags.data_ptr(),
            N_states=neuron_states.N_props.data_ptr(),

            N_weights=synapses.N_weights.data_ptr(),

            fired=self.Fired.data_ptr(),
            last_fired=self.last_Fired.data_ptr(),
            firing_times=self.Firing_times.data_ptr(),
            firing_idcs=self.Firing_idcs.data_ptr(),
            firing_counts=self.Firing_counts.data_ptr(),

            G_firing_count_hist=self.G_firing_count_hist.data_ptr(),
            G_stdp_config0=element.G2G_stdp_config0.data_ptr(),
            G_stdp_config1=element.G2G_stdp_config1.data_ptr(),
            G_avg_weight_inh=element.G2G_avg_weight_inh.data_ptr(),
            G_avg_weight_exc=element.G2G_avg_weight_exc.data_ptr(),
            G_syn_count_inh=element.G2G_syn_count_inh.data_ptr(),
            G_syn_count_exc=element.G2G_syn_count_exc.data_ptr(),

            L_winner_take_all_map=synapses.pseudo_tensor_i32.data_ptr(),
            max_n_winner_take_all_layers=1,
            max_winner_take_all_layer_size=1,

            C_old=chemicals.C0.c_current.data_ptr(),
            C_new=chemicals.C0.c_next.data_ptr(),
            C_source=chemicals.C0.c_source.data_ptr(),
            # debug_neuron_id=-1,
            chem_grid_w=chemicals.C0.config.shape.width,
            chem_grid_h=chemicals.C0.config.shape.height,
            chem_grid_d=chemicals.C0.config.shape.depth,
            chem_k_val=chemicals.C0.config.k_val,
            chem_depreciation=chemicals.C0.config.depreciation
        )

        return sim
