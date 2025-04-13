from __future__ import annotations

from functools import cached_property
from typing import Callable, TYPE_CHECKING

import numpy as np
import torch

from snngine_v4.nn.construction.config_models.neurons.synapse_model import (
    SynapseCountTensors, SynapseModel,
)
from snngine_v4.nn.construction.config_models.reservoir.n_type_groups import (
    NeuronType, NTypeGroupConnList, NTypeGroupList,
)
from snngine_v4.nn.construction.engine_element import EngineElement

from snngine_v4.utils.cuda_utils.cuda_functions import \
    (
    print_allocated_memory_diff, save_current_allocated_memory,
)

from snngine_v4.utils.cuda_utils.tensor_dataframe import TensorDataFrame


if TYPE_CHECKING:
    from snngine_v4.nn.spnn_reservoir import NetworkReservoir


class SynCounts(EngineElement):

    config_model: SynapseCountTensors
    parent_element: Callable[..., Synapses]

    G_exp_ccsyn_per_src_type_and_delay: TensorDataFrame
    G_exp_exc_ccsyn_per_snk_type_and_delay: TensorDataFrame

    def __init__(self, model: SynapseModel, **kwargs):
        super().__init__(config_model=model, **kwargs)

        self.G = None
        self.D = None
        self.S = None
        self.L_Group_neuronCounts = None

        self.exp_inh = None
        self.exp_exc = None
        self.row_exc_max = None
        self.exc_syn_counts = []
        self.max_median_inh_targets_delay = -1
        self.max_median_exc_targets_delay = -1
        self.last_row_inh = None
        self.last_row_exc = None

    def masked_add(self, row, v, mask=None):
        t = self.G_exp_exc_ccsyn_per_snk_type_and_delay.gpu_values
        if mask is not None:
            t[row, :][mask] = (t[row, :] + v)[mask]
        else:
            t[row, :] += v

    def inh_targets(self, delay):
        return self.L_Group_neuronCounts[2 + delay, :]

    def exc_targets(self, delay):
        return self.L_Group_neuronCounts[2 + self.D + delay, :]

    # noinspection PyPep8Naming
    def fill_tensors(
            self, G, D, S, L_Group_neuronCounts, conn_probs,
            ntypes: NTypeGroupList, ntype_conns: NTypeGroupConnList):
        # noinspection PyUnresolvedReferences
        from snngine_v4.nn.cuda_backend import snn_construction_gpu

        self.G = G
        self.D = D
        self.S = S
        self.L_Group_neuronCounts = L_Group_neuronCounts
        
        snn_construction_gpu.fill_G_exp_ccsyn_per_src_type_and_delay(
            S=S, D=D, G=G,
            G_neuron_counts=self.L_Group_neuronCounts.data_ptr(),
            G_conn_probs=conn_probs.data_ptr(),
            G_exp_ccsyn_per_src_type_and_delay=self
            .G_exp_ccsyn_per_src_type_and_delay.data_ptr())

        self.sync_to_cpu()

        (self.config_model.G_exp_ccsyn_per_src_type_and_delay
         .validate_data(
            data=self.G_exp_ccsyn_per_src_type_and_delay.gpu_values,
            type_groups=ntypes, D=D, G=G, S=S))

        for gc in ntype_conns.conns:
            if gc.src.ntype == NeuronType.EXCITATORY.value:
                self.exc_syn_counts.append(gc.n_synapses)
        assert np.array(self.exc_syn_counts).cumsum()[-1] == self.S

        self.exp_inh = self.zeros_i32(self.G)
        self.exp_exc = self.zeros_i32(self.G)
        self.row_exc_max = self.D + 2

        autapse_mask = self.potential_autapse_mask

        for d in range(self.D):
            row_inh = d + 1
            row_exc = self.D + 2 + d

            if d > 0:
                if (self.max_median_inh_targets_delay
                        < self.inh_targets(d).median()):
                    self.max_median_inh_targets_delay = d
                    # max_inh_target_row = inh_targets(d)
                if (self.max_median_exc_targets_delay
                        < self.exc_targets(d).median()):
                    self.max_median_exc_targets_delay = d
                    # max_exc_target_row = exc_targets(d)
                    self.row_exc_max = row_exc

            exc_ccsyn = self.G_exp_ccsyn_per_src_type_and_delay[row_exc, :]
            self.exp_inh[:] = exc_ccsyn * (self.exc_syn_counts[0] / self.S) + .5
            self.masked_add(row_inh, self.exp_inh)
            self.exp_exc[:] = exc_ccsyn * (self.exc_syn_counts[1] / self.S) + .5
            self.masked_add(row_exc, self.exp_exc)
            # avoid forcing the existence of autapses
            self.masked_add(row_exc, -1, autapse_mask)

            def output_correction(exp_count, d_threshold, row, n_targets):
                diff = exp_count - n_targets(d)
                expect_too_high = diff > 0
                if expect_too_high.any():
                    diff[diff < 0] = 0
                    if d > d_threshold:
                        i = 0
                        while i <= d:
                            # i += 1
                            if (diff > 0).any():
                                expect_too_high = diff > 0
                                diff[diff < 0] = 0
                                next_subtract = (n_targets(d - i)
                                                 - self.row_diff(row - i))
                                next_subtract[next_subtract > diff] = (
                                    diff)[next_subtract > diff]
                                self.masked_add(row - i, next_subtract,
                                                mask=expect_too_high)
                                diff -= next_subtract
                            else:
                                break
                            i += 1
                    else:
                        self.masked_add(row, - diff, mask=expect_too_high)

            output_correction(self.row_diff(row_inh), 0, row_inh,
                              self.inh_targets)
            output_correction(self.row_diff(row_exc), 1, row_exc,
                              self.exc_targets)

        self.validate_sink_counts()

    def last_row_check(self, row_values,
                       n_targets, row, prefix, exc_g_count_gt_zero):
        mask = (row_values != n_targets) & exc_g_count_gt_zero
        if mask.any():
            indices_ = mask.nonzero()
            self.print_error(indices_[0], None, n_targets)
            raise ValueError(f"Last {prefix} row({row}), "
                             f"n_errors: {mask.sum()}")

    @property
    def potential_autapse_mask(self):
        n_exp_exc_syn = self.G_exp_ccsyn_per_src_type_and_delay[self.D + 2, :]
        n_targets = self.exc_targets(0)
        exp_exc_synapses = (n_exp_exc_syn
                            * (self.exc_syn_counts[1] / self.S) + .5)
        n_exc_neurons_gt_0 = self.L_Group_neuronCounts[1, :] > 0
        return ((exp_exc_synapses == n_targets) & (exp_exc_synapses > 0)
                & n_exc_neurons_gt_0)

    def print_error(self, indices, row=None, n_targets=None):
        counts_total = (self.L_Group_neuronCounts[:2, indices]
                        .cpu().numpy().flatten().tolist())
        counts_inh = (self.L_Group_neuronCounts[2:2 + self.D, indices]
                      .cpu().numpy().flatten().tolist())
        counts_exc = (self.L_Group_neuronCounts[2 + self.D:, indices]
                      .cpu().numpy().flatten().tolist())
        print('\ncounts_total:\t', counts_total)
        print('counts_inh:\t', counts_inh)
        print('counts_exc:\t', counts_exc)
        total_synapses_per_src_type = (
            self.G_exp_ccsyn_per_src_type_and_delay[:, indices]
            .cpu().numpy().flatten().tolist())
        cumulative = (self.G_exp_exc_ccsyn_per_snk_type_and_delay[:, indices]
                      .cpu().numpy().flatten().tolist())
        print('total_synapses_per_src_type:\t', total_synapses_per_src_type)
        print('cumulative_exc_per_snk_type:\t', cumulative, '\n')
        if n_targets is not None:
            if isinstance(n_targets, torch.Tensor):
                m1 = self.G_exp_exc_ccsyn_per_snk_type_and_delay[
                    row - 1, indices]
                m = self.G_exp_exc_ccsyn_per_snk_type_and_delay[row, indices]
                exp_count = m - m1
                print('exp_count:\t', exp_count
                      .cpu().numpy().flatten().tolist(),
                      f' ({m.cpu().numpy().flatten().tolist()} '
                      f'- {m1.cpu().numpy().flatten().tolist()})')
                n_targets = n_targets[indices].cpu().numpy().flatten().tolist()
            print('n_targets:\t', n_targets)
            return

    def row_diff(self, row):
        return (self.G_exp_exc_ccsyn_per_snk_type_and_delay[row, :]
                - self.G_exp_exc_ccsyn_per_snk_type_and_delay[row - 1, :])

    def validate_sink_counts(self):

        exc_g_count_gt_zero = self.L_Group_neuronCounts[1, :] > 0

        def validate_row(row, prefix, n_targets):
            exp_count = self.row_diff(row)
            cond_neg = (exp_count < 0) & exc_g_count_gt_zero
            if cond_neg.any():
                indices = cond_neg.nonzero()
                self.print_error(indices[0], row, n_targets)
                raise ValueError(f"{prefix} (expected count negative) "
                                 f"(d:{d}) n_errors: {cond_neg.sum()}")
            cond_count = ((n_targets - exp_count) < 0) & exc_g_count_gt_zero
            if cond_count.any():
                indices = cond_count.nonzero()
                self.print_error(indices[0], row, n_targets)
                raise ValueError(f"{prefix} (expected count not reached) "
                                 f"(d:{d}) n_errors: {cond_count.sum()}")

        row_inh = 1
        row_exc = self.D + 2

        for d in range(self.max_median_exc_targets_delay, self.D):
            row_inh = d + 1
            row_exc = self.D + 2 + d
            self.masked_add(row_exc, 1, mask=self.potential_autapse_mask)

            validate_row(row_inh, 'inh', self.inh_targets(d))
            validate_row(row_exc, 'exc', self.exc_targets(d))

            if d == (self.D - 1):
                if ((self.max_median_exc_targets_delay == 0)
                        or (self.row_exc_max == self.D + 2)):
                    raise AssertionError
                self.last_row_inh = (
                    self.G_exp_exc_ccsyn_per_snk_type_and_delay)[row_inh, :]
                self.last_row_exc = (
                    self.G_exp_exc_ccsyn_per_snk_type_and_delay)[row_exc, :]

        self.last_row_check(self.last_row_inh, self.exc_syn_counts[0],
                            row_inh, 'inh', exc_g_count_gt_zero)
        self.last_row_check(self.last_row_exc, self.exc_syn_counts[1],
                            row_exc, 'exc', exc_g_count_gt_zero)
        # print(G_exp_exc_ccsyn_per_snk_type_and_delay)


# noinspection PyPep8Naming
class Synapses(EngineElement):

    config_model: SynapseModel

    parent_element: Callable[..., NetworkReservoir]

    N_rep: TensorDataFrame
    N_delays: TensorDataFrame

    N_weights: TensorDataFrame

    rep_pre_synaptic: TensorDataFrame
    rep_pre_synaptic_idcs: TensorDataFrame
    rep_pre_synaptic_counts: TensorDataFrame

    conn_probs: TensorDataFrame

    counts: SynCounts

    parent_model: NetworkReservoir

    def __init__(self, model: SynapseModel, **kwargs):
        super().__init__(config_model=model, **kwargs)
        self.N_rep_buffer = self.zeros_i32((self.N_rep.shape[1],
                                            self.N_rep.shape[0]))
        self.N_rep_groups = None
        self.pseudo_tensor_i32 = self.zeros_i32((1, 1))

    def fill_tensors(self):

        # noinspection PyUnresolvedReferences
        from snngine_v4.nn.cuda_backend import snn_construction_gpu

        reservoir = self.parent_element()
        
        N = reservoir.config_model.N
        G = reservoir.config_model.G
        S = reservoir.config_model.S
        D = reservoir.config_model.D

        type_conns = reservoir.config_model.type_conns

        save_current_allocated_memory()

        self.counts.fill_tensors(
            S=S, D=D, G=G,
            L_Group_neuronCounts=reservoir.L_Group_neuronCounts,
            conn_probs=self.conn_probs,
            ntypes=reservoir.config_model.type_groups,
            ntype_conns=type_conns)

        torch.cuda.empty_cache()
        # self.print_allocated_memory('syn_counts')

        # torch.cuda.empty_cache()
        # self.print_allocated_memory('N_rep')
        self.N_rep_buffer[:] = 0

        def cc_syn_(gc_):
            t = self.zeros_i32((D + 1, G))
            if (gc_.src.ntype == NeuronType.INHIBITORY) and (
                    gc_.snk.ntype == NeuronType.EXCITATORY):
                t[:, :] = self.counts.G_exp_ccsyn_per_src_type_and_delay[
                          0: D + 1, :]
            elif ((gc_.src.ntype == NeuronType.EXCITATORY)
                  and (gc_.snk.ntype == NeuronType.INHIBITORY)):
                t[:, :] = self.counts.G_exp_exc_ccsyn_per_snk_type_and_delay[
                          0: D + 1, :]
            elif ((gc_.src.ntype == NeuronType.EXCITATORY)
                  and (gc_.snk.ntype == NeuronType.EXCITATORY)):
                t[:, :] = self.counts.G_exp_exc_ccsyn_per_snk_type_and_delay[
                          D + 1: 2 * (D + 1), :]
            else:
                raise ValueError
            return t

        for i, gc in enumerate(type_conns.conns):
            ct_row = (gc.snk.ntype - 1) * D + 2

            ccn_idx_src = G * (gc.src.ntype - 1)
            ccn_idx_snk = G * (gc.snk.ntype - 1)

            G_autapse_indices = self.zeros_i32((D, G))
            G_relative_autapse_indices = self.zeros_i32((D, G))
            cc_syn = cc_syn_(gc)

            self.RepBackend.fill_N_rep(
                cc_src=reservoir.G_neuron_typed_ccount[
                       ccn_idx_src: ccn_idx_src + G + 1].data_ptr(),
                cc_snk=reservoir.G_neuron_typed_ccount[
                       ccn_idx_snk: ccn_idx_snk + G + 1].data_ptr(),
                G_rep=reservoir.G_rep.data_ptr(),
                G_neuron_counts=reservoir.L_Group_neuronCounts[
                                ct_row: ct_row+D, :].data_ptr(),
                G_autapse_indices=G_autapse_indices.data_ptr(),
                G_relative_autapse_indices=G_relative_autapse_indices
                .data_ptr(),
                has_autapses=ccn_idx_src == ccn_idx_snk,
                gc_location=gc.location,
                gc_conn_shape=gc.conn_shape,
                cc_syn=cc_syn.data_ptr(),
                sort_keys=self.N_rep_buffer.data_ptr(),
                verbose=False)

            if (G_autapse_indices[1:, :].sum()
                    != -(G_autapse_indices.shape[0] - 1)
                    * G_autapse_indices.shape[1]):
                raise AssertionError

            if (G_relative_autapse_indices[1:, :].sum()
                    != -(G_relative_autapse_indices.shape[0] - 1)
                    * G_relative_autapse_indices.shape[1]):
                raise AssertionError

        del G_autapse_indices
        del G_relative_autapse_indices
        torch.cuda.empty_cache()

        snn_construction_gpu.sort_N_rep(N=N, S=S,
                                        sort_keys=self.N_rep_buffer.data_ptr(),
                                        N_rep=self.N_rep.data_ptr())

        for i, gc in enumerate(type_conns.conns):

            ct_row = (gc.snk.ntype - 1) * D + 2

            ccn_idx_src = G * (gc.src.ntype - 1)
            ccn_idx_snk = G * (gc.snk.ntype - 1)
            cc_syn = cc_syn_(gc)

            snn_construction_gpu.reindex_N_rep(
                N=N, S=S, D=D, G=G,
                N_flags=reservoir.N_flags.data_ptr(),
                cc_src=reservoir.G_neuron_typed_ccount[
                       ccn_idx_src: ccn_idx_src + G + 1].data_ptr(),
                cc_snk=reservoir.G_neuron_typed_ccount[
                       ccn_idx_snk: ccn_idx_snk + G + 1].data_ptr(),
                G_rep=reservoir.G_rep.data_ptr(),
                G_neuron_counts=reservoir.L_Group_neuronCounts[
                                ct_row: ct_row+D, :].data_ptr(),
                G_group_delay_counts=reservoir.L_Group_delay_counts.data_ptr(),
                gc_location=gc.location,
                gc_conn_shape=gc.conn_shape,
                cc_syn=cc_syn.data_ptr(),
                N_delays=self.N_delays.data_ptr(),
                sort_keys=self.N_rep_buffer.data_ptr(),
                N_rep=self.N_rep.data_ptr(),
                N_flags_row_group=reservoir.neuron_states.group_flag_index,
                verbose=False)

        snn_construction_gpu.sort_N_rep(N=N, S=S,
                                        sort_keys=self.N_rep_buffer.data_ptr(),
                                        N_rep=self.N_rep.data_ptr())

        # transpose the actual values
        self.N_rep[:] = self.N_rep.gpu_values.T.reshape(self.N_rep.shape)
        self.N_rep_buffer[:] = -1
        # self.print_allocated_memory(f'transposed')

        if len(self.N_rep[self.N_rep == -1]) != 0:
            self.N_rep.sync_to_df()
            df = self.N_rep.data_cpu
            # noinspection PyUnusedLocal,PyUnresolvedReferences
            df = df[df.columns[(df == -1).any(axis=0)]]
            raise AssertionError
        assert len(self.N_rep[self.N_rep == -1]) == 0

        N_rep_groups_gpu_temp = self.N_rep.gpu_values.clone()

        snn_construction_gpu.fill_N_rep_groups(
            N=N, S=S, N_flags=reservoir.N_flags.data_ptr(),
            N_rep=self.N_rep.data_ptr(),
            N_rep_groups=N_rep_groups_gpu_temp.data_ptr(),
            N_flags_row_group=reservoir.neuron_states.group_flag_index,
        )

        self.N_rep_groups = N_rep_groups_gpu_temp.cpu()

        type_conns.apply_init_weights(self.N_weights.gpu_values)

        # self.G_swap_tensor = self._G_swap_tensor()
        # self.N_relative_G_indices = self._N_relative_G_indices()
        return

    @cached_property
    def N_relative_G_indices(self):
        reservoir = self.parent_element()
        all_groups = reservoir.N_flags.group.type(torch.int64)
        inh_start_indices = reservoir.G_neuron_typed_ccount[all_groups]
        start_indices = reservoir.G_neuron_typed_ccount[
            all_groups + reservoir.config_model.G]
        inh_neurons = reservoir.N_flags.type == NeuronType.INHIBITORY.value
        start_indices[inh_neurons] = inh_start_indices[inh_neurons]
        start_indices[~inh_neurons] -= (reservoir.G_neuron_typed_ccount[
                                            all_groups + 1][~inh_neurons]
                                        - inh_start_indices[~inh_neurons])
        # return (self.neuron_ids - start_indices).type(torch.int32)
        return (reservoir.N_flags.id - start_indices).type(torch.int32)

    @cached_property
    def RepBackend(self):
        # noinspection PyUnresolvedReferences
        from snngine_v4.nn.cuda_backend import snn_construction_gpu

        reservoir = self.parent_element()
        return snn_construction_gpu.SnnRepresentation(
            N=reservoir.config_model.N,
            G=reservoir.config_model.G,
            S=reservoir.config_model.S,
            D=reservoir.config_model.D,
            curand_states_p=reservoir.curand_states,
            N_pos=reservoir.N_pos.data_ptr(),
            G_group_delay_counts=reservoir
            .L_Group_delay_counts.data_ptr(),
            G_flags=reservoir.L_Group_flags.data_ptr(),
            G_props=reservoir.L_Group_properties.data_ptr(),
            N_rep=self.N_rep.data_ptr(),
            N_rep_buffer=self.N_rep_buffer.data_ptr(),
            N_rep_pre_synaptic=self.rep_pre_synaptic.data_ptr(),
            N_rep_pre_synaptic_idcs=self.rep_pre_synaptic_idcs.data_ptr(),
            N_rep_pre_synaptic_counts=self.rep_pre_synaptic_counts.data_ptr(),
            N_delays=self.N_delays.data_ptr(),
            N_flags=reservoir.neuron_states.N_flags.data_ptr(),
            N_weights=self.N_weights.data_ptr(),
            L_winner_take_all_map=self.pseudo_tensor_i32.data_ptr(),
            max_n_winner_take_all_layers=1,
            max_winner_take_all_layer_size=1
        )
