from typing import ClassVar

from pydantic import BaseModel
from vispy.scene import Box, Cube
from vispy.visuals import BoxVisual, Visual

from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.utils.settings.object_builder import (
    BuilderDict,
)
from snngine_v4.utils.settings.settings_keywords import ParamOpts
from snngine_v4.visualization.config_models.visual_configs import (
    BoxVisualConfig, VispyVisualConfig,
)


class VispyVisualBuilder(BuilderDict):

    BUILDER_DEFAULT_MODEL_CLASS: ClassVar = None
    BUILDER_DEFAULT_OBJECT_CLASS: ClassVar = None

    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        BoxVisualConfig: Box,
        FiniteGridConfig: Box,
    }

    @classmethod
    def make_object_kwargs(cls, model: BaseModel, **kwargs):
        dump = model.model_dump(mode='python')

        if isinstance(model, FiniteGridConfig):
            model = BoxVisualConfig(**dump)

        # dump = model.model_dump(mode=VispyVisualConfig.VISPY_VISUAL_DUMP)
        dump = model.model_dump(mode='python')
        dump = ParamOpts.pop_ui_options_keyword(dump)

        object_kwargs = VispyVisualConfig.convert_to_vispy(dump, model=model)

        object_kwargs.update(**kwargs)
        return object_kwargs

    @classmethod
    def make_object(cls, object_class, **object_kwargs):

        visual: Visual = object_class(**object_kwargs)

        return visual
