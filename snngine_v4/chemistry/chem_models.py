from snngine_v4.construction.engine_element_config import \
    EngineElementConfigMixin
from snngine_v4.geometry.volume import VolumeConfig
from snngine_v4.utils.settings.config_model import (
    ConfigContainerModel,
)
from snngine_v4.visualization.config_models.visuals.parameters import (
    RGBAColorType,
)


class ChemicalConcentrationModel(VolumeConfig, EngineElementConfigMixin):

    # name: str = 'NULL'
    color: RGBAColorType = 'white'
    k_val: float = .16
    # k_val: float = Field(default=.16, gt=0., lt=1.)
    depreciation: float = 0.0

    b_test_init: bool = True


class ChemicalContainerModel(ConfigContainerModel, EngineElementConfigMixin):
    pass


class DefaultChemicals(ChemicalContainerModel):

    C0: ChemicalConcentrationModel
    C1: ChemicalConcentrationModel

    # def model_post_init(self, __context):
    #     self.C0.name = 'C0'
    #     self.C1.name = 'C1'
