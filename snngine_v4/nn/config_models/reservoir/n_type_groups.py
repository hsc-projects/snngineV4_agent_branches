from __future__ import annotations

from copy import deepcopy
from enum import auto, IntEnum, unique
from typing import Annotated, Iterator, List

import numpy as np
from annotated_types import Ge, Gt
from pydantic import (
    BeforeValidator, computed_field, Field,
    NonNegativeInt,
)

from snngine_v4.utils.core_utils import get_intenum_member
from snngine_v4.utils.data_utils.validation.dtype_annotation import UInt64, UInt8
from snngine_v4.utils.settings.xml_settings import XMLSettingsModel


@unique
class NeuronType(IntEnum):
    INHIBITORY = 1
    EXCITATORY = auto()


def validate_neuron_type(value):
    if isinstance(value, (int, str)):
        value = get_intenum_member(value, NeuronType)
    return value


type AnnotatedNeuronType = Annotated[int, BeforeValidator(validate_neuron_type)]


def shape_from_max_size(shape, max_size, n_bytes=4):
    if ((len(shape) != 2)
            or (not isinstance(shape[0], int))
            or (not isinstance(shape[1], int))):
        raise TypeError

    max_size = np.ceil(max_size / n_bytes)
    shape_size_ = np.array(shape).cumprod()[-1]

    if shape_size_ > max_size:
        max_square_length = np.sqrt(max_size)
        new_shape = np.array([max_square_length, max_square_length])

        for i in range(len(shape)):
            if shape[i] < new_shape[i]:
                new_shape[i] = shape[i]
                if i < (len(shape) - 1):
                    new_shape[i + 1] += (new_shape[i + 1] - new_shape[i])

        sqrt_new_shape = tuple(np.sqrt(new_shape))

        for i in range(len(shape)):
            while ((((shape[i] % (new_shape[i] - sqrt_new_shape[i]))
                     - (shape[i] % new_shape[i])) > 0)
                   and ((shape[i] % new_shape[i]) > 0)):
                # find a better x such that batch sizes become closer
                # to each other.
                # As long a reducing x by sqrt(x) does not result in
                # int(old_x/x) increasing, reduce x by sqrt(x).

                new_shape[i] -= sqrt_new_shape[i]

        new_shape_size = np.array(new_shape).cumprod()[-1]

        if not new_shape_size < max_size:
            raise ValueError

        return tuple(new_shape)
    return shape


@unique
class NTypeGroupGenerationMode(IntEnum):
    CUSTOM = 0
    UNIFORM_RATIO = auto()


class NeuronTypeGroup(XMLSettingsModel):
    ntype: NeuronType
    start_idx: NonNegativeInt
    end_idx: NonNegativeInt
    # filler: NonNegativeFloat = 0.
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

    def __len__(self):
        return self.size

    @property
    def size(self):
        return self.end_idx - self.start_idx + 1


def make_counts(ratios, exp_total):

    counts = []
    count_sum = 0
    ratio_sum = 0

    for i in range(len(ratios)):

        count = int(ratios[i] * exp_total)
        exp_count = int(exp_total * (ratio_sum + ratios[i]))
        next_count = int(count_sum + count)
        if exp_count < next_count:
            count -= 1
        elif next_count < exp_count:
            count += 1

        counts.append(count)
        count_sum += count
        ratio_sum += ratios[i]

    if count_sum != exp_total:
        raise AssertionError(f"sum({counts}) != {exp_total} = exp_total")
    return counts


type NonNegativeFloatList = List[Annotated[float, Ge(0)]]


class NTypeGroupList(XMLSettingsModel):

    gen_mode: NTypeGroupGenerationMode = NTypeGroupGenerationMode.UNIFORM_RATIO
    groups: list[NeuronTypeGroup | AnnotatedNeuronType] = Field(
        default_factory=lambda: [NeuronType.INHIBITORY,
                                 NeuronType.EXCITATORY],)
    gen_factors: NonNegativeFloatList = Field(
        default_factory=lambda: [1, 4],)

    def generate_groups(self, n_neurons):

        match self.gen_mode:
            case NTypeGroupGenerationMode.UNIFORM_RATIO:
                if len(self.groups) != len(self.gen_factors):
                    raise ValueError(
                        "Length of groups and factors do not match")
                gen_factors = np.array(self.gen_factors)
                gen_ratios = gen_factors/np.sum(gen_factors)
                previous_group = None

                counts = make_counts(gen_ratios, n_neurons)

                for i, group in enumerate(self.groups):
                    if isinstance(group, (int, str, NeuronType,
                                          NeuronTypeGroup)):
                        if isinstance(group, (int, str)):
                            group = validate_neuron_type(group)
                        if i > 0:
                            previous_group = self.groups[i - 1]
                        if isinstance(group, NeuronType):
                            ntype = group
                        else:
                            ntype = group.ntype
                        group = NeuronTypeGroup.from_count(
                            count=counts[i],
                            ntype=ntype, previous_group=previous_group)
                        self.groups[i] = group
                    else:
                        raise NotImplementedError

            case _:
                raise NotImplementedError
        return self

    def __getitem__(self, item):
        return self.groups[item]

    def __len__(self):
        return len(self.groups)

    def __setitem__(self, idx, value):
        self.groups[idx] = value

    def __iter__(self) -> Iterator[NeuronTypeGroup]:
        return iter(self.groups)


@unique
class WeightGenerationMode(IntEnum):
    CUSTOM = 0
    UNIFORM = auto()
    RND_UNIFORM = auto()


@unique
class TypeConnGenerationMode(IntEnum):
    CUSTOM = 0
    UNIFORM = auto()


class NTypeGroupConnInit(XMLSettingsModel):
    src: NonNegativeInt
    snk: NonNegativeInt
    w0: float


class NTypeGroupConn(XMLSettingsModel):
    src: NeuronTypeGroup
    snk: NeuronTypeGroup
    w0: float

    # max_batch_size_mb: NonNegativeInt = 300
    n_synapses: UInt64 | None = None
    col: UInt64 | None = None
    nbytes: UInt8 = 4

    # conn_shape: tuple[int, int]

    def batch_shape(self, max_size) -> tuple[int, int]:
        return shape_from_max_size(self.conn_shape, max_size, self.nbytes)

    @computed_field
    @property
    def conn_shape(self) -> tuple[int, int]:
        return len(self.src), self.n_synapses


class NTypeGroupConnList(XMLSettingsModel):

    gen_mode: TypeConnGenerationMode = TypeConnGenerationMode.UNIFORM
    conns: list[NTypeGroupConn | NTypeGroupConnInit]

    def generate_uniform_connections(self, groups: NTypeGroupList, n_syn):
        match groups.gen_mode:
            case NTypeGroupGenerationMode.UNIFORM_RATIO:
                snk_ratios = {}
                for i, conn in enumerate(self.conns):
                    if isinstance(conn.src, int):
                        if conn.src not in snk_ratios:
                            snk_ratios[conn.src] = []
                        snk_ratios[conn.src].append(
                            groups.gen_factors[conn.snk])

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
                    if isinstance(conn.src, int):
                        if conn.src not in src_counts:
                            src_counts[conn.src] = 0
                        else:
                            src_counts[conn.src] += 1
                        snk_syn_counts_idx = src_counts[conn.src]
                        conn = NTypeGroupConn(
                            src=deepcopy(groups[conn.src]),
                            snk=deepcopy(groups[conn.snk]),
                            w0=conn.w0,
                            n_synapses=snk_syn_counts[conn.src][
                                snk_syn_counts_idx],
                            col=snk_syn_counts_cumulative[conn.src][
                                snk_syn_counts_idx],
                        )
                        self.conns[i] = conn

    def generate_conns(
            self, groups: NTypeGroupList, n_syn):
        match self.gen_mode:
            case TypeConnGenerationMode.UNIFORM:
                self.generate_uniform_connections(groups, n_syn)
            case _:
                raise NotImplementedError
