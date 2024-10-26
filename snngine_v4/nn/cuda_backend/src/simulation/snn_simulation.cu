#include "simulation/snn_simulation.cuh"
//#define BLOCK_SIZE 8

#define VISPY_MARKER_STRIDE 14

__global__ void update_N_state_(
	const int N,
	const int G,
	const float t,
	curandState* randstate,
	float* N_pos,
	const int* G_flags,
	const float* G_props,
	const int* N_flags,
	float* N_states,
	float* fired,
	int* last_fired,
	int* G_firing_count_hist,
	const int t_mod_scatter_plot_length,
	const int row_sensory_input_type = 0,
	const int row_b_thalamic_input = 1,
	const int row_b_sensory_input = 3,
	const int row_b_monitor_group_firing_count = 6,
	const int row_thalamic_inh_input_current = 0,
	const int row_thalamic_exc_input_current = 1,
	const int row_sensory_input_current0 = 2,
	const int row_sensory_input_current1 = 3,
	const int N_flag_row_b_sensory_input = 0,
	const int N_flag_row_model = 3,
	bool b_monitor_group_firing_counts = true,
	const int N_flags_row_type = 1,
	const int N_flags_row_group = 2
)
{
	const int n = blockIdx.x * blockDim.x + threadIdx.x;

	if (n < N)
	{
		curandState local_state = randstate[n];
		fired[n] = 0.f;
		N_pos[n * 14 + 10] = .3f;

		const int ntype = N_flags[n + N_flags_row_type * N] - 1;
		const int src_G = N_flags[n + N_flags_row_group * N];

		float pt = N_states[n];
		float u = N_states[n + N];
		float v = N_states[n + 2 * N];
		const float a = N_states[n + 3 * N];
		const float b = N_states[n + 4 * N];
		const float c = N_states[n + 5 * N];
		const float d = N_states[n + 6 * N];
		float i = N_states[n + 7 * N];

		// printf("\n (%d) (src_G=%d, pt=%f, u=%f, v=%f, a=%f, b=%f, c=%f, d=%f, i=%f)",
		// n, src_G, pt, u, v, a, b, c, d, i);

		if ((G_flags[src_G + row_b_thalamic_input * G] == 1)
            && (pt > 0.f)
            && (curand_uniform(&local_state) < pt))
		{
			const float rt = curand_uniform(&local_state);
			i += (G_props[src_G + row_thalamic_exc_input_current * G] * ntype
				+ G_props[src_G + row_thalamic_inh_input_current * G] * (1 - ntype)) * rt;
		}

		if (N_flags[n + N_flag_row_b_sensory_input * N] == 1)
		{
			const int input_type = G_flags[src_G + row_sensory_input_type * G];
			if (input_type >= 0){
				i += (G_props[src_G + row_sensory_input_current1 * G] * input_type
				      + G_props[src_G + row_sensory_input_current0 * G] * (1 - input_type));
			}
		}

		bool b_fired = false;
		if (N_flags[n + N_flag_row_model * N] == 0){
			if (v > 30.f)
			{
				v = c;
				u = u + d;
				b_fired = true;
			}
			v = v + 0.5f * (0.04f * v * v + 5 * v + 140 - u + i);
			v = v + 0.5f * (0.04f * v * v + 5 * v + 140 - u + i);
			u = u + a * (b * v - u);

		}

		else {
			float v_prev = N_states[n + 9 * N];
			N_states[n + 9 * N] = v;

			float x_3_50 = 50 * (b * i - u - a);

			u = u - c * (u + ((1 - b) * (i)));

			if (v < 0){
				v = ((2500.f + 150.f * v) / (50.f - v)) + x_3_50;
			} else if ((0 <= v) && (v < (50 + x_3_50)) && (v_prev < 0)){
				v = 50 + x_3_50;
			} else {
				v = -50;
				u += d * c;
				b_fired = true;
			}
		}

		if (b_fired){
			fired[n] = t;
			last_fired[n] = __float2int_rn(t);
			N_pos[n * VISPY_MARKER_STRIDE + 10] = 1.f;

			if ((b_monitor_group_firing_counts) && (ntype == 1) &&
				(G_flags[src_G + row_b_monitor_group_firing_count * G] == 1)){

				atomicAdd(&G_firing_count_hist[src_G + t_mod_scatter_plot_length * G], 1);

				// printf("\nG_firing_count_hist[%d]=%d", src_G + t_mod_scatter_plot_length * G,
				// 	G_firing_count_hist[src_G + t_mod_scatter_plot_length * G]);
			}
		}



		N_states[n + N] = u;
		N_states[n + 2 * N] = v;
		// debug_i[n]  = i;
		// debug_v[n]  = v;
		N_states[n + 7 * N] = 0.f;
		N_states[n + 8 * N] = i;

		randstate[n] = local_state;
	}
}


__global__ void update_voltage_plot_(
	const int* voltage_plot_map,
	const float* N_states,
	float* voltage_plot_data,
	// const int min_idx,
	// const int max_idx,
	const int plot_length,
	const int t,
	const int N,
	const int n_voltage_plots
)
{
	const int plot_idx = blockIdx.x * blockDim.x + threadIdx.x;
	if (plot_idx < n_voltage_plots)
	{
		const int n = voltage_plot_map[plot_idx];
		if (n >= 0){
			const int start_idx = plot_idx * plot_length * 2;
			voltage_plot_data[start_idx + 2 * t + 1] = (
				N_states[n + 2 * N] / 200.f + __int2float_rn(plot_idx) + 0.5 );

		}
//        if (n <= 10) {
//            const int start_idx = plot_idx * plot_length * 2;
//            printf("%f, ", voltage_plot_data[start_idx + 2 * t + 1] );
//        }
	}
}


__global__ void update_scatter_plot_(
	const int* scatter_plot_map,
	const float* fired,
	float* scatter_plot_data,
	// const int min_idx,
	// const int max_idx,
	const int plot_length,
	const int t,
	const int N,
	const int n_scatter_plots
)
{
	const int plot_idx = blockIdx.x * blockDim.x + threadIdx.x;
	if (plot_idx < n_scatter_plots)
	{
		const int n = scatter_plot_map[plot_idx];
		if (n >= 0){
			const int start_idx = plot_idx * plot_length * VISPY_MARKER_STRIDE;
			// scatter_plot_data[start_idx + VISPY_MARKER_STRIDE * t + 3] = 0.;
			// scatter_plot_data[start_idx + VISPY_MARKER_STRIDE * t + 4] = 0.;
			// scatter_plot_data[start_idx + VISPY_MARKER_STRIDE * t + 5] = 0.;
			scatter_plot_data[start_idx + VISPY_MARKER_STRIDE * t + 10] = fired[n];

			// scatter_plot_data[start_idx + VISPY_MARKER_STRIDE * t + 5] = (
				// 999.
				// N_states[n + 2 * N] / 2. + __int2float_rn(plot_idx) * 100 + 50
			// );
		}

	}
}


__global__ void update_chemical_concentrations_(
	float *C_old, float *C_new, const float *C_source,
	int grid_w, int grid_h, int grid_d,
	float k_val = 0.75f,
	float depreciation = 0.1f)
{

	// original source: https://github.com/AdityaNair111/2D-3D-Heat-Flow-CUDA/blob/master/src/heat2D3D.cu
	//
	// C_new = C_old + sum[n in neighbors] k_val * (T_n - C_old) or C_source - depreciation


	const int chem_block_size = 8;
	__shared__ float Mat[chem_block_size + 2][chem_block_size + 2][chem_block_size + 2];

	const int j = blockIdx.x * chem_block_size + threadIdx.x; // witdth
	const int i = blockIdx.y * chem_block_size + threadIdx.y; // height
	const int k = blockIdx.z * chem_block_size + threadIdx.z; // depth


	if ((i <= grid_h) && (j <= grid_w) && (k <= grid_d))
	{
		const int grid_wd = grid_w * grid_d;
		const int idx = i * grid_wd + j * grid_d + k;

		const int j_mat = threadIdx.x + 1;
		const int i_mat = threadIdx.y + 1;
		const int k_mat = threadIdx.z + 1;

//        printf("ccc");

		// length <= BLOCK_SIZE
		const int length_j = (blockIdx.x == (int)(grid_w / chem_block_size)) ? (grid_w % chem_block_size) : chem_block_size;
		const int length_i = (blockIdx.y == (int)(grid_h / chem_block_size)) ? (grid_h % chem_block_size) : chem_block_size;
		const int length_k = (blockIdx.z == (int)(grid_d / chem_block_size)) ? (grid_d % chem_block_size) : chem_block_size;

		const float c_old = C_old[idx];

		Mat[i_mat][j_mat][k_mat] = c_old;  // fill Mat[1: BLOCK_SIZE + 2][1: BLOCK_SIZE + 2][1: BLOCK_SIZE + 2] with C_old[i, j, k]

		if (j_mat == 1)  // sum_block_border
		{
			// Mat[][0 or block-end][] "outside" C_old => fill Mat[][0 or block-end][] with C_old[, . +/- 1, ] (or else C_old[, .,]).
			Mat[i_mat][0           ][k_mat] = (j == 0)                 ? c_old                                : C_old[idx - grid_d];  /// check j or j-1
			Mat[i_mat][length_j + 1][k_mat] = (j >= grid_w - length_j) ? C_old[idx + (length_j - 1) * grid_d] : C_old[idx + length_j * grid_d];
		}

		if (i_mat == 1)
		{
			Mat[0           ][j_mat][k_mat] = (i == 0)                 ? c_old      							       : C_old[idx - grid_wd];  /// check j or j-1
			Mat[1 + length_i][j_mat][k_mat] = (i >= grid_h - length_i) ? C_old[idx + (length_i - 1) * grid_wd] : C_old[idx + length_i * grid_wd];
		}

		if (k_mat == 1)
		{
			Mat[i_mat][j_mat][0           ] = (k < 1)                  ? c_old      			   : C_old[idx - 1];  /// check j or j-1
			Mat[i_mat][j_mat][1 + length_k] = (k >= grid_d - length_k) ? C_old[idx + length_k - 1] : C_old[idx + length_k];
		}

		__syncthreads();

		if ((i < grid_h) && (j < grid_w) && (k < grid_d))
		{

			//const float t_source = C_source[idx];
			float c_new = C_source[idx];

			if (!(c_new > 0.f)){
				float sum_mat = (
					Mat[i_mat + 1][j_mat	  ][k_mat    ]
					+ Mat[i_mat - 1][j_mat	  ][k_mat    ]
					+ Mat[i_mat    ][j_mat + 1][k_mat    ]
					+ Mat[i_mat    ][j_mat - 1][k_mat    ]
					+ Mat[i_mat	   ][j_mat 	  ][k_mat - 1]
					+ Mat[i_mat	   ][j_mat	  ][k_mat + 1]
				);

				c_new = (fminf(2000.0f, fmaxf(0.0f, c_old + k_val * (sum_mat - 6 * c_old) - depreciation)));

				// if (c_old > 1500){
				// 	int max_ = fmaxf(0.0f, + k_val * (sum_mat - 6 * c_old) - depreciation);
				// 	printf("\n %.2f = %.2f + %.2f * (%.2f - %.2f) - %.2f; max = %.2f, min = %.2f  ",
				// 		   c_new, c_old, k_val, sum_mat, 6 * c_old, depreciation, max_, fminf(2000.0f, max_));
				// }
			}
			C_new[idx] = c_new;
			C_old[idx] = c_new;

		}
	}
}


SnnSimulation::SnnSimulation(
    const int N_,
    const int G_,
    const int S_,
    const int D_,
	const int T_,

	const int n_voltage_plots_,
    const int voltage_plot_length_,
	float* voltage_plot_data_,
	int* voltage_plot_map_,

	const int n_scatter_plots_,
    const int scatter_plot_length_,
	float* scatter_plot_data_,
	int* scatter_plot_map_,

	curandState* rand_states_,
	float* N_pos_,
	int* G_group_delay_counts_,
    int* G_flags_,
    float* G_props_,
    int* N_rep_,
    int* N_rep_buffer_,
    int* N_rep_pre_synaptic_,
    int* N_rep_pre_synaptic_idcs_,
    int* N_rep_pre_synaptic_counts_,
    int* N_delays_,
    int* N_flags_,
    float* N_states_,
	float* N_weights_,
	float* fired_,
	int* last_fired_,
	float* firing_times_,
	int* firing_idcs_,
	int* firing_counts_,
	int* G_firing_count_hist_,
	int* G_stdp_config0_,
	int* G_stdp_config1_,
	float* G_avg_weight_inh_,
	float* G_avg_weight_exc_,
	int* G_syn_count_inh_,
	int* G_syn_count_exc_,

	int* L_winner_take_all_map_,
    int max_n_winner_take_all_layers_,
    int max_winner_take_all_layer_size_,

	float* C_old_,
	float* C_new_,
	float* C_source_,

	int chem_grid_w_,
	int chem_grid_h_,
	int chem_grid_d_,
	float chem_k_val_,
	float chem_depreciation_
){

	N = N_;
	G = G_;
	S = S_;
	D = D_;
	T = T_;

	n_voltage_plots = n_voltage_plots_;
	voltage_plot_length = voltage_plot_length_;
	voltage_plot_data = voltage_plot_data_;
	voltage_plot_map = voltage_plot_map_;

	n_scatter_plots = n_scatter_plots_;
	scatter_plot_length = scatter_plot_length_;
	scatter_plot_data = scatter_plot_data_;
	scatter_plot_map = scatter_plot_map_;

	rand_states = rand_states_;

	N_pos = N_pos_;
	G_group_delay_counts = G_group_delay_counts_;
    G_flags = G_flags_;
    G_props = G_props_;
    N_rep = N_rep_;

	N_rep_buffer = N_rep_buffer_;
    N_rep_pre_synaptic = N_rep_pre_synaptic_;
    N_rep_pre_synaptic_idcs = N_rep_pre_synaptic_idcs_;
    N_rep_pre_synaptic_counts = N_rep_pre_synaptic_counts_;

    N_delays = N_delays_;

	N_flags = N_flags_;
    N_states = N_states_;

	N_weights = N_weights_;

	fired = fired_;
	last_fired = last_fired_;

	firing_times = firing_times_;
	firing_idcs = firing_idcs_;
	firing_counts = firing_counts_;
	G_firing_count_hist = G_firing_count_hist_;

	firing_times_write = firing_times;
	firing_times_read = firing_times;

	firing_idcs_write = firing_idcs;
	firing_idcs_read = firing_idcs;

	firing_counts_write = firing_counts;

	G_stdp_config0 = G_stdp_config0_;
	G_stdp_config_current = G_stdp_config0;
	G_stdp_config1 = G_stdp_config1_;

	G_avg_weight_inh = G_avg_weight_inh_;
	G_avg_weight_exc = G_avg_weight_exc_;
	G_syn_count_inh = G_syn_count_inh_;
	G_syn_count_exc = G_syn_count_exc_;

	reset_firing_times_ptr_threshold = 13 * N;
	reset_firing_count_idx_threshold = 2 * T;

    LAUNCH_PARAMETERS_B64(lp_update_state_, update_N_state_, N)
    lp_update_state = lp_update_state_;
//    lp_update_state = LaunchParameters(N, (void *)update_N_state_);
    LAUNCH_PARAMETERS_B64(lp_update_voltage_plot_, update_voltage_plot_, n_voltage_plots)
    lp_update_voltage_plot = lp_update_voltage_plot_;
//    lp_update_voltage_plot = LaunchParameters(n_voltage_plots, (void *)update_voltage_plot_);
    LAUNCH_PARAMETERS_B64(lp_update_scatter_plot_, update_scatter_plot_, n_scatter_plots)
	lp_update_scatter_plot = lp_update_scatter_plot_;
//	lp_update_scatter_plot = LaunchParameters(n_scatter_plots, (void *)update_scatter_plot_);

//    lp_update_state.print_info();
//    lp_update_voltage_plot.print_info();
//    lp_update_scatter_plot.print_info();
    // fired
	checkCusparseErrors(cusparseCreate(&fired_handle));
	checkCusparseErrors(cusparseCreateDnMat(&firing_times_dense,
		1, N, N,
		fired,
		CUDA_R_32F, CUSPARSE_ORDER_ROW));

	checkCusparseErrors(cusparseCreateCsr(&firing_times_sparse, 1, N, 0,
		firing_counts_write,
		firing_idcs_write,
		firing_times_write,
		CUSPARSE_INDEX_32I, CUSPARSE_INDEX_32I,
		CUSPARSE_INDEX_BASE_ZERO, CUDA_R_32F));

	// allocate an external buffer if needed
	checkCusparseErrors(cusparseDenseToSparse_bufferSize(
		fired_handle, firing_times_dense, firing_times_sparse,
		CUSPARSE_DENSETOSPARSE_ALG_DEFAULT,
		&fired_buffer_size));
	checkCudaErrors(cudaMalloc(&fired_buffer, fired_buffer_size));

	L_winner_take_all_map = L_winner_take_all_map_;

    max_n_winner_take_all_layers = max_n_winner_take_all_layers_;
    max_winner_take_all_layer_size = max_winner_take_all_layer_size_;

	C_old = C_old_;
	C_new = C_new_;
	C_source = C_source_;
	chem_grid_w = chem_grid_w_;
	chem_grid_h = chem_grid_h_;
	chem_grid_d = chem_grid_d_;
	if (chem_grid_w * chem_grid_h * chem_grid_d > 0){
        b_update_chemical_concentrations = true;
	}
	chem_k_val = chem_k_val_;
	chem_depreciation = chem_depreciation_;
    lp_update_chemical_concentrations = LaunchParameters(
		chem_grid_w,
		chem_grid_h,
		chem_grid_d,
		chem_block_size,
		chem_block_size,
		chem_block_size
	);
}


void SnnSimulation::update_chemical_concentrations(){
	update_chemical_concentrations_ KERNEL_ARGS2(lp_update_chemical_concentrations.grid3,
                                              lp_update_chemical_concentrations.block3) (
		C_old, C_new, C_source,
		chem_grid_w, chem_grid_h, chem_grid_d,
		chem_k_val,
		chem_depreciation
	);
}


__global__ void update_current_(
	const int N,
	const int G,
	const int S,
	const int D,
	const int* fired_idcs_read,
	const int* fired_idcs,
	const float* firing_times_read,
	const float* firing_times,
	const int* N_flags,
	const int* G_flags,
	const float* G_props,
	const int* N_rep,
	// const int* Buffer,
	const int* N_rep_pre_synaptic,
	const int* N_rep_pre_synaptic_idcs,
	const int* N_rep_pre_synaptic_counts,
	float* N_weights,
	float* N_states,
	const int n_fired_m1_to_end,
	const int n_fired,
	const int t,
	const int* N_delays,
	bool r_stdp,
	const int* G_stdp_config_current,
	const int* last_fired,
    const int debug_neuron_id_0,
    const int debug_neuron_id_1,
//	float alpha = 1.f,
//	float beta = 0.f,
	float phi_r = 1.f,
	float phi_p = 1.f,
	float a_r_p = .95f,
	float a_p_m = -.95f,
	float a_r_m = -.95f,
	float a_p_p = .95f,
	float max_w_exc = 1.f,
	float min_w_exc = .05f,
	float max_w_inh = -.05f,
	float min_w_inh = -1.f,
	const int row_b_sensory_input = 3,
	const int N_flags_row_type = 1,
	const int N_flags_row_group = 2
)
{

	const int fired_idx = blockIdx.x * blockDim.x + threadIdx.x;

	if (fired_idx < n_fired)
	{
		int n;
		int firing_time;

		if (fired_idx < n_fired_m1_to_end)
		{
			// global index of firing-array < len(fired-array)
			// -> use the trailing pointer
			n = fired_idcs_read[fired_idx];
			firing_time = __float2int_rn(firing_times_read[fired_idx]);
		}
		else
		{
			// global index of firing-array >= len(fired-array)
			// -> use the 'normal' pointer
			n = fired_idcs[fired_idx - n_fired_m1_to_end];
			firing_time = __float2int_rn(firing_times[fired_idx - n_fired_m1_to_end]);
		}

		int time_since_firing = t - firing_time;
		const int delay_idx = n + N * (time_since_firing);

		int src_G;
		if (r_stdp){src_G = N_flags[n + N_flags_row_group * N];}

		int snk_N;
		int snk_G;
		int idx;
		int s_end = N_delays[delay_idx + N];
		int s_end2;
		float w1;

        int n_type;
        if (r_stdp){n_type = N_flags[ n + N_flags_row_type * N];}

		for (int s = N_delays[delay_idx]; s < s_end; s++)
		{
			idx = n + N * s;
			snk_N = N_rep[idx];

			if (snk_N >= 0)  // allows deleting synapses with -1
			{
				snk_G = N_flags[snk_N + N_flags_row_group * N];
				w1  =  N_weights[idx];
                // Add the current to the target neuron
				atomicAdd(&N_states[snk_N + 7 * N], w1);

				if (r_stdp){

					int stdp_config = G_stdp_config_current[src_G + snk_G * G];
                    // Check if the synapse is eligible for STDP:
                    // stdp_config = 0: no STDP; 1: Reward; -1: Punishment
                    bool b_print = (n == debug_neuron_id_0)
                                   && (snk_N == debug_neuron_id_1);
                    int time_diff = (firing_time - last_fired[snk_N]);
                    if (b_print) {
                        printf("\n(%d, %d)"
                               " t=%d, ft=%d,ft[snk]=%d, diff=%d"
                               ", w=%.2f tsf=%d, %d",
                               n, snk_N,
                               t, firing_time, last_fired[snk_N],
                               time_diff,
                               w1, time_since_firing, stdp_config
                               );
                    }
					if ((stdp_config != 0) && (time_diff > 0) && (time_diff <= time_since_firing)){
						//w1 = fabsf(w1);
						//if ((w1 < .98) && (w1 > 0.02)){
                            // EXCITATORY target (N_flags.type == 2)
                            float dw;
                            int snk_type = N_flags[ snk_N + N_flags_row_type * N];
                            if (snk_type == 2){
                                dw = (
                                        (stdp_config > 0) * phi_r * a_r_m
                                        + (stdp_config < 0) * phi_p * a_p_p);

                            // INHIBITORY target (N_flags.type == 1)
                            } else {
                                dw = ((stdp_config > 0) * phi_r * a_r_p
                                       + (stdp_config < 0) * phi_p * a_p_m);
                            }
                            w1 = N_weights[idx];
//                            dw *= fabsf(w1) * (1.f - fabsf(w1));
                            dw *= fabsf(w1) * (
                                fabsf(min_w_inh) * (2 - n_type)
                                + fabsf(max_w_exc) * (n_type - 1)
                                - fabsf(w1));
                            w1 += dw;
                            N_weights[idx] = fminf(
                                  max_w_exc * (n_type - 1)
                                  + max_w_inh * (2 - n_type),
                                  fmaxf(min_w_exc * (n_type - 1)
                                        + min_w_inh * (2 - n_type), w1));
                            if (b_print) {
                                printf("\n(post) (%d, %d[type=%d]) dw=%f",
                                       n, snk_N, snk_type, dw);
                            }
						//}
					}
				}
			}
		}

//        bool b_print = (n == debug_neuron_id_1);
//
//        if (b_print) {
//            printf("\n(%d) t=%d, tsf=%d, b_sensory_input=%d,",
//                   n, t, time_since_firing, G_flags[src_G + row_b_sensory_input * G]);
//        }

		if (r_stdp && (time_since_firing == 0)
			&& ((G_flags[src_G + row_b_sensory_input * G] == 0))
		)
		{
			int pre_src_N;
			float w2;
			s_end2 = N_rep_pre_synaptic_counts[n + 1];
			// Check all pre-synaptic neurons
            for (int s2 = N_rep_pre_synaptic_counts[n]; s2 < s_end2; s2++){

				idx = N_rep_pre_synaptic_idcs[s2];
				//w2 = fabsf(N_weights[idx]);
				pre_src_N = N_rep_pre_synaptic[s2];

                bool b_print = (pre_src_N == debug_neuron_id_0)
                                && (n == debug_neuron_id_1);
//                bool b_print = (n == debug_neuron_id_1);
//
//                if (b_print) {
//                    if (s2 == N_rep_pre_synaptic_counts[n]){
//                        printf("\n");
//                    }
////                    int stdp_config = G_stdp_config_current[
////                            N_flags[pre_src_N + N_flags_row_group * N] + src_G * G];
////                    printf("\n(%d, %d) t=%d, tsf=%d, idx=%d, %d",
////                           pre_src_N, n, t, time_since_firing, idx, stdp_config);
//                    printf("%d, "
////                           "%d), "
////                           "t=%d, tsf=%d, "
////                           "idx=%d, %d"
//                           "",
//                           pre_src_N
////                           , n
////                           , t, time_since_firing
////                           , idx, stdp_config
//                           );
//                    if (s2 == s_end2 - 1){
//                        printf("\n");
//                    }
//                }

//                b_print = (pre_src_N == debug_neuron_id_0)
//                                && (n == debug_neuron_id_1);

				//if ((w2 < .98) && (w2 > 0.02) && (pre_src_N >= 0))
				if (pre_src_N >= 0)  // allows deleting synapses with -1
				{
					int stdp_config = G_stdp_config_current[
                            N_flags[pre_src_N + N_flags_row_group * N] + src_G * G];

                    int time_diff = last_fired[pre_src_N] - firing_time;

                    if (b_print) {
                        printf("\n  (%d, %d)"
                               " t=%d, ft[src]=%d,ft=%d, diff=%d"
                               ", w=%.2f tsf=%d, %d",
                               pre_src_N, n,
                               t, last_fired[pre_src_N], firing_time,
                               time_diff,
                               N_weights[idx], time_since_firing, stdp_config
                               );
                    }

					if ((time_diff <= 0)
                        && (time_diff > - (2 * D + 1))
                        // ((t - last_fired[pre_src_N]) < (2 * D))
						&& (stdp_config != 0)){
                        float dw;
                        // EXCITATORY target (N_flags.type == 2)

						if (n_type == 2){
							dw = ((stdp_config > 0) * phi_r * a_r_p
                                  + (stdp_config < 0) * phi_p * a_p_m);
                        // INHIBITORY target (N_flags.type == 1)
						} else {
							dw = ((stdp_config > 0) * phi_r * a_r_m
                                    + (stdp_config < 0) * phi_p * a_p_p);
						}

                        w2 = N_weights[idx];
                        dw *= fabsf(w2) * (
                                fabsf(min_w_inh) * (2 - n_type)
                                + fabsf(max_w_exc) * (n_type - 1)
                                - fabsf(w2));
                        w2 = N_weights[idx] + dw;
                        int src_type = N_flags[pre_src_N + N_flags_row_type * N];
                        N_weights[idx] = fminf(
                                max_w_exc * (src_type - 1)
                                + max_w_inh * (2 - src_type),
                                fmaxf(min_w_exc * (src_type - 1)
                                      + min_w_inh * (2 - src_type), w2));
                        if (b_print) {
                            printf("\n(pre) (%d, %d[type=%d]) dw=%f, %.2f",
                                   pre_src_N, n, n_type, dw, max_w_exc);
                        }


					}
				}
				// }

				// else {
				// 	printf("\nidx=%d", idx);
				// }
				//}

			}
		}
	}

}


void SnnSimulation::update_plots()
{

    update_voltage_plot_ KERNEL_ARGS2(lp_update_voltage_plot.grid3,
									  lp_update_voltage_plot.block3) (
		voltage_plot_map,
		N_states,
		voltage_plot_data,
		voltage_plot_length,
		t % voltage_plot_length,
		N,
		n_voltage_plots
	);


	update_scatter_plot_ KERNEL_ARGS2(lp_update_scatter_plot.grid3,
									  lp_update_scatter_plot.block3) (
		scatter_plot_map,
		fired,
		scatter_plot_data,
		scatter_plot_length,
		t % scatter_plot_length,
		N,
		n_scatter_plots
	);

}

// void print_array()

void SnnSimulation::print_info(bool bprint_idcs, bool bprint_firing_times){
	std::cout << "\n\n  ------------------------------------ ";
	printf("\nt=%d", t);
	printf("\nn_fired=%d", n_fired);
	printf("\nn_fired_m1_to_end=%d", n_fired_m1_to_end);
	printf("\nn_fired_0=%d", n_fired_0);
	printf("\nn_fired_m1=%d", n_fired_m1);
	printf("\nn_fired_total=%d", n_fired_total);
	printf("\nn_fired_total_m1=%d", n_fired_total_m1);
	// printf("\nfiring_counts_write=%p", (void * )firing_counts_write);
	printf("\nfiring_counts_write=%ld", firing_counts_write - firing_counts);
	printf("\n\nfiring_idcs_read=%ld", firing_idcs_read - firing_idcs);
	printf("\nfiring_idcs_write=%ld", firing_idcs_write - firing_idcs);
	printf("\n\nfiring_times_read=%ld", firing_times_read - firing_times);
	printf("\nfiring_times_write=%ld", firing_times_write - firing_times);
	printf("\n");

	if (bprint_idcs){
		printf("\nfiring_idcs:");
		for (int i = 0; i < 15; i++) {
			printf("\n");
			for (int j = 0; j < N; j++) {
				int firing_index;
				cudaMemcpy(&firing_index, firing_idcs + i * N + j,
					sizeof(float), cudaMemcpyDeviceToHost);
				printf("%d, ", firing_index);
			}
		}
		printf("\n");
	}
	if (bprint_firing_times){
		printf("\nfiring_times:");
		for (int i = 0; i < 15; i++) {
			printf("\n");
			for (int j = 0; j < N; j++) {
				float firing_time;
				cudaMemcpy(&firing_time, firing_times + i * N + j,
					sizeof(float), cudaMemcpyDeviceToHost);
				printf("%.0f, ", firing_time);
			}
		}
	}
	printf("\n");


}

void SnnSimulation::_update_sim_pointers(){

	checkCudaErrors(cudaMemcpy(
		&n_fired_0, firing_counts + firing_counts_idx, sizeof(int), cudaMemcpyDeviceToHost));

	n_fired_total += n_fired_0;
	n_fired += n_fired_0;
	firing_counts_idx += 2;

	if (n_fired_total > n_fired_total_m1) {
		n_fired_m1_to_end += n_fired_0;
	}


	if (t >= D)
	{
		cudaMemcpy(&n_fired_m1, firing_counts + firing_counts_idx_m1,
                   sizeof(int), cudaMemcpyDeviceToHost);

        //n_fired_m1 = firing_counts.d_M[firing_counts_idx_m1];
		n_fired_total_m1 += n_fired_m1;
		n_fired -= n_fired_m1;
		n_fired_m1_to_end -= n_fired_m1;
		firing_counts_idx_m1 += 2;
	}

	if (n_fired_total <= reset_firing_times_ptr_threshold)
	{
		firing_times_write += n_fired_0;
		firing_idcs_write += n_fired_0;
	}
	else
	{
		firing_times_write = firing_times;
		firing_idcs_write = firing_idcs;
		n_fired_total = 0;
		resetting = true;
	}

	if (firing_counts_idx > reset_firing_count_idx_threshold){
		firing_counts_idx = 1;
		firing_counts_write = firing_counts;
	} else {
		firing_counts_write += 2;
	}

	if (firing_counts_idx_m1 > reset_firing_count_idx_threshold){
		firing_counts_idx_m1 = 1;
	}


	if (n_fired_total_m1 <= reset_firing_times_ptr_threshold)
	{
		firing_times_read += n_fired_m1;
		firing_idcs_read += n_fired_m1;
	}
	else
	{
		firing_times_read = firing_times;
		firing_idcs_read = firing_idcs;
		n_fired_m1_to_end = n_fired_total;
		n_fired_total_m1 = 0;
		resetting = false;
	}
}



void SnnSimulation::update(const bool b_stdp, const bool verbose)
{
	t0 = std::chrono::steady_clock::now();

//    printf("ddd");

	// renderer->neurons_bodies.pos_colors.map_buffer();

	update_N_state_ KERNEL_ARGS2(lp_update_state.grid3, lp_update_state.block3 )(
		N,
		G,
		static_cast<float>(t),
		rand_states,
		N_pos,
		G_flags,
		G_props,
		N_flags,
		N_states,
		fired,
		last_fired,
		G_firing_count_hist,
		t % scatter_plot_length
		// debug_i.get_dp(),
		// debug_v.get_dp()
    );

	// renderer->neurons_bodies.pos_colors.unmap_buffer();

	if (verbose) std::cout << "\nt = " << t;

	if (b_update_voltage_plot)
	{

        update_plots();
	}

	checkCudaErrors(cudaDeviceSynchronize());

	// fired
	checkCusparseErrors(cusparseDenseToSparse_analysis(
		fired_handle, firing_times_dense, firing_times_sparse,
		CUSPARSE_DENSETOSPARSE_ALG_DEFAULT, fired_buffer));

	checkCudaErrors(cudaDeviceSynchronize());

	checkCusparseErrors(cusparseDenseToSparse_convert(
		fired_handle, firing_times_dense, firing_times_sparse,
		CUSPARSE_DENSETOSPARSE_ALG_DEFAULT, fired_buffer));


	checkCudaErrors(cudaDeviceSynchronize());

	if (verbose) print_info(false, false);

	_update_sim_pointers();


	int block_dim_x = 32;
	int grid_dim_x = static_cast<int>(::ceilf(static_cast<float>(n_fired) / static_cast<float>(block_dim_x)));

	checkCudaErrors(cudaDeviceSynchronize());

	update_current_ KERNEL_ARGS2(grid_dim_x, block_dim_x)(
            N,
            G,
            S,
            D,
            firing_idcs_read,
            firing_idcs,
            firing_times_read,
            firing_times,
            N_flags,
            G_flags,
            G_props,
            N_rep,
		// N_rep_buffer,
		N_rep_pre_synaptic,
            N_rep_pre_synaptic_idcs,
            N_rep_pre_synaptic_counts,
            N_weights,
            N_states,
            n_fired_m1_to_end,
            n_fired,
            t,
            N_delays,
		// stdp_active && (t > 100),
		b_stdp && (t > no_stdp_time_threshold),
            G_stdp_config_current,
            last_fired,
            debug_neuron_0,
            debug_neuron_1,
//        alpha,
//        beta ,
        phi_r,
            phi_p,
            a_r_p,
            a_p_m,
            a_r_m,
            a_p_p,
            max_w_exc,
            min_w_exc,
            max_w_inh,
            min_w_inh
    );

	checkCudaErrors(cudaDeviceSynchronize());

	t++;


	cusparseCsrSetPointers(firing_times_sparse,
                           firing_counts_write,
	                       firing_idcs_write,
	                       firing_times_write);

	// if (true)
	// {
	// 	debug_i.print_d_m();
	// 	//neuron_states.print_d_m();
	// }

	checkCudaErrors(cudaDeviceSynchronize());

	// if (verbose)
	// {
	// 	printf("\n");
	// }

	if (b_update_chemical_concentrations){
		update_chemical_concentrations();

	}

	update_duration = std::chrono::duration_cast<std::chrono::milliseconds>(
		std::chrono::steady_clock::now() - t0).count();
}


void SnnSimulation::set_stdp_config(int stdp_config_id, bool activate){

	if (stdp_config_id==0){
		G_stdp_config_current = G_stdp_config0;
	} else if (stdp_config_id==1){
		G_stdp_config_current = G_stdp_config1;
	} else {
		throw std::invalid_argument( "not in [0, 1]" );
	}

	if (activate){
		stdp_active = true;
	}
}


__global__ void reset_G_avg_weight_G_syn_count_(
	const int G,
	float* G_avg_weight_inh,
	float* G_avg_weight_exc,
	int* G_syn_count_inh,
	int* G_syn_count_exc
){
	const int src_G = blockIdx.x * blockDim.x + threadIdx.x;
	if (src_G < G){
		int write_idx;
		for (int snk_G = 0; snk_G < G; snk_G++){
			write_idx = src_G + snk_G * G;
			G_avg_weight_inh[write_idx] = 0.f;
			G_syn_count_inh[write_idx] = 0;
			G_avg_weight_exc[write_idx] = 0.f;
			G_syn_count_exc[write_idx] = 0;
		}
	}
}


__global__ void prefill_G_avg_weight_G_syn_count_(
	const int N,
	const int G,
	const int S,
	const int* N_flags,
	const int* G_group_delay_counts,
	const int* N_rep,
	const float* N_weights,
	float* G_avg_weight_inh,
	float* G_avg_weight_exc,
	int* G_syn_count_inh,
	int* G_syn_count_exc,
	const int N_flags_row_type = 1,
	const int N_flags_row_group = 2
){
	const int src_N = blockIdx.x * blockDim.x + threadIdx.x;

	if (src_N < N){


		int src_type = N_flags[src_N + N_flags_row_type * N];
		int src_G = N_flags[src_N + N_flags_row_group * N];
		int snk_N;
		int snk_G;
		int N_rep_idx;
		int write_idx;
		float weight;

		for (int s = 0; s < S; s++){

			N_rep_idx = src_N + s * N;
			snk_N = N_rep[N_rep_idx];
			snk_G = N_flags[snk_N + N_flags_row_group * N];
			write_idx = src_G + snk_G * G;
			weight = N_weights[N_rep_idx];

			if (src_type == 1){
				atomicAdd(&G_avg_weight_inh[write_idx], 100 * weight);
				atomicAdd(&G_syn_count_inh[write_idx], 1);
			} else if (src_type == 2){
				atomicAdd(&G_avg_weight_exc[write_idx], 100 * weight);
				atomicAdd(&G_syn_count_exc[write_idx], 1);
			}
		}

	}
}

__global__ void fill_G_avg_weight_(
	const int G,
	float* G_avg_weight_inh,
	float* G_avg_weight_exc,
	const int* G_syn_count_inh,
	const int* G_syn_count_exc
){
	const int src_G = blockIdx.x * blockDim.x + threadIdx.x;

	if (src_G < G){

		int count;
		int write_idx;

		for (int snk_G = 0; snk_G < G; snk_G++){

			write_idx = src_G + snk_G * G;

			count = G_syn_count_inh[write_idx];
			if (count != 0){
				G_avg_weight_inh[write_idx] /= 100.f * __int2float_rn(count);
			}

			count = G_syn_count_exc[write_idx];
			if (count != 0){
				G_avg_weight_exc[write_idx] /= 100.f * __int2float_rn(count);
			}
		}

	}
}


void SnnSimulation::calculate_avg_group_weight(){

    LAUNCH_PARAMETERS_B64(launch_pars_N, prefill_G_avg_weight_G_syn_count_, N)
    LAUNCH_PARAMETERS_B64(launch_pars_G, reset_G_avg_weight_G_syn_count_, N)
//	LaunchParameters launch_pars_N = LaunchParameters(N, (void *)prefill_G_avg_weight_G_syn_count_);
//	LaunchParameters launch_pars_G = LaunchParameters(N, (void *)reset_G_avg_weight_G_syn_count_);

	checkCudaErrors(cudaDeviceSynchronize());

	reset_G_avg_weight_G_syn_count_ KERNEL_ARGS2(launch_pars_G.grid3, launch_pars_G.block3)(
		G,
		G_avg_weight_inh,
		G_avg_weight_exc,
		G_syn_count_inh,
		G_syn_count_exc
	);

	checkCudaErrors(cudaDeviceSynchronize());

	prefill_G_avg_weight_G_syn_count_ KERNEL_ARGS2(launch_pars_N.grid3, launch_pars_N.block3)(
		N,
		G,
		S,
		N_flags,
		G_group_delay_counts,
		N_rep,
		N_weights,
		G_avg_weight_inh,
		G_avg_weight_exc,
		G_syn_count_inh,
		G_syn_count_exc
	);

	checkCudaErrors(cudaDeviceSynchronize());

	fill_G_avg_weight_ KERNEL_ARGS2(launch_pars_G.grid3, launch_pars_G.block3)(
		G,
		G_avg_weight_inh,
		G_avg_weight_exc,
		G_syn_count_inh,
		G_syn_count_exc
	);

	checkCudaErrors(cudaDeviceSynchronize());

}

void SnnSimulation::set_b_update_chemical_concentrations(const bool b_update_chemical_concentrations_) {
	if (!b_update_chemical_concentrations_){
        b_update_chemical_concentrations = b_update_chemical_concentrations_;
	}
	if (chem_grid_w * chem_grid_h * chem_grid_d <= 0){
        b_update_chemical_concentrations = b_update_chemical_concentrations_;
	}
}
bool SnnSimulation::get_b_update_chemical_concentrations() { return b_update_chemical_concentrations; }
