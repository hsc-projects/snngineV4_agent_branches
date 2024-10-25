from __future__ import annotations

from enum import auto, IntEnum, unique

import numpy as np
from pydantic import BaseModel, Field, NonNegativeInt
from pydantic.v1 import PositiveFloat

from snngine_v4.utils.data.validation.array_annotation import ArrayInterfaces
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


@unique
class NeuronType(IntEnum):
    INHIBITORY = 1
    EXCITATORY = auto()


@unique
class TypeGroupGenerationMode(IntEnum):
    CUSTOM = 0
    RND_UNIFORM = auto()


class NeuronTypeGroup(XMLSettingsModel):
    ntype: NeuronType
    start_idx: int
    end_idx: int
    # indices: ArrayInterfaces().ibo_array_type(1) | None

    @classmethod
    def from_count(
            cls, count: int,
            ntype: NeuronType,
            previous_group: NeuronTypeGroup = None):
        if previous_group is None:
            start_idx = 0
            end_idx = count - 1
        else:
            start_idx = previous_group.end_idx + 1
            end_idx = previous_group.end_idx + count
        return NeuronTypeGroup(
            start_idx=start_idx, end_idx=end_idx, ntype=ntype)


def make_counts(ratios, exp_total):
    counts = []
    ratio_sum = 0
    count_sum = 0
    for i in range(len(ratios)):
        count = int(ratios[i] * exp_total)
        exp_count = int(exp_total * (ratio_sum + ratios[i]))
        next_count = int(count_sum + (count * ratios[i]))
        if exp_count < next_count:
            count -= 1
        ratio_sum += ratios[i]
        count_sum += count
        counts.append(count)
    if count_sum != exp_total:
        raise AssertionError()
    return counts


class NeuronTypeGroupList(XMLSettingsModel):

    gen_mode: TypeGroupGenerationMode = TypeGroupGenerationMode.RND_UNIFORM
    groups: list[NeuronTypeGroup | NeuronType] = Field(
        default_factory=lambda: [NeuronType.INHIBITORY,
                                 NeuronType.EXCITATORY],)
    gen_factors: list[int] = Field(
        default_factory=lambda: [1, 4],)

    def generate_groups(self, n_neurons):

        match self.gen_mode:
            case TypeGroupGenerationMode.RND_UNIFORM:
                if len(self.groups) != len(self.gen_factors):
                    raise ValueError(
                        "Length of groups and factors do not match")
                gen_factors = np.array(self.gen_factors)
                gen_ratios = gen_factors/np.sum(gen_factors)
                previous_group = None

                counts = make_counts(gen_ratios, n_neurons)

                for i, group in enumerate(self.groups):
                    if isinstance(group, NeuronType):
                        if i > 0:
                            previous_group = self.groups[i - 1]
                        group = NeuronTypeGroup.from_count(
                            count=counts[i],
                            ntype=group, previous_group=previous_group)
                        self.groups[i] = group
                    elif isinstance(group, NeuronTypeGroup):
                        pass
                    else:
                        raise NotImplementedError

            case _:
                raise NotImplementedError
        return




@unique
class WeightGenerationMode(IntEnum):
    CUSTOM = 0
    UNIFORM = auto()
    RND_UNIFORM = auto()


class NeuronTypeGroupConnection(XMLSettingsModel):
    src: NeuronTypeGroup
    snk: NeuronTypeGroup
    w0: float

    max_batch_size_mb: NonNegativeInt
    n_synapses: NonNegativeInt
    col: NonNegativeInt

    conn_shape: tuple[int, int]
    batch_shape: tuple[int, int]


class NeuronTypeGroupConnectionList(XMLSettingsModel):

    init_weights: list[float]
    conns: list[NeuronTypeGroupConnection | tuple[int, int]]

    def generate_conns(
            self, groups: NeuronTypeGroupList, n_syn):
        match groups.gen_mode:
            case TypeGroupGenerationMode.RND_UNIFORM:
                snk_ratios = {}
                for i, conn in enumerate(self.conns):
                    if isinstance(conn, tuple):
                        if conn[0] not in snk_ratios:
                            snk_ratios[conn[0]] = []
                        snk_ratios[conn[0]].append(groups.gen_factors[conn[1]])

                for k0, v0 in snk_ratios.items():
                    snk_ratios[k0] /= np.sum(np.array(v0))

                src_counts = {}
                snk_syn_counts = {}
                snk_syn_counts_cumulative = {}
                for k0, v0 in snk_ratios.items():
                    snk_syn_counts[k0] = make_counts(
                        ratios=v0, exp_total=n_syn)
                    snk_syn_counts_cumulative[k0] = np.cumsum(
                        snk_syn_counts[k0])

                for i, conn in enumerate(self.conns):
                    if isinstance(conn, tuple):
                        if conn[0] not in src_counts:
                            src_counts[conn[0]] = 0
                        else:
                            src_counts[conn[0]] += 1
                        snk_idx = src_counts[conn[0]]
                        conn = NeuronTypeGroupConnection(
                            src=groups[conn[0]],
                            snk=groups[conn[1]],
                            w0=self.init_weights[conn[2]],
                            n_synapses=snk_syn_counts[conn[0]][snk_idx],
                            col=snk_syn_counts_cumulative[conn[0]][snk_idx],
                        )
                        self.conns[i] = conn


            case _:
                raise NotImplementedError

