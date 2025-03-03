#include "connector.cuh"

TypeGroupConnector::TypeGroupConnector (
        NetworkConstants* nn_consts,
        TypeGroupConnection* gc,
        curandState* curand_states,

        const int *cc_src,
        const int *cc_snk,

        const int *G_rep,
        const int *G_neuron_counts,
        const int *G_group_delay_counts,
        int *G_relative_autapse_indices,
        int *G_autapse_indices,

        const int* N_Flags,
        int* N_delays,
        int* N_rep,

        const int *cc_syn,
        int *sort_keys,

        int N_flags_row_group,
        const bool has_autapses,
        bool verbose,
        bool debug_mode
        ):
//        cumulativeCountsSource(cc_src),
//        cumulativeCountsTarget(cc_snk),
        hasAutapses(has_autapses)

{
    NNConsts = nn_consts;
    connection = gc;

    curandStates = curand_states;

    cumulativeCountsSource = cc_src;
    cumulativeCountsTarget = cc_snk;

    gridGroupsRepresentation = G_rep;
    gridGroupsNeuronCounts = G_neuron_counts;
    gridGroupsSynapseDelayCounts = G_group_delay_counts;


    gridGroupsAutapse_globalIdcs = G_autapse_indices;
    gridGroupsAutapse_localIdcs = G_relative_autapse_indices;

    neuronFlags = N_Flags;
    neuronCumulativeDelaysCounts = N_delays;
    neuronsSynapseRepresentation = N_rep;

    cumulativeSynapseCounts = cc_syn;
    sortKeyBuffer = sort_keys;

    N_flags_GridGroupRowIdx = N_flags_row_group;
    b_verbose = verbose;
    b_debug_mode = debug_mode;

}

__device__ int set_local_typed_delay_repr_idx_kernel(
        const int N_autapse_idx,
        const int G_rep_idx0,
        const int G_rep_idx1,
        const int g_N_count,
        const int* G_rep,
        const int n_groups,
        const int* cc_snk,
        bool verbose

)
{
    if (g_N_count == 0)
    {
        return -1;
    }

    int G_rep_idx = G_rep_idx0;
    int g = G_rep[G_rep_idx];
    int Ng_start = cc_snk[g];
    const int Ng_last = cc_snk[G_rep[G_rep_idx1] +1];


    if ((N_autapse_idx < Ng_start) || (N_autapse_idx >= Ng_last))
    {
        return -1;
        if (verbose)
        {
            printf(
                    "(search, not in range) g=(%d), n=%d, G_rep[%d: %d], Ng_start=%d, Ng_last=%d\n",
                    g, N_autapse_idx, G_rep_idx0, G_rep_idx1, Ng_start, Ng_last);
        }
    }

    int result = N_autapse_idx;
    result -= Ng_start;
    int Ng_next = cc_snk[g + 1];

    if (verbose)
    {
        printf("(search) g=(%d), n=%d, Ng_start=%d, Ng_next=%d\n", g, N_autapse_idx, Ng_start, Ng_next);
    }
    //if (bprint)
    //{
    //	printf("\n  search (%d) g_start_col %d, n_g_search %d, g=%d",
    //		N_autapse_idx, g_search_start_col, n_g_search, g );
    //	printf("\n  (%d)  [%d], src_G %d, g = %d [%d, %d]... %d]",
    //		N_autapse_idx, result, src_G, g, start_col_next_group, end_col_next_group, last_col);
    //}

    bool found = (N_autapse_idx >= Ng_start) && (N_autapse_idx < Ng_next);

    int Ng_prev = Ng_next;

    while ((!found) && (G_rep_idx < G_rep_idx1))
    {
        G_rep_idx++;

        g = G_rep[G_rep_idx];
        Ng_start = cc_snk[g];
        Ng_next = cc_snk[g + 1];

        result -= (Ng_start - Ng_prev);

        found = (N_autapse_idx >= Ng_start) && (N_autapse_idx < Ng_next);
        if (verbose)
        {
            printf("(search, found=%d) g=(%d), n=%d, Ng_start=%d, Ng_next=%d\n", found, g, N_autapse_idx, Ng_start, Ng_next);
        }
    }
    return result * found + (-1) * (!found);
}

__global__ void set_local_autapse_idcs_kernel(
        const int D,
        const int G,
        const int* cc_src,
        const int* cc_snk,
        const int* G_rep,
        const int* G_delay_counts,
        int* G_autapse_indices,
        int* G_relative_autapse_indices,
        bool verbose = 0,
        int print_group = 1
)
{
    const int g = blockIdx.x * blockDim.x + threadIdx.x;  // NOLINT(bugprone-narrowing-conversions, cppcoreguidelines-narrowing-conversions)

    if (g < G)
    {

        const int N_autapse_idx = cc_src[g];
        const int g_N_count = cc_src[g + 1] - N_autapse_idx;

        for (int d=0; d < D; d++)
        {
            const int g_rep_col0 = G_delay_counts[g * (D + 1) + d];
            const int g_rep_col1 = G_delay_counts[g * (D + 1) + d+1]-1;
            const int G_rep_idx0 = g * G + g_rep_col0;
            const int G_rep_idx1 = g * G + g_rep_col1;
            const int n_groups = g_rep_col1 - g_rep_col0 +1;

            if (verbose && (g == print_group))
            {
                printf("g=(%d), n=%d, d=%d, g_rep_cols=[%d, %d], idcs=[%d,%d], groups=[%d, ...,%d]\n",
                       g, N_autapse_idx, d,
                       g_rep_col0, g_rep_col1,
                       G_rep_idx0, G_rep_idx1,
                       G_rep[G_rep_idx0], G_rep[G_rep_idx1]);
            }

            const int relative_autapse_index = set_local_typed_delay_repr_idx_kernel(
                    N_autapse_idx,
                    G_rep_idx0,
                    G_rep_idx1,
                    g_N_count,
                    G_rep,
                    n_groups,
                    cc_snk,
                    verbose && (g == print_group)
            );

            G_relative_autapse_indices[g + d * G] = relative_autapse_index;

            if (relative_autapse_index != -1){
                G_autapse_indices[g + d * G] = N_autapse_idx;
            } else {
                G_autapse_indices[g + d * G] = -1;
            }

            if (verbose && (g == print_group))
            {
                printf("g=(%d), n=%d, d=%d, N=%d, rN=%d\n",
                       g, N_autapse_idx, d,
                       G_autapse_indices[g + d * G],
                       relative_autapse_index);
            }

            //if (bprint)
            //{
            //	printf("\n res: %d << %d, g = %d, d = %d\n---------\n", relative_self_index[g + d * G], self_index[g + d * G],g,d);
            //}

        }
    }
}

__forceinline__ __device__ int random_uniform_int(curandState *local_state, const float min, const float max)
{
    return __float2int_rd(fminf(min + curand_uniform(local_state) * (max - min + 1.f), max));
}

__device__ int random_uniform_int_with_exclusion(
        curandState *local_state,
        const float minf,
        const float maxf,
        const float maxf0,
        const bool exclude,
        const int autapse_idx,
        const int n,
        const int s
){
    int new_sink = __float2int_rd(fminf(minf + curand_uniform(local_state) * (maxf - minf + 1.f), maxf));
    int i = 0;
    if (exclude){
        while ((new_sink==autapse_idx) && (i<50))
        {
            new_sink = __float2int_rd(fminf(minf + curand_uniform(local_state) * (maxf - minf + 1.f), maxf));
            i++;
        }

        if (i < 50){ return new_sink; } else {
            printf("\n Loop-Warning [autapse_2](%d, %d) range=[%f, %f] -> [%f, %f], autapse_idx=%d, sink=%d",
                   n, s, 0.f, maxf0, minf, maxf, autapse_idx, new_sink);
        }
    }
    return new_sink;
}


__device__ void print_array(int* arr, int r, int c, int col0, int sep_row){

    printf("\n\n");
    int v;
    for (int i=0; i < c; i++)
    {
        v = col0 + i;
        printf("[%d]", v);
        if (v < 10){
            printf(" ");
        }
    }
    printf("\n");
    for (int j=0; j < r; j++)
    {
        if (j == sep_row){
            for (int i=0; i < c; i++)
            {
                printf("----");
            }
            printf("\n");
        }
        for (int i=0; i < c; i++)
        {
            v = arr[i + j * c];
            printf(" %d ", v);
            if (v < 10){
                printf(" ");
            }
        }
        printf("\n");
    }
}


__device__ bool duplicated_int(
        const int min_hit, const int max_hit,
        const int row_idx0,
        const int n, const int s,
        const float maxf0, const float minf, const float maxf,
        const int delay_col0, const int delay_col1, const int autapse_idx, const int new_sink,
        int* N_rep,
        const int k
){
    int i = delay_col0;

    if ((k==45)){
        printf("\n Loop-Warning [duplicated](%d, %d) range=[%f, %f] -> [%f, %f], delay_cols=[%d,%d], autapse_idx=%d, sink=%d",
               n, s, 0.f, maxf0, minf, maxf, delay_col0, delay_col1, autapse_idx, new_sink);}

    // check if the drawn integer has alredy been set

    if ((min_hit < new_sink) && (new_sink < max_hit)) {
        while (i < s) {
            if (N_rep[row_idx0 + i] == new_sink) {
                if ((k >= 45)){
                    printf("\nLoop-Warning [duplicated (%d)](%d, %d), col0=%d, write_idx=%d, k=%d) rep=%d sink=%d",
                           true, n, s, i, row_idx0 + i, k, N_rep[row_idx0 + i], new_sink);}
                return true; }
            i++;
        }
    } else if ((new_sink == min_hit) || (new_sink == max_hit)){
        if ((k >= 45)){
            printf("\nLoop-Warning [duplicated (%d) hit](%d, %d), col0=%d, write_idx=%d, k=%d) rep=%d sink=%d",
                   true, n, s, i, row_idx0 + i, k, N_rep[row_idx0 + i], new_sink);}
        return true; }
    return false;
}

void TypeGroupConnector::set_local_autapse_idcs() const {
    cudaDeviceSynchronize();
    LAUNCH_PARAMETERS_B64(launch, set_local_autapse_idcs_kernel, NNConsts->G);

    set_local_autapse_idcs_kernel KERNEL_ARGS2(launch.grid3, launch.block3)(
            NNConsts->D,
            NNConsts->G,
            cumulativeCountsSource,
            cumulativeCountsTarget,
            gridGroupsRepresentation,
            gridGroupsSynapseDelayCounts,
            gridGroupsAutapse_globalIdcs,
            gridGroupsAutapse_localIdcs,
            false);
}

__global__ void k_set_locally_indexed_connections(
        const int N,
        const int S,
        const int D,
        const int G,
        curandState* curand_states,
        const int* N_flags,
        const int* cc_src,
        const int* G_neuron_counts,
        const int* G_relative_autapse_indices,
        bool has_autapses,
        const int gc_location0,
        const int gc_location1,
        const int gc_conn_shape0,
        const int gc_conn_shape1,
        //const float init_weight,
        //float* weights,
        const int* cc_syn,
        int* N_delays,
        int* sort_keys,
        int* N_rep,
        const int N_flags_row_group,
        bool verbose
)
{
    extern __shared__ int sh_delays[];
    int* n_targets = &sh_delays[(D+1) * blockDim.x];

    const int n = gc_location0 + blockIdx.x * blockDim.x + threadIdx.x;

    //{ printf("(%d, 0) = %d\n", n, N_rep[n * S]);}

    if (n < gc_location0 + gc_conn_shape0)
    {
        curandState local_state = curand_states[n];

        const int src_G = N_flags[n + N_flags_row_group * N];
        int tdx = threadIdx.x;
        const int row_idx0 = n * S;

        N_delays[n] = 0;

        // if (n == gc_location0){print_array(sh_delays, 2 * D + 1, blockDim.x, gc_location1);}

        sh_delays[tdx] = gc_location1;

        for (int d=1; d<D+1; d++)
        {
            int end_rep_col = cc_syn[src_G + d * G];

            sh_delays[tdx + d * blockDim.x] = gc_location1 + end_rep_col;
            n_targets[tdx + (d-1)* blockDim.x] = G_neuron_counts[src_G + (d-1) * G];

            N_delays[n + d * N] += end_rep_col;

        }

        if ((verbose) && (n == gc_location0)){ print_array(sh_delays, 2 * D + 1, blockDim.x, gc_location0, D + 1); }

        int sort_key = row_idx0 + gc_location1; // + gc_location1 + max(0, (D - S) * n);

        // [delay_col0, delay_col1]: column-interval in which to write sink neurons
        int delay = 0;
        int delay_col0 = sh_delays[tdx];
        int delay_col1 = sh_delays[tdx + blockDim.x];
        int n_rep_cols = delay_col1 - delay_col0;

        // [min, max]: interval from which to draw an integer ('sink'-neuron)
        int min = 0;
        int max = n_targets[tdx] - 1;
        float maxf = __int2float_rn(max);
        float minf = 0.f;
        float maxf0 = maxf;

        int autapse_idx = -1;
        if (has_autapses){
            autapse_idx = G_relative_autapse_indices[src_G + delay * G] + (n - cc_src[src_G]);
        }
        int new_sink;

        int min_hit = -1;
        int max_hit = gc_location1 + gc_conn_shape1;

        // fill N_rep[n, s] for in [gc_location1, gc_location1 + gc_conn_shape1]
        for (int s = gc_location1; s < gc_location1 + gc_conn_shape1; s++)
        {
            const int write_idx = row_idx0 + s;

            while ((s == delay_col1) && (delay < D+1))
            {
                // if we reach the end of the write interval, update all variables
                if (delay >= 1){ autapse_idx = -1; }

                tdx += blockDim.x;
                delay_col0 = sh_delays[tdx];
                delay_col1 = sh_delays[tdx + blockDim.x];
                n_rep_cols = delay_col1 - delay_col0;
                if (n_rep_cols >0)
                {
                    min_hit = -1;
                    max_hit = gc_location1 + gc_conn_shape1;
                    min = 0;
                    max = n_targets[tdx] - 1;
                    minf = 0.f;
                    maxf0 = __int2float_rn(max);
                    maxf = maxf0;
                    sort_key = write_idx;
                }
                delay++;
            }

            if (n_rep_cols > 0) {

                if (min > max){ printf("\n Warning [min>max] (%d, %d in [%d, %d], d=%d) %d > %d, range=[%f, %f] targets %d/%d",
                                       n, s, delay, delay_col0, delay_col1, min, max,
                                       0.f, maxf0, n_targets[tdx], G_neuron_counts[src_G + (delay) * G]); }

                new_sink = random_uniform_int_with_exclusion(&local_state, minf, maxf, maxf0, (has_autapses) && (delay == 0), autapse_idx, n, s);


                if (s == delay_col0){
                    min_hit = new_sink;
                    max_hit = new_sink;
                } else {

                    int k = 0;
                    bool duplicated = true;
                    while (duplicated && (k<=50))
                    {
                        duplicated = duplicated_int(min_hit, max_hit, row_idx0, n, s, maxf0, minf, maxf, delay_col0, delay_col1, autapse_idx, new_sink, &N_rep[0], k);
                        if (duplicated) {
                            new_sink = random_uniform_int_with_exclusion(&local_state, minf, maxf, maxf0, (has_autapses) && (delay == 0), autapse_idx, n, s);
                        }
                        k++;
                    }
                }

                // we can narrow the range if we hit the border
                //if (new_sink > max){ printf("\n Loop-Warning [new_sink>max] (%d, %d) range=[%f, %f] -> [*, %d], sink=%d", n, s, 0.f, maxf0, max, new_sink); }
                if (new_sink == max){ max--; maxf -= 1.f; }
                else if (new_sink == min){ min++; minf += 1.f; }
                else if (new_sink < min_hit){ min_hit = new_sink; }
                else if (new_sink > max_hit){ max_hit = new_sink; }

                sort_keys[write_idx] = sort_key;
                N_rep[write_idx] = new_sink;

                // if (n == gc_location0) { printf("(%d, %d) = %d\n", n, s, N_rep[write_idx]);}
            }
        }

        curand_states[n] = local_state;
    }
}


void TypeGroupConnector::set_local_networkRepresentation_idcs() const {

    int min_grid_size = 0;
    int launch_block_size = 0;
    const int blockSizeLimit = 64;
    const int shared_memory_size = blockSizeLimit * ((2 * NNConsts->D) + 1) * (int)sizeof(int);
    checkCudaErrors(cudaOccupancyMaxPotentialBlockSize(
            &min_grid_size, &launch_block_size,
            (void *)k_set_locally_indexed_connections, shared_memory_size, blockSizeLimit));
    LaunchParameters l(min_grid_size, launch_block_size, connection->shape[0]);
    cudaDeviceSynchronize();
    k_set_locally_indexed_connections KERNEL_ARGS3(
            l.grid3, l.block3, l.block3.x * ((2 * NNConsts->D) + 1) * sizeof(int))(
            NNConsts->N,
            NNConsts->S,
            NNConsts->D,
            NNConsts->G,
            curandStates,
            neuronFlags,
            cumulativeCountsSource,
            gridGroupsNeuronCounts,
            gridGroupsAutapse_localIdcs,
            hasAutapses,
            connection->loc[0],
            connection->loc[1],
            connection->shape[0],
            connection->shape[1],
            //group_conn.initial_weight,
            //weights,
            cumulativeSynapseCounts,
            neuronCumulativeDelaysCounts,
            sortKeyBuffer,
            neuronsSynapseRepresentation,
            N_flags_GridGroupRowIdx,
            b_verbose
    );

    checkCudaErrors(cudaDeviceSynchronize());
}

int TypeGroupConnector::connect() const {

    printf("Connecting: ");
    connection->print();

    set_local_autapse_idcs();

    set_local_networkRepresentation_idcs();

    printf("\n");
    return 0;

}


