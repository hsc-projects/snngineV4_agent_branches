from enum import IntEnum, unique
from functools import cached_property
from typing import Any, ClassVar

import numpy as np

from pydantic import computed_field, Field, NonNegativeInt

from snngine_v4.geometry.grid.finite_grid import FiniteGrid
from snngine_v4.nn.config_models.n_type_groups import (
    NeuronType, NeuronTypeGroup,
    NTypeGroupConn, NTypeGroupConnInit, NTypeGroupConnList,
    NTypeGroupList,
)
from snngine_v4.nn.config_models.nn_element_config import EngineElementConfig
from snngine_v4.geometry.spatial_pars import FloatShape3D, PositionVBO
from snngine_v4.utils.data.validation.array_annotation import (
    ArrayInterfaces, fill_array_field_default,
)
from snngine_v4.utils.field_utils import fill_field_default

from snngine_v4.utils.settings.ui_parameter_options import FrozenParamOpts


@unique
class PosGenerationMode(IntEnum):
    CUSTOM = 0
    RND_UNIFORM = 1


class NetworkReservoir(EngineElementConfig):

    class Slots:
        N_NEURONS: ClassVar[str] = 'N'
        N_SYNAPSES: ClassVar[str] = 'S'
        N_DELAYS: ClassVar[str] = 'D'
        POS: ClassVar[str] = 'pos'
        POS_GEN_MODE: ClassVar[str] = 'pos_gen_mode'
        SHAPE: ClassVar[str] = 'reservoir_shape'
        SEG: ClassVar[str] = 'reservoir_segmentation'
        TYPE_GROUPS: ClassVar[str] = 'type_groups'
        TYPE_CONNS: ClassVar[str] = 'type_conns'

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        expanded=False,
        c_auto_collapse=True,
        c_collapsed_children=True)

    N: NonNegativeInt = 200
    S: NonNegativeInt = 1
    D: NonNegativeInt = Field(default=0, le=20)

    pos_gen_mode: PosGenerationMode = PosGenerationMode.RND_UNIFORM
    reservoir_shape: FloatShape3D
    reservoir_segmentation: FloatShape3D

    type_groups: NTypeGroupList = Field(
        default_factory=lambda: NTypeGroupList(
            groups=[NeuronType.INHIBITORY, NeuronType.EXCITATORY]))

    type_conns: NTypeGroupConnList = Field(
        default_factory=lambda: NTypeGroupConnList(
            conns=[NTypeGroupConnInit(src=0, snk=1, w0=-.44),
                   NTypeGroupConnInit(src=1, snk=0, w0=.45),
                   NTypeGroupConnInit(src=1, snk=1, w0=.47), ]))

    pos: PositionVBO = Field(
        default_factory=lambda: np.array([
            [1.5, 1.5, 1.5],
            [1.5, 1.5, 0],
            [0, 1.5, 1.5],
            [1.5, 0, 1.5],
            [-1.5, 1.5, 1.5],
            [-1.5, 1.5, 0]],
            dtype=np.float32))

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
            # if len(pos) <= 100:
            #     print('\n', pos[g.start_idx:g.end_idx + 1])
        return grid_coordinates
        # if self.pos_grid_coord is None:
        #     self.pos_grid_coord = grid_coordinates

    @classmethod
    def _validate_model_before(cls, data: Any) -> Any:
        super()._validate_model_before(data)

        if isinstance(data, dict):
            n_neurons = fill_field_default(data, cls, cls.Slots.N_NEURONS)
            pos = fill_array_field_default(data, cls, cls.Slots.POS)

            type_groups = fill_field_default(
                data, cls, cls.Slots.TYPE_GROUPS,
                field_model=NTypeGroupList).generate_groups(n_neurons)

            if pos.shape[0] != n_neurons:
                pos_gen_mode = fill_field_default(
                    data, cls, cls.Slots.POS_GEN_MODE)
                shape = fill_field_default(
                    data, cls, cls.Slots.SHAPE,
                    field_model=FloatShape3D).as_tuple()
                seg = fill_field_default(data, cls, cls.Slots.SEG,
                                         field_model=FloatShape3D).as_tuple()

                data[cls.Slots.POS], grid_coordinates = cls.generate_pos(
                    mode=pos_gen_mode, shape=shape, n_neurons=n_neurons,
                    grid_segmentation=seg, type_groups=type_groups.groups)

            n_syn = fill_field_default(data, cls, cls.Slots.N_SYNAPSES)
            type_conns = fill_field_default(
                data, cls, cls.Slots.TYPE_CONNS,
                field_model=NTypeGroupConnList).generate_conns(
                groups=type_groups, n_syn=n_syn)

        return data

    @computed_field
    @property
    def inner_grid_coordinates(self) -> ArrayInterfaces().ibo_array_type(3):
        return FiniteGrid.cls_grid_coordinates(
            self.pos, outer_shape=self.reservoir_shape.as_tuple(),
            grid_segmentation=self.reservoir_segmentation.as_tuple())


    # @classmethod
    # def _validate_model_after(cls, data):
    #     if isinstance(data, cls):
    #         data.type_groups.generate_groups(data.N)
    #         if len(data.pos) != data.N:
    #             data.pos = data.generate_pos(
    #                 n
    #             )
    #     data = super()._validate_model_after(data)
    #     return data
