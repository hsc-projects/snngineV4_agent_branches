from snngine_v4.geometry.spatial_pars import Object3DConfig
from snngine_v4.utils.data_utils.dataframe_config import TypedDataFrameBase


class EngineElementConfig(Object3DConfig):

    def tdf_dict(self, **kwargs):
        return self.filtered_model_dict(
            type_filter=TypedDataFrameBase, **kwargs)

    def tdf_values(self, **kwargs):
        return self.filtered_model_values(
            type_filter=TypedDataFrameBase, **kwargs)
