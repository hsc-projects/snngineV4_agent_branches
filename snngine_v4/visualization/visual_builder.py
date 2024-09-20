from typing import ClassVar

import numpy as np
from pydantic import BaseModel
from vispy.scene import Box, XYZAxis
from vispy.visuals import Visual

from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.geometry.spatial_pars import (
    AxDir3D, Directions3DBoolPars, FloatShape3D,
    Segmentation3D,
)
from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict,
    DictContainerConfig,
)
from snngine_v4.utils.core_utils import get_intenum_member
from snngine_v4.utils.object_builder.object_builder_dict import BuilderDict
from snngine_v4.utils.settings.settings_keywords import InternalOpts
from snngine_v4.visualization.config_models.vispy_visual_parameters import (
    OpenGLState, OpenGlStateType,
    RGBAColor, WDHKw,
    WDHSegKw,
)
from snngine_v4.visualization.config_models.visual_configs import (
    BoxVisualConfig, OuterGridVisualConfig, XYZAxisVisualConfig,
)


class VispyVisualManager(BuilderDict):

    VISPY_VISUAL_DUMP_KW: ClassVar[str] = 'vispy'

    POS_KW: ClassVar[str] = 'pos'
    COLOR_KW: ClassVar[str] = 'color'

    BUILDER_DEFAULT_MODEL_CLASS: ClassVar = None
    BUILDER_DEFAULT_OBJECT_CLASS: ClassVar = None

    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        BoxVisualConfig: Box,
        FiniteGridConfig: Box,
        OuterGridVisualConfig: Box,
        XYZAxisVisualConfig: XYZAxis,
    }

    @classmethod
    def ax_dir_aliases(cls, member):
        member = get_intenum_member(member, AxDir3D)
        match member:
            case AxDir3D.XP:
                return '+x'
            case AxDir3D.XM:
                return '-x'
            case AxDir3D.YP:
                return '+y'
            case AxDir3D.YM:
                return '-y'
            case AxDir3D.ZP:
                return '+z'
            case AxDir3D.ZM:
                return '-z'

    @classmethod
    def _convert_to_vispy(cls, dct, model: BaseModel):
        res = ConfigurableDict(
            container_conf=DictContainerConfig(
                b_duplicates_allowed=True
            )
        )

        dct.pop(InternalOpts.Slots.TECHNICAL, None)

        if isinstance(dct, dict):

            if isinstance(model, XYZAxisVisualConfig):
                if dct.get(cls.POS_KW, None) is None:
                    dct[cls.POS_KW] = np.array([
                        [0, 0, 0],
                        [1, 0, 0],
                        [0, 0, 0],
                        [0, 1, 0],
                        [0, 0, 0],
                        [0, 0, 1]])
                if dct.get(cls.COLOR_KW, None) is None:
                    dct[cls.COLOR_KW] = np.array([
                        [1, 0, 0, 1],
                        [1, 0, 0, 1],
                        [0, 1, 0, 1],
                        [0, 1, 0, 1],
                        [0, 0, 1, 1],
                        [0, 0, 1, 1]])

            up_keys = {}
            for k, dump_value_ in dct.items():
                model_ = getattr(model, k)
                if isinstance(model_, FloatShape3D):
                    up_keys[k] = WDHKw.convert_dict(dump_value_)
                elif isinstance(model_, Segmentation3D):
                    up_keys[k] = WDHSegKw.convert_dict(dump_value_)
                elif isinstance(model_, RGBAColor):
                    dct[k] = tuple(dump_value_.values())
                elif isinstance(model_, Directions3DBoolPars):
                    vals = list(dump_value_.keys())
                    vals = [cls.ax_dir_aliases(x) for x in vals]
                    dct[k] = tuple(vals)

            for k in up_keys:
                dct.pop(k)
                res.update(up_keys[k])
            res.update(dct)

        return res.data

    @classmethod
    def get_model(cls, model: BaseModel | None):
        dump = model.model_dump(mode='python')
        if isinstance(model, FiniteGridConfig):
            model = OuterGridVisualConfig(**dump)
        return super().get_model(model=model)

    @classmethod
    def make_object_kwargs(cls, model: BaseModel, **kwargs):
        object_kwargs = super().make_object_kwargs(model=model)
        object_kwargs = cls._convert_to_vispy(object_kwargs, model=model)
        object_kwargs.update(**kwargs)
        return object_kwargs

    @classmethod
    def make_object(cls, object_class, model, **object_kwargs):

        opengl_kwargs = cls._pop_opengl_kwargs(dct=object_kwargs, model=model)

        visual: Visual = super().make_object(
            object_class=object_class, model=model, **object_kwargs,)

        if len(opengl_kwargs) > 0:
            cls.apply_open_gl_kwargs(visual, opengl_kwargs)

        return visual

    @classmethod
    def _pop_opengl_kwargs(cls, dct, model: BaseModel):
        res = ConfigurableDict()
        for k, v in dct.items():
            if hasattr(model, k):
                model_ = getattr(model, k)
                if isinstance(model_, OpenGLState):
                    res[k] = v
        for k in res:
            dct.pop(k)
        return res

    @classmethod
    def apply_open_gl_kwargs(
        cls, visual: Visual, opengl_kwargs,
            state_type: OpenGlStateType | None = None
    ):
        if state_type is None:
            cls.apply_open_gl_kwargs(visual, opengl_kwargs,
                                     state_type=OpenGlStateType.SET)
            cls.apply_open_gl_kwargs(visual, opengl_kwargs,
                                     state_type=OpenGlStateType.UPDATE)
        else:
            for k, kwargs in opengl_kwargs.items():
                if kwargs.pop(OpenGLState.Slots.STATE_TYPE, None) == state_type:
                    if ((k_ := kwargs.pop(OpenGLState.Slots.ATTRIBUTE_KEY))
                            is not None):
                        k = k_
                    attr: Visual = getattr(visual, k)

                    match state_type:
                        case OpenGlStateType.SET:
                            attr.set_gl_state(**kwargs)
                        case OpenGlStateType.UPDATE:
                            attr.update_gl_state(**kwargs)
                        case _:
                            raise NotImplementedError(f"{state_type}")
