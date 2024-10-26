from enum import IntEnum, unique
from functools import cached_property
from typing import ClassVar

import numpy as np
from pydantic import Field, NonNegativeInt

from snngine_v4.geometry.grid.finite_grid import FiniteGrid
from snngine_v4.nn.config_models.n_type_groups import NeuronTypeGroupList
from snngine_v4.nn.config_models.nn_element_config import EngineElementConfig
from snngine_v4.geometry.spatial_pars import FloatShape3D, PositionVBO
from snngine_v4.utils.data.validation.array_annotation import ArrayInterfaces
from snngine_v4.utils.settings.ui_parameter_options import FrozenParamOpts


@unique
class PosGenerationMode(IntEnum):
    CUSTOM = 0
    RND_UNIFORM = 1


class NetworkReservoir(EngineElementConfig):

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        expanded=False,
        c_auto_collapse=True,
        c_collapsed_children=True,
    )

    N: NonNegativeInt = 200
    S: NonNegativeInt = 1
    D: int = Field(default=0, ge=0, le=20)

    pos_gen_mode: PosGenerationMode = PosGenerationMode.RND_UNIFORM

    reservoir_shape: FloatShape3D
    reservoir_segmentation: FloatShape3D

    type_groups: NeuronTypeGroupList

    pos: PositionVBO = Field(
        default_factory=lambda: np.array([
            [1.5, 1.5, 1.5],
            [1.5, 1.5, 0],
            [0, 1.5, 1.5],
            [1.5, 0, 1.5],
            [-1.5, 1.5, 1.5],
            [-1.5, 1.5, 0]],
            dtype=np.float32))
    # pos_grid_coord: ArrayInterfaces().ibo_array_type(3) | None

    def generate_pos(self):
        shape = self.reservoir_shape.as_tuple()
        match self.pos_gen_mode:
            case PosGenerationMode.RND_UNIFORM:
                pos = (np.random.rand(self.N, 3).astype(np.float32) * np.array(
                    shape, dtype=np.float32))
                pos[pos == max(shape)] = pos[pos == max(
                    shape)] * 0.999999
                FiniteGrid.validate_pos(pos, shape, self.N)
            case _:
                raise NotImplementedError
        # self.sort_pos(pos=pos)
        return pos

    def sort_pos(self, pos: np.ndarray | None):
        """
        Sort neuron positions w.r.t. location-based groups and neuron types.
        """
        grid_coordinates = FiniteGrid.cls_grid_coordinates(
                pos,
                outer_shape=self.reservoir_shape,
                grid_segmentation=self.reservoir_segmentation)

        for g in self.type_groups.groups:
            grid_pos = grid_coordinates[g.start_idx: g.end_idx + 1]

            p0 = grid_pos[:, 0].argsort(kind='stable')
            p1 = grid_pos[p0][:, 1].argsort(kind='stable')
            p2 = grid_pos[p0][p1][:, 2].argsort(kind='stable')

            grid_coordinates[g.start_idx: g.end_idx + 1] = grid_pos[p0][p1][p2]
            pos[g.start_idx: g.end_idx + 1] = \
                pos[g.start_idx: g.end_idx + 1][p0][p1][p2]
            # if len(pos) <= 100:
            #     print('\n', pos[g.start_idx:g.end_idx + 1])

        # if self.pos_grid_coord is None:
        #     self.pos_grid_coord = grid_coordinates

    @classmethod
    def _validate_model_after(cls, data):
        if isinstance(data, cls):
            data.type_groups.generate_groups(data.N)
            if len(data.pos) != data.N:
                data.pos = data.generate_pos()
        data = super()._validate_model_after(data)
        return data
