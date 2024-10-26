#pragma once

#include "utils/curand_states.cuh"
#include "structures/network_structures.h"


struct TypeGroupConnector
{
    NetworkConstants* NNConsts;
    TypeGroupConnection* connection;

    curandState* curandStates;

    const int* cumulativeCountsSource;
    const int* cumulativeCountsTarget;

    const int* gridGroupsRepresentation;
    const int* gridGroupsNeuronCounts;
    const int* gridGroupsSynapseDelayCounts;

    int* gridGroupsAutapse_localIdcs;
    int* gridGroupsAutapse_globalIdcs;

    const int*  neuronFlags;
    int* neuronCumulativeDelaysCounts;
    int* neuronsSynapseRepresentation;

    const int* cumulativeSynapseCounts;
    int* sortKeyBuffer;

    int N_flags_GridGroupRowIdx;
    const bool hasAutapses;

    bool b_verbose;
    bool b_debug_mode{false};


    TypeGroupConnector(
            NetworkConstants* nn_consts,
            TypeGroupConnection* gc,
            curandState* curand_states,

            const int* cc_src,
            const int* cc_snk,

            const int* G_rep,
            const int* G_neuron_counts,
            const int* G_group_delay_counts,
            int* G_relative_autapse_indices,
            int* G_autapse_indices,

            const int* N_Flags,
            int* N_delays,
            int* N_rep,

            const int* cc_syn,
            int* sort_keys,

            int N_flags_row_group,
            bool has_autapses,
            bool verbose,
            bool debug_mode = false
    );

    int connect() const;

private:
    void set_local_autapse_idcs() const;
    void set_local_networkRepresentation_idcs() const;

};