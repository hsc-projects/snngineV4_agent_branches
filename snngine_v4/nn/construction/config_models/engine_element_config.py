from typing import ClassVar

from snngine_v4.geometry.spatial_pars import (
    Object3DConfig
)
from snngine_v4.utils.data_utils.dataframe_config import (
    SeriesModel, TypedDataFrameModel,
)
from snngine_v4.utils.settings.config_model import ConfigModel


class EngineElementConfigMixin:
    def elt_dict(self: ConfigModel, **kwargs):
        return self.filtered_model_dict(
            type_filter=EngineElementConfig, **kwargs)

    def elt_values(self: ConfigModel, **kwargs):
        return self.filtered_model_values(
            type_filter=EngineElementConfig, **kwargs)

    def tdf_dict(self: ConfigModel, **kwargs):
        return self.filtered_model_dict(
            type_filter=SeriesModel, **kwargs)

    def tdf_values(self: ConfigModel, **kwargs):
        return self.filtered_model_values(
            type_filter=SeriesModel, **kwargs)


class EngineElementConfig(ConfigModel, EngineElementConfigMixin):

    class Slots:
        INITIALIZER: ClassVar[str] = 'initializer'

    @staticmethod
    def reset_array(model, class_=None, slot=None, n_indices=None, n_cols=None):

        if isinstance(n_indices, tuple) and n_cols is None:
            if len(n_indices) != 2:
                raise ValueError('n_indices as shape must have length 2')
            n_indices, n_cols = n_indices

        if slot is not None:
            value = getattr(model, slot)
        else:
            value = model
        if isinstance(value, dict):
            obj = class_(**value)
            value[TypedDataFrameModel.Slots.DATA] = obj.zeroes(
                n_indices=n_indices, n_cols=n_cols, )
        else:
            value.data = value.zeroes(n_cols=n_cols, n_indices=n_indices)


class EngineElementConfig3D(EngineElementConfig, Object3DConfig):
    pass


if __name__ == '__main__':
    from pprint import pprint
    pprint(EngineElementConfig3D().model_dump())
