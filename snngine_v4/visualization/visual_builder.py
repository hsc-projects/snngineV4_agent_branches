from __future__ import annotations

from typing import Any, Callable, ClassVar, Set, Type

import numpy as np
from pydantic import BaseModel
from vispy.gloo import get_current_canvas
from vispy.scene import Box, Markers, VisualNode, XYZAxis
from vispy.util.event import EmitterGroup
from vispy.visuals import CompoundVisual, MarkersVisual, MeshVisual, Visual

from snngine_v4.geometry.grid_config import FiniteGridConfig
from snngine_v4.geometry.spatial_pars import (
    AxDir3D, Directions3DBoolPars, FloatShape3D,
    Segmentation3D,
)
from snngine_v4.nn.config_models.nn_reservoir_config import NetworkReservoir
from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict,
    DictContainerConfig,
)
from snngine_v4.utils.class_mixer import ClassMixer
from snngine_v4.utils.field_utils import model_keys, Undefined
from snngine_v4.utils.object_builder.object_builder_dict import BuilderDict
from snngine_v4.utils.settings.settings_keywords import (
    BaseModelSlots,
    InternalOpts,
)

from snngine_v4.visualization.config_models.visuals.markers import \
    MarkersVisualConfig

from snngine_v4.visualization.config_models.visuals.parameters import (
    OpenGLState, OpenGlStateType,
    RGBAColor, VispyKeyWords, WDHKw,
    WDHSegKw,
)
from snngine_v4.visualization.config_models.visuals.lines import (
    XYZAxisVisualConfig,
)
from snngine_v4.visualization.config_models.visuals.boxes import (
    BoxVisualInitConfig, OuterGridVisualInitConfig,
)
from snngine_v4.visualization.scenes.setattribute_event import (
    MeshDataChangedEvent, SetAttributeEvent,
)


class EmitterMap(ConfigurableDict):

    class ContainerConfigClass(DictContainerConfig):
        allowed_types: Any = Callable | ConfigurableDict
        allowed_key_types: Any = str | int
        b_duplicates_allowed: bool = True

    def __init__(self, events: EmitterGroup, keys, **kwargs):
        self.events = events
        super().__init__(**kwargs)
        self.set_items(*keys)

    def __call__(self, key, value):
        try:
            self[key](key=key, value=value)
            return
        except KeyError:
            pass

    def set_items(self, *keys):
        for key in keys:
            self[key] = self.events.attr_changed


class VisualMixin:

    SET_DATA_KWS = {
        Box: [VispyKeyWords.COLOR],
        Markers: [VispyKeyWords.POS,
                  VispyKeyWords.EDGE_COLOR,
                  VispyKeyWords.FACE_COLOR,
                  VispyKeyWords.SIZE,
                  VispyKeyWords.EDGE_WIDTH,
                  ],
        XYZAxis: [VispyKeyWords.COLOR,
                  VispyKeyWords.POS,
                  VispyKeyWords.CONNECT,
                  'width'],
        MeshVisual: ['vertices', 'faces',
                     VispyKeyWords.VERTEX_COLORS,
                     VispyKeyWords.FACE_COLORS,
                     'vertex_values',
                     'meshdata']
    }

    attr_changed_keys: ClassVar[Set[str]] = set()

    def __pre_init__(self, *args, **kwargs):
        object.__setattr__(self, "emitter_map", None)
        self._initialized = True
        self._compound_post_init_called = False
        # self.emitter_map = None

    def mesh_data_changed(self: MeshVisual):
        MeshVisual.mesh_data_changed(self)
        print('mesh_data_changed', id(self))
        self.events.mesh_data_changed(instance=self, data=self._meshdata)

    def __post_init__(self: VisualMixin | Visual):
        self.events.add(
            auto_connect=False,
            attr_changed=SetAttributeEvent)
        self.emitter_map = EmitterMap(self.events, keys=self.attr_changed_keys)

        def connect_mesh_data_changed(v_):
            v_.mesh_data_changed = lambda: VisualMixin.mesh_data_changed(v_)

        # if isinstance(self, MarkersVisual):
        #     self.events.add(
        #         auto_connect=False,
        #         attr_changed=SetAttributeEvent)

        if isinstance(self, CompoundVisual):
            for i, v in enumerate(self._subvisuals):
                v: Visual
                if isinstance(v, MeshVisual):
                    v.events.add(
                        auto_connect=False,
                        attr_changed=SetAttributeEvent,
                        mesh_data_changed=MeshDataChangedEvent)
                    print('build MeshVisual', id(v))
                    connect_mesh_data_changed(v)
                # mesh_data: MeshData = v.mesh_data
                # new_v: MeshVisual = VisualMixins()
                # .mix(class_item=v.__class__)(
                #     vertices=mesh_data.get_vertices(indexed=mesh_data.),
                #     faces=None, vertex_colors=None,
                #     face_colors=None, color=(0.5, 0.5, 1, 1),
                #     vertex_values=None,
                #     meshdata=None, shading=None, mode='triangles'
                # )
                # self.remove_subvisual(v)


class VisualMixins(ClassMixer):
    Mixins: ClassVar = VisualMixin

    @classmethod
    def mix(cls, class_item: Type, name=None, attr_changed_keys=Undefined):

        if issubclass(class_item, (VisualNode, )):
            if class_item == XYZAxis:
                # set_data_kw = VisualMixin.SET_DATA_KWS[XYZAxis]
                # attr_changed_keys = [
                #     x for x in XYZAxisVisualConfig.model_fields.keys()
                #     if x not in set_data_kw]
                attr_changed_keys = model_keys(
                    XYZAxisVisualConfig, exclude=BaseModelSlots.CLASS__NAME)
            elif class_item == Box:
                attr_changed_keys = {'_mesh': ['shading']}
            elif class_item == MeshVisual:
                attr_changed_keys = ['color']
            elif class_item == Markers:
                attr_changed_keys = (
                    ['alpha'] +
                    model_keys(MarkersVisualConfig,
                               exclude=BaseModelSlots.CLASS__NAME))
            else:
                raise NotImplementedError()

            def init(self: VisualMixin | Visual, *args, **kwargs_):
                self.__pre_init__(*args, **kwargs_)
                class_item.__init__(self, *args, **kwargs_)
                self.__post_init__()

            def set_attr(self: VisualMixin | Visual, key, value):
                class_item.__setattr__(self, key, value)
                if self._initialized and self.emitter_map:
                    self.emitter_map.__call__(key, value)

            kwargs = dict(__init__=init,
                          __setattr__=set_attr,
                          attr_changed_keys=attr_changed_keys)

            new = super().mix(class_item, name, **kwargs)

            VisualMixin.SET_DATA_KWS[new] = VisualMixin.SET_DATA_KWS[class_item]

            return new
        else:
            raise AssertionError
            # return class_item


class VispyVisualBuilder(BuilderDict):

    VISPY_VISUAL_DUMP_KW: ClassVar[str] = 'vispy'

    POS_KW: ClassVar[str] = 'pos'
    COLOR_KW: ClassVar[str] = 'color'
    SUBVISUALS_KW: ClassVar[str] = 'subvisuals'

    BUILDER_DEFAULT_MODEL_CLASS: ClassVar = None
    BUILDER_DEFAULT_OBJECT_CLASS: ClassVar = None
    BUILDER_OBJECT_CLASS_MIXER: ClassVar = VisualMixins

    BUILDER_OBJECT_CLASS_MAP: ClassVar = {
        BoxVisualInitConfig: Box,
        FiniteGridConfig: Box,
        OuterGridVisualInitConfig: Box,
        XYZAxisVisualConfig: XYZAxis,
        MarkersVisualConfig: Markers,
        NetworkReservoir: Markers,
    }

    @classmethod
    def _convert_to_vispy(cls, dct, model: BaseModel):
        res = ConfigurableDict(
            container_conf=DictContainerConfig(
                b_duplicates_allowed=True
            )
        )

        dct.pop(InternalOpts.Slots.TECHNICAL, None)
        subvisuals = dct.pop(cls.SUBVISUALS_KW, None)
        if subvisuals and len(subvisuals) > 0:
            raise NotImplementedError

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
                    dct[k] = RGBAColor.to_vispy(dump_value_)
                elif isinstance(model_, Directions3DBoolPars):
                    vals = list(dump_value_.keys())
                    vals = [AxDir3D.vispy_name_alias(x) for x in vals]
                    dct[k] = tuple(vals)

            for k in up_keys:
                dct.pop(k)
                res.update(up_keys[k])
            res.update(dct)

        return res.data

    @classmethod
    def get_model(cls, model: BaseModel | None):
        dump = model.model_dump(mode='python',
                                exclude={BaseModelSlots.CLASS__NAME})
        if isinstance(model, FiniteGridConfig):
            model = OuterGridVisualInitConfig(**dump)
        elif isinstance(model, NetworkReservoir):
            model = MarkersVisualConfig()
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
