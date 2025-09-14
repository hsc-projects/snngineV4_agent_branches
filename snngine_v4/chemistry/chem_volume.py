from functools import cached_property
from typing import ClassVar

import numpy as np
from vispy import io

from snngine_v4.chemistry.chem_models import ChemicalConcentrationModel
from snngine_v4.construction.engine_element import EngineElement
from snngine_v4.geometry.grid.finite_grid import FiniteGrid
from snngine_v4.geometry.volume import LinkedVolumeGridConfig


class ChemicalConcentrationVolume(EngineElement):
    config_model: ChemicalConcentrationModel

    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        LinkedVolumeGridConfig: FiniteGrid,
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        init_data_cpu = np.zeros(
            self.config_model.shape.shape_wdh, dtype=np.float32)

        if self.config_model.b_test_init:
            init_data_cpu = self.test_data(init_data_cpu)

        self.init_data_cpu = init_data_cpu

        self.add_build(self.config_model.linked_grid_config,
                       parent_model=self.config_model,
                       b_default_build_kwargs=False)

    @staticmethod
    def test_data(data):
        arr = np.array(np.load(io.load_data_file('volume/stent.npz'))['arr_0'],
                       dtype=np.float32)
        if data is not None:
            max_x = min(data.shape[0], arr.shape[0])
            max_y = min(data.shape[1], arr.shape[1])
            max_z = min(data.shape[2], arr.shape[2])
            data[0: max_x, 0: max_y, 0: max_z] = (
                arr[0: max_x, 0: max_y, 0: max_z])
        else:
            data = arr
        assert len(data.shape) == 3
        data[:, :, -1] = 2000
        data[:, :, -2] = 1800
        data[:, :, -3] = 1800
        return data

    @cached_property
    def inner_grid(self) -> FiniteGrid:
        return self[self.config_model.linked_grid_config]
