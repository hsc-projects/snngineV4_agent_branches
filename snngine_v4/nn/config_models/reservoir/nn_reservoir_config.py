from __future__ import annotations

from enum import IntEnum, unique
from typing import Any, ClassVar

import numpy as np

from pydantic import computed_field, Field, NonNegativeInt

from snngine_v4.chemistry.chem_models import (ChemicalContainerModel,
                                              DefaultChemicals)
from snngine_v4.geometry.grid.finite_grid import FiniteGrid
from snngine_v4.geometry.grid.finite_grid_config import FiniteGridConfig
from snngine_v4.nn.config_models.neurons.synapse_model import (
    SynapseModel,
)
from snngine_v4.nn.config_models.reservoir.n_type_groups import (
    NeuronType, NeuronTypeGroup,
    NTypeGroupConnInit, NTypeGroupConnList,
    NTypeGroupList,
)
from snngine_v4.construction.engine_element_config import (
    EngineElementConfig3D,
)
from snngine_v4.geometry.spatial_pars import (
    Pos3DVBO,
    Segmentation3D,
)
from snngine_v4.nn.config_models.reservoir.lgroup_states import (
    LGNeuronCounts, LG2LGFlags, LG2LGProp, LGroupProps, LGroupFlags,
)
from snngine_v4.nn.config_models.neurons.neuron_state import (
    NeuronStateModel,
)
from snngine_v4.utils.data_utils.dataframe_config import (
    TypedDataFrameModel,
)
from snngine_v4.utils.data_utils.validation.array_annotation import (
    ArrayInterfaces
)
from snngine_v4.utils.field_utils import (
    fill_field_default, get_attr_or_item,
    set_attr_or_item,
)

from snngine_v4.utils.settings.ui_parameter_options import (
    FrozenParamOpts,
)


@unique
class PosGenerationMode(IntEnum):
    CUSTOM = 0
    RND_UNIFORM = 1


class NetworkReservoirConfig(EngineElementConfig3D):

    class Slots:
        N_NEURONS: ClassVar[str] = 'N'
        N_SYNAPSES: ClassVar[str] = 'S'
        N_DELAYS: ClassVar[str] = 'D'

        N_LGROUPS: ClassVar[str] = 'G'

        POS_GEN_MODE: ClassVar[str] = 'pos_gen_mode'
        # SHAPE: ClassVar[str] = 'reservoir_shape'
        # SEG: ClassVar[str] = 'reservoir_segmentation'

        GRID: ClassVar[str] = 'grid'

        TYPE_GROUPS: ClassVar[str] = 'type_groups'
        TYPE_CONNS: ClassVar[str] = 'type_conns'

        POS: ClassVar[str] = 'pos'

        N_FLAGS: ClassVar[str] = 'N_flags'
        NEURON_STATES: ClassVar[str] = 'neuron_states'

        L_GROUP_NEURON_COUNTS: ClassVar[str] = 'L_Group_neuronCounts'
        L_GROUP_FLAGS: ClassVar[str] = 'L_Group_flags'
        L_GROUP_PROPERTIES: ClassVar[str] = 'L_Group_properties'
        L_GROUP2GROUP_FLAGS: ClassVar[str] = 'L_Group2Group_flags'
        L_GROUP2GROUP_PROPERTIES: ClassVar[str] = 'L_Group2Group_properties'

        SYNAPSES: ClassVar[str] = 'synapses'

    class GeneratedSlots:
        G_NEURON_COUNTS: ClassVar[str] = 'G_neuron_counts'
        G_NEURON_TYPED_CCOUNTS: ClassVar[str] = 'G_neuron_typed_ccount'

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        expanded=False,
        c_auto_collapse=True,
        c_collapsed_children=True)

    N: NonNegativeInt = 200
    S: NonNegativeInt | None = None
    D: NonNegativeInt = Field(default=0, le=20)
    G: NonNegativeInt = 0

    pos_gen_mode: PosGenerationMode = PosGenerationMode.RND_UNIFORM

    grid: FiniteGridConfig

    type_groups: NTypeGroupList = Field(
        default_factory=lambda: NTypeGroupList(
            groups=[NeuronType.INHIBITORY, NeuronType.EXCITATORY]))

    type_conns: NTypeGroupConnList = Field(
        default_factory=lambda: NTypeGroupConnList(
            conns=[NTypeGroupConnInit(src=0, snk=1, w0=-.44),
                   NTypeGroupConnInit(src=1, snk=0, w0=.45),
                   NTypeGroupConnInit(src=1, snk=1, w0=.47), ]))

    pos: Pos3DVBO = Field(
        default_factory=lambda: np.array([
            [1.5, 1.5, 1.5],
            [1.5, 1.5, 0],
            [0, 1.5, 1.5],
            [1.5, 0, 1.5],
            [-1.5, 1.5, 1.5],
            [-1.5, 1.5, 0]],
            dtype=np.float32),
        repr=False)

    neuron_states: NeuronStateModel
    synapses: SynapseModel
    # N_flags: NeuronFlags
    # N_props: NeuronProperties

    L_Group_neuronCounts: LGNeuronCounts

    L_Group_flags: LGroupFlags
    L_Group_properties: LGroupProps

    L_Group2Group_flags: LG2LGFlags
    L_Group2Group_properties: LG2LGProp

    chemicals: DefaultChemicals = Field(
        default_factory=DefaultChemicals)

    @staticmethod
    def _calc_delay_count(n_neurons, max_=20, min_=2, ):
        n_delays = np.log10(n_neurons) * (1 + np.sqrt(np.log10(n_neurons)))
        return min(int(max(n_delays, min_)), max_)

    @classmethod
    def calc_synapse_base_count(cls, n_neurons):
        return np.sqrt(n_neurons) + 50

    @classmethod
    def calc_synapse_count(cls, n_neurons, min0=2, max0=1000, max1_divider=4):
        n_synapses = cls.calc_synapse_base_count(n_neurons=n_neurons)
        return cls.limit_synapse_count(
            n_synapses=n_synapses, n_neurons=n_neurons, min0=min0, max0=max0,
            max1_divider=max1_divider)

    @classmethod
    def generate_pos(cls, mode: PosGenerationMode,
                     shape, grid_segmentation, n_neurons, type_groups):
        match mode:
            case PosGenerationMode.RND_UNIFORM:

                pos = (np.random.rand(n_neurons, 3).astype(np.float32)
                       * np.array(shape, dtype=np.float32))
                pos[pos == max(shape)] = pos[pos == max(shape)] * 0.999999

                FiniteGrid.validate_pos(pos, shape, n_neurons)
            case _:
                raise NotImplementedError
        grid_coordinates = cls.sort_pos(
            pos=pos, shape=shape, grid_segmentation=grid_segmentation,
            type_groups=type_groups)
        return pos, grid_coordinates

    @classmethod
    def generate_segmentation(cls, n_delays, shape):
        segmentation_list = []
        for s in shape:
            f = max(shape) / min(shape)
            segmentation_list.append(
                    int(
                        int(max(n_delays / (np.sqrt(3) * f), 2))
                        * (s / min(shape))))
        seg = tuple(segmentation_list)
        min_g_shape = min(seg)
        if not all(
                [isinstance(s, int)
                 and (s / min_g_shape == int(s / min_g_shape))
                 for s in seg]):
            raise AssertionError
        return Segmentation3D.from_tuple(seg)

    @computed_field(repr=False)
    @property
    def inner_grid_coordinates(self) -> ArrayInterfaces().ibo_array_type(3):
        return FiniteGrid.cls_grid_coordinates(
            self.pos, outer_shape=self.grid.shape.as_tuple(),
            grid_segmentation=self.grid.seg.as_tuple())

    @classmethod
    def limit_synapse_count(cls, n_synapses, n_neurons,
                            min0=2, max0=1000, max1_divider=4, ):
        n_synapses0 = int(min(max0, max(n_synapses, min0)))
        return min(n_synapses0, n_neurons // max1_divider)

    def model_post_init(self, __context):
        self.model_config['validate_assignment'] = False
        super().model_post_init(__context)

        n_neurons = self.N

        if self.S is None:
            self.S = self.calc_synapse_count(n_neurons=n_neurons, )
        self.type_groups = self.type_groups.generate_groups(
            n_neurons=n_neurons)

        if b_reset := (self.pos.shape[0] != n_neurons):

            self.reset_arrays(data=self)

        if b_reset is True:
            b_reset_synapses = True
        else:
            syn_shape = self.synapses.N_rep.data.shape
            b_reset_synapses = syn_shape != (n_neurons, self.S)

        if b_reset_synapses:
            self.synapses = SynapseModel.reset_model(
                self.synapses, n_neurons=n_neurons,
                n_delays=self.D, S=self.S, n_groups=self.G,
                ntypes=self.type_groups)

        self.L_Group_neuronCounts = LGNeuronCounts.from_shape(
            ntypes=self.type_groups, d=self.D, g=self.G)

        self.type_conns = self.type_conns.generate_conns(
            groups=self.type_groups, n_syn=self.S)

        self.model_config['validate_assignment'] = True
        self.model_validate(self)

    @property
    def n_type_groups(self):
        return len(self.type_groups.groups)

    @classmethod
    def reset_arrays(cls, data):

        n_neurons = get_attr_or_item(data, cls.Slots.N_NEURONS)
        type_groups: NTypeGroupList = get_attr_or_item(
            data, cls.Slots.TYPE_GROUPS)
        # type_groups = fill_field_default(
        #     data, cls, cls.Slots.TYPE_GROUPS,
        #     field_model=NTypeGroupList).generate_groups(n_neurons)

        grid = get_attr_or_item(data, cls.Slots.GRID)
        shape = grid.shape.as_tuple()

        set_attr_or_item(data, cls.Slots.N_DELAYS,
                         cls._calc_delay_count(n_neurons=n_neurons))
        n_delays = get_attr_or_item(data, cls.Slots.N_DELAYS)
        grid.seg = cls.generate_segmentation(n_delays, shape)
        seg: Segmentation3D = grid.seg

        set_attr_or_item(data, cls.Slots.N_LGROUPS, int(seg.prod()))

        pos_gen_mode = get_attr_or_item(data, cls.Slots.POS_GEN_MODE)

        pos, grid_coordinates = cls.generate_pos(
            mode=pos_gen_mode, shape=shape, n_neurons=n_neurons,
            grid_segmentation=seg.as_tuple(), type_groups=type_groups.groups)
        set_attr_or_item(data, cls.Slots.POS, pos)

        n_states = NeuronStateModel.reset_model(
            get_attr_or_item(data, cls.Slots.NEURON_STATES), n_neurons)
        set_attr_or_item(data, cls.Slots.NEURON_STATES, n_states)

        n_groups = get_attr_or_item(data, cls.Slots.N_LGROUPS)
        cls._reset_lg_array(data=data, class_=LGroupFlags, n_groups=n_groups,
                            slot=cls.Slots.L_GROUP_FLAGS)
        cls._reset_lg_array(data=data, class_=LGroupProps, n_groups=n_groups,
                            slot=cls.Slots.L_GROUP_PROPERTIES)
        cls._reset_lg_array(data=data, class_=LG2LGFlags, n_groups=n_groups,
                            slot=cls.Slots.L_GROUP2GROUP_FLAGS, )
        cls._reset_lg_array(data=data, class_=LG2LGProp, n_groups=n_groups,
                            slot=cls.Slots.L_GROUP2GROUP_PROPERTIES, )

    @staticmethod
    def _reset_lg_array(data, class_, slot, n_groups):
        value: TypedDataFrameModel = get_attr_or_item(data, slot)
        if isinstance(value, dict):
            obj: TypedDataFrameModel = class_(**value)
            value[TypedDataFrameModel.Slots.DATA] = obj.zeroes(n_cols=n_groups)
            obj.apply_index_init_values(
                data=value[TypedDataFrameModel.Slots.DATA])
        else:
            value.data = value.zeroes(n_cols=n_groups)
            value.apply_index_init_values()

    @classmethod
    def sort_pos(cls, pos: np.ndarray | None, shape, grid_segmentation,
                 type_groups: list[NeuronTypeGroup]):
        """
        Sort neuron positions w.r.t. location-based groups and neuron types.
        """
        grid_coordinates = FiniteGrid.cls_grid_coordinates(
                pos, outer_shape=shape,
                grid_segmentation=grid_segmentation)

        for g in type_groups:
            grid_pos = grid_coordinates[g.start_idx: g.end_idx + 1]

            p0 = grid_pos[:, 0].argsort(kind='stable')
            p1 = grid_pos[p0][:, 1].argsort(kind='stable')
            p2 = grid_pos[p0][p1][:, 2].argsort(kind='stable')

            grid_coordinates[g.start_idx: g.end_idx + 1] = grid_pos[p0][p1][p2]
            pos[g.start_idx: g.end_idx + 1] = \
                pos[g.start_idx: g.end_idx + 1][p0][p1][p2]
        return grid_coordinates

    @classmethod
    def _validate_model_before(cls, data: Any) -> Any:
        data = super()._validate_model_before(data)
        if isinstance(data, dict):
            fill_field_default(
                    data, cls, cls.Slots.TYPE_GROUPS,
                    field_model=NTypeGroupList)
            fill_field_default(
                    data, cls, cls.Slots.TYPE_CONNS,
                    field_model=NTypeGroupConnList)
        return data


if __name__ == '__main__':
    from pprint import pprint
    pprint(NetworkReservoirConfig())
